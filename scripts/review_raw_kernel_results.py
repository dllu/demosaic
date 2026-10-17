"""Audit a completed RAW-head trial against retained development observations."""

import argparse
import json
from pathlib import Path

import torch
import yaml
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
JOINT_TRAINING_TERMINAL = (
    "completed-joint2000-of-original10000-awaiting-full-quality-and-native-review"
)
FULL_JOINT_TRAINING_TERMINAL = (
    "completed-original-joint10000-awaiting-full-quality-and-native-review"
)


def completed_primary(workflow, training_workflow):
    """Require successful exact owners, unchanged code/data and frozen whole state."""
    status, training = read(workflow), read(training_workflow)
    if status["status"] != PRIMARY_TERMINAL or training["status"] not in (
        TRAINING_TERMINAL,
        JOINT_TRAINING_TERMINAL,
        FULL_JOINT_TRAINING_TERMINAL,
    ):
        raise RuntimeError("RAW-head primary/training workflow has not completed")
    exited(status)
    exited(training)
    primary_plan, training_plan = read(status["plan"]), read(training["plan"])
    assert status["controller"]["driver_sha256"] == primary_plan["driver_sha256"]
    assert training["controller"]["driver_sha256"] == training_plan["driver_sha256"]
    assert primary_plan["previous_owner"] == training["controller"]
    assert status["checkpoint"] == training["checkpoint"]
    recipe = yaml.safe_load(Path(training_plan["recipe"]).read_text())
    joint = recipe.get("raw_kernel_only", False) is False
    if joint:
        assert training["planned_updates"] == recipe["steps"] == 10000
        assert training["finite94model94EMA92Adam"]
        assert training["normalization_buffers_bitwise_parent"]
        parent_review = Path(training_plan["quality_review"])
        assert sha(parent_review) == training_plan["quality_review_sha256"]
        review = read(parent_review)
        assert review["review_complete"] is True
        if training["status"] == FULL_JOINT_TRAINING_TERMINAL:
            assert training["completed_updates"] == training_plan["review_updates"] == 10000
            assert training["resumed_from_step"] == training_plan["resume_from_step"] == 2000
            assert training["original2000_run_and_review_unchanged"] is True
            assert training["all2_fixture_traced_input_hashes_domains_LRs_exact"] is True
            assert sha(training["plan"]) == training["plan_sha256"]
            assert training_plan["resume_review"] == {
                "path": str(parent_review),
                "sha256": training_plan["quality_review_sha256"],
            }
            assert review["boundary"]["step"] == 2000
            assert {
                k: review["checkpoint"][k] for k in ("path", "sha256")
            } == training_plan["resume_checkpoint"]
        else:
            assert training["status"] == JOINT_TRAINING_TERMINAL
            assert training["completed_updates"] == training_plan["review_updates"] == 2000
            assert review["checkpoint"]["sha256"] == training_plan["parent_sha256"]
        assert recipe["model"]["raw_kernel_phase_conditioning"] is True
    else:
        assert recipe["raw_kernel_only"] is True
        assert training["status"] == TRAINING_TERMINAL
        assert training["completed_updates"] == training["planned_updates"] == 1000
        assert training["all91_existing_model_and_EMA_tensors_bitwise_parent"]
    phase = recipe["model"].get("raw_kernel_phase_conditioning", False)
    assert type(phase) is bool
    if phase and not joint:
        assert training["finite94model94EMA3Adam"]
        assert training["all41_V65_control_observations_domains_LRs_exact"]
        control_path = Path(training_plan["matched_control_review"])
        assert sha(control_path) == training_plan["matched_control_review_sha256"]
        control = read(control_path)
        assert control["review_complete"] is True
        control_workflow = control["workflow_records"]["raw-kernel-warmup-v65"]["result"]
        control_plan = read(control_workflow["plan"])
        assert control_plan["parent_sha256"] == training_plan["parent_sha256"]
        old_recipe = yaml.safe_load(Path(control_plan["recipe"]).read_text())
        skip = {"run", "experiment_notes", "model"}
        assert {k: v for k, v in recipe.items() if k not in skip} == {
            k: v for k, v in old_recipe.items() if k not in skip
        }
        assert old_recipe["model"].get("raw_kernel_phase_conditioning", False) is False
        assert {
            k: v for k, v in recipe["model"].items() if k != "raw_kernel_phase_conditioning"
        } == {k: v for k, v in old_recipe["model"].items() if k != "raw_kernel_phase_conditioning"}
    elif not joint:
        assert training["finite_93model_93EMA_2Adam"]
    for plan in [primary_plan, training_plan]:
        for path, digest in plan["guards"].items():
            assert sha(path) == digest, path
    checkpoint = status["checkpoint"]
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    return status, training, primary_plan, training_plan


