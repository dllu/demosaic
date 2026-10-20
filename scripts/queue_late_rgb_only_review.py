"""Queue V92 quality only after the actual training owner and all CPU proofs."""

import argparse
from pathlib import Path

from preflight_late_rgb_only_review import COMPLETE
from queue_directional_bank_review import main as queue
from review_late_rgb_only import ENGINEERING_BOUNDARY
from train_directional_bank_trial import guard, read, ref


def validate_preflight(proof):
    assert proof["status"] == COMPLETE and proof["CUDA_initialized"] is False
    assert (
        proof["incomplete_production_refused"]
        and proof["engineering_quality_and_packaging_refused"]
    )
    assert proof["original4000_LR_rows_checked"] == 322
    assert (
        proof["all20_historical_PNGs_exact"]
        and proof["native_cells"] == 125
        and proof["source_triplets"] == 81
    )
    assert proof["focused_tests_passed"] >= 63 and len(proof["engineering_boundaries"]) == 2
    for item in [
        proof["source_plan"],
        proof["test_receipt"],
        proof["historical_tool_replay"],
        proof["historical_assets"],
        *proof["engineering_boundaries"],
        *proof["scripts"],
    ]:
        assert ref(item["path"]) == item
    guard(read(proof["source_plan"]["path"]))
    devices = set()
    for item in proof["engineering_boundaries"]:
        boundary = read(item["path"])
        assert boundary["status"] == ENGINEERING_BOUNDARY and boundary["engineering_preflight"]
        assert all(c["step"] == 16 for c in boundary["checkpoints"])
        assert boundary["recorded_observation_pairs"] == 16
        assert boundary["evidence"][1]["finite_states"] == [115, 115, 24]
        assert boundary["evidence"][1]["common_model_and_EMA_byte_exact_V63"]
        assert boundary["inference_modules_byte_identical"] == 46
        training_status = read(boundary["training_status"]["path"])
        devices.add(read(training_status["plan"]["path"])["device"])
    assert devices == {"cpu", "cuda"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    args = parser.parse_args()
    queue(args.plan.resolve(), args.preflight.resolve(), validate_preflight=validate_preflight)
