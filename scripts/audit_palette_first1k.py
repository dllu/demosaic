"""Independent first1k or final4k palette state, score and artifact audit."""

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
import psutil
import tifffile
import torch
from audit_fresh_dino_statistics import CLASSICAL, audit_photo, audit_real, sha
from audit_nonlocal_reference_review import control_cases, control_differences
from PIL import Image

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
STATUS = BASE / "runs/wide-flat-palette-first1k-workflow-v1.json"
PARENT_SHA = "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3"
RAW_SHA = "c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0"


def read(p):
    return json.loads(Path(p).read_text())


def method(label):
    if label.lower().startswith("rawnind"):
        return "raw-channel" if "channel" in label.lower() else "raw-global"
    if "dino-convnext-palette-control-b16-v59" in label:
        return "control"
    if "dino-convnext-palette-wide-b16-v60" in label:
        return "wide"
    return None


def crop_label(c):
    return c.get("model_label", c.get("model", {}).get("label", ""))


def completed(workflow=STATUS, expected_step=1000):
    s = read(workflow)
    terminal = {
        1000: "completed-first1000-and-evaluation-awaiting-manual-review",
        4000: "completed-original4000-and-evaluation-awaiting-manual-review",
    }
    if s["status"] != terminal[expected_step]:
        raise RuntimeError("Palette workflow incomplete; inspect/wait without restarting")
    try:
        p = psutil.Process(s["controller"]["pid"])
        if (
            abs(p.create_time() - s["controller"]["created"]) < 0.01
            and p.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError("Palette owner remains live")
    except psutil.NoSuchProcess:
        pass
    return s


def main(output, workflow=STATUS, expected_step=1000):
    status = completed(workflow, expected_step)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit exists; choose a new output")
    plan = read(status["plan"])
    for p, digest in {**plan["inputs"], **plan["source_files"]}.items():
        assert sha(p) == digest
    weights = {}
    boundaries = {}
    logs = {}
    log_copies = {}
    for c in status["checkpoints"]:
        assert (
            sha(c["path"]) == c["sha256"]
            and c["step"] == expected_step
            and c["parent_sha256"] == PARENT_SHA
        )
        weights[c["arm"]] = c["sha256"]
        state = torch.load(c["path"], map_location="cpu", weights_only=True, mmap=True)
        cfg = state["config"]
        assert (
            state["step"] == expected_step
            and cfg["steps"] == 4000
            and cfg["initialized_from"]["sha256"] == PARENT_SHA
        )
        assert cfg["flat_chroma_stops"] == (0 if c["arm"] == "control" else 8)
        assert (
            len(state["model"]) == len(state["ema"]) == 91
            and len(state["optimizer"]["state"]) == 89
        )
        assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {expected_step}
        assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in state[key].values())
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
        assert (
            cfg["source_sha256"]
            == "c9058d90d7d77e61ad7ec53293b805d8ea72da173318e38d1329e138215544c8"
        )
        for p, digest in plan["source_files"].items():
            assert sha(Path(cfg["source_snapshot"]) / Path(p).name) == digest
        for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]:
            assert cfg[key + "_sha256"] == plan["inputs"][cfg[key]]
        path = Path(cfg["run"]) / "metrics.jsonl"
        # Continuation appends the live run logs. Prefer the original immutable
        # first1k copies when reviewing that historical boundary again.
        frozen_root = BASE / "evaluation/wide-flat-palette-first1k-complete-audit-v1"
        frozen = frozen_root / "frozen-training-logs" / (c["arm"] + "-first1000-metrics.jsonl")
        if expected_step == 1000 and frozen.exists():
            previous = read(frozen_root / "complete-audit.json")
            assert sha(frozen) == previous["boundary"][c["arm"]]["log_sha256"]
            path = frozen
        rows = [
            r
            for line in path.read_text().splitlines()
            if (r := json.loads(line)).get("event") == "train" and r["step"] <= expected_step
        ]
        log_steps = [1, *range(25, 1001, 25)]
        if expected_step == 4000:
            log_steps += [1001, *range(1025, 4001, 25)]
        assert [r["step"] for r in rows] == log_steps and all(
            math.isfinite(v) for r in rows for v in r.values() if isinstance(v, (float, int))
        )
        logs[c["arm"]] = rows
        log_copies[c["arm"]] = path.read_bytes()
        boundaries[c["arm"]] = {
            "checkpoint": c,
            "step": expected_step,
            "planned_steps": 4000,
            "source_bundle_sha256": cfg["source_sha256"],
            "model_EMA_tensors": 91,
            "AdamW_states": 89,
            "all_states_and_logs_finite": True,
            "complete_RNG_present": True,
            "log_path": str(path),
            "log_sha256": sha(path),
            "immutable_log_copy": str(
                output / "frozen-training-logs" / (c["arm"] + "-metrics.jsonl")
            ),
            "gate_norms": {
                k: float(v.norm())
                for k, v in state["ema"].items()
                if k.startswith("context.gates.")
            },
            "learning_rates": [g["lr"] for g in state["optimizer"]["param_groups"]],
        }
        del state
    assert set(weights) == {"control", "wide"}
    observed = []
    for a, b in zip(logs["control"], logs["wide"]):
        assert (a["step"], a["domain"], a["lr"]) == (b["step"], b["domain"], b["lr"])
        colored = 0
        if a["domain"] == "synthetic":
            for i in range((a["step"] - 1) * 16, a["step"] * 16):
                rng = random.Random(48 + i)
                if rng.random() < 0.1:
                    rng.uniform(-13, -1)
                    colored += rng.random() >= 0.5
        exact = a["batch_sha256"] == b["batch_sha256"]
        if not colored:
            assert exact, (a["step"], "unchanged batch differs")
        observed.append(
            {
                "step": a["step"],
                "domain": a["domain"],
                "colored_clean_targets": colored,
                "batch_hash_equal": exact,
            }
        )
    assert any(not r["batch_hash_equal"] for r in observed)
    statistics = {}
    for panel in ["full427", "known", "unseen"]:
        root = Path(status["outputs"][panel])
        statistics[panel] = (
            audit_photo(root, 7)
            if panel == "full427"
            else audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                7,
            )
        )
    assert (
        sum(r["cases"] for r in statistics.values()) == 87962
        and sum(r["paired_comparisons"] for r in statistics.values()) == 252
    )
    controls = {}
    all_exact = 0
    for panel, filename, fields, count in [
        ("full427", "per-image.jsonl", ["model", "kind", "id", "condition", "pattern"], 62020),
        ("known", "per-crop.jsonl", ["model", "scene", "pair", "tile_id", "pattern"], 360),
        ("unseen", "per-crop.jsonl", ["model", "scene", "pair", "tile_id", "pattern"], 450),
    ]:
        old = BASE / "evaluation" / f"nonlocal-reference-fp32-{panel}-v1" / filename
        new = Path(status["outputs"][panel]) / filename
        labels = CLASSICAL | (
            {"RawNIND:CFA-LS", "RawNIND:CFA-channel"}
            if panel == "full427"
            else {"RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"}
        )
        a, b = [control_cases(p, labels, fields) for p in [old, new]]
        assert len(a) == len(b) == count
        delta = control_differences(a, b)
        controls[panel] = {
            "previous": str(old),
            "previous_sha256": sha(old),
            "current": str(new),
            "current_sha256": sha(new),
            **delta,
        }
        all_exact += delta["all_metric_cases_exact"]
    weights.update({"raw-global": RAW_SHA, "raw-channel": RAW_SHA})
    specs = [
        ("known", "summary.json", 8),
        ("unseen", "summary.json", 8),
        ("full427", "summary.json", 8),
        ("analytic", "summary.json", 6),
        ("gfx", "report.json", 16),
        ("three-camera", "report.json", 24),
    ]
    runs = {}
    images = []
    floats = []
    common_fields = [
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
    for panel, filename, count in specs:
        root = Path(status["outputs"][panel])
        p = root / filename
        d = read(p)
        assert len(d["native_crops"]) == count
        for m in d["models"]:
            arm = method(m["label"])
            assert arm is not None
            assert m.get("sha256", m.get("weight_sha256")) == weights[arm]
        common = {}
        restored = {}
        seen = set()
        for c in d["native_crops"]:
            arm = method(crop_label(c))
            assert arm is not None
            if panel == "three-camera":
                identity = (
                    c["raw_metadata"]["camera"]
                    + "-"
                    + c["region"]
                    + "-"
                    + method(c["baseline"]["label"])
                )
                common_key = c["source_sha256"], tuple(c["sensor_roi_xywh"]), c["baseline"]["label"]
                restored_key = c["source_sha256"], tuple(c["sensor_roi_xywh"]), arm
                assert c["checkpoint_sha256"] == weights[arm] and "not gt" in c["reference"].lower()
                base = c["baseline"]
                assert base.get("sha256", base.get("weight_sha256")) == RAW_SHA
            else:
                identity = c.get("scene", c.get("source_id", c.get("region", {}).get("name")))
                common_key = identity
            assert (arm, identity) not in seen
            seen.add((arm, identity))
            png = root / c["image"]
            assert sha(png) == c["png_sha256"]
            with Image.open(png) as im:
                assert im.mode == "RGB" and im.size == (512, 192)
                a = np.array(im)
            assert [r["png_xywh"] for r in c["panels"]] == [
                [8, 24, 160, 160],
                [176, 24, 160, 160],
                [344, 24, 160, 160],
            ]
            if common_key in common:
                parent, b = common[common_key]
                for x in [8, 344]:
                    np.testing.assert_array_equal(a[24:184, x : x + 160], b[24:184, x : x + 160])
                for field in common_fields:
                    assert (field in c) == (field in parent), (panel, identity, field)
                    if field in c:
                        assert c[field] == parent[field], (panel, identity, field)
            else:
                common[common_key] = c, a
            if panel == "three-camera":
                tile = a[24:184, 176:336]
                if restored_key in restored:
                    np.testing.assert_array_equal(tile, restored[restored_key])
                else:
                    restored[restored_key] = tile.copy()
            images.append(
                {
                    "path": str(png),
                    "sha256": sha(png),
                    "panel": panel,
                    "method": arm,
                    "source": identity,
                }
            )
        for item in d.get("float_contexts", []):
            p = root / item["image"]
            assert sha(p) == item["sha256"]
            v = np.load(p, mmap_mode="r", allow_pickle=False)
            assert v.dtype == np.float32 and list(v.shape) == item["shape"] and np.isfinite(v).all()
            floats.append(
                {"path": str(p), "sha256": sha(p), "shape": list(v.shape), "dtype": "float32"}
            )
        runs[panel] = {
            "report": str(root / filename),
            "report_sha256": sha(root / filename),
            "native_PNGs": count,
        }
    assert len(images) == 70 and len(floats) == 29
    gfx = read(runs["gfx"]["report"])
    assert len(gfx["full_frames"]) == 4
    recorded = {f["path"]: f for frame in gfx["full_frames"] for f in frame["files"]}
    assert len(recorded) == len(status["verified_files"]) == 8
    files = []
    for item in status["verified_files"]:
        p = Path(item["absolute_path"])
        assert sha(p) == item["sha256"] == recorded[item["path"]]["sha256"]
        assert p.stat().st_size == item["bytes"] == recorded[item["path"]]["bytes"]
        with tifffile.TiffFile(p) as tif:
            page = tif.pages[0]
            assert (
                page.shape == (8746, 11662, 3)
                and page.bitspersample == 16
                and page.samplesperpixel == 3
            )
            if "srgb16" in p.name:
                assert 34675 in page.tags
        v = tifffile.memmap(p, mode="r")
        assert v.dtype == np.uint16 and v.shape == (8746, 11662, 3)
        codes = int(np.unique(v[::97, ::101]).size)
        assert codes == item["sampled_unique_codes"] and codes > 256
        files.append(
            {**item, "independent_full_SHA_dimensions_dtype_tags_and_sampled_codes_verified": True}
        )
    result = {
        "scope": f"Completed palette step{expected_step} state/data/numerical/native/RGB16 integrity audit; quality and visual selection remain separate.",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "actual_owner_exit_confirmed": True,
        "plan_sha256": sha(status["plan"]),
        "boundary": boundaries,
        "logged_observations": observed,
        "statistics": statistics,
        "control_replay": controls,
        "all_exact_control_cases": all_exact,
        "control_tolerance_origin": "FourF32ULP bound inherited from the earlier reference replay, fixed before these palette evaluation results. Every drift retained; not exact replay.",
        "weights": weights,
        "runs": runs,
        "images": images,
        "float_arrays": floats,
        "full_RGB16_files": files,
        "common_noisy_reference_pixels_coordinates_transforms_exact": True,
        "three_camera_restored_pixels_exact_between_both_comparator_triplets": True,
        "driver_sha256": sha(__file__),
        "helper_sources": {
            str(Path(__file__).with_name(n)): sha(Path(__file__).with_name(n))
            for n in ["audit_fresh_dino_statistics.py", "audit_nonlocal_reference_review.py"]
        },
        "CUDA_initialized": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "frozen-training-logs").mkdir()
    for arm, payload in log_copies.items():
        p = Path(boundaries[arm]["immutable_log_copy"])
        p.write_bytes(payload)
        assert sha(p) == boundaries[arm]["log_sha256"]
    (output / "complete-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "audit": str(output / "complete-audit.json"),
                "cases": 87962,
                "CI": 252,
                "PNG": len(images),
                "F32": len(floats),
                "RGB16": len(files),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workflow", type=Path, default=STATUS)
    p.add_argument("--expected-step", type=int, choices=[1000, 4000], default=1000)
    a = p.parse_args()
    main(a.output, a.workflow, a.expected_step)