def compare_one(outputs, checkpoint, expected_methods=4, additional_registry=None):
    """The caller may replay genuine completed historical panels for verification."""
    histories = [
        (label, REPO / path, sha(REPO / path), digest, historical_runs(REPO / path, expected))
        for label, path, expected, digest in REGISTRIES
    ]
    if additional_registry is not None:
        path = Path(additional_registry["path"])
        assert sha(path) == additional_registry["sha256"]
        control = read(path)
        assert control["review_complete"] is True
        digest = control["checkpoint"]["sha256"]
        assert sha(control["checkpoint"]["path"]) == digest
        histories.append(
            (
                additional_registry["label"],
                path,
                sha(path),
                digest,
                control["artifact_integrity"]["runs"],
            )
        )
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
    assert len(comparisons) == 12 * len(histories)
    assert len(sources) == len(witnesses) == 3 * len(histories)
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
    status, training, _, plan = completed_primary(workflow, training_workflow)
    matched = plan.get("matched_control_review")
    full_joint = training["status"] == FULL_JOINT_TRAINING_TERMINAL
    joint = training["status"] in (JOINT_TRAINING_TERMINAL, FULL_JOINT_TRAINING_TERMINAL)
    additional = (
        None
        if matched is None
        else {
            "path": matched,
            "sha256": plan["matched_control_review_sha256"],
            "label": "V65-matched-phase-control",
        }
    )
    if joint:
        additional = {
            "path": plan["quality_review"],
            "sha256": plan["quality_review_sha256"],
            "label": "V67-first2k-same-schedule" if full_joint else "V66-head-warmup-parent",
        }
    checkpoint = {
        **status["checkpoint"],
        "label": (
            f"RAW-phase-joint{plan['review_updates']}"
            if joint
            else ("RAW-phase-head-warmup1000" if matched else "RAW-head-warmup1000")
        ),
    }
    result = {
        "status": "completed-independent-RAW-head-primary-statistics-and-saved-comparisons",
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "training_workflow": str(training_workflow),
        "training_workflow_sha256": sha(training_workflow),
        **compare_one(status["outputs"], checkpoint, additional_registry=additional),
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "scope": (
            "One original V67 schedule, resumed with model/EMA/AdamW/RNG at2000 and completed at10000; the2k comparison measures progress along this single training trajectory, not architecture, unfreezing or seed effects. "
            if full_joint
            else "Separately initialized joint restoration stage from V66 EMA; initialization/scope/seed/LR/budget differ, so this does not isolate unfreezing. "
            if joint
            else "Matched direct-phase-conditioning comparison against V65; additional phase capacity is part of the intervention. "
            if matched
            else "One exploratory new-head warmup, not a matched architecture control. "
        )
        + "Retained V60/V58/V43 differ in initialization/training history; V43 real batch differs. Source intervals do not measure training/selection uncertainty. No inference, output fitting, protected-final score, continuation or promotion.",
    }
    assert training["checkpoint"] == status["checkpoint"]
    output = writable_path(output)
    assert not output.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "comparisons": len(result["comparisons"]),
                "CUDA_initialized": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["workflow", "training-workflow", "output"]:
        p.add_argument("--" + name, required=True, type=Path)
    main(**vars(p.parse_args()))
