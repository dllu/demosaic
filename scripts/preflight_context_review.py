"""CPU-only real-checkpoint and historical-arithmetic integration of context review."""

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

from review_context_trial import boundaries, require_completed, run
from score_context_eligibility import evaluate_analytic, evaluate_primary
from score_context_eligibility import main as criteria
from train_directional_interval_trial import read, ref, save

from demosaic.safety import writable_path


def main(training_path, engineering_paths, historical_path, tests_path, output):
    import torch
    from compare_long_commons_scores import rows
    from score_native_data_eligibility import evaluate_analytic as previous_analytic
    from score_native_data_eligibility import evaluate_primary as previous_primary

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    tests = ET.parse(tests_path).getroot()
    cases = tests.findall(".//testcase")
    assert len(cases) >= 25 and not tests.findall(".//failure") and not tests.findall(".//error")
    assert not tests.findall(".//skipped")
    assert {c.get("classname") for c in cases} >= {
        "tests.test_context_review",
        "tests.test_native_data_review",
        "tests.test_directional_bank_review",
    }
    root = writable_path(output)
    root.mkdir(parents=True, exist_ok=False)
    records = []
    assert len(engineering_paths) == 2
    for training in engineering_paths:
        source = read(training)
        destination = root / source["device"]
        destination.mkdir(exist_ok=False)
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
            assert "Production context training boundary" in str(error)
        else:
            raise AssertionError("Engineering boundary accepted as quality")
        for stage in [None, "known", "full427", "gfx", "hue"]:
            try:
                run(destination / "plan.json", stage)
            except ValueError as error:
                assert "cannot produce quality evidence" in str(error)
            else:
                raise AssertionError("Engineering state entered a quality worker")
        assert not (destination / "forbidden.json").exists()
        records.append(ref(destination / "training-boundary.json"))
    assert {read(r["path"])["training_geometry"]["device"] for r in records} == {"cpu", "cuda"}
    production = read(training_path)
    status_path = Path(production["root"]) / "status.json"
    status = read(status_path)
    try:
        require_completed(
            {
                "training_status": str(status_path),
                "training_owner": status["controller"],
                "training_plan": ref(training_path),
            }
        )
    except RuntimeError as error:
        assert "Both fixed context budgets" in str(error)
    else:
        raise AssertionError("Incomplete production accepted")
    historical = read(historical_path)
    control, context = read(Path(historical["root"]) / "training-boundary.json")["checkpoints"]
    stats = read(Path(historical["root"]) / "primary-statistics.json")
    parent = dict(historical["parent"], label="V63-parent")
    primary, previous = (
        evaluate_primary(stats, control, context, parent),
        previous_primary(stats, control, context, parent),
    )
    renamed = copy.deepcopy(previous)
    renamed["matched_context_effect"] = renamed.pop("matched_native_data_effect")
    assert primary == renamed
    analytic_root = Path(historical["outputs"]["analytic"])
    summary, per_case = read(analytic_root / "summary.json"), rows(analytic_root / "per-case.jsonl")
    analytic = evaluate_analytic(summary, per_case, control, context)
    previous = previous_analytic(summary, per_case, control, context)

    def rename(value):
        if isinstance(value, dict):
            return {k.replace("expanded", "context"): rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return value

    assert analytic == rename(previous)
    assert len(analytic["ADC_detail"]["cases"]) == 192
    assert len(analytic["ADC_detail"]["group_means"]) == 12
    save(
        root / "historical-threshold-replay.json",
        {
            "preflight_only": True,
            "historical_review": ref(historical_path),
            "primary": primary,
            "analytic": analytic,
            "scope": "Existing V84/V85 scores only. Positional context role is an arithmetic replay, not V86/V87 evidence.",
        },
    )
    script_names = [
        "review_context_trial",
        "score_context_eligibility",
        "close_context_review",
        "prepare_context_review",
        "queue_context_review",
        "preflight_context_review",
        "review_directional_bank",
        "close_bank_detachment_review",
        "queue_directional_bank_review",
    ]
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-context-review-CPU-integration-no-quality-result",
        "driver": ref(__file__),
        "engineering_boundaries": records,
        "historical_review": ref(historical_path),
        "historical_replay": ref(root / "historical-threshold-replay.json"),
        "historical_primary_arms_and_matched_gates_exact": True,
        "historical_analytic_gates_and_all_ADC_cases_exact": True,
        "incomplete_production_refused": True,
        "engineering_quality_refused": True,
        "ADC_cases": 192,
        "ADC_groups": 12,
        "focused_tests_passed": len(cases),
        "test_receipt": ref(tests_path),
        "CUDA_initialized": False,
        "scripts": [ref(Path("scripts") / (s + ".py")) for s in script_names],
        "scope": "Independent genuine16-update boundary audits and historical arithmetic only. No new held-out prediction or production-quality result.",
    }
    save(root / "receipt.json", receipt)
    print({"receipt": ref(root / "receipt.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["training-plan", "historical-review", "tests", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--engineering-training-plan", type=Path, action="append", required=True)
    args = parser.parse_args()
    main(
        args.training_plan.resolve(),
        [p.resolve() for p in args.engineering_training_plan],
        args.historical_review.resolve(),
        args.tests.resolve(),
        args.output.resolve(),
    )
