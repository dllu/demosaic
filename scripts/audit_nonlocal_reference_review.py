"""Independent completed-reference scores, control replay and artifact audit.

CPU/read-only against completed evaluation artifacts. Manual pixel inspection
and quality decisions are separate; no neural inference or source RAW decoding.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import psutil
import tifffile
import torch
from audit_fresh_dino_statistics import CLASSICAL, audit_photo, audit_real, sha
from PIL import Image

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
STATUS = BASE / "runs/nonlocal-reference-full-workflow.json"
NL = "NonlocalMatchFilter2026+Malvar:authors-RAW"
V43_SHA = "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5"
NL_SHA = "b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2"
RAW_SHA = "c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0"


def read(p):
    return json.loads(Path(p).read_text())


def completed():
    status = read(STATUS)
    if status["status"] != "completed-reference-evaluation-awaiting-manual-review":
        raise RuntimeError("Reference workflow incomplete; wait/inspect without restarting")
    owner = status["controller"]
    try:
        process = psutil.Process(owner["pid"])
        if (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError("Reference owner remains live")
    except psutil.NoSuchProcess:
        pass
    return status


def method(label):
    if label.startswith("Nonlocal"):
        return "NL"
    if label.lower().startswith("rawnind"):
        return "raw-channel" if "channel" in label.lower() else "raw-global"
    if "dino-anchored-native-diverse-b16-v43" in label:
        return "V43"
    return None


def crop_label(c):
    return c.get("model_label", c.get("model", {}).get("label", ""))


def control_cases(path, methods, fields):
    rows = {}
    with Path(path).open() as stream:
        for line in stream:
            r = json.loads(line)
            if r["model"] not in methods:
                continue
            key = tuple(r[f] for f in fields)
            assert key not in rows
            rows[key] = r["metrics"]
    return rows


def control_differences(old, new):
    """Record all drift; post-hoc bound after exact replay failed by <=4F32ULPs.

    This is evidence of bounded numerical agreement, not exact replay or proof
    of why kernels/reductions differ. Observation keys and nullable support
    must stay exact. A larger difference fails the audit.
    """
    assert old.keys() == new.keys()
    differences = []
    exact = 0
    for key in old:
        assert old[key].keys() == new[key].keys()
        exact += old[key] == new[key]
        for metric, a in old[key].items():
            b = new[key][metric]
            assert (a is None) == (b is None)
            if a == b:
                continue
            assert np.isfinite(a) and np.isfinite(b)
            spacing = float(np.spacing(np.float32(max(abs(a), abs(b)))))
            distance = abs(a - b)
            ulps = distance / spacing
            assert ulps <= 4, (key, metric, a, b, ulps)
            differences.append(
                {
                    "observation": key,
                    "metric": metric,
                    "old": a,
                    "new": b,
                    "absolute_difference": distance,
                    "float32_ULPs": ulps,
                }
            )
    return {
        "cases": len(old),
        "all_metric_cases_exact": exact,
        "keys_and_nullable_support_exact": True,
        "differences": differences,
        "maximum_float32_ULPs": max((r["float32_ULPs"] for r in differences), default=0),
        "bound_is_posthoc": True,
        "bound": "At most4 float32 ULPs per saved scalar metric; not exact replay.",
    }


def main(output):
    status = completed()
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit exists; choose a new output")
    plan = read(status["plan"])
    for p, digest in plan["inputs"].items():
        assert sha(p) == digest, (p, "input changed")
    preflight_path = Path(status["outputs"]["GPU_preflight"]) / "receipt.json"
    assert sha(preflight_path) == status["GPU_preflight_sha256"]
    preflight = read(preflight_path)
    assert preflight["status"].startswith("completed-genuine-reference-default-stream")
    assert status["CUDA_test_result"] == "509 passed in 82.18s (0:01:22)"
    statistics = {}
    for panel in ["full427", "known", "unseen"]:
        root = Path(status["outputs"][panel])
        statistics[panel] = (
            audit_photo(root, expected_methods=6)
            if panel == "full427"
            else audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                expected_methods=6,
            )
        )
    assert sum(r["cases"] for r in statistics.values()) == 75396
    assert sum(r["paired_comparisons"] for r in statistics.values()) == 180
    controls = {}
    all_exact = 0
    for panel, newname, oldname, filename, fields, expected in [
        (
            "full427",
            "nonlocal-reference-fp32-full427-v1",
            "synthetic-convnext-v58-fresh-10k-full427",
            "per-image.jsonl",
            ["model", "kind", "id", "condition", "pattern"],
            62020,
        ),
        (
            "known",
            "nonlocal-reference-fp32-known-v1",
            "paired-known-convnext-v58-fresh-10k",
            "per-crop.jsonl",
            ["model", "scene", "pair", "tile_id", "pattern"],
            360,
        ),
        (
            "unseen",
            "nonlocal-reference-fp32-unseen-v1",
            "paired-unseen-convnext-v58-fresh-10k",
            "per-crop.jsonl",
            ["model", "scene", "pair", "tile_id", "pattern"],
            450,
        ),
    ]:
        root = BASE / "evaluation"
        old, new = [root / name / filename for name in [oldname, newname]]
        labels = CLASSICAL | (
            {"RawNIND:CFA-LS", "RawNIND:CFA-channel"}
            if panel == "full427"
            else {"RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"}
        )
        a, b = [control_cases(p, labels, fields) for p in [old, new]]
        assert len(a) == len(b) == expected
        comparison = control_differences(a, b)
        controls[panel] = {
            "old_path": str(old),
            "old_sha256": sha(old),
            "new_path": str(new),
            "new_sha256": sha(new),
            **comparison,
        }
        all_exact += comparison["all_metric_cases_exact"]
    assert sum(r["cases"] for r in controls.values()) == 62830
    weights = {"V43": V43_SHA, "NL": NL_SHA, "raw-global": RAW_SHA, "raw-channel": RAW_SHA}
    specs = [
        ("known", "summary.json", 6),
        ("unseen", "summary.json", 6),
        ("full427", "summary.json", 6),
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
            if arm == "NL":
                assert (
                    m["compute_precision"] == "IEEE float32" and m["native_network_batch_size"] == 1
                )
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
    assert len(images) == 64 and len(floats) == 29
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
        "scope": "Independent arithmetic/coverage, bounded RawNIND/classical replay, native PNG/F32 and fullRGB16 artifact integrity. Manual visual review/quality decisions remain separate.",
        "workflow": str(STATUS),
        "workflow_sha256": sha(STATUS),
        "actual_owner_exit_confirmed": True,
        "plan_sha256": sha(status["plan"]),
        "all_plan_inputs_full_SHA_verified": True,
        "GPU_preflight_sha256": sha(preflight_path),
        "CUDA_test_result": status["CUDA_test_result"],
        "statistics": statistics,
        "control_replay": controls,
        "all_exact_control_cases": all_exact,
        "all_control_cases": 62830,
        "weights": weights,
        "runs": runs,
        "images": images,
        "float_arrays": floats,
        "full_RGB16_files": files,
        "common_noisy_reference_panels_coordinates_transforms_exact": True,
        "three_camera_restored_panels_exact_between_RawNIND_comparators": True,
        "driver_sha256": sha(__file__),
        "independent_statistics_helper_sha256": sha(
            Path(__file__).with_name("audit_fresh_dino_statistics.py")
        ),
        "CUDA_initialized": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "complete-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "audit": str(output / "complete-audit.json"),
                "cases": 75396,
                "exact_controls": all_exact,
                "PNG": len(images),
                "F32": len(floats),
                "RGB16": len(files),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)
