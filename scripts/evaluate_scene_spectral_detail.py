"""Collect a scene spectral pilot on fixed development and standing GFX observations."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

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
from demosaic.models import load_model
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.scene_restoration import EncodedScene, encode_scene
from demosaic.scene_spectral_detail import SceneSpectralDetail

KEYS = ("packed", "variance", "colors", "wb", "matrix")


def prepare(root, training, native, development):
    native = reference(native)
    training = reference(training)
    development = reference(development)
    contract = read_json(checked(native))
    earlier_spatial = reference(Path(contract["root"]) / "spatial/collection.json")
    baseline = contract["baseline_collection"]
    rendered = reference(Path(contract["root"]) / "render-all-v1/result.json")
    study = read_json(checked(development))
    assert len(study["cases"]) == 128
    assert study["endpoints"]["V120"] == read_json(checked(training))["parent"]
    root.mkdir()
    work, sources = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_spectral_detail.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "frozen_files": sources,
            "inputs": [training, native, development, earlier_spatial, baseline, rendered],
            "driver": reference(work / "scripts" / Path(__file__).name),
            "reporter": reference(work / "scripts/report_scene_spectral_detail.py"),
            "training": training,
            "native": native,
            "development": development,
            "whole_camera_sources": earlier_spatial,
            "camera_baseline": baseline,
            "native_boards": rendered,
            "max_cuda_GiB": 6,
            "min_available_RAM_GiB": 32,
            "scope": "Existing matched CPU FP32 V120 parent outputs; IEEE CUDA FP32 frozen scene encodes "
            "and spectral heads. All 64 reserved sources at both established positive-noise conditions and both standing GFX captures. "
            "A horizontal feature roll changes alignment while preserving each level's pooled descriptor.",
        },
    )


def shifted(scene):
    levels = []
    for level, stride in zip(scene.features, (4, 8, 16, 32), strict=True):
        active = scene.grid.preview_hw[1] // stride
        # Roll only completely covered feature columns, preserving the
        # weighted pooled descriptor with partial and padded cells intact.
        levels.append(
            torch.cat((level[..., :active].roll(active // 2, -1), level[..., active:]), -1)
        )
    return EncodedScene(tuple(levels), scene.grid)


def load_arguments(record, *, development):
    prefix = "crop_" if development else ""
    with np.load(checked(record), allow_pickle=False) as value:
        args = {k: torch.from_numpy(value[prefix + k].copy()) for k in KEYS}
        full = torch.from_numpy(value["scene_packed"].copy()) if development else None
    return args, full


def write_array(path, value):
    with path.open("xb") as file:
        np.save(file, value, allow_pickle=False)
    return reference(path)


@torch.inference_mode()
def collect(path, *, preflight=False):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    training = read_json(checked(plan["training"]))
    trial = "preflight" if preflight else "training"
    terminal_path = Path(training["root"]) / trial / "completed.json"
    done = read_json(terminal_path)
    assert done["plan"] == plan["training"] and done["discarded_preflight"] == preflight
    assert done["parent_untouched"] and done["steps_per_mode"] == (
        3 if preflight else training["steps"]
    )
    torch.set_num_threads(2)
    torch.cuda.set_per_process_memory_fraction(
        min(1.0, plan["max_cuda_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory)
    )
    assert psutil.virtual_memory().available >= plan["min_available_RAM_GiB"] * 2**30
    base, _ = load_model("v120", checkpoint=checked(training["parent"]), device="cpu")
    encoder = base.context.cuda().eval()
    assert model_hash(encoder.backbone) == training["DINO_sha256"]
    del base
    heads = {}
    for mode, endpoint in done["endpoints_raw_and_ema"].items():
        state = torch.load(checked(endpoint), map_location="cpu", weights_only=True)
        assert (state["plan"], state["mode"], state["parent"], state["step"]) == (
            done["plan"],
            mode,
            training["parent"],
            done["steps_per_mode"],
        )
        head = SceneSpectralDetail(
            encoder.backbone.config.hidden_sizes,
            max_window=state["max_window"],
            adapter_width=state["adapter_width"],
        )
        head.load_state_dict(state["ema"], strict=True)
        heads[mode] = head.cuda().eval()
    root = Path(plan["root"]) / ("qualification" if preflight else "collection")
    root.mkdir()
    development = read_json(checked(plan["development"]))["cases"]
    native = read_json(checked(plan["native"]))
    camera = [r for r in native["observations"] if r["kind"] != "development"]
    parent_by_camera = {r["id"]: r for r in read_json(checked(plan["camera_baseline"]))["records"]}
    camera_raws = read_json(checked(plan["whole_camera_sources"]))["full_real_noisy_sources"]
    records, real_cache = [], {}
    began = time.monotonic()

    def run(key, record, args, stored_parent, scene, boxes):
        color_input = {k: fingerprint(v) for k, v in args.items()}
        assert color_input == record["input_fingerprints"]
        parent = torch.from_numpy(np.load(checked(stored_parent), allow_pickle=False)).cuda()
        result = {
            "id": key,
            "parent": stored_parent,
            "physical": color_input,
            "variants": {},
            "boxes_xywh": boxes,
        }
        args_gpu = [args[k].cuda() for k in ("packed", "variance", "colors", "wb")]
        for mode, context in (
            ("pooled", scene),
            ("spatial", scene),
            ("spatial-shifted", shifted(scene)),
        ):
            arm = mode.removesuffix("-shifted")
            value = heads[arm](parent, *args_gpu, scene=context, boxes_xywh=boxes, mode=arm)
            assert torch.isfinite(value).all()
            result["variants"][mode] = write_array(root / f"{key}-{mode}.npy", value.cpu().numpy())
        result["scene_features"] = [fingerprint(v) for v in scene.features]
        write_json(root / f"{key}.json", result)
        records.append(reference(root / f"{key}.json"))
        print(len(records), key, round(time.monotonic() - began, 3), flush=True)

    with ieee_fp32():
        for binding in development[:1] if preflight else development:
            assert psutil.virtual_memory().available >= plan["min_available_RAM_GiB"] * 2**30
            item = read_json(checked(binding))
            args, complete = load_arguments(item["inputs"], development=True)
            boxes = item["boxes_xywh"]
            for tile, (x, y, w, h) in zip(args["packed"], boxes, strict=True):
                exact = complete[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
                torch.testing.assert_close(tile, exact, atol=0, rtol=0)
            scene = encode_scene(
                encoder,
                complete,
                args["colors"][0],
                args["wb"][0],
                args["matrix"][0],
                long_side=training["preview_long_side"],
                exposure=training["preview_exposure"],
            )
            parent = next(v["prediction"] for v in item["variants"] if v["variant"] == "V120")
            run(item["id"], item, args, parent, scene, boxes)
        for item in camera[-1:] if preflight else camera:
            key = item["id"]
            parent = parent_by_camera[key]
            family = "main" if item["kind"] == "gfx" else "mesh"
            args, _ = load_arguments(item["arrays"], development=False)
            if family not in real_cache:
                loc = checked(camera_raws[family])
                assert loc.parent.name == "gfx-qualitative-20231231"
                raw, camera_metadata = read_raw(loc)
                assert camera_metadata.pattern == "RGGB"
                full = torch.from_numpy(raw)
                scene = encode_scene(
                    encoder,
                    pack(full[None, None])[0],
                    args["colors"][0],
                    args["wb"][0],
                    args["matrix"][0],
                    long_side=training["preview_long_side"],
                    exposure=training["preview_exposure"],
                )
                real_cache[family] = (full, scene)
            full, scene = real_cache[family]
            box = item["metadata"]["context_xywh"] if family == "main" else [600, 6260, 768, 768]
            x, y, w, h = box
            torch.testing.assert_close(
                args["packed"], pack(full[None, None, y : y + h, x : x + w]), atol=0, rtol=0
            )
            run(key, parent, args, parent["prediction"], scene, [box])
    assert len(records) == (2 if preflight else 134)
    assert model_hash(encoder.backbone) == training["DINO_sha256"]
    write_json(
        root / "result.json",
        {
            "plan": reference(path),
            "training": reference(terminal_path),
            "driver": reference(__file__),
            "records": records,
            "heads": done["endpoints_raw_and_ema"],
            "weights": "EMA",
            "preflight": preflight,
            "seconds": time.monotonic() - began,
            "cuda_peak_GiB": torch.cuda.max_memory_allocated() / 2**30,
            "new_V120_calls": 0,
            "scene_calls": 2 if preflight else 130,
            "DINO_unchanged": True,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", nargs=3, type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), *(p.resolve() for p in args.prepare_from))
    else:
        os.sched_setaffinity(0, (6, 7))
        os.nice(11)
        collect(args.path.resolve(), preflight=args.preflight)
