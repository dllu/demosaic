"""Evaluate V61 against audited parent/V60/nonlocal arrays on the fixed hue grid."""

import argparse
import copy
from pathlib import Path

import psutil
from evaluate_color_grid_cuda import evaluate_records, read
from prepare_color_grid import sha

PARENT = "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3"
CONTROL = "dde398a05fc5df33167d73967d6b5f62ccf3b165f27f8c745b1fdeb45a87f19a"
CANDIDATE = "f4b503c7b511c2d935ffd5dfb2f8f138c75945dfd29a83bc4fd5b2bb8a9ccf72"


def main(inputs, workflow, output, reuse_report, reuse_audit):
    status = read(workflow)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    owner = status["controller"]
    try:
        process = psutil.Process(owner["pid"])
        if (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError("V61 primary evaluation owner remains live")
    except psutil.NoSuchProcess:
        pass
    checkpoint = status["checkpoint"]
    assert (
        checkpoint["step"] == 1000 and checkpoint["sha256"] == sha(checkpoint["path"]) == CANDIDATE
    )
    old = read(reuse_report)
    assert old["checkpoints"][0]["sha256"] == PARENT
    assert old["checkpoints"][2]["sha256"] == CONTROL
    assert old["checkpoints"][3]["kind"] == "authors-RAW-reference-plus-Malvar"
    records = [copy.deepcopy(old["checkpoints"][i]) for i in [0, 2]]
    records[0]["comparison_role"] = "mature-parent"
    records[1]["comparison_role"] = "matched-loss-off-control-V60-first1k"
    records.append(
        {
            "path": checkpoint["path"],
            "sha256": CANDIDATE,
            "kind": "joint-checkpoint",
            "arm": "sensor-mean-additional1k",
            "comparison_role": "loss-on-V61-first1k",
        }
    )
    records.append(copy.deepcopy(old["checkpoints"][3]))
    records[-1]["comparison_role"] = "released-nonlocal-reference"
    evaluate_records(inputs, workflow, output, records, PARENT, 1000, reuse_report, reuse_audit)
    # Archive the entry point as well as the shared engine/helpers.
    archive = output / "source" / Path(__file__).name
    archive.write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "workflow", "output", "reuse-report", "reuse-audit"]:
        parser.add_argument("--" + name, required=True, type=Path)
    main(**vars(parser.parse_args()))
