"""Queue CPU-only color arithmetic and native boards after the exact review exits."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import psutil

TERMINAL = "completed-directional-interval-inference-awaiting-statistical-and-manual-native-closure"
STAGES = {
    "boundary",
    "known",
    "unseen",
    "full427",
    "statistics",
    "sensitivity",
    "gfx",
    "analytic",
    "hue",
    "highlights",
}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def ready(status, owner):
    if status["controller"] != owner:
        raise RuntimeError("Review owner identity differs")
    if status["status"].startswith("failed-"):
        raise RuntimeError("Review failed; no automatic closure/retry")
    if alive(owner):
        return False
    if status["status"] != TERMINAL:
        raise RuntimeError("Review exited without complete inference")
    if set(status["completed"]) != STAGES or len(status["completed"]) != len(STAGES):
        raise RuntimeError("Review stages are incomplete")
    return not alive(status["child"])


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def select_retained(fresh, retained, kind, parent_sha, rawnind_sha):
    """A fresh parent must cover every case; never append its old duplicate."""
    from build_native_crop_board import case_key, identity

    cases = {case_key(c, kind) for c in fresh}
    assert len(cases) == 2
    fresh_parent = [c for c in fresh if identity(c)[1] == parent_sha]
    assert not fresh_parent or (
        len(fresh_parent) == 2 and {case_key(c, kind) for c in fresh_parent} == cases
    ), "Fresh parent coverage is incomplete or duplicated"
    selected = []
    for crop in retained:
        label, digest = identity(crop)
        keep = (digest == parent_sha and not fresh_parent) or (
            kind == "camera" and digest == rawnind_sha and "cfa-channel" in label
        )
        if keep and case_key(crop, kind) in cases:
            selected.append(crop)
    expected = (0 if fresh_parent else 2) + (2 if kind == "camera" else 0)
    assert len(selected) == expected
    # Require a full retained case rectangle per method, before reading pixels.
    methods = {identity(c) for c in selected}
    for method in methods:
        group = [c for c in selected if identity(c) == method]
        assert len(group) == 2 and {case_key(c, kind) for c in group} == cases
    return selected


def native_report(fresh_path, retained_path, output, kind, parent_sha, rawnind_sha):
    """Copy exact PNGs into one comparable report; verify source metadata before use."""
    import copy

    from build_native_crop_board import identity, read_crop

    fresh_path, retained_path, output = map(Path, (fresh_path, retained_path, output))
    fresh, retained = read(fresh_path), read(retained_path)
    selected = select_retained(
        fresh["native_crops"], retained["native_crops"], kind, parent_sha, rawnind_sha
    )
    output.mkdir(parents=True, exist_ok=False)
    crops = []
    geometry_checks = {}
    for report, entries, retained_flag in [
        (fresh_path, fresh["native_crops"], False),
        (retained_path, selected, True),
    ]:
        for crop in entries:
            _, _, png = read_crop(report, crop, kind)
            label, digest = identity(crop)
            for field in [
                "native_source_png",
                "native_source_metadata",
                "original_crop",
                "original_PNG",
            ]:
                item = crop.get("model", {}).get(field)
                if item is not None:
                    assert ref(item["path"]) == item
            path = output / ("native-" + crop["png_sha256"] + ".png")
            assert not path.exists()
            shutil.copyfile(png["path"], path)
            result = copy.deepcopy(crop)
            if kind == "synthetic":
                source = crop["source"]
                key = (source["id"], crop["validation_seed"], crop["validation_index"])
                if key not in geometry_checks:
                    geometry_checks[key] = synthetic_geometry(crop, fresh)
                for field, value in geometry_checks[key]["crop_metadata"].items():
                    if field in result:
                        assert result[field] == value, field
                    result[field] = value
            result["image"] = path.name
            result["model"] = {
                **result.get("model", {}),
                "label": label,
                "sha256": digest,
                "native_source_report": ref(report),
                "native_source_PNG": png,
                "retained_baseline": retained_flag,
            }
            crops.append(result)
    path = output / "report.json"
    save(
        path,
        {
            "native_crops": crops,
            "synthetic_geometry_checks": list(geometry_checks.values()),
            "scope": "Fresh fixed cases including the newly evaluated parent plus retained RawNIND-channel PNGs. Exact source bytes/metadata rechecked; unchanged pixels, no resizing, new noise, warping, inference or quality finding. Canonical synthetic GT and independent AHD camera reference labels retained. Manual review required.",
        },
    )
    return path


def synthetic_geometry(crop, report):
    """Derive native cache coordinates from the actual unchanged loader recipe."""
    import random

    import numpy as np
    import torch

    from demosaic.data import CleanDataset

    assert report["native_crop"] is True and report["split"] == "val"
    source, size = crop["source"], report["patch_size"]
    cache = Path(source["cache"])
    if not cache.is_absolute():
        cache = Path(report["manifest"]).parent / cache
    assert sha(cache) == source["cache_sha256"]
    array = np.load(cache, mmap_mode="r", allow_pickle=False)
    assert list(array.shape) == source["shape"]
    height, width = array.shape[:2]
    rng = random.Random(crop["validation_seed"] + crop["validation_index"])
    rng.random()
    y, x = rng.randrange(height - size + 1), rng.randrange(width - size + 1)
    expected = torch.from_numpy(array[y : y + size, x : x + size].copy().astype(np.float32))
    expected = expected.permute(2, 0, 1) / 65535
    dataset = CleanDataset(
        report["manifest"],
        patch_size=size,
        split="val",
        records=[source],
        seed=crop["validation_seed"],
        native_crop=True,
    )
    assert torch.equal(dataset[crop["validation_index"]]["rgb"], expected)
    roi = crop["evaluation_tile_xywh"]
    return {
        "source_id": source["id"],
        "cache": ref(cache),
        "actual_loader_matches_direct_native_slice": True,
        "crop_metadata": {
            "white_balance": report["protocol"]["white_balance"],
            "camera_to_srgb": report["protocol"]["camera_to_srgb"],
            "cache_context_xywh": [x, y, size, size],
            "displayed_cache_ROI_xywh": [x + roi[0], y + roi[1], roi[2], roi[3]],
        },
    }


def main(plan_path):
    os.nice(10)
    plan = read(plan_path)
    root = Path(plan["root"])
    assert ref(__file__) == plan["worker"]
    assert ref(plan["review_plan"]["path"]) == plan["review_plan"]
    for item in plan["retained_native_reports"].values():
        assert ref(item["path"]) == item
    with (root / "closure.claim").open("x") as stream:
        stream.write(str(psutil.Process().pid))
    status = {
        "controller": {"pid": psutil.Process().pid, "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }

    def record(stage, **values):
        status.update(status=stage, updated_unix=time.time(), **values)
        save(root / "closure-status.json", status)
        print(json.dumps({"status": stage}), flush=True)

    try:
        record("waiting-for-exact-directional-interval-review-owner-exit")
        review = read(plan["review_plan"]["path"])
        while not ready(read(Path(review["root"]) / "status.json"), plan["review_owner"]):
            time.sleep(5)
        sys.path[:0] = [str(Path(review["work"]) / p) for p in ("scripts", "src")]
        import torch
        from audit_analytic_summary import main as analytic_audit
        from audit_color_grid_summary import main as summary_audit
        from audit_saved_color_flats import main as case_audit
        from build_native_crop_board import build
        from train_directional_interval_trial import guard

        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        assert psutil.virtual_memory().available > 24 * 2**30
        guard(review)
        out = Path(review["work"]) / "outputs/closure"
        out.mkdir(parents=True, exist_ok=False)
        outputs = {key: Path(value) for key, value in review["outputs"].items()}
        record("auditing-saved-hue-predictions-and-native-renders")
        hue = outputs["hue"] / "report.json"
        case_audit(hue, out / "hue-cases", plan["extra_palettes"])
        report = read(out / "hue-cases/audit.json")
        assert report["observations"] == 1176 and report["float_predictions"] == 3528
        status["completed"].append("hue-case-array-metrics-and-native-renders")
        record("auditing-hue-summary-and-analytic-arithmetic")
        summary_audit(hue, out / "hue-cases/audit.json", out / "hue-summary-audit.json")
        analytic_audit(outputs["analytic"], out / "analytic-audit.json", candidates=2)
        status["completed"].extend(["hue-summary", "analytic-summary"])
        record("binding-fresh-and-retained-native-photo-and-camera-crops")
        boards = []
        for panel, kind in [("full427", "synthetic"), ("known", "camera"), ("unseen", "camera")]:
            report_path = native_report(
                outputs[panel] / "summary.json",
                Path(plan["retained_native_reports"][panel]["path"]),
                out / (panel + "-native-sources"),
                kind,
                plan["retained_parent_sha256"],
                plan["retained_RawNIND_sha256"],
            )
            result = build([report_path], out / (panel + "-native.png"), kind)
            boards.append(
                {
                    "panel": panel,
                    "board": result["board"],
                    "receipt": ref(out / (panel + "-native.json")),
                    "native_cells": result["native_cells_exact"],
                }
            )
        status["completed"].append("fresh-and-retained-photo-camera-native-boards")
        record("building-remaining-native-boards-without-resampling")
        for panel, filename, kind in [
            ("gfx", "report.json", "gfx"),
            ("analytic", "summary.json", "analytic"),
            ("hue", "report.json", "hue"),
            ("highlights", "report.json", "highlights"),
        ]:
            result = build([outputs[panel] / filename], out / (panel + "-native.png"), kind)
            boards.append(
                {
                    "panel": panel,
                    "board": result["board"],
                    "receipt": ref(out / (panel + "-native.json")),
                    "native_cells": result["native_cells_exact"],
                }
            )
        extra = out / "hue-extra-native"
        extra.mkdir()
        for crop in report["additional_native_crops"]:
            source = out / "hue-cases" / crop["image"]
            assert sha(source) == crop["png_sha256"]
            shutil.copyfile(source, extra / source.name)
        save(
            extra / "report.json",
            {
                "native_crops": report["additional_native_crops"],
                "scope": "Same fixed additional palettes from saved arrays.",
            },
        )
        result = build([extra / "report.json"], out / "hue-extra-native.png", "hue")
        boards.append(
            {
                "panel": "hue-extra",
                "board": result["board"],
                "receipt": ref(out / "hue-extra-native.json"),
                "native_cells": result["native_cells_exact"],
            }
        )
        status["completed"].append("remaining-native-boards-created")
        assert not torch.cuda.is_initialized()
        guard(review)
        result = {
            "status": "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review",
            "closure_plan": ref(plan_path),
            "review_terminal": ref(root / "status.json"),
            "hue_cases": ref(out / "hue-cases/audit.json"),
            "hue_summary": ref(out / "hue-summary-audit.json"),
            "analytic_summary": ref(out / "analytic-audit.json"),
            "boards": boards,
            "CUDA_initialized": False,
            "scope": "No new model inference, noise or image selection. CPU-only independent "
            "saved-array/color/analytic arithmetic and exact native PNG rearrangement. Four extra "
            "palettes were declared before new hue outputs existed. All new boards still require "
            "actual manual review and full quality/continuation decision; no promotion.",
        }
        save(root / "closure-result.json", result)
        record(result["status"], result=ref(root / "closure-result.json"))
    except BaseException as error:
        record("failed-CPU-directional-interval-closure-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
