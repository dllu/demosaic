"""Read-only completed ConvNeXt boundary/native/RGB16/context integrity audit."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import psutil
import tifffile
import torch
from PIL import Image

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
NAMES = [
    "control-anchored-native-fresh-b16-v45",
    "dino-anchored-native-fresh-b16-v44",
    "dino-base-anchored-native-fresh-b16-v51",
    "dino-convnext-pyramid-fresh-b16-v58",
]
ARMS = ["none", "S", "B", "V58"]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def method(label):
    prefix = label.split(":", 1)[0]
    if prefix.isdigit():
        return ARMS[int(prefix)]
    if label.lower().startswith("rawnind"):
        return "raw-channel" if "channel" in label.lower() else "raw-global"
    for arm, name in zip(ARMS, NAMES):
        if name in label:
            return arm
    return None


def label(crop):
    return crop.get("model_label", crop.get("model", {}).get("label", ""))


def main(steps, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    suffix = {1000: "1k", 10000: "10k"}[steps]
    workflow_path = BASE / (
        "runs/dino-convnext-pyramid-v58-workflow.json"
        if steps == 1000
        else "runs/dino-convnext-pyramid-v58-10k-workflow.json"
    )
    workflow = read(workflow_path)
    assert workflow["status"] == (
        "completed-first1000-and-evaluation-awaiting-manual-review"
        if steps == 1000
        else "completed-to10000-and-evaluation-awaiting-manual-review"
    ), "Workflow incomplete; inspect/wait without restarting it"
    owner = workflow["controller"]
    try:
        p = psutil.Process(owner["pid"])
        assert abs(p.create_time() - owner["created"]) >= 0.01 or p.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass
    plan = read(workflow["plan"])
    checkpoint = (
        {"path": workflow["candidate_checkpoint"], "sha256": workflow["candidate_sha256"]}
        if steps == 1000
        else next(c for c in workflow["checkpoints"] if c["step"] == steps)
    )
    weights = {}
    for arm, control in zip(ARMS, plan["controls"]):
        digest = control.get("sha256", control.get("checkpoint_sha256"))
        assert sha(control["path"]) == digest
        weights[arm] = digest
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    weights["V58"] = checkpoint["sha256"]
    raw_sha = sha(BASE / "references/rawnind/utnet2-bayer.pt")
    assert raw_sha == "c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0"
    weights.update({"raw-global": raw_sha, "raw-channel": raw_sha})
    state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == steps and state["config"]["steps"] == 10000
    assert len(state["model"]) == len(state["ema"]) == 91 and len(state["optimizer"]["state"]) == 89
    assert state["model_config"]["dino_feature_fusion"] == "convnext-pyramid"
    assert state["model_config"]["dino_revision"] == "10d30274b4d445111e2d5bf75ac93bbd94db274b"
    assert state["model_config"]["rgb_middle_skip_fp32"]
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {steps}
    assert all(torch.isfinite(t).all() for field in ["model", "ema"] for t in state[field].values())
    assert all(
        torch.isfinite(t).all()
        for row in state["optimizer"]["state"].values()
        for t in row.values()
        if isinstance(t, torch.Tensor)
    )
    assert (
        all(k in state for k in ["python_rng", "torch_rng", "cuda_rng"])
        and len(state["cuda_rng"]) == 1
    )
    assert all(
        sha(Path(state["config"]["source_snapshot"]) / name) == digest
        for name, digest in plan["source_files"].items()
    )
    rows = [
        r
        for line in (BASE / "runs/dino-convnext-pyramid-fresh-b16-v58/metrics.jsonl")
        .read_text()
        .splitlines()
        if (r := json.loads(line)).get("event") == "train" and r["step"] <= steps
    ]
    assert len(rows) == (41 if steps == 1000 else 403) and rows[-1]["step"] == steps
    assert all(math.isfinite(r[k]) for r in rows for k in ["loss", "grad_norm", "lr"])
    identities = [(r["step"], r["domain"], r["batch_sha256"]) for r in rows]
    for control in plan["controls"]:
        old = [
            r
            for line in (BASE / "runs" / control["name"] / "metrics.jsonl").read_text().splitlines()
            if (r := json.loads(line)).get("event") == "train" and r["step"] <= steps
        ]
        assert identities == [(r["step"], r["domain"], r["batch_sha256"]) for r in old]
    boundary = {
        "checkpoint": checkpoint,
        "step": steps,
        "original_planned_steps": 10000,
        "model_tensors": 91,
        "EMA_tensors": 91,
        "AdamW_states": 89,
        "all_training_values_and_model_EMA_AdamW_states_finite": True,
        "whole_Python_Torch_CUDA_RNG_present": True,
        "logged_observations_equal_to_each_original_arm": len(rows),
        "source_bundle_sha256": state["config"]["source_sha256"],
        "learning_rates": [g["lr"] for g in state["optimizer"]["param_groups"]],
        "EMA_gate_norms": {
            k: float(v.norm()) for k, v in state["ema"].items() if k.startswith("context.gates.")
        },
    }
    if steps == 10000:
        assert all(lr == 1e-5 for lr in boundary["learning_rates"])
    del state
    specs = [
        ("known", f"paired-known-convnext-v58-fresh-{suffix}", "summary.json", 12),
        ("unseen", f"paired-unseen-convnext-v58-fresh-{suffix}", "summary.json", 12),
        ("full427", f"synthetic-convnext-v58-fresh-{suffix}-full427", "summary.json", 12),
        ("analytic", f"analytic-convnext-v58-fresh-{suffix}", "summary.json", 12),
        ("gfx", f"gfx-3879-3880-convnext-v58-fresh-{suffix}-full", "report.json", 24),
        ("three-camera", f"three-camera-convnext-v58-fresh-{suffix}", "report.json", 48),
    ]
    images, runs, float_arrays = [], {}, []
    for panel, directory, filename, count in specs:
        root = BASE / "evaluation" / directory
        path = root / filename
        d = read(path)
        assert len(d["native_crops"]) == count
        for model in d["models"]:
            arm = method(model["label"])
            assert arm is not None
            assert model.get("sha256", model.get("weight_sha256")) == weights[arm]
        common, restored, seen = {}, {}, set()
        for c in d["native_crops"]:
            arm = method(label(c))
            assert arm is not None
            if panel == "three-camera":
                ident = (
                    c["raw_metadata"]["camera"]
                    + "-"
                    + c["region"]
                    + "-"
                    + method(c["baseline"]["label"])
                )
                common_key = c["source_sha256"], tuple(c["sensor_roi_xywh"]), c["baseline"]["label"]
                restore_key = c["source_sha256"], tuple(c["sensor_roi_xywh"]), arm
                assert c["checkpoint_sha256"] == weights[arm]
                assert (
                    c["baseline"].get("sha256", c["baseline"].get("weight_sha256"))
                    == weights[method(c["baseline"]["label"])]
                )
                assert "not gt" in c["reference"].lower()
            else:
                ident = c.get("scene", c.get("source_id", c.get("region", {}).get("name")))
                common_key = ident
            assert (arm, ident) not in seen
            seen.add((arm, ident))
            png = root / c["image"]
            assert sha(png) == c["png_sha256"]
            with Image.open(png) as im:
                assert im.mode == "RGB" and im.size == (512, 192)
                values = np.asarray(im).copy()
            assert [p["png_xywh"] for p in c["panels"]] == [
                [8, 24, 160, 160],
                [176, 24, 160, 160],
                [344, 24, 160, 160],
            ]
            if common_key in common:
                parent, previous = common[common_key]
                for x in [8, 344]:
                    np.testing.assert_array_equal(
                        values[24:184, x : x + 160], previous[24:184, x : x + 160]
                    )
                for field in [
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
                ]:
                    assert (field in c) == (field in parent)
                    if field in c:
                        assert c[field] == parent[field], (panel, ident, field)
            else:
                common[common_key] = c, values
            if panel == "three-camera":
                current = values[24:184, 176:336]
                if restore_key in restored:
                    np.testing.assert_array_equal(current, restored[restore_key])
                else:
                    restored[restore_key] = current.copy()
            images.append(
                {
                    "path": str(png),
                    "sha256": sha(png),
                    "panel": panel,
                    "method": arm,
                    "source": ident,
                }
            )
        for item in d.get("float_contexts", []):
            p = root / item["image"]
            assert sha(p) == item["sha256"]
            a = np.load(p, mmap_mode="r", allow_pickle=False)
            assert a.dtype == np.float32 and list(a.shape) == item["shape"] and np.isfinite(a).all()
            float_arrays.append(
                {"path": str(p), "sha256": sha(p), "shape": list(a.shape), "dtype": "float32"}
            )
        runs[panel] = {"report": str(path), "report_sha256": sha(path), "native_PNGs": count}
    assert len(images) == 120 and len(float_arrays) == 35
    verified = []
    gfx = read(Path(runs["gfx"]["report"]))
    assert len(gfx["full_frames"]) == 6 and len(workflow["verified_files"]) == 12
    report_files = {item["path"]: item for frame in gfx["full_frames"] for item in frame["files"]}
    for item in workflow["verified_files"]:
        path = Path(item["absolute_path"])
        assert sha(path) == item["sha256"] == report_files[item["path"]]["sha256"]
        assert path.stat().st_size == item["bytes"] == report_files[item["path"]]["bytes"]
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            assert (
                page.shape == (8746, 11662, 3)
                and page.bitspersample == 16
                and page.samplesperpixel == 3
            )
            if "srgb16" in path.name:
                assert 34675 in page.tags
        a = tifffile.memmap(path, mode="r")
        assert a.dtype == np.uint16 and a.shape == (8746, 11662, 3)
        codes = int(np.unique(a[::97, ::101]).size)
        assert codes == item["sampled_unique_codes"] and codes > 256
        verified.append(
            {**item, "independent_full_SHA_size_dtype_dimensions_tags_sampled_codes_verified": True}
        )
    result = {
        "scope": "Integrity of120 native PNGs,35 unquantized context arrays and12 fullRGB16 TIFFs. Manual visual review and quality decision are separate.",
        "workflow": str(workflow_path),
        "workflow_sha256": sha(workflow_path),
        "actual_owner_exit_confirmed": True,
        "boundary": boundary,
        "weights": weights,
        "runs": runs,
        "images": images,
        "float_arrays": float_arrays,
        "full_RGB16_files": verified,
        "common_noisy_and_reference_panels_coordinates_transforms_exact": True,
        "three_camera_restored_panel_exact_between_both_RawNIND_comparator_triplets": True,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": torch.cuda.is_initialized(),
    }
    assert not result["CUDA_initialized"]
    OUT = writable_path(output)
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "complete-artifact-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "native_PNGs": 120,
                "float_arrays": 35,
                "full_RGB16_TIFFs": 12,
                "audit": str(OUT / "complete-artifact-audit.json"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, choices=[1000, 10000], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.steps, args.output)
