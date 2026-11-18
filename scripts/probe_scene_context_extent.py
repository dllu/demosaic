"""Separate nearby preview information from distant scene context with fixed RAW tiles."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import torch
from profile_raw_kernel_inference import model_hash
from scipy.ndimage import gaussian_filter
from torch.nn import functional as F

from demosaic.cfa import pack
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.io import read_raw
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.scene_context import scene_preview
from demosaic.scene_inference import load_scene_checkpoint
from demosaic.scene_restoration import EncodedScene

ARGUMENTS = ("packed", "variance", "colors", "wb", "matrix")


def prepare(root, earlier):
    baseline = earlier / "spatial/collection.json"
    original = earlier / "plan.json"
    prior = read_json(baseline)
    assert prior["plan"] == reference(original) and prior["weights"] == "EMA"
    root.mkdir()
    work, files = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "inputs": [reference(original), reference(baseline)],
            "frozen_files": files,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "original": reference(original),
            "baseline": reference(baseline),
            "preview_sigma": 24,
            "preview_halo": 16,
            "preview_transition": 16,
            "scope": "All 10 existing spatial native observations, no quality-based selection. "
            "Compare full baseline, blurred distant areas and blurred protected near areas of its scene preview. "
            "These are input interventions on the ordinary full-RAW model.",
        },
    )


def near_weight(grid, boxes, halo, transition):
    height, width = grid.preview_hw
    nh, nw = grid.native_hw
    yy, xx = np.ogrid[:height, :width]
    distance = np.full((height, width), np.inf)
    for x, y, w, h in boxes:
        # Include the complete projected tile with a halo. A cosine transition
        # keeps the interventions from adding a hard edge at the footprint.
        dx = np.maximum(np.maximum(x * width / nw - xx - 1, xx - (x + w) * width / nw), 0)
        dy = np.maximum(np.maximum(y * height / nh - yy - 1, yy - (y + h) * height / nh), 0)
        distance = np.minimum(distance, np.hypot(dx, dy))
    phase = np.clip((distance - halo) / transition, 0, 1)
    return torch.from_numpy((0.5 + 0.5 * np.cos(np.pi * phase)).astype(np.float32))


def encode(model, preview, grid):
    height, width = grid.preview_hw
    ph, pw = grid.padded_hw
    padded = F.pad(preview, (0, pw - width, 0, ph - height), mode="replicate")
    context = model.base.context
    encoded = context.backbone(
        pixel_values=(padded - context.mean) / context.std, output_hidden_states=True
    )
    return EncodedScene(tuple(encoded.hidden_states[1:]), grid)


def observation(path, development):
    prefix = "crop_" if development else ""
    with np.load(checked(path), allow_pickle=False) as arrays:
        args = {key: torch.from_numpy(arrays[prefix + key].copy()) for key in ARGUMENTS}
        complete = torch.from_numpy(arrays["scene_packed"].copy()) if development else None
    return args, complete


@torch.inference_mode()
def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    old_plan = read_json(checked(plan["original"]))
    baseline = read_json(checked(plan["baseline"]))
    root = Path(plan["root"])
    model, payload = load_scene_checkpoint(
        checked(baseline["checkpoint"]),
        weights="ema",
        expected_sha256=baseline["checkpoint"]["sha256"],
    )
    assert model.mode == "spatial" and payload["step"] == 2000
    del payload
    model.eval().to(memory_format=torch.contiguous_format)
    assert model_hash(model.base.context.backbone) == old_plan["DINO_sha256"]
    output = root / "predictions"
    output.mkdir()
    cached = {}
    rows = []
    start = time.monotonic()
    with ieee_fp32():
        for declared, old in zip(old_plan["observations"], baseline["records"], strict=True):
            key = declared["id"]
            assert key == old["id"]
            development = declared["kind"] == "development"
            args, complete = observation(declared["arrays"], development)
            assert {k: fingerprint(v) for k, v in args.items()} == old["input_fingerprints"]
            boxes = old["scene_box_xywh"]
            if development:
                for packed, (x, y, w, h) in zip(args["packed"], boxes, strict=True):
                    torch.testing.assert_close(
                        complete[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
                        packed,
                        atol=0,
                        rtol=0,
                    )
            else:
                family = "main" if declared["kind"] == "gfx" else "mesh"
                if family not in cached:
                    ref = baseline["full_real_noisy_sources"][family]
                    source = checked(ref)
                    assert source.parent.name == "gfx-qualitative-20231231"
                    raw, metadata = read_raw(source)
                    assert metadata.pattern == "RGGB"
                    cached[family] = torch.from_numpy(raw)
                full = cached[family]
                ((x, y, w, h),) = boxes
                torch.testing.assert_close(
                    pack(full[None, None, y : y + h, x : x + w]), args["packed"], atol=0, rtol=0
                )
                complete = pack(full[None, None])[0]
            preview, grid = scene_preview(
                complete,
                args["colors"][0],
                args["wb"][0],
                args["matrix"][0],
                long_side=old_plan["preview_long_side"],
                exposure=old_plan["preview_exposure"],
            )
            del complete
            weight = near_weight(grid, boxes, plan["preview_halo"], plan["preview_transition"])
            blurred = torch.from_numpy(
                gaussian_filter(
                    preview.numpy(),
                    (0, 0, plan["preview_sigma"], plan["preview_sigma"]),
                    mode="reflect",
                )
            )
            near, distant = weight == 1, weight == 0
            assert near.any() and distant.any()
            model.base.set_noise(declared["noise"]["shot"], declared["noise"]["read"])
            protected = torch.lerp(blurred, preview, weight)
            removed = torch.lerp(preview, blurred, weight)
            protected[..., near] = preview[..., near]
            removed[..., distant] = preview[..., distant]
            interventions = {"full": preview, "blur-distant": protected, "blur-near": removed}
            predictions, inputs = {}, {}
            for arm, p in interventions.items():
                field = encode(model, p, grid)
                prediction = model(*args.values(), scene=field, boxes_xywh=boxes)
                assert torch.isfinite(prediction).all()
                if arm == "full":
                    torch.testing.assert_close(
                        prediction,
                        torch.from_numpy(np.load(checked(old["prediction"]))),
                        rtol=0,
                        atol=0,
                    )
                    predictions[arm] = old["prediction"]
                else:
                    file = output / f"{key}-{arm}.npy"
                    with file.open("xb") as stream:
                        np.save(stream, prediction.numpy(), allow_pickle=False)
                    predictions[arm] = reference(file)
                inputs[arm] = fingerprint(p)
            assert {k: fingerprint(v) for k, v in args.items()} == old["input_fingerprints"]
            row = {
                "case": key,
                "prediction": predictions,
                "local_inputs": old["input_fingerprints"],
                "preview": inputs,
                "preview_hw": grid.preview_hw,
                "native_boxes_xywh": boxes,
                "near_fraction": float(near.float().mean()),
                "distant_fraction": float(distant.float().mean()),
                "protected_preview_exact": bool(
                    torch.equal(protected[..., near], preview[..., near])
                ),
                "distant_preview_exact": bool(
                    torch.equal(removed[..., distant], preview[..., distant])
                ),
            }
            assert row["protected_preview_exact"] and row["distant_preview_exact"]
            rows.append(row)
            write_json(output / f"{key}.json", row)
            print(len(rows), key, round(time.monotonic() - start, 3), flush=True)
    assert len(rows) == 10
    assert model_hash(model.base.context.backbone) == old_plan["DINO_sha256"]
    write_json(
        root / "collection.json",
        {
            "plan": reference(path),
            "checkpoint": baseline["checkpoint"],
            "rows": rows,
            "seconds": time.monotonic() - start,
            "root_calls": 30,
            "scene_encoder_calls": 30,
            "full_outputs_bit_exact": 10,
            "new_training_updates": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare", type=Path)
    cli = parser.parse_args()
    if cli.prepare is not None:
        prepare(cli.path.resolve(), cli.prepare.resolve())
    else:
        os.sched_setaffinity(0, (6, 7))
        os.nice(11)
        torch.set_num_threads(2)
        collect(cli.path.resolve())
