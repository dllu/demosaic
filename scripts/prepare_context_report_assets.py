"""Package completed V86/V87 native crops; leave actual review and quality pending."""

import argparse
import os
from pathlib import Path

from close_directional_bank_review import STAGES, TERMINAL, alive
from prepare_bank_report_assets import bundle, checked_reference
from review_context_trial import BOUNDARY, require_completed
from train_directional_interval_trial import guard, read, ref


def ready(plan):
    """Require the actual fixed endpoints and exact successful queued owners."""
    require_completed(plan)
    root = Path(plan["root"])
    queue = read(root / "queue-launch.json")
    assert queue["plan"] == ref(root / "plan.json")
    if any(alive(queue[k]) for k in ("review_owner", "closure_owner", "reference_owner")):
        raise RuntimeError("All exact review/closure/reference owners must exit before packaging")
    state = read(root / "status.json")
    if (
        state["controller"] != queue["review_owner"]
        or state["status"] != TERMINAL
        or len(state["completed"]) != len(STAGES)
        or set(state["completed"]) != STAGES
    ):
        raise ValueError("The exact queued ten-stage review did not complete")
    closure = read(root / "closure-result.json")
    closed = read(root / "closure-status.json")
    if (
        closure["status"]
        != "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review"
        or closed["status"] != closure["status"]
        or closed["controller"] != queue["closure_owner"]
    ):
        raise ValueError("The exact CPU closure did not complete")
    assert closed["result"] == ref(root / "closure-result.json")
    assert checked_reference(closure["review_terminal"]) == root / "status.json"
    references = read(Path(plan["work"]) / "outputs/reference-closure/receipt.json")
    if (
        references["status"]
        != "prepared-directional-working-reference-boards-awaiting-manual-review"
    ):
        raise ValueError("The retained working-reference supplement is incomplete")
    boundary = read(root / "training-boundary.json")
    if (
        boundary["status"] != BOUNDARY
        or boundary["engineering_preflight"] is not False
        or [c["label"] for c in boundary["checkpoints"]] != ["V86-original4000", "V87-original4000"]
        or any(c["step"] != 4000 for c in boundary["checkpoints"])
    ):
        raise ValueError("Expected genuine completed context original4000 endpoints")
    assert boundary["training_status"] == ref(plan["training_status"])
    return closure, references, boundary["checkpoints"]


def main(plan_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan = read(plan_path)
    guard(plan)
    closure, references, checkpoints = ready(plan)
    result = bundle(
        closure,
        references,
        checkpoints,
        output,
        purpose=(
            "Actual completed V86/V87 original4000 fixed-context comparison. Native crop/source "
            "validation only; actual visual review and numerical interpretation remain required. "
            "No quality gain, full-frame eligibility, README change or promotion is implied."
        ),
    )
    guard(plan)
    print({"report_assets": ref(result), "context_adapter": ref(__file__)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.review_plan.resolve(), args.output.resolve())
