"""Evaluate only the new RAW-head checkpoint after its completed primary owner exits."""

import argparse
from pathlib import Path

from evaluate_color_grid_cuda import evaluate_records
from review_raw_kernel_results import completed_primary


def main(inputs, workflow, training_workflow, output):
    status, _, _, training_plan = completed_primary(workflow, training_workflow)
    records = [
        {
            **status["checkpoint"],
            "kind": "joint-checkpoint",
            "arm": "RAW-head-warmup1000",
            "comparison_role": "exploratory-new-head-warmup",
        }
    ]
    # No legacy arrays are inserted into this report. Their immutable reports
    # keep their own original model code and can be compared as retained results.
    evaluate_records(
        inputs, workflow, output, records, training_plan["parent_sha256"], expected_step=1000
    )
    (output / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "workflow", "training-workflow", "output"]:
        p.add_argument("--" + name, required=True, type=Path)
    main(**vars(p.parse_args()))
