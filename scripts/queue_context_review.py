"""Queue the full context review after its exact training owner exits."""

import argparse
from pathlib import Path

from queue_directional_bank_review import main as queue
from train_directional_interval_trial import read, ref


def validate_preflight(proof):
    assert proof["status"] == "completed-context-review-CPU-integration-no-quality-result"
    assert proof["incomplete_production_refused"] and proof["engineering_quality_refused"]
    assert proof["historical_primary_arms_and_matched_gates_exact"]
    assert proof["ADC_cases"] == 192 and proof["ADC_groups"] == 12
    assert proof["focused_tests_passed"] >= 11 and proof["CUDA_initialized"] is False
    assert proof["historical_analytic_gates_and_all_ADC_cases_exact"]
    assert len(proof["engineering_boundaries"]) == 2
    for item in [*proof["scripts"], *proof["engineering_boundaries"], proof["historical_replay"]]:
        assert ref(item["path"]) == item
    for item in proof["engineering_boundaries"]:
        boundary = read(item["path"])
        assert boundary["status"] == "independently-verified-context-engineering-boundaries"
        assert boundary["engineering_preflight"] and all(
            c["step"] == 16 for c in boundary["checkpoints"]
        )
    assert {
        read(item["path"])["training_geometry"]["device"]
        for item in proof["engineering_boundaries"]
    } == {"cpu", "cuda"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    args = parser.parse_args()
    queue(args.plan.resolve(), args.preflight.resolve(), validate_preflight=validate_preflight)
