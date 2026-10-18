"""Review the fresh mixed16 trial after its exact training owners exit.

The 12-update prefix is genuine training. Its immutable archive, full-state
resume receipt, original source schedule and final 32,000-example state must
agree before any quality inference. No automatic continuation or promotion.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
import yaml
from audit_fresh_dino_statistics import audit_photo, audit_real
from compare_long_commons_scores import compare_pair, descriptor, rows
from evaluate_color_grid_cuda import evaluate_records
from review_packed_isotropic_trial import artifacts, exited, read, ref, reference_descriptor, sha

from demosaic.model import ModelConfig
from demosaic.safety import writable_path
from demosaic.train import training_domain

TERMINAL = "completed-matched-mixed16-first32000-examples-awaiting-full-quality-review"
STATISTICS_STATUS = "completed-packed-isotropic-mixed16-first32000-example-statistics"


def source_bundle(plan, recipe):
    work = Path(plan["work"])
    payloads = {p.name: p.read_bytes() for p in (work / "src/demosaic").glob("*.py")}
    payloads.update({name: (work / name).read_bytes() for name in ["pyproject.toml", "uv.lock"]})
    for name, key in [
        ("paired-manifest.json", "paired_manifest"),
        ("raw-clean-manifest.json", "raw_clean_manifest"),
        ("validation-manifest.jsonl", "validation_manifest"),
    ]:
        payloads[name] = Path(recipe[key]).read_bytes()
    payloads["validation_protocol.yaml"] = (work / recipe["validation_protocol"]).read_bytes()
    digest = hashlib.sha256()
    for name, value in sorted(payloads.items()):
        digest.update(name.encode() + value)
    return digest.hexdigest()


def check_state(state, recipe, plan, step, source_sha):
    config = state["config"]
    assert state["step"] == step and state["data_step"] == step * 4
    assert state["example_draws"] == step * 16
    assert "initialized_from" not in config
    for key in [
        "steps",
        "batch_size",
        "optimizer_batch_groups",
        "optimizer_forward_groups",
        "precision",
        "warmup_steps",
        "ema_decay",
        "lr",
        "seed",
        "channels_last",
        "data_seed_per_step",
        "paired_fraction",
        "raw_clean_fraction",
    ]:
        assert config[key] == recipe[key], key
    assert config["steps"] == 40000 and config["warmup_steps"] == 500
    assert config["precision"] == "float32" and config["lr"] == 2e-4
    assert config["ema_decay"] == 0.999**4 and config["batch_size"] == 4
    assert config["optimizer_batch_groups"] == 4 and config["optimizer_forward_groups"] == 1
    assert config["source_sha256"] == source_sha
    for key, value in plan["manifest_hashes"].items():
        assert config[key] == value
    model = ModelConfig.from_checkpoint(state["model_config"])
    assert model.to_dict() == ModelConfig(**recipe["model"]).to_dict()
    assert model.isotropic_raw_gain == 32 and model.isotropic_residual_scale == 1 / 32
    count = 863 if model.dino else 852
    assert len(state["optimizer"]["state"]) == count
    for values in state["optimizer"]["state"].values():
        assert int(values["step"]) == step
        assert all(torch.isfinite(v).all() for v in values.values())
    assert all(torch.isfinite(v).all() for k in ["model", "ema"] for v in state[k].values())
    assert all(k in state for k in ["torch_rng", "python_rng", "cuda_rng"])
    assert len(state["cuda_rng"]) == 1


def check_worker(training, plan, arm, phase, source_sha):
    boundary = training["completed"][phase + "-" + arm["arm"]]
    assert boundary["result"] == ref(boundary["result"]["path"])
    actual = read(boundary["result"]["path"])
    exited({"controller": actual["owner"]})
    prefix = phase == "prefix"
    start, end = (0, 12) if prefix else (12, 2000)
    archive = ref(arm["prefix_checkpoint"] if prefix else arm["target"])
    assert boundary["checkpoint"] == archive
    # The producer's prefix last.pt has since advanced. Bind its recorded hash
    # to the immutable prefix archive; never rehash that mutable historical path.
    assert actual["checkpoint"]["sha256"] == archive["sha256"]
    if not prefix:
        assert actual["checkpoint"] == ref(actual["checkpoint"]["path"])
    assert actual["phase"] == phase and actual["arm"] == arm["arm"]
    assert actual["start_optimizer_step"] == start and actual["end_optimizer_step"] == end
    assert actual["fresh"] is prefix
    assert actual["resume"] == (None if prefix else ref(arm["prefix_checkpoint"]))
    assert actual["first_physical_forward_batch"] == 4
    if prefix:
        assert actual["initial_physical_bilinear_equal"]
    else:
        assert actual["actual_full_state_restore_verified_before_first_backward"]
    assert actual["source_bundle_SHA256"] == source_sha
    assert actual["finite_model_EMA_Adam_states"] == (863 if arm["arm"] == "dino" else 852)
    assert actual["all_Adam_steps"] == end and actual["data_steps"] == 4 * end
    assert actual["example_draws"] == 16 * end
    assert actual["actual_prepared_source_groups"] == 4 * (end - start)
    assert actual["portable_FP32_bitwise_equal"] and actual["portable_FP32_max_abs"] == 0
    assert actual["portable_checkpoint_hash"] == archive["sha256"]
    assert actual["initial_RAW_state_SHA256"] == plan["initial_RAW_state_SHA256"]
    if arm["arm"] == "dino":
        assert actual["genuine_DINO_unchanged_and_gradient_free"]
        assert actual["DINO_SHA256"] == plan["official_frozen_DINO_SHA256"]
    recipe = yaml.safe_load(Path(arm["config"]).read_text())
    state = torch.load(archive["path"], map_location="cpu", weights_only=True, mmap=True)
    check_state(state, recipe, plan, end, source_sha)
    return actual


def check_observations(records):
    assert [r["step"] for r in records] == [1, 13, *range(25, 2001, 25)]
    for row in records:
        step = row["step"]
        assert row["data_step_start"] == 4 * (step - 1) + 1
        assert row["data_step_end"] == 4 * step and row["example_draws"] == 16 * step
        assert row["effective_batch_size"] == 16 and row["optimizer_batch_groups"] == 4
        assert row["optimizer_forward_groups"] == 1 and row["domain"] == "mixed"
        assert all(math.isfinite(row[k]) for k in ["loss", "grad_norm"])
        warmup = min(1, step / 500)
        progress = max(0, step - 500) / (40000 - 500)
        assert row["lr"] == 2e-4 * warmup * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        groups = row["source_groups"]
        assert (
            row["batch_sha256"]
            == hashlib.sha256(json.dumps(groups, sort_keys=True).encode()).hexdigest()
        )
        assert [g["data_step"] for g in groups] == list(range(4 * step - 3, 4 * step + 1))
        for group in groups:
            assert group["examples"] == 4
            assert group["domain"] == training_domain(group["data_step"], 51, 0.25, 0.25)
            assert len(bytes.fromhex(group["batch_sha256"])) == 32


def original_data_matches(observations, original):
    current = {g["data_step"]: g for row in observations for g in row["source_groups"]}
    domains = {"synthetic": "commons", "native-RAW-synthetic": "native", "paired-RAW": "paired"}
    matched = 0
    for row in original:
        if row.get("event") != "train" or row["step"] not in current:
            continue
        group = current[row["step"]]
        assert group["batch_sha256"] == row["batch_sha256"]
        assert group["domain"] == domains[row["domain"]]
        matched += 1
    assert matched == 82
    return matched


def completed(plan):
    training = read(plan["training_workflow"])
    if training["status"] != TERMINAL:
        raise RuntimeError("Both mixed16 training boundaries must complete before review")
    assert training["controller"] == plan["previous_owner"]
    exited(training)
    exited({"controller": training["child"]})
    assert training["plan"] == plan["training_plan"] == ref(training["plan"]["path"])
    train_plan = read(training["plan"]["path"])
    for path, digest in {**train_plan["inputs"], **train_plan["guards"]}.items():
        assert sha(path) == digest, path
    assert train_plan["quality_gate_updates"] == 2000 and train_plan["prefix_updates"] == 12
    assert train_plan["quality_gate_examples"] == 32000 and train_plan["planned_examples"] == 640000
    assert training["all_logged_groups_noise_LR_and_example_counts_equal"]
    checkpoints, observations, constructions, evidence = [], [], [], []
    for arm in train_plan["arms"]:
        recipe = yaml.safe_load(Path(arm["config"]).read_text())
        source_sha = source_bundle(train_plan, recipe)
        checks = [
            check_worker(training, train_plan, arm, phase, source_sha)
            for phase in ["prefix", "finish"]
        ]
        for key in [
            "initial_RAW_state_SHA256",
            "initial_Torch_RNG_SHA256",
            "initial_Python_RNG_SHA256",
        ]:
            assert checks[0][key] == checks[1][key]
        constructions.append(checks[0])
        log = Path(recipe["run"]) / "metrics.jsonl"
        records = [r for r in rows(log) if r.get("event") == "train"]
        check_observations(records)
        observations.append(records)
        checkpoints.append(
            {
                **ref(arm["target"]),
                "arm": arm["arm"],
                "step": 2000,
                "data_steps": 8000,
                "example_draws": 32000,
                "initialization": "fresh",
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-{arm['arm']}-mixed16-first32000examples",
            }
        )
        evidence.append(
            {
                "arm": arm["arm"],
                "source_bundle_sha256": source_sha,
                "metrics": ref(log),
                "prefix": training["completed"]["prefix-" + arm["arm"]],
                "finish": training["completed"]["finish-" + arm["arm"]],
            }
        )
    for key in [
        "initial_RAW_state_SHA256",
        "initial_Torch_RNG_SHA256",
        "initial_Python_RNG_SHA256",
        "source_bundle_SHA256",
    ]:
        assert constructions[0][key] == constructions[1][key]
    root = Path(train_plan["root"])
    first = read(root / "no-dino-first16.json")
    assert first == read(root / "dino-first16.json")
    assert [g["data_step"] for g in first] == list(range(1, 17))
    for a, b in zip(*observations, strict=True):
        assert all(
            a[k] == b[k] for k in ["step", "lr", "batch_sha256", "source_groups", "example_draws"]
        )
    assert plan["original_RAW_metrics"] == ref(plan["original_RAW_metrics"]["path"])
    original = rows(plan["original_RAW_metrics"]["path"])
    for records, receipt in zip(observations, evidence, strict=True):
        receipt["original_RAW_source_noise_groups_matched"] = original_data_matches(
            records, original
        )
    assert [c["arm"] for c in checkpoints] == ["no-dino", "dino"]
    return training, checkpoints, evidence


def scores(plan, checkpoints):
    statistics, comparisons, sources, witnesses = {}, [], [], []
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        folder = Path(plan["outputs"][panel])
        statistics[panel] = (
            audit_photo(folder, 11)
            if panel == "full427"
            else audit_real(
                folder,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                11,
                require_rawnind=True,
            )
        )
        report, cases = folder / "summary.json", folder / filename
        summary, records = read(report), rows(cases)
        current = [
            descriptor(c["label"], c["sha256"], report, cases, summary, records)
            for c in checkpoints
        ]
        references = [
            descriptor(c["label"], c["sha256"], report, cases, summary, records)
            for c in [*plan["references"], *plan["matched_budget_references"]]
        ]
        labels = (
            ["RawNIND:CFA-LS", "RawNIND:CFA-channel"]
            if panel == "full427"
            else ["RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"]
        )
        references += [
            reference_descriptor(
                label,
                plan["rawnind_weights"]["sha256"],
                model_label,
                report,
                cases,
                summary,
                records,
            )
            for label, model_label in zip(
                ["RawNIND-global-CFA", "RawNIND-channel-CFA"], labels, strict=True
            )
        ]
        pairs = [(current[1], current[0])] + [
            (model, reference) for model in current for reference in references
        ]
        assert len(pairs) == 13
        for a, b in pairs:
            result, source, witness = compare_pair(panel, a, b)
            comparisons.extend(result)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 156 and len(sources) == len(witnesses) == 39
    return {
        "status": STATISTICS_STATUS,
        "statistics": statistics,
        "comparisons": comparisons,
        "sources": sources,
        "matched_classical_control_witnesses": witnesses,
        "scope": "All primary NN predictions freshly recomputed in FP32 on shared observations. New pair differs only in DINO presence/fusion. Original RAW8k controls have the same32000-example budget but different units, precision and optimizer grouping; not a one-factor ablation. V43/V63 are mature external quality controls. Source bootstrap is not scene-certified independence or training-repeat uncertainty. No convergence, SOTA or promotion claim.",
    }


def hue(plan, checkpoints, workflow, output):
    parent = next(c for c in plan["references"] if c["label"] == "V63-original20k")
    records = [{**c, "arm": c["label"]} for c in checkpoints]
    records.append({**parent, "kind": "joint-checkpoint", "arm": parent["label"]})
    records.append(
        {
            **plan["nonlocal_reference"],
            "kind": "authors-RAW-reference-plus-Malvar",
            "arm": "released-RAW-reference",
        }
    )
    return evaluate_records(
        plan["grid_inputs"],
        workflow,
        output,
        records,
        parent["sha256"],
        expected_step=2000,
        precision="float32",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["training", "scores", "hue", "artifacts"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    plan = read(args.plan)
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path
    _training, checkpoints, evidence = completed(plan)
    if args.mode == "hue":
        hue(plan, checkpoints, args.workflow, args.output)
        return
    result = (
        scores(plan, checkpoints)
        if args.mode == "scores"
        else artifacts(plan, checkpoints)
        if args.mode == "artifacts"
        else {
            "status": "completed-independent-mixed16-full-state-source-schedule-boundary-audit",
            "training": ref(plan["training_workflow"]),
            "checkpoints": checkpoints,
            "evidence": evidence,
            "first16_groups_equal": True,
            "all82_logged_mixed_groups_LR_examples_equal": True,
            "runtime_restore_check": "Producer verifies model/Adam/global RNG at first resumed forward before backward; independent final/prefix states and original schedule checked here. CPU stop/resume tests separately cover EMA restoration.",
        }
    )
    output = writable_path(args.output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
