"""CPU-only real-boundary, historical-threshold and native-packaging integration."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from review_late_rgb_trial import boundaries, require_completed, run, scheduled_learning_rate
from score_late_rgb_eligibility import evaluate_analytic, evaluate_primary
from score_late_rgb_eligibility import main as criteria
from train_directional_bank_trial import read, ref, save

from demosaic.safety import writable_path


def rename(value):
    if isinstance(value, dict):
        return {k.replace("spectral", "spatial"): rename(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rename(v) for v in value]
    return value


def main(training_path, engineering_paths, historical_path, tests_path, output):
    import torch
    from compare_long_commons_scores import rows
    from prepare_bank_report_assets import bundle

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    tests = ET.parse(tests_path).getroot()
    cases = tests.findall(".//testcase")
    assert len(cases) >= 37 and not any(
        tests.findall(".//" + k) for k in ["failure", "error", "skipped"]
    )
    assert {c.get("classname") for c in cases} >= {
        "tests.test_late_rgb_review",
        "tests.test_context_review",
        "tests.test_directional_bank_review",
    }
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    records = []
    assert len(engineering_paths) == 2
    for training in engineering_paths:
        source = read(training)
        destination = root / source["device"]
        destination.mkdir()
        status_path = Path(source["root"]) / "status.json"
        status = read(status_path)
        plan = {
            "root": str(destination),
            "training_status": str(status_path),
            "training_plan": ref(training),
            "training_owner": status["controller"],
            "engineering_preflight": True,
            "inputs": [],
            "frozen_files": {},
        }
        save(destination / "plan.json", plan)
        boundaries(plan)
        try:
            criteria(destination / "plan.json", destination / "forbidden.json")
        except ValueError as error:
            assert "Production late RGB training boundary" in str(error)
        else:
            raise AssertionError("Engineering state accepted as quality")
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
                run(destination / "plan.json", stage)
            except ValueError as error:
                assert "cannot produce quality evidence" in str(error)
            else:
                raise AssertionError("Engineering state entered quality stage")
        assert not (destination / "forbidden.json").exists()
        records.append(ref(destination / "training-boundary.json"))
    assert {read(r["path"])["training_geometry"]["device"] for r in records} == {"cpu", "cuda"}
    production = read(training_path)
    path = Path(production["root"]) / "status.json"
    status = read(path)
    try:
        require_completed(
            {
                "training_status": str(path),
                "training_owner": status["controller"],
                "training_plan": ref(training_path),
            }
        )
    except RuntimeError as error:
        assert "Both fixed late RGB budgets" in str(error)
    else:
        raise AssertionError("Incomplete production accepted")
    historical = read(historical_path)
    oldroot = Path(historical["root"])
    control, spectral = read(oldroot / "training-boundary.json")["checkpoints"]
    saved = read(Path(historical["work"]) / "outputs/closure/numerical-criteria.json")
    primary = evaluate_primary(
        read(oldroot / "primary-statistics.json"),
        control,
        spectral,
        dict(historical["parent"], label="V63-parent"),
    )
    analytic_root = Path(historical["outputs"]["analytic"])
    analytic = evaluate_analytic(
        read(analytic_root / "summary.json"),
        rows(analytic_root / "per-case.jsonl"),
        control,
        spectral,
    )
    expected_primary = rename(saved["primary"])
    expected_primary["status"] = (
        "applied-predeclared-late-RGB-numerical-criteria-manual-review-pending"
    )
    matched = expected_primary["matched_spatial_effect"]
    matched["gates"]["photo_SSIM_loss_at_most_.0001"] = (
        matched["comparisons"]["photo_SSIM"]["mean_first_minus_second"] >= -0.0001
    )
    matched["all_numerical_criteria_pass"] = all(matched["gates"].values())
    assert primary == expected_primary and analytic == rename(saved["analytic"])
    historical_training = read(historical["training_plan"]["path"])
    historical_status = read(Path(historical_training["root"]) / "status.json")
    lr_rows = 0
    for name in ["control", "spectral"]:
        case = read(historical_status["completed"][name]["path"])
        for row in case["logged_observations"]:
            assert row["lr"] == scheduled_learning_rate(row["step"])
            lr_rows += 1
    assert (
        len(analytic["ADC_detail"]["cases"]) == 192
        and len(analytic["ADC_detail"]["group_means"]) == 12
    )
    save(
        root / "historical-threshold-replay.json",
        {
            "preflight_only": True,
            "historical_review": ref(historical_path),
            "original_criteria": ref(
                Path(historical["work"]) / "outputs/closure/numerical-criteria.json"
            ),
            "primary": primary,
            "analytic": analytic,
            "historical_training_LR_rows_exact": lr_rows,
            "scope": "Existing V88/V89 data only, with positional role renaming and the explicitly predeclared late-RGB matched-SSIM cap. No V90/V91 quality evidence.",
        },
    )
    result = bundle(
        read(oldroot / "closure-result.json"),
        read(Path(historical["work"]) / "outputs/reference-closure/receipt.json"),
        [control, spectral],
        root / "historical-assets",
        purpose="Historical native packaging integration only, not V90/V91 quality evidence or a new manual-view claim.",
    )
    assets = read(result)
    original = read(Path(historical["work"]) / "outputs/report-assets-v1/index.json")
    assert assets["native_cells_verified"] == 125 and assets["source_triplets_verified"] == 81
    assert len(assets["selected_triplets"]) == 12 and len(assets["all_boards"]) == 8
    for key in ["selected_triplets", "all_boards"]:
        assert [x["asset"]["sha256"] for x in assets[key]] == [
            x["asset"]["sha256"] for x in original[key]
        ]
    assert assets["manual_review_completed"] is False and assets["quality_decision"] is None
    names = [
        "review_late_rgb_trial",
        "score_late_rgb_eligibility",
        "close_late_rgb_review",
        "prepare_late_rgb_review",
        "queue_late_rgb_review",
        "preflight_late_rgb_review",
        "prepare_late_rgb_report_assets",
        "review_directional_bank",
        "close_bank_detachment_review",
        "queue_directional_bank_review",
        "prepare_bank_report_assets",
        "watch_bank_report_assets",
    ]
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-late-RGB-review-CPU-integration-no-quality-result",
        "driver": ref(__file__),
        "engineering_boundaries": records,
        "historical_review": ref(historical_path),
        "historical_replay": ref(root / "historical-threshold-replay.json"),
        "historical_primary_arms_and_matched_gates_exact": True,
        "predeclared_matched_SSIM_limit_checked": True,
        "historical_full_horizon_LR_rows_exact": lr_rows,
        "historical_analytic_gates_and_all_ADC_cases_exact": True,
        "historical_packaging": ref(result),
        "all20_historical_PNGs_unchanged": True,
        "native_cells": 125,
        "source_triplets": 81,
        "selected_triplets": 12,
        "incomplete_production_refused": True,
        "engineering_quality_refused": True,
        "ADC_cases": 192,
        "ADC_groups": 12,
        "focused_tests_passed": len(cases),
        "test_receipt": ref(tests_path),
        "CUDA_initialized": False,
        "scripts": [ref(Path("scripts") / (name + ".py")) for name in names],
        "scope": "Real discarded16-state boundary audits, historical criteria and unchanged native packaging only. No new model prediction, held-out quality decision or manual-view claim.",
    }
    save(root / "receipt.json", receipt)
    print({"receipt": ref(root / "receipt.json")})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["training-plan", "historical-review", "tests", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--engineering-training-plan", type=Path, action="append", required=True)
    a = p.parse_args()
    main(
        a.training_plan.resolve(),
        [x.resolve() for x in a.engineering_training_plan],
        a.historical_review.resolve(),
        a.tests.resolve(),
        a.output,
    )
