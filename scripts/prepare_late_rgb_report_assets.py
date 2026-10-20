"""Package completed late RGB native pixels, leaving actual viewing pending."""

import argparse
import os
from pathlib import Path

from close_directional_bank_review import STAGES, TERMINAL, alive
from prepare_bank_report_assets import bundle, checked_reference
from review_late_rgb_trial import BOUNDARY, require_completed
from train_directional_bank_trial import guard, read, ref


def ready(plan):
    require_completed(plan)
    root = Path(plan["root"])
    queue = read(root / "queue-launch.json")
    assert queue["plan"] == ref(root / "plan.json")
    if any(alive(queue[k]) for k in ["review_owner", "closure_owner", "reference_owner"]):
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
        raise ValueError("Retained reference supplement incomplete")
    boundary = read(root / "training-boundary.json")
    if (
        boundary["status"] != BOUNDARY
        or boundary["engineering_preflight"] is not False
        or [c["label"] for c in boundary["checkpoints"]] != ["V90-original4000", "V91-original4000"]
        or any(c["step"] != 4000 for c in boundary["checkpoints"])
    ):
        raise ValueError("Expected genuine completed late RGB original4000 endpoints")
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
        purpose="Actual V90/V91 original4000 global/spatial late RGB comparison. Native pixel/source validation only. Actual visual review and numerical interpretation remain required; no automatic quality gain, full-frame eligibility, README change or promotion.",
    )
    guard(plan)
    print({"report_assets": ref(result), "late_RGB_adapter": ref(__file__)})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review-plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.review_plan.resolve(), a.output.resolve())
