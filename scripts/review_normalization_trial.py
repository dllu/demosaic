"""Review the completed matched normalization first1k gate with frozen operators."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

import torch
import yaml
from audit_fresh_dino_statistics import audit_photo, audit_real
from audit_long_commons_artifacts import audit_panels
from audit_sensor_mean_artifacts import exited
from compare_long_commons_scores import compare_pair, descriptor, rows
from evaluate_color_grid_cuda import evaluate_records

from demosaic.model import ModelConfig
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def completed(training_workflow):
    training = read(training_workflow)
    if training["status"] != "completed-matched-first1000-awaiting-full-quality-and-native-review":
        raise RuntimeError("Matched normalization first1000 training is incomplete")
    exited(training)
    plan = read(training["plan"])
    assert training["all41_logged_observation_domain_LR_fields_match"] is True
    assert plan["planned_updates_per_arm"] == 4000 and plan["first_gate_updates"] == 1000
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path
    checkpoints = []
    for arm in plan["arms"]:
        boundary = training["completed"][arm["arm"]]
        assert boundary["step"] == 1000 and boundary["planned_updates"] == 4000
        assert boundary["finite91model91EMA89Adam"]
        assert boundary["logged_rows"] == 41
        assert boundary["checkpoint"]["sha256"] == sha(arm["target"])
        checkpoints.append(
            {
                **boundary["checkpoint"],
                "arm": arm["arm"],
                "step": 1000,
                "label": f"V{arm['version']}-normalization-{arm['arm']}-first1k",
            }
        )
    assert [c["arm"] for c in checkpoints] == ["control", "augmented"]
    return training, plan, checkpoints


def saved_comparisons(
    outputs, checkpoints, parent_review, parent, *, expected_methods=5, parent_in_current=False
):
    """Actual saved source means; this pure reader also supports historical replay."""
    statistics, sources, witnesses, comparisons = {}, [], [], []
    for panel, filename in [
        ("full427", "per-image.jsonl"),
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
    ]:
        folder = Path(outputs[panel])
        statistics[panel] = (
            audit_photo(folder, expected_methods)
            if panel == "full427"
            else audit_real(
                folder,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                expected_methods,
                require_rawnind=False,
            )
        )
        report, cases = folder / "summary.json", folder / filename
        summary, records = read(report), rows(cases)
        current = [
            descriptor(c["label"], c["sha256"], report, cases, summary, records)
            for c in checkpoints
        ]
        retained = [
            pair[role]
            for pair in parent_review["primary_statistics"]["sources"]
            for role in ["first", "second"]
            if pair["panel"] == panel and pair[role]["checkpoint_sha256"] == parent["sha256"]
        ]
        assert retained and all(item == retained[0] for item in retained)
        retained = retained[0]
        assert sha(retained["report"]) == retained["report_sha256"]
        assert sha(retained["cases"]) == retained["cases_sha256"]
        baseline = (
            descriptor("V63-original20k-parent", parent["sha256"], report, cases, summary, records)
            if parent_in_current
            else descriptor(
                "V63-original20k-parent",
                parent["sha256"],
                retained["report"],
                retained["cases"],
                read(retained["report"]),
                rows(retained["cases"]),
            )
        )
        for first, second in [
            (current[1], current[0]),
            (current[0], baseline),
            (current[1], baseline),
        ]:
            result, source, witness = compare_pair(panel, first, second)
            comparisons.extend(result)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 36 and len(sources) == len(witnesses) == 9
    return {
        "statistics": statistics,
        "sources": sources,
        "witnesses": witnesses,
        "comparisons": comparisons,
    }


def audit_states(plan, checkpoints):
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    result = {}
    for checkpoint in checkpoints:
        arm = next(a for a in plan["arms"] if a["arm"] == checkpoint["arm"])
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
        assert state["step"] == 1000 and state["config"]["steps"] == 4000
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["source_sha256"] == plan["source_bundle_sha256"]
        assert state["config"]["initialized_from"] == {**plan["parent"], "step": 20000}
        assert (
            ModelConfig.from_checkpoint(state["model_config"]).to_dict()
            == ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        )
        assert len(state["model"]) == len(state["ema"]) == 91
        assert len(state["optimizer"]["state"]) == 89
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
            assert sorted(
                k for k, v in state[field].items() if torch.equal(v, parent["ema"][k])
            ) == ["context.mean", "context.std"]
        for item in state["optimizer"]["state"].values():
            assert int(item["step"]) == 1000
            assert all(
                torch.isfinite(v).all() for v in item.values() if isinstance(v, torch.Tensor)
            )
        assert all(key in state for key in ["python_rng", "torch_rng", "cuda_rng"])
        snapshot = Path(state["config"]["source_snapshot"])
        digest = hashlib.sha256()
        for path in sorted(
            p for p in snapshot.iterdir() if p.is_file() and p.name != "manifest.jsonl"
        ):
            digest.update(path.name.encode() + path.read_bytes())
        assert digest.hexdigest() == plan["source_bundle_sha256"]
        assert sha(snapshot / "manifest.jsonl") == state["config"]["manifest_sha256"]
        for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]:
            assert state["config"][key + "_sha256"] == sha(cfg[key])
        result[checkpoint["arm"]] = {
            "checkpoint": checkpoint,
            "step": 1000,
            "planned_updates": 4000,
            "finite_state_counts": [91, 91, 89],
            "source_recipe_parent_data_and_context_buffers_verified": True,
            "complete_RNG_present": True,
        }
    return result


def main(args):
    torch.set_num_threads(2)
    training, train_plan, checkpoints = completed(args.training_workflow)
    plan, workflow = read(args.review_plan), read(args.review_workflow)
    assert plan["previous_owner"] == training["controller"]
    assert workflow["primary_complete"] is True
    assert sha(plan["parent_review"]["path"]) == plan["parent_review"]["sha256"]
    parent_review = read(plan["parent_review"]["path"])
    common = {
        "training_workflow": ref(args.training_workflow),
        "review_plan": ref(args.review_plan),
        "operator": ref(__file__),
        "step": 1000,
        "planned_updates": 4000,
    }
    if args.action == "hue":
        old = read(plan["parent_hue"]["path"])
        assert sha(plan["parent_hue"]["path"]) == plan["parent_hue"]["sha256"]
        reference = [
            r for r in old["checkpoints"] if r["kind"] == "authors-RAW-reference-plus-Malvar"
        ]
        assert len(reference) == 1
        records = [
            {**train_plan["parent"], "kind": "joint-checkpoint", "arm": "V63-original20k-parent"}
        ]
        records += [
            {**{k: c[k] for k in ["path", "sha256"]}, "kind": "joint-checkpoint", "arm": c["label"]}
            for c in checkpoints
        ]
        records.append(copy.deepcopy(reference[0]))
        evaluate_records(
            Path(plan["grid_inputs"]),
            args.review_workflow,
            args.output,
            records,
            train_plan["parent"]["sha256"],
            1000,
        )
        return
    assert not torch.cuda.is_initialized()
    if args.action == "scores":
        result = {
            "status": "completed-normalization-trial-statistics-and-parent-comparisons",
            **common,
            **saved_comparisons(
                plan["outputs"],
                checkpoints,
                parent_review,
                train_plan["parent"],
                expected_methods=6,
                parent_in_current=True,
            ),
            "scope": "One seed. Matched policy comparison plus parent progress after a fresh optimizer. Same numerical/observation witnesses and source bootstrap; no quality selection, new inference or convergence claim.",
        }
        output = writable_path(args.output)
        assert not output.exists()
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        evaluated = checkpoints + [{**train_plan["parent"], "arm": "parent", "step": 20000}]
        artifacts = audit_panels(
            plan["outputs"],
            evaluated,
            old_registry=Path(plan["artifact_parent_registry"]["path"]),
        )
        assert len(artifacts["images"]) == 57 and len(artifacts["float_arrays"]) == 29
        assert len(artifacts["full_RGB16_files"]) == 6
        result = {
            "status": "completed-normalization-first1k-state-and-artifact-audit",
            **common,
            "boundary": audit_states(train_plan, checkpoints),
            **artifacts,
            "CUDA_initialized": False,
        }
        output = writable_path(args.output)
        output.mkdir(parents=True, exist_ok=False)
        (output / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scores", "hue", "artifacts"])
    for name in ["training-workflow", "review-plan", "review-workflow", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())
