"""Queue the late RGB review only after CPU integration and actual owner checks."""

import argparse
from pathlib import Path

from queue_directional_bank_review import main as queue
from review_late_rgb_trial import ENGINEERING_BOUNDARY
from train_directional_bank_trial import read, ref


def validate_preflight(proof):
    assert proof["status"] == "completed-late-RGB-review-CPU-integration-no-quality-result"
    assert proof["incomplete_production_refused"] and proof["engineering_quality_refused"]
    assert proof["predeclared_matched_SSIM_limit_checked"]
    assert proof["historical_full_horizon_LR_rows_exact"] >= 322
    assert (
        proof["historical_primary_arms_and_matched_gates_exact"]
        and proof["historical_analytic_gates_and_all_ADC_cases_exact"]
    )
    assert proof["ADC_cases"] == 192 and proof["ADC_groups"] == 12
    assert proof["focused_tests_passed"] >= 37 and proof["CUDA_initialized"] is False
    assert len(proof["engineering_boundaries"]) == 2
    for item in [*proof["scripts"], *proof["engineering_boundaries"], proof["historical_replay"]]:
        assert ref(item["path"]) == item
    for item in proof["engineering_boundaries"]:
        boundary = read(item["path"])
        assert boundary["status"] == ENGINEERING_BOUNDARY and boundary["engineering_preflight"]
        assert all(c["step"] == 16 for c in boundary["checkpoints"])
    assert {
        read(item["path"])["training_geometry"]["device"]
        for item in proof["engineering_boundaries"]
    } == {"cpu", "cuda"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--preflight", type=Path, required=True)
    a = p.parse_args()
    queue(a.plan.resolve(), a.preflight.resolve(), validate_preflight=validate_preflight)
