"""Collect EMA scene-context endpoints on fixed native GT and protected GFX inputs."""

import argparse
import math
import os
import time
from pathlib import Path

import numpy as np
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import color_indices, pack
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.io import read_raw
from demosaic.metrics import quality_metrics
from demosaic.models import load_model
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.scene_inference import load_scene_checkpoint
from demosaic.scene_restoration import WholeSceneRestorer


@torch.inference_mode()
def collect(plan_path, arm):
    plan = read_json(plan_path)
    assert reference(__file__) == plan["script"]
    for path, digest in plan["sources"].items():
        checked({"path": path, "sha256": digest})
    os.sched_setaffinity(0, [8, 9])
    os.nice(10)
    torch.set_num_threads(2)
    root = Path(plan["root"])
    training = read_json(checked(plan["training_plan"]))
    endpoint = None
    if arm == "parent":
        base, _ = load_model("v120", checkpoint=checked(plan["parent"]), device="cpu")
        model = WholeSceneRestorer(base, mode="none", adapter_width=training["adapter_width"])
    else:
        terminal = read_json(Path(training["work"]) / "artifacts/train" / arm / "completed.json")
        assert terminal["steps"] == training["steps"] == 2000 and terminal["DINO_unchanged"]
        assert terminal["plan"] == plan["training_plan"]
        endpoint = terminal["checkpoints"][-1]
        model, state = load_scene_checkpoint(
            checked(endpoint), weights="ema", expected_sha256=endpoint["sha256"]
        )
        assert state["step"] == 2000 and model.mode == arm
        del state
    model.eval().to(memory_format=torch.contiguous_format)
    assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
    output = root / arm
    output.mkdir()
    counts = {"root": 0, "encoder": 0}
    hooks = [
        model.register_forward_pre_hook(lambda *_, c=counts: c.__setitem__("root", c["root"] + 1)),
        model.base.context.backbone.register_forward_pre_hook(
            lambda *_, c=counts: c.__setitem__("encoder", c["encoder"] + 1)
        ),
    ]
    encoded, records, full_observations, real_sources = {}, [], {}, {}
    began = time.monotonic()
    with ieee_fp32():
        for observation in plan["observations"]:
            with np.load(checked(observation["arrays"]), allow_pickle=False) as data:
                arrays = {k: torch.from_numpy(data[k].copy()) for k in data.files}
            development = observation["kind"] == "development"
            args = {
                k: arrays[("crop_" if development else "") + k]
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            }
            noise = observation["noise"]
            model.base.set_noise(noise["shot"], noise["read"])
            scene, box = None, None
            if model.mode != "none":
                if development:
                    scene = model.encode_scene(
                        arrays["scene_packed"],
                        args["colors"][0],
                        args["wb"][0],
                        args["matrix"][0],
                        long_side=plan["preview_long_side"],
                        exposure=plan["preview_exposure"],
                    )
                    box = observation["boxes_xywh"]
                else:
                    family = "main" if observation["kind"] == "gfx" else "mesh"
                    if family not in encoded:
                        config = read_json(checked(plan[family + "_full_RAW"]))
                        raw_source = (
                            (Path.cwd() / config["noisy"])
                            if family == "main"
                            else checked(config["sources"]["noisy"])
                        )
                        raw, meta = read_raw(raw_source)
                        real_sources[family] = reference(raw_source)
                        assert meta.pattern == "RGGB"
                        torch.testing.assert_close(
                            torch.tensor(meta.white_balance), args["wb"][0], atol=0, rtol=0
                        )
                        torch.testing.assert_close(
                            torch.tensor(meta.camera_to_srgb), args["matrix"][0], atol=0, rtol=0
                        )
                        full = torch.from_numpy(raw)
                        full_observations[family] = full
                        encoded[family] = model.encode_scene(
                            pack(full[None, None])[0],
                            color_indices(meta.pattern),
                            args["wb"][0],
                            args["matrix"][0],
                            long_side=plan["preview_long_side"],
                            exposure=plan["preview_exposure"],
                        )
                        del full, raw
                    scene = encoded[family]
                    box = [
                        observation["metadata"]["context_xywh"]
                        if family == "main"
                        else [600, 6260, 768, 768]
                    ]
                    x, y, w, h = box[0]
                    torch.testing.assert_close(
                        pack(full_observations[family][None, None, y : y + h, x : x + w]),
                        args["packed"],
                        atol=0,
                        rtol=0,
                    )
            t = time.monotonic()
            prediction = model(
                *(args[k] for k in ["packed", "variance", "colors", "wb", "matrix"]),
                scene=scene,
                boxes_xywh=box,
            )
            inference_seconds = time.monotonic() - t
            assert tuple(prediction.shape) == (
                (4, 3, 256, 256) if development else tuple(observation["output_shape"])
            )
            path = output / (observation["id"] + "-RGB-f32.npy")
            with path.open("xb") as stream:
                np.save(stream, prediction.numpy(), allow_pickle=False)
            metrics = None
            if development:
                metrics = {
                    k: [float(x) if math.isfinite(float(x)) else None for x in v.detach().cpu()]
                    for k, v in quality_metrics(
                        prediction[..., 8:-8, 8:-8],
                        arrays["crop_target"][..., 8:-8, 8:-8],
                        args["wb"],
                        args["matrix"],
                    ).items()
                }
            records.append(
                {
                    "id": observation["id"],
                    "prediction": reference(path),
                    "input_fingerprints": {k: fingerprint(v) for k, v in args.items()},
                    "inference_seconds": inference_seconds,
                    "metrics": metrics,
                    "scene_box_xywh": box,
                }
            )
            print(arm, observation["id"], inference_seconds, flush=True)
    for hook in hooks:
        hook.remove()
    assert counts["root"] == 10
    assert counts["encoder"] == (16 if model.mode != "none" else 10)
    write_json(
        output / "collection.json",
        {
            "plan": reference(plan_path),
            "arm": arm,
            "checkpoint": endpoint or plan["parent"],
            "weights": "EMA",
            "mode": model.mode,
            "counts": counts,
            "seconds": time.monotonic() - began,
            "records": records,
            "DINO_unchanged": model_hash(model.base.context.backbone) == plan["DINO_sha256"],
            "full_real_noisy_sources": real_sources,
            "scope": "Native development and protected GFX collection complete, actual viewing and broad panels separate. CPU IEEE FP32 contiguous B4 development/B1 real, one scene encoding per noisy development field or real capture. No original spinning-drive media, reference context, optimizer or new real noise. Native512 main and768 mesh predictions remain native, no resizing.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("arm", choices=["parent", "none", "pooled", "spatial"])
    args = parser.parse_args()
    collect(args.plan, args.arm)
