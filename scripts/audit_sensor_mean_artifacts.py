"""Read-only V61 state, primary native panels, saved controls and RGB16 audit."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import psutil
import tifffile
import torch
from audit_fresh_dino_statistics import sha
from compare_sensor_mean_scores import CANDIDATE
from PIL import Image

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
FIELDS = [
    "prepared_crop",
    "evaluation_tile_xywh",
    "conditioning",
    "condition",
    "pattern",
    "white_balance",
    "camera_to_srgb",
    "display_exposure",
    "region",
    "context_xywh",
    "shared_wb",
    "shared_matrix",
    "full_frame",
    "reference",
    "sensor_roi_xywh",
    "context_roi_xywh",
]


def read(path):
    return json.loads(Path(path).read_text())


def exited(status):
    owner = status["controller"]
    try:
        p = psutil.Process(owner["pid"])
        assert abs(p.create_time() - owner["created"]) >= 0.01 or p.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


def identity(panel, crop):
    if panel == "three-camera":
        return crop["source_sha256"], tuple(crop["sensor_roi_xywh"]), crop["baseline"]["label"]
    return crop.get("scene", crop.get("source_id", crop.get("region", {}).get("name")))


def main(workflow, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    assert not output.exists()
    status = read(workflow)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    exited(status)
    plan = read(status["plan"])
    original = read(plan["previous_failed_workflow"])
    assert original["status"] == "failed"
    exited(original)
    training = read(BASE / "runs/sensor-mean-v61-first1k-workflow-v1.json")
    exited(training)
    training_plan = read(training["plan"])
    for guard in [plan, read(original["plan"]), training_plan]:
        for path, digest in {
            **guard["inputs"],
            **guard["source_files"],
            **guard.get("tools", {}),
        }.items():
            assert sha(path) == digest, path
    checkpoint = status["checkpoint"]
    assert sha(checkpoint["path"]) == checkpoint["sha256"] == CANDIDATE
    state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    cfg = state["config"]
    assert state["step"] == 1000 and cfg["steps"] == 4000
    assert cfg["multiscale_sensor_weight"] == 0.01 and cfg["flat_chroma_stops"] == 8
    assert cfg["initialized_from"]["sha256"] == training_plan["parent"]["sha256"]
    assert (
        cfg["source_sha256"] == "c9058d90d7d77e61ad7ec53293b805d8ea72da173318e38d1329e138215544c8"
    )
    assert len(state["model"]) == len(state["ema"]) == 91 and len(state["optimizer"]["state"]) == 89
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {1000}
    assert all(torch.isfinite(v).all() for k in ["model", "ema"] for v in state[k].values())
    assert all(
        torch.isfinite(v).all()
        for r in state["optimizer"]["state"].values()
        for v in r.values()
        if isinstance(v, torch.Tensor)
    )
    assert (
        all(k in state for k in ["python_rng", "torch_rng", "cuda_rng"])
        and len(state["cuda_rng"]) == 1
    )
    for path, digest in training_plan["source_files"].items():
        assert sha(Path(cfg["source_snapshot"]) / Path(path).name) == digest
    for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]:
        assert cfg[key + "_sha256"] == training_plan["inputs"][cfg[key]]
    new_log = Path(cfg["run"]) / "metrics.jsonl"
    old_log = (
        BASE
        / "evaluation/wide-flat-palette-first1k-complete-audit-v1/frozen-training-logs/wide-first1000-metrics.jsonl"
    )
    logs = [
        [
            r
            for line in p.read_text().splitlines()
            if (r := json.loads(line)).get("event") == "train"
        ]
        for p in [new_log, old_log]
    ]
    assert len(logs[0]) == len(logs[1]) == 41
    keys = ["step", "domain", "lr", "batch_sha256"]
    assert [[r[k] for k in keys] for r in logs[0]] == [[r[k] for k in keys] for r in logs[1]]
    assert [r["step"] for r in logs[0]] == [1, *range(25, 1001, 25)]
    assert all(math.isfinite(v) for r in logs[0] for v in r.values() if isinstance(v, (float, int)))
    images, floats, runs = [], [], {}
    old_registry = read("docs/results/wide-flat-palette-first1k-review.json")
    for panel, count in [
        ("full427", 2),
        ("known", 2),
        ("unseen", 2),
        ("analytic", 3),
        ("gfx", 4),
        ("three-camera", 6),
    ]:
        root = Path(status["outputs"][panel])
        report_path = root / (
            "summary.json" if panel in ["full427", "known", "unseen", "analytic"] else "report.json"
        )
        report = read(report_path)
        old_path = Path(old_registry["runs"][panel]["report"])
        assert sha(old_path) == old_registry["runs"][panel]["report_sha256"]
        old = read(old_path)
        assert len(report["native_crops"]) == count
        for crop in report["native_crops"]:
            assert crop.get("checkpoint_sha256", crop.get("model", {}).get("sha256")) == CANDIDATE
            matches = [
                c
                for c in old["native_crops"]
                if identity(panel, c) == identity(panel, crop)
                and "wide-b16-v60" in c.get("model_label", c.get("model", {}).get("label", ""))
            ]
            assert len(matches) == 1, (panel, identity(panel, crop))
            previous = matches[0]
            for field in FIELDS:
                assert crop.get(field) == previous.get(field), (panel, field)
            png, old_png = root / crop["image"], old_path.parent / previous["image"]
            assert sha(png) == crop["png_sha256"] and sha(old_png) == previous["png_sha256"]
            arrays = []
            for path in [png, old_png]:
                with Image.open(path) as im:
                    assert im.mode == "RGB" and im.size == (512, 192)
                    arrays.append(np.array(im))
            assert [p["png_xywh"] for p in crop["panels"]] == [
                [8, 24, 160, 160],
                [176, 24, 160, 160],
                [344, 24, 160, 160],
            ]
            for x in [8, 344]:
                np.testing.assert_array_equal(
                    arrays[0][24:184, x : x + 160], arrays[1][24:184, x : x + 160]
                )
            images.append(
                {
                    "panel": panel,
                    "path": str(png),
                    "sha256": sha(png),
                    "metadata": crop,
                    "saved_V60_control": str(old_png),
                }
            )
        for item in report.get("float_contexts", []):
            path = root / item["image"]
            assert sha(path) == item["sha256"]
            v = np.load(path, mmap_mode="r", allow_pickle=False)
            assert v.dtype == np.float32 and list(v.shape) == item["shape"] and np.isfinite(v).all()
            floats.append({"path": str(path), "sha256": sha(path), "shape": list(v.shape)})
        runs[panel] = {
            "report": str(report_path),
            "report_sha256": sha(report_path),
            "native_PNGs": count,
        }
    assert len(images) == 19 and len(floats) == 23
    gfx = read(runs["gfx"]["report"])
    assert len(gfx["full_frames"]) == 1
    files = []
    for item in gfx["full_frames"][0]["files"]:
        path = Path(status["outputs"]["gfx"]) / item["path"]
        assert sha(path) == item["sha256"] and path.stat().st_size == item["bytes"]
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            assert (
                page.shape == (8746, 11662, 3)
                and page.bitspersample == 16
                and page.samplesperpixel == 3
            )
            if "srgb16" in path.name:
                assert 34675 in page.tags
        v = tifffile.memmap(path, mode="r")
        codes = int(np.unique(v[::97, ::101]).size)
        assert v.dtype == np.uint16 and codes > 256
        files.append({**item, "absolute_path": str(path), "sampled_unique_codes": codes})
    result = {
        "status": "completed-independent-V61-state-primary-native-and-RGB16-integrity-audit",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "original_failure_retained": original,
        "checkpoint": checkpoint,
        "all_guards_finite_state_RNG_steps_and_41_logged_control_inputs_verified": True,
        "training_log": {"path": str(new_log), "sha256": sha(new_log)},
        "runs": runs,
        "images": images,
        "float_arrays": floats,
        "full_RGB16_files": files,
        "common_noisy_reference_pixels_coordinates_transforms_exact_to_V60": True,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": torch.cuda.is_initialized(),
        "scope": "Integrity only. No inference, training, protected-final scoring or quality decision. Every native noisy/reference pixel matches saved V60. Model quality requires actual visual and statistical review.",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (output / "training-metrics.jsonl").write_bytes(new_log.read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "native_PNG": len(images),
                "F32": len(floats),
                "RGB16": len(files),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
