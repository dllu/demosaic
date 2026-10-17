"""Evaluate a sensor-loss trial with audited parent/V60/prior/reference grid arrays."""

import argparse
import copy
from pathlib import Path

import psutil
from evaluate_color_grid_cuda import evaluate_records, read
from prepare_color_grid import sha

PARENT = "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3"
CONTROL = "dde398a05fc5df33167d73967d6b5f62ccf3b165f27f8c745b1fdeb45a87f19a"


def main(
    inputs,
    workflow,
    output,
    reuse_report,
    reuse_audit,
    candidate_arm="sensor-mean-additional1k",
    previous_trial_sha256=None,
):
    status = read(workflow)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    owner = status["controller"]
    try:
        process = psutil.Process(owner["pid"])
        if (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError("Primary evaluation owner remains live")
    except psutil.NoSuchProcess:
        pass
    checkpoint = status["checkpoint"]
    candidate = checkpoint["sha256"]
    assert checkpoint["step"] == 1000 and candidate == sha(checkpoint["path"])
    old = read(reuse_report)

    def previous(digest):
        found = [c for c in old["checkpoints"] if c["sha256"] == digest]
        assert len(found) == 1 and found[0]["kind"] == "joint-checkpoint"
        return copy.deepcopy(found[0])

    records = [previous(digest) for digest in [PARENT, CONTROL]]
    records[0]["comparison_role"] = "mature-parent"
    records[1]["comparison_role"] = "matched-loss-off-control-V60-first1k"
    if previous_trial_sha256:
        assert previous_trial_sha256 not in [PARENT, CONTROL, candidate]
        records.append(previous(previous_trial_sha256))
        records[-1]["comparison_role"] = "previous-sensor-loss-trial-first1k"
    records.append(
        {
            "path": checkpoint["path"],
            "sha256": candidate,
            "kind": "joint-checkpoint",
            "arm": candidate_arm,
            "comparison_role": "new-sensor-loss-trial-first1k",
        }
    )
    references = [c for c in old["checkpoints"] if c["kind"] == "authors-RAW-reference-plus-Malvar"]
    assert len(references) == 1
    records.append(copy.deepcopy(references[0]))
    records[-1]["comparison_role"] = "released-nonlocal-reference"
    evaluate_records(inputs, workflow, output, records, PARENT, 1000, reuse_report, reuse_audit)
    # Archive the entry point as well as the shared engine/helpers.
    archive = output / "source" / Path(__file__).name
    archive.write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "workflow", "output", "reuse-report", "reuse-audit"]:
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--candidate-arm", default="sensor-mean-additional1k")
    parser.add_argument("--previous-trial-sha256")
    main(**vars(parser.parse_args()))
