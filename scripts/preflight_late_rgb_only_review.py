"""Verify genuine discarded states and historical review tools without CUDA inference."""

import argparse
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
TRAINING = Path("/mnt/external/demosaic/experiments/late-rgb-head-only-v92-original4k-v1")
HISTORICAL = Path("/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-review-v1")
COMPLETE = "completed-head-only-review-CPU-integration-no-quality-result"
TOOLS = [
    "review_late_rgb_only",
    "score_late_rgb_only_eligibility",
    "close_late_rgb_only_review",
    "prepare_late_rgb_only_review",
    "queue_late_rgb_only_review",
    "preflight_late_rgb_only_review",
    "prepare_late_rgb_only_report_assets",
    "review_directional_bank",
    "evaluate_gfx_highlight_inputs",
    "prepare_late_rgb_report_assets",
    "prepare_bank_report_assets",
    "close_bank_detachment_review",
    "close_directional_bank_review",
    "prepare_directional_reference_boards",
    "queue_directional_bank_review",
    "score_late_rgb_eligibility",
    "score_context_eligibility",
    "score_directional_bank_eligibility",
    "build_native_crop_board",
    "audit_analytic_summary",
    "audit_saved_color_flats",
    "audit_color_grid_summary",
]


def prepare(root, tests):
    root = Path(root).resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    execution_root = work / "preflight"
    execution_root.mkdir(parents=True)
    trained = Path(read(TRAINING / "plan.json")["work"])
    sources = [*trained.glob("src/demosaic/*.py"), trained / "pyproject.toml", trained / "uv.lock"]
    for source in sources:
        target = work / source.relative_to(trained)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in (REPO / "scripts").glob("*.py"):
        target = work / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    inputs = [
        ref(tests),
        ref(TRAINING / "plan.json"),
        ref(HISTORICAL / "plan.json"),
        ref(HISTORICAL / "closure-result.json"),
    ]
    for name in ["CPU", "CUDA"]:
        path = TRAINING.with_name(f"late-rgb-head-only-v92-{name}16-v1") / "plan.json"
        inputs += [ref(path), ref(path.parent / "status.json")]
    plan = {
        "root": str(execution_root),
        "work": str(work),
        "training": ref(TRAINING / "plan.json"),
        "historical": ref(HISTORICAL / "plan.json"),
        "tests": ref(tests),
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "driver": ref(work / "scripts/preflight_late_rgb_only_review.py"),
    }
    guard(plan)
    save(root / "plan.json", plan)
    print({"plan": ref(root / "plan.json"), "driver": plan["driver"]})


