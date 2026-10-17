"""Audit a completed RAW-head trial against retained development observations."""

import argparse
import json
from pathlib import Path

import torch
from audit_fresh_dino_statistics import audit_photo, audit_real, sha
from audit_sensor_mean_artifacts import exited
from compare_long_commons_scores import (
    REGISTRIES,
    compare_pair,
    descriptor,
    historical_runs,
    read,
    rows,
)

from demosaic.safety import writable_path

REPO = Path("/home/dllu/proj/demosaic")
PRIMARY_TERMINAL = (
    "completed-primary-panels-awaiting-full-statistics-hue-artifact-and-native-review"
)
TRAINING_TERMINAL = "completed-head-only1000-awaiting-full-quality-and-native-review"


def completed_primary(workflow, training_workflow):
    """Require successful exact owners, unchanged code/data and frozen whole state."""
    status, training = read(workflow), read(training_workflow)
    if status["status"] != PRIMARY_TERMINAL or training["status"] != TRAINING_TERMINAL:
        raise RuntimeError("RAW-head primary/training workflow has not completed")
    exited(status)
    exited(training)
    primary_plan, training_plan = read(status["plan"]), read(training["plan"])
    assert primary_plan["previous_owner"] == training["controller"]
    assert status["checkpoint"] == training["checkpoint"]
    assert training["completed_updates"] == training["planned_updates"] == 1000
    assert training["all91_existing_model_and_EMA_tensors_bitwise_parent"]
    assert training["finite_93model_93EMA_2Adam"]
    for plan in [primary_plan, training_plan]:
        for path, digest in plan["guards"].items():
            assert sha(path) == digest, path
    checkpoint = status["checkpoint"]
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    return status, training, primary_plan, training_plan


def compare_one(outputs, checkpoint, expected_methods=4):
    """The caller may replay genuine completed historical panels for verification."""
    histories = [
        (label, REPO / path, sha(REPO / path), digest, historical_runs(REPO / path, expected))
        for label, path, expected, digest in REGISTRIES
    ]
    statistics, sources, witnesses, comparisons = {}, [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        root = Path(outputs[panel])
        statistics[panel] = (
            audit_photo(root, expected_methods)
            if panel == "full427"
            else audit_real(
                root,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                expected_methods,
                require_rawnind=False,
            )
        )
        report, cases = root / "summary.json", root / filename
        first = descriptor(
            checkpoint["label"], checkpoint["sha256"], report, cases, read(report), rows(cases)
        )
        for label, _, _, digest, runs in histories:
            record = runs[panel]
            old_report = Path(record.get("report", record.get("source")))
            assert sha(old_report) == record.get(
                "report_sha256", record.get("source_report_sha256")
            )
            old_cases = old_report.parent / filename
            second = descriptor(
                label, digest, old_report, old_cases, read(old_report), rows(old_cases)
            )
            result, source, witness = compare_pair(panel, first, second)
            comparisons.extend(result)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 36 and len(sources) == len(witnesses) == 9
    return {
        "statistics": statistics,
        "comparisons": comparisons,
        "sources": sources,
        "witnesses": witnesses,
        "retained_registries": [
            {"label": label, "path": str(path), "sha256": digest, "checkpoint_sha256": ckpt}
            for label, path, digest, ckpt, _ in histories
        ],
        "resampling": {"paired_source_bootstrap": 1000, "seed": 42},
    }


def main(workflow, training_workflow, output):
    assert not torch.cuda.is_initialized()
    status, training, _, _ = completed_primary(workflow, training_workflow)
    checkpoint = {**status["checkpoint"], "label": "RAW-head-warmup1000"}
    result = {
        "status": "completed-independent-RAW-head-primary-statistics-and-saved-comparisons",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "training_workflow": str(training_workflow),
        "training_workflow_sha256": sha(training_workflow),
        **compare_one(status["outputs"], checkpoint),
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "scope": "One exploratory new-head warmup, not a matched architecture control. Retained V60/V58/V43 differ in initialization/training history; V43 real batch differs. Source intervals do not measure training/selection uncertainty. No inference, output fitting, protected-final score, continuation or promotion.",
    }
    assert training["checkpoint"] == status["checkpoint"]
    output = writable_path(output)
    assert not output.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"output": str(output), "comparisons": 36, "CUDA_initialized": False}),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["workflow", "training-workflow", "output"]:
        p.add_argument("--" + name, required=True, type=Path)
    main(**vars(p.parse_args()))
