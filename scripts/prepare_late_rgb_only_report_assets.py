"""Package V92/historical-V90 native pixels; actual viewing remains required."""

import argparse
import os
from pathlib import Path

from prepare_bank_report_assets import bundle
from prepare_late_rgb_report_assets import ready
from review_late_rgb_only import BOUNDARY, LABELS, require_completed
from train_directional_bank_trial import guard, read, ref


def main(plan_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan = read(plan_path)
    if plan.get("engineering_preflight", False):
        raise ValueError("Discarded engineering checkpoints cannot produce quality evidence")
    guard(plan)
    closure, references, checkpoints = ready(
        plan, training_checker=require_completed, boundary_status=BOUNDARY, labels=LABELS
    )
    result = bundle(
        closure,
        references,
        checkpoints,
        output,
        purpose="Exploratory V92 head-only original4000 versus fixed historical V90 global-head original4000. Both evaluated afresh under unchanged FP32 inputs, with fresh V63 and witnessed V43/RawNIND references. Native pixel/source proof only; actual viewing and quality decisions remain pending. No automatic promotion or extension.",
    )
    guard(plan)
    print({"report_assets": ref(result)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.review_plan.resolve(), args.output.resolve())
