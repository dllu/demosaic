"""Review genuine full-state RAW continuations after both training owners exit.

Reuse verified first-boundary scores for own-model progress; never infer progress
from the matched DINO gap or admit diagnostic weights into a quality comparison.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
import yaml
from compare_long_commons_scores import compare_pair, descriptor, rows
from evaluate_color_grid_cuda import evaluate_records
from review_packed_isotropic_trial import (
    artifacts,
    exited,
    read,
    ref,
    sha,
)
from review_packed_isotropic_trial import (
    completed as first_completed,
)
from review_packed_isotropic_trial import (
    scores as first_scores,
)

from demosaic.model import ModelConfig
from demosaic.safety import writable_path

TERMINAL = "completed-matched-quarter-horizon-awaiting-full-quality-review"
STATISTICS_STATUS = "completed-packed-isotropic-quarter-statistics-and-first8k-progress"


def training_observations(path):
    records = [r for r in rows(path) if r.get("event") == "train"]
    expected = [1, *range(25, 8001, 25), 8001, *range(8025, 40001, 25)]
    assert [r["step"] for r in records] == expected
    return records


def completed(plan):
    training = read(plan["training_workflow"])
    if training["status"] != TERMINAL:
        raise RuntimeError("The matched quarter-horizon training boundary is incomplete")
    exited(training)
    exited({"controller": training["child"]})
    assert training["controller"] == plan["previous_owner"]
    assert training["plan"] == ref(training["plan"]["path"])
    assert training["plan"] == plan["training_plan"]
    train_plan = read(training["plan"]["path"])
    assert train_plan["start"] == 8000 and train_plan["review_step"] == 40000
    assert train_plan["original_horizon"] == 160000 and train_plan["batch"] == 4
    assert train_plan["total_examples_at_review"] == 160000
    assert training["all_logged_observation_domain_LR_matches"]
    for path, digest in {**train_plan["inputs"], **train_plan["guards"]}.items():
        assert sha(path) == digest, path
    # This validates the actual original fresh initialization and full8k state,
    # not merely a parent filename or the absence of an initialization field.
    _, first_plan, first = first_completed(plan["first_training_workflow"])
    assert first_plan["source_bundle_sha256"] == train_plan["source_bundle_sha256"]
    assert first == plan["first_checkpoints"]
    checkpoints, observations = [], []
    for arm, parent in zip(train_plan["arms"], first, strict=True):
        label = arm["arm"]
        assert label == parent["arm"] and arm["parent"] == {
            k: parent[k] for k in ["path", "sha256"]
        }
        boundary = training["completed"][label]
        target = arm["targets"]["40000"]
        assert boundary["checkpoint"] == ref(target)
        assert boundary["step"] == 40000 and boundary["original_horizon"] == 160000
        assert boundary["finite_model_EMA_Adam"]
        assert boundary["actual_training"] == ref(boundary["actual_training"]["path"])
        assert boundary["metrics"] == ref(boundary["metrics"]["path"])
        actual = read(boundary["actual_training"]["path"])
        assert actual["model_optimizer_and_global_RNG_restored_before_first_update"]
        assert actual["EMA_restored_before_first_update"]
        assert actual["first16_training_observations_match_discarded_fixture"]
        count = 863 if label == "dino" else 852
        assert actual["restored_Adam_tensors"] == count
        original = torch.load(parent["path"], map_location="cpu", weights_only=True, mmap=True)
        raw_digest = hashlib.sha256()
        for name, value in original["model"].items():
            if name.startswith("packed_isotropic."):
                raw_digest.update(name.removeprefix("packed_isotropic.").encode())
                raw_digest.update(value.contiguous().numpy().tobytes())
        assert raw_digest.hexdigest() == actual["initial_RAW_sha256"]
        del original
        first16 = read(
            Path(training["plan"]["path"]).parent / (label + "-first16-observations.json")
        )
        fixtures = read(plan["first16_fixtures"])
        assert [r["step"] for r in first16] == list(range(8001, 8017))
        assert all(
            observed["batch_sha256"] == fixture["batch_fingerprint"]
            and observed["step"] == fixture["production_step"]
            and observed["domain"] == fixture["domain"]
            for observed, fixture in zip(first16, fixtures, strict=True)
        )
        if label == "dino":
            assert actual["DINO_unchanged_and_gradient_free"]
            assert actual["DINO_sha256"] == (
                "1d679a021c6c26b5a610281aff421afe8ec33ff0e18dc029c8da736eade9cc36"
            )
        assert actual["checkpoint"] == ref(Path(arm["run"]) / "last.pt")
        assert actual["checkpoint"]["sha256"] == boundary["checkpoint"]["sha256"]
        state = torch.load(target, map_location="cpu", weights_only=True, mmap=True)
        config = state["config"]
        recipe = yaml.safe_load(Path(arm["config"]).read_text())
        assert state["step"] == 40000 and config["steps"] == 160000
        assert config["source_sha256"] == train_plan["source_bundle_sha256"]
        assert "initialized_from" not in config
        assert config["warmup_steps"] == 2000 and config["batch_size"] == 4
        assert config["lr"] == 2e-4 and config["precision"] == "bfloat16"
        assert (
            ModelConfig.from_checkpoint(state["model_config"]).to_dict()
            == ModelConfig(**recipe["model"]).to_dict()
        )
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert config[key + "_sha256"] == train_plan["inputs"][recipe[key]]
        assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in state[key].values())
        assert len(state["optimizer"]["state"]) == count
        for entry in state["optimizer"]["state"].values():
            assert int(entry["step"]) == 40000
            assert all(torch.isfinite(v).all() for v in entry.values())
        assert all(key in state for key in ["torch_rng", "python_rng", "cuda_rng"])
        assert len(state["cuda_rng"]) == 1
        log = Path(boundary["metrics"]["path"])
        assert log.read_bytes().startswith(Path(arm["prefix_metrics"]["path"]).read_bytes())
        assert arm["prefix_metrics"] == ref(arm["prefix_metrics"]["path"])
        records = training_observations(log)
        for row in records:
            step = row["step"]
            warm = min(1, step / 2000)
            progress = max(0, step - 2000) / (160000 - 2000)
            expected_lr = 2e-4 * warm * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            assert row["lr"] == expected_lr
            assert all(math.isfinite(row[k]) for k in ["loss", "grad_norm"])
        observations.append(records)
        checkpoints.append(
            {
                **boundary["checkpoint"],
                "arm": label,
                "step": 40000,
                "initialization": "fresh",
                "kind": "joint-checkpoint",
                "label": f"V{70 if label == 'dino' else 71}-{label}-quarter160000examples",
            }
        )
        del state
    for first_row, second_row in zip(*observations, strict=True):
        assert all(
            first_row[key] == second_row[key] for key in ["step", "domain", "lr", "batch_sha256"]
        )
    return training, train_plan, checkpoints


def progress_pairs(current, parents):
    assert [c["arm"] for c in current] == [c["arm"] for c in parents] == ["no-dino", "dino"]
    assert len({c["sha256"] for c in [*current, *parents]}) == 4
    return list(zip(current, parents, strict=True))


def scores(plan, checkpoints, output):
    # The nine primary pairs retain identical observations and both publisher
    # RawNIND adapters; own progress adds two external saved-score comparisons.
    result = first_scores(plan, checkpoints, output)
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        descriptors = []
        for outputs, models in [
            (plan["outputs"], checkpoints),
            (plan["first_outputs"], plan["first_checkpoints"]),
        ]:
            folder = Path(outputs[panel])
            report, cases = folder / "summary.json", folder / filename
            summary, records = read(report), rows(cases)
            descriptors.append(
                {
                    c["sha256"]: descriptor(
                        c["label"], c["sha256"], report, cases, summary, records
                    )
                    for c in models
                }
            )
        for current, parent in progress_pairs(checkpoints, plan["first_checkpoints"]):
            comparisons, source, witness = compare_pair(
                panel, descriptors[0][current["sha256"]], descriptors[1][parent["sha256"]]
            )
            result["comparisons"].extend(comparisons)
            result["sources"].append(source)
            result["matched_classical_control_witnesses"].append(witness)
    assert len(result["comparisons"]) == 132
    assert len(result["sources"]) == len(result["matched_classical_control_witnesses"]) == 33
    result.update(
        status=STATISTICS_STATUS,
        scope="Matched original fresh DINO/no-DINO trial at40000 updates, with genuine "
        "full-state continuation from8000 under its original160000-update horizon. "
        "Own8k progress reuses hash-bound saved scores after exact observation metadata "
        "and all three classical witnesses match. V43/V63 have different training "
        "histories. Source bootstrap is not training-repeat/scene-independence evidence; "
        "no convergence, quality decision, promotion or SOTA claim.",
    )
    return result


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
        expected_step=40000,
        reuse_report=plan["first_hue_report"]["path"],
        reuse_audit=plan["first_hue_audit"]["path"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["training", "scores", "hue", "artifacts"])
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    plan = read(args.plan)
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path
    torch.set_num_threads(2)
    training, _, checkpoints = completed(plan)
    if args.mode == "hue":
        hue(plan, checkpoints, args.workflow, args.output)
        return
    result = (
        scores(plan, checkpoints, args.output)
        if args.mode == "scores"
        else artifacts(plan, checkpoints)
        if args.mode == "artifacts"
        else {
            "status": "completed-independent-quarter-boundary-full-state-and-observation-audit",
            "training": ref(plan["training_workflow"]),
            "checkpoints": checkpoints,
            "controller": training["controller"],
        }
    )
    output = writable_path(args.output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
