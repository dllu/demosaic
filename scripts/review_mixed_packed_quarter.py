"""Audit the isolated mixed16 160k-example boundary and its fixed observations."""

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import torch
import yaml
from compare_long_commons_scores import compare_pair, descriptor, rows
from evaluate_color_grid_cuda import evaluate_records
from review_packed_isotropic_trial import artifacts, exited, read, ref

from demosaic.safety import writable_path

# The original reviewer is frozen beside this script by the queue preparer.
_initial_path = Path(__file__).with_name("review_mixed_packed_initial.py")
if not _initial_path.exists():
    _initial_path = Path(__file__).with_name("review_mixed_packed_trial.py")
_spec = importlib.util.spec_from_file_location("mixed16_initial_review", _initial_path)
initial = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(initial)

TERMINAL = "completed-matched-mixed16-quarter160000-examples-awaiting-full-quality-review"
STATISTICS = "completed-packed-isotropic-mixed16-quarter160000-example-statistics"


def startup_checks(checks, arm, fixtures):
    assert checks["parent"] == ref(arm["prefix_checkpoint"])
    assert checks["first_optimizer_step"] == 2001 and checks["completed_continuation"]
    for key in [
        "model_Adam_global_RNG_restored_before_first_update",
        "Adam_param_groups_restored",
        "first16_original_training_inputs_verified",
        "EMA_restored_before_first_EMA_update",
    ]:
        assert checks[key] is True, key
    expected = [
        {
            "data_step": v["production_step"],
            "domain": v["domain"],
            "batch_sha256": v["batch_fingerprint"],
        }
        for v in fixtures
    ]
    assert len(expected) == 16 and checks["first16"] == expected
    assert [v["data_step"] for v in expected] == list(range(8001, 8017))


def check_observations(records):
    expected = [1, 13, *range(25, 2001, 25), 2001, *range(2025, 10001, 25)]
    assert [r["step"] for r in records] == expected
    # Retain the original independent checks, with the additional resume row.
    initial.check_observations(records[:82])
    for row in records[82:]:
        step = row["step"]
        assert row["data_step_start"] == 4 * step - 3 and row["data_step_end"] == 4 * step
        assert row["example_draws"] == 16 * step and row["effective_batch_size"] == 16
        assert row["optimizer_batch_groups"] == 4 and row["optimizer_forward_groups"] == 1
        assert row["domain"] == "mixed"
        progress = (step - 500) / 39500
        lr = 2e-4 * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        assert row["lr"] == lr
        assert all(math.isfinite(row[k]) for k in ["loss", "grad_norm"])
        groups = row["source_groups"]
        assert (
            row["batch_sha256"]
            == hashlib.sha256(json.dumps(groups, sort_keys=True).encode()).hexdigest()
        )
        assert [g["data_step"] for g in groups] == list(range(4 * step - 3, 4 * step + 1))
        for group in groups:
            assert group["examples"] == 4
            assert group["domain"] == initial.training_domain(group["data_step"], 51, 0.25, 0.25)
            assert len(bytes.fromhex(group["batch_sha256"])) == 32


