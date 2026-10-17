"""Evaluate both long-data arms after primary exit, retaining audited grid controls.

Run from the frozen model worktree with its package on PYTHONPATH: the shared
engine requires exact model-source and observation identity before array reuse.
"""

import argparse
import copy
from pathlib import Path

from audit_sensor_mean_artifacts import exited
from evaluate_color_grid_cuda import evaluate_records, read
from prepare_color_grid import sha

PARENT = "1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e"
REFERENCE = "b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2"
TRAINING = Path("/mnt/external/demosaic/runs/long-commons-v63-v64-first4k-workflow-v1.json")


def retained_records(reuse_report):
    """Select exact completed V60 and authors' RAW-reference records, unchanged."""
    old = read(reuse_report)
    records = []
    for digest, kind, role in [
        (PARENT, "joint-checkpoint", "V60-full4k-new-stage-parent"),
        (REFERENCE, "authors-RAW-reference-plus-Malvar", "released-nonlocal-reference"),
    ]:
        found = [r for r in old["checkpoints"] if r["sha256"] == digest and r["kind"] == kind]
        assert len(found) == 1
        record = copy.deepcopy(found[0])
        record["comparison_role"] = role
        if kind == "joint-checkpoint":
            assert sha(record["path"]) == digest
        else:
            # The authors' adapter identifies a verified release directory,
            # while sha256 identifies its original RAW checkpoint file.
            root = Path(record["path"])
            assert sha(root / "rawnoise_25_15_9nbr.ckpt") == digest
            receipt = record["reference_receipt"]
            assert receipt["source_checkpoint_sha256"] == digest
            export = receipt["weights_only_export"]
            assert sha(export["path"]) == export["sha256"]
            for name, expected in receipt["source_receipts"].items():
                assert sha(root / name) == expected
        records.append(record)
    return records


def main(inputs, workflow, output, reuse_report, reuse_audit):
    status = read(workflow)
    assert status["status"] == "completed-primary-panels-awaiting-hue-statistical-and-native-review"
    exited(status)
    plan = read(status["plan"])
    training = read(TRAINING)
    assert training["status"] == "trained-both-first4000-awaiting-controlled-quality-review"
    assert training["controller"] == plan["previous_owner"]
    assert training["checkpoints"] == status["checkpoints"]
    assert training["all161_logged_domains_LRs_and_unchanged_domain_hashes_match"]
    exited(training)
    training_plan = read(training["plan"])
    assert training_plan["parent"]["sha256"] == PARENT
    for guard in [plan, training_plan]:
        for path, digest in {
            **guard["inputs"],
            **guard["source_files"],
            **guard.get("tools", {}),
        }.items():
            assert sha(path) == digest, path
    checkpoints = sorted(status["checkpoints"], key=lambda c: c["arm"])
    assert [c["arm"] for c in checkpoints] == ["control", "expanded"]
    retained = retained_records(reuse_report)
    records = [retained[0]]
    for checkpoint in checkpoints:
        assert checkpoint["step"] == 4000 and sha(checkpoint["path"]) == checkpoint["sha256"]
        records.append(
            {
                "path": checkpoint["path"],
                "sha256": checkpoint["sha256"],
                "kind": "joint-checkpoint",
                "arm": checkpoint["arm"] + "-data-stage-first4k",
                "comparison_role": "matched-long-data-" + checkpoint["arm"],
            }
        )
    records.append(retained[1])
    evaluate_records(inputs, workflow, output, records, PARENT, 4000, reuse_report, reuse_audit)
    (output / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "workflow", "output", "reuse-report", "reuse-audit"]:
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
