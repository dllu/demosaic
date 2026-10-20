"""Test saved-array/native review on historical GPU bytes, with no new inference."""

import argparse
import math
import os
import shutil
import statistics
import sys
from pathlib import Path

import numpy as np
import psutil
from audit_uniform_physics_arrays import check_pairs, check_timings
from audit_uniform_physics_arrays import main as audit_current
from PIL import Image
from train_directional_bank_trial import read, ref, save

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]
BASE = Path("/mnt/external/demosaic")
CURRENT = BASE / "experiments/uniform-physics-CUDA-v1/controller-plan.json"


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    assert psutil.virtual_memory().available >= 40 * 2**30
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    sources = output / "sources"
    sources.mkdir()
    names = [
        "audit_uniform_physics_arrays.py",
        "render_uniform_physics_native.py",
        "preflight_uniform_physics_review.py",
        "build_native_crop_board.py",
        "queue_uniform_physics_cuda.py",
        "queue_tf32x3_cuda.py",
        "train_directional_bank_trial.py",
    ]
    for name in names:
        shutil.copy2(REPO / "scripts" / name, sources / name)
    shutil.copytree(REPO / "src", sources / "src", ignore=shutil.ignore_patterns("__pycache__"))
    historical = read(REPO / "docs/results/mature-TF32x3-CUDA-complete-v1.json")
    source = historical["worker_receipt"]
    assert ref(source["path"]) == source
    old = read(source["path"])
    assert (
        old["status"]
        == "completed-isolated-TF32x3-CUDA-array-gates-and-resident-timing-awaiting-native-review"
    )
    plan = read(old["plan"]["path"])
    assert ref(old["plan"]["path"]) == old["plan"]
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    audited = check_pairs(old["cases"], original_key="IEEE")
    assert len(audited) == 6 and sum(c["values"] for c in audited) == 7077888
    assert all(c["passes_original_limits"] for c in audited)
    assert (
        ref(historical["independent_array_replay"]["path"])
        == historical["independent_array_replay"]
    )
    previous = read(historical["independent_array_replay"]["path"])
    for actual, expected in zip(audited, previous["cases"], strict=True):
        assert actual["arrays"] == expected["arrays"]
        assert actual["maximum_DN16"] == expected["maximum_DN16"]
        assert abs(actual["RMS_DN16"] - expected["RMS_DN16"]) <= 1e-15
    timings = []
    for model in ("V43", "V63"):
        samples = [
            {"candidate": t["policy"] == "candidate", "seconds": t["seconds"]}
            for t in old["resident_timings"]
            if t["model"] == model
        ]
        medians = {
            name: statistics.median(t["seconds"] for t in samples if t["candidate"] is flag)
            for name, flag in [("original", False), ("candidate", True)]
        }
        timings.append({"model": model, "samples": samples, "median_seconds": medians})
    checked_times = check_timings(timings, ("V43", "V63"))
    for actual, expected in zip(checked_times, previous["resident_timings"], strict=True):
        assert actual["candidate_over_original_median"] == expected["candidate_over_IEEE_median"]
    # Exercise the actual production entry against the currently live controller.
    try:
        audit_current(CURRENT, output / "must-not-exist-current-review")
    except RuntimeError as error:
        assert str(error) == "Exact CUDA/training/quality owners remain live; no completed review"
    else:
        raise AssertionError("Incomplete current GPU work was accepted")
    assert not (output / "must-not-exist-current-review").exists() and "torch" not in sys.modules
    save(
        output / "historical-array-replay.json",
        {
            "status": "completed-historical-array-arithmetic-integration-no-current-CUDA-result",
            "historical_worker": source,
            "cases": audited,
            "timings": checked_times,
            "Torch_imported": False,
        },
    )
    from render_uniform_physics_native import png_parts, render_cases

    native_path = render_cases(
        old["cases"],
        output / "native",
        original_key="IEEE",
        candidate_label="Historical TF32x3",
        evidence="historical-TF32x3-integration-fixture",
    )
    native = read(native_path)
    previous_native = read(historical["native_report"]["path"])
    assert ref(historical["native_report"]["path"]) == historical["native_report"]
    old_crops = {
        (c["model"]["label"], c["fixture_label"], c["policy"]): c
        for c in previous_native["native_crops"]
    }
    panels = 0
    for crop in native["native_crops"]:
        old_crop = old_crops[
            crop["model"]["base_label"],
            crop["fixture_label"],
            "IEEE" if crop["model"]["policy"] == "original" else "candidate",
        ]
        actual_parts = png_parts(output / "native", crop)
        old_path = Path(historical["native_report"]["path"]).parent / old_crop["image"]
        assert ref(old_path)["sha256"] == old_crop["png_sha256"]
        with Image.open(old_path) as image:
            pixels = np.asarray(image).copy()
        for part, rectangle in zip(actual_parts, old_crop["panels"], strict=True):
            x, y, w, h = rectangle["png_xywh"]
            assert (w, h) == (160, 160) and np.array_equal(part, pixels[y : y + h, x : x + w])
            panels += 1
    assert len(native["native_crops"]) == 24 and panels == 72
    assert native["displayed_board_cells"] == 48 and len(native["boards"]) == 4
    assert native["manual_review_completed"] is False and native["CUDA_initialized"] is False
    assert all(math.isfinite(c["RMS_DN16"]) for c in audited)
    save(
        output / "receipt.json",
        {
            "status": "completed-uniform-physics-review-historical-CPU-integration-no-current-GPU-result",
            "driver": ref(__file__),
            "sources": [ref(p) for p in sorted(sources.rglob("*.py"))],
            "historical_worker": source,
            "historical_native_report": historical["native_report"],
            "array_replay": ref(output / "historical-array-replay.json"),
            "native_report": ref(native_path),
            "historical_RGB_values_independently_reduced": 7077888,
            "historical_timings_arithmetic_exact": True,
            "live_current_GPU_refused_before_output": True,
            "native_triplets": 24,
            "native_panels_match_historical_pixels": panels,
            "native_board_cells": 48,
            "manual_review_completed": False,
            "CUDA_initialized": False,
            "scope": "Historical actual TF32x3 GPU arrays only, explicitly labelled in every crop. No new uniform-physics GPU output, timing, inference, manual viewing, quality conclusion, default change or promotion. All current CUDA results remain pending.",
        },
    )
    print(ref(output / "receipt.json"))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    main(p.parse_args().output.resolve())