def completed(plan):
    training = read(plan["training_workflow"])
    if training["status"] != TERMINAL:
        raise RuntimeError(
            "Both isolated mixed16 160k-example boundaries must complete before inference"
        )
    assert training["controller"] == plan["previous_owner"]
    exited(training)
    exited({"controller": training["child"]})
    assert training["plan"] == plan["training_plan"] == ref(plan["training_plan"]["path"])
    train_plan = read(plan["training_plan"]["path"])
    for path, digest in {**train_plan["inputs"], **train_plan["guards"]}.items():
        assert initial.sha(path) == digest, path
    assert (
        train_plan["prefix_updates"],
        train_plan["quality_gate_updates"],
        train_plan["quality_gate_examples"],
        train_plan["planned_examples"],
    ) == (2000, 10000, 160000, 640000)
    assert training["verification"] == {
        "logged_macro_rows_per_arm": 403,
        "all_logged_pair_observations_equal": True,
        "original_source_overlaps_per_arm": [403, 403],
    }
    assert plan["initial_review_plan"] == ref(plan["initial_review_plan"]["path"])
    _old, parents, _evidence = initial.completed(read(plan["initial_review_plan"]["path"]))
    checkpoints, logs, evidence = [], [], []
    for arm, parent in zip(train_plan["arms"], parents, strict=True):
        assert ref(arm["prefix_checkpoint"]) == {k: parent[k] for k in ["path", "sha256"]}
        boundary = training["completed"][arm["arm"]]
        assert boundary["checkpoint"] == ref(arm["target"])
        assert boundary["result"] == ref(boundary["result"]["path"])
        assert boundary["actual_restoration"] == ref(boundary["actual_restoration"]["path"])
        actual, checks = (
            read(boundary["result"]["path"]),
            read(boundary["actual_restoration"]["path"]),
        )
        exited({"controller": actual["owner"]})
        assert checks["owner"] == actual["owner"]
        startup_checks(checks, arm, read(train_plan["portable_fixtures"]["path"]))
        assert actual["phase"] == "finish" and actual["arm"] == arm["arm"] and not actual["fresh"]
        assert actual["resume"] == checks["parent"]
        assert (
            actual["start_optimizer_step"],
            actual["end_optimizer_step"],
            actual["actual_prepared_source_groups"],
        ) == (2000, 10000, 32000)
        assert actual["actual_full_state_restore_verified_before_first_backward"]
        assert actual["source_bundle_SHA256"] == train_plan["source_bundle_sha256"]
        assert actual["initial_RAW_state_SHA256"] == train_plan["initial_RAW_state_SHA256"]
        assert actual["finite_model_EMA_Adam_states"] == (863 if arm["arm"] == "dino" else 852)
        assert (actual["all_Adam_steps"], actual["data_steps"], actual["example_draws"]) == (
            10000,
            40000,
            160000,
        )
        assert actual["portable_FP32_bitwise_equal"] and actual["portable_FP32_max_abs"] == 0
        assert actual["checkpoint"] == ref(actual["checkpoint"]["path"])
        assert (
            actual["checkpoint"]["sha256"]
            == actual["portable_checkpoint_hash"]
            == boundary["checkpoint"]["sha256"]
        )
        if arm["arm"] == "dino":
            assert actual["genuine_DINO_unchanged_and_gradient_free"]
            assert actual["DINO_SHA256"] == train_plan["official_frozen_DINO_SHA256"]
        recipe = yaml.safe_load(Path(arm["config"]).read_text())
        source = initial.source_bundle(train_plan, recipe)
        assert source == train_plan["source_bundle_sha256"]
        state = torch.load(arm["target"], map_location="cpu", mmap=True, weights_only=True)
        initial.check_state(state, recipe, train_plan, 10000, source)
        del state
        metric_path = Path(arm["run"]) / "metrics.jsonl"
        assert metric_path.read_bytes().startswith(Path(arm["prefix_metrics"]["path"]).read_bytes())
        records = [r for r in rows(metric_path) if r.get("event") == "train"]
        check_observations(records)
        logs.append(records)
        checkpoints.append(
            {
                **ref(arm["target"]),
                "arm": arm["arm"],
                "step": 10000,
                "data_steps": 40000,
                "example_draws": 160000,
                "initialization": "fresh",
                "continuation": "full-state-from-reviewed2k-on-original-schedule",
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-{arm['arm']}-mixed16-quarter160000examples",
            }
        )
        evidence.append(
            {"arm": arm["arm"], **boundary, "parent": parent, "metrics": ref(metric_path)}
        )
    for a, b in zip(*logs, strict=True):
        assert all(
            a[k] == b[k] for k in ["step", "lr", "batch_sha256", "source_groups", "example_draws"]
        )
    original = rows(plan["original_RAW_metrics"]["path"])
    assert plan["original_RAW_metrics"] == ref(plan["original_RAW_metrics"]["path"])
    for records in logs:
        observed = {g["data_step"]: g for r in records for g in r["source_groups"]}
        overlaps = [r for r in original if r.get("event") == "train" and r["step"] in observed]
        assert len(overlaps) == 403
        for old in overlaps:
            group = observed[old["step"]]
            assert group["batch_sha256"] == old["batch_sha256"]
            assert (
                group["domain"]
                == {
                    "synthetic": "commons",
                    "native-RAW-synthetic": "native",
                    "paired-RAW": "paired",
                }[old["domain"]]
            )
    return training, checkpoints, evidence