def run(plan_path):
    import torch
    from compare_long_commons_scores import rows
    from prepare_bank_report_assets import bundle
    from prepare_late_rgb_only_report_assets import main as package
    from review_late_rgb_only import (
        boundaries,
        require_completed,
        scheduled_learning_rate,
    )
    from review_late_rgb_only import (
        run as review,
    )
    from score_late_rgb_only_eligibility import evaluate_analytic, evaluate_primary, historical_keys
    from score_late_rgb_only_eligibility import main as criteria

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["driver"]
    root = Path(plan["root"])
    tests = ET.parse(plan["tests"]["path"]).getroot()
    cases = tests.findall(".//testcase")
    assert len(cases) >= 63 and not any(
        tests.findall(".//" + k) for k in ["failure", "error", "skipped"]
    )
    assert {c.get("classname") for c in cases} >= {
        "tests.test_late_rgb_only_review",
        "tests.test_late_rgb_review",
        "tests.test_context_review",
        "tests.test_directional_bank_review",
    }
    records = []
    for name in ["CPU", "CUDA"]:
        source = TRAINING.with_name(f"late-rgb-head-only-v92-{name}16-v1")
        status = read(source / "status.json")
        output = root / name.lower()
        output.mkdir()
        fixture = {
            "root": str(output),
            "training_plan": ref(source / "plan.json"),
            "training_status": str(source / "status.json"),
            "training_owner": status["controller"],
            "engineering_preflight": True,
            "inputs": [],
            "frozen_files": {},
        }
        path = output / "plan.json"
        save(path, fixture)
        boundaries(fixture)
        for stage in [
            None,
            "known",
            "unseen",
            "full427",
            "statistics",
            "sensitivity",
            "gfx",
            "analytic",
            "hue",
            "highlights",
        ]:
            try:
                review(path, stage)
            except ValueError as error:
                assert "cannot produce quality evidence" in str(error)
            else:
                raise AssertionError("Discarded state entered quality stage")
        try:
            criteria(path, output / "forbidden.json")
        except ValueError as error:
            assert "Production head-only training boundary" in str(error)
        else:
            raise AssertionError("Discarded state entered production criteria")
        try:
            package(path, output / "forbidden-assets")
        except ValueError as error:
            assert "cannot produce quality evidence" in str(error)
        else:
            raise AssertionError("Discarded state entered report packaging")
        assert (
            not (output / "forbidden.json").exists() and not (output / "forbidden-assets").exists()
        )
        records.append(ref(output / "training-boundary.json"))
    training = read(plan["training"]["path"])
    status_path = Path(training["root"]) / "status.json"
    status = read(status_path)
    try:
        require_completed(
            {
                "training_status": str(status_path),
                "training_owner": status["controller"],
                "training_plan": plan["training"],
            }
        )
    except RuntimeError as error:
        assert "must complete" in str(error)
    else:
        raise AssertionError("Incomplete V92 accepted by production reader")
    old = HISTORICAL
    historical = read(plan["historical"]["path"])
    checkpoints = read(old / "training-boundary.json")["checkpoints"]
    oldout = Path(historical["work"]) / "outputs"
    saved = read(oldout / "closure/numerical-criteria.json")
    primary = evaluate_primary(
        read(old / "primary-statistics.json"),
        *checkpoints,
        dict(historical["parent"], label="V63-parent"),
    )
    assert primary["historical_reference_vs_parent"] == saved["primary"]["arms"][0]
    assert primary["candidate_vs_parent"] == saved["primary"]["arms"][1]
    assert (
        primary["candidate_minus_historical_comparisons"]
        == saved["primary"]["matched_spatial_effect"]["comparisons"]
    )
    assert (
        primary["candidate_primary_criteria_pass"]
        == saved["primary"]["arms"][1]["all_numerical_criteria_pass"]
    )
    analytic = evaluate_analytic(
        read(oldout / "analytic/summary.json"),
        rows(oldout / "analytic/per-case.jsonl"),
        *checkpoints,
    )
    expected = historical_keys(saved["analytic"])
    expected["comparison_kind"] = (
        "Head-only candidate versus fixed historical global-head reference"
    )
    assert analytic == expected
    lr_rows = 0
    for evidence in read(old / "training-boundary.json")["evidence"]:
        case = read(evidence["result"]["path"])
        for row in case["logged_observations"]:
            assert row["lr"] == scheduled_learning_rate(row["step"])
            lr_rows += 1
    save(
        root / "historical-tool-replay.json",
        {
            "preflight_only": True,
            "historical_checkpoints": checkpoints,
            "primary": primary,
            "analytic": analytic,
            "original4000_LR_rows_checked": lr_rows,
            "scope": "Existing actual V90/V91 observations and labels retained. Role-based scorer replay only; these are not V92 predictions or quality evidence.",
        },
    )
    assets = bundle(
        read(old / "closure-result.json"),
        read(oldout / "reference-closure/receipt.json"),
        checkpoints,
        root / "historical-assets",
        purpose="Historical V90/V91 tool replay only. No V92 predictions, manual-view assertion or new quality finding.",
    )
    actual = read(assets)
    original = read(oldout / "report-assets-v1/index.json")
    for key in ["selected_triplets", "all_boards"]:
        assert [v["asset"]["sha256"] for v in actual[key]] == [
            v["asset"]["sha256"] for v in original[key]
        ]
    assert actual["native_cells_verified"] == 125 and actual["source_triplets_verified"] == 81
    assert actual["manual_review_completed"] is False and actual["quality_decision"] is None
    assert not torch.cuda.is_initialized()
    guard(plan)
    receipt = {
        "status": COMPLETE,
        "driver": ref(__file__),
        "source_plan": ref(plan_path),
        "engineering_boundaries": records,
        "incomplete_production_refused": True,
        "engineering_quality_and_packaging_refused": True,
        "historical_tool_replay": ref(root / "historical-tool-replay.json"),
        "original4000_LR_rows_checked": lr_rows,
        "historical_assets": ref(assets),
        "all20_historical_PNGs_exact": True,
        "native_cells": 125,
        "source_triplets": 81,
        "focused_tests_passed": len(cases),
        "test_receipt": plan["tests"],
        "scripts": [ref(Path(plan["work"]) / "scripts" / (name + ".py")) for name in TOOLS],
        "CUDA_initialized": False,
        "scope": "Independent discarded real CPU/CUDA16-state readers, original historical gates and all native packaging only. No new training, model inference or V92 quality result.",
    }
    save(root / "receipt.json", receipt)
    print({"receipt": ref(root / "receipt.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    p = modes.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("tests", type=Path)
    p = modes.add_parser("run")
    p.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root, args.tests)
    else:
        run(args.plan)
