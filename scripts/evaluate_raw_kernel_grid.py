"""Evaluate only the new RAW-head checkpoint after its completed primary owner exits."""

import argparse
from pathlib import Path

from evaluate_color_grid_cuda import evaluate_records
from review_raw_kernel_results import FULL_JOINT_TRAINING_TERMINAL, completed_primary


def main(inputs, workflow, training_workflow, output):
    status, training, _, training_plan = completed_primary(workflow, training_workflow)
    phase = "matched_control_review" in training_plan
    joint = "review_updates" in training_plan
    full_joint = training["status"] == FULL_JOINT_TRAINING_TERMINAL
    records = [
        {
            **status["checkpoint"],
            "kind": "joint-checkpoint",
            "arm": f"RAW-phase-joint{training_plan['review_updates']}"
            if joint
            else ("RAW-phase-head-warmup1000" if phase else "RAW-head-warmup1000"),
            "comparison_role": "original-joint-schedule-completed"
            if full_joint
            else "separately-initialized-joint-stage"
            if joint
            else ("matched-phase-conditioning" if phase else "exploratory-new-head-warmup"),
        }
    ]
    # No legacy arrays are inserted into this report. Their immutable reports
    # keep their own original model code and can be compared as retained results.
    evaluate_records(
        inputs,
        workflow,
        output,
        records,
        training_plan["parent_sha256"],
        expected_step=training_plan["review_updates"] if joint else 1000,
    )
    (output / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "workflow", "training-workflow", "output"]:
        p.add_argument("--" + name, required=True, type=Path)
    main(**vars(p.parse_args()))