def scores(plan, checkpoints):
    result = initial.scores(plan, checkpoints)
    result["status"] = STATISTICS
    result["scope"] = (
        "All primary methods freshly FP32 on shared observations. Mixed16 10k and older RAW40k controls each saw160k examples; units, precision, grouping and EMA differ. New pair differs only in DINO presence/fusion. Own2k progression is audited separately on existing matching observations. One seed; source bootstraps do not certify scene independence or training-repeat uncertainty. No promotion or SOTA claim."
    )
    return result


def progress(plan, checkpoints):
    comparisons, sources, witnesses = [], [], []
    old_plan = read(plan["initial_review_plan"]["path"])
    _training, parents, _ = initial.completed(old_plan)
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        folders = [Path(p["outputs"][panel]) for p in [plan, old_plan]]
        reports = [read(p / "summary.json") for p in folders]
        records = [rows(p / filename) for p in folders]
        for current, parent in zip(checkpoints, parents, strict=True):
            pair = [
                descriptor(
                    c["label"],
                    c["sha256"],
                    folder / "summary.json",
                    folder / filename,
                    summary,
                    values,
                )
                for c, folder, summary, values in zip(
                    [current, parent], folders, reports, records, strict=True
                )
            ]
            cs, source, witness = compare_pair(panel, *pair)
            comparisons.extend(cs)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 24 and len(sources) == len(witnesses) == 6
    return {
        "status": "completed-mixed16-quarter-versus-own32k-parent-statistics",
        "comparisons": comparisons,
        "sources": sources,
        "matched_classical_control_witnesses": witnesses,
        "scope": "Existing2k parent results reused only after exact observation coverage, protocol and classical-control checks. No parent inference or fitting repeated. Six paired source comparisons/24 metrics; same seed and original schedule at different example budgets. Source bootstrap does not cover training-repeat uncertainty.",
    }


def hue(plan, checkpoints, workflow, output):
    parent = next(c for c in plan["references"] if c["label"] == "V63-original20k")
    records = [{**c, "arm": c["label"]} for c in checkpoints]
    records += [
        {**parent, "kind": "joint-checkpoint", "arm": parent["label"]},
        {
            **plan["nonlocal_reference"],
            "kind": "authors-RAW-reference-plus-Malvar",
            "arm": "released-RAW-reference",
        },
    ]
    return evaluate_records(
        plan["grid_inputs"],
        workflow,
        output,
        records,
        parent["sha256"],
        expected_step=10000,
        precision="float32",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["training", "scores", "hue", "artifacts", "progress"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    plan = read(args.plan)
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert initial.sha(path) == digest, path
    _training, checkpoints, evidence = completed(plan)
    if args.mode == "hue":
        hue(plan, checkpoints, args.workflow, args.output)
        return
    result = (
        scores(plan, checkpoints)
        if args.mode == "scores"
        else artifacts(plan, checkpoints)
        if args.mode == "artifacts"
        else progress(plan, checkpoints)
        if args.mode == "progress"
        else {
            "status": "completed-independent-mixed16-quarter-full-state-source-schedule-boundary-audit",
            "training": ref(plan["training_workflow"]),
            "checkpoints": checkpoints,
            "evidence": evidence,
            "actual_model_Adam_global_RNG_and_EMA_restoration_verified": True,
            "all403_logged_mixed_groups_LR_examples_equal": True,
            "first16_resumed_original_inputs_equal": True,
        }
    )
    output = writable_path(args.output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
