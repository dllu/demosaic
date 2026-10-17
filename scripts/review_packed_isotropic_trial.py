"""Review the completed fresh RAW-native trial with shared frozen observations.

Training completion and actual owner exit are required. These operators do not
train, select a continuation, promote a model or replace native visual review.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import tifffile
import torch
import yaml
from audit_fresh_dino_statistics import audit_photo, audit_real
from audit_long_commons_artifacts import audit_panels
from audit_sensor_mean_artifacts import exited
from compare_long_commons_scores import compare_pair, descriptor, rows
from evaluate_color_grid_cuda import evaluate_records

from demosaic.model import ModelConfig
from demosaic.safety import writable_path

TERMINAL = "completed-matched-first32000-examples-awaiting-full-quality-and-native-review"
STATISTICS_STATUS = "completed-packed-isotropic-first32000-example-statistics"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def training_observations(path):
    records = [record for record in rows(path) if record.get("event") == "train"]
    assert [record["step"] for record in records] == [1, *range(25, 8001, 25)]
    return records


def completed(workflow):
    training = read(workflow)
    if training["status"] != TERMINAL:
        raise RuntimeError("The matched fresh training boundary is incomplete")
    exited(training)
    exited({"controller": training["child"]})
    assert training["all_logged_observations_domain_LR_equal"]
    assert training["actual_fresh_RAW_initialization_and_global_RNG_equal"]
    plan = read(training["plan"])
    assert plan["batch"] == 4 and plan["first_gate_updates"] == 8000
    assert plan["planned_updates_per_arm"] == 160000
    assert plan["first_review_examples_per_arm"] == 32000
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path
    checkpoints, observations, constructions = [], [], []
    for arm in plan["arms"]:
        boundary = training["completed"][arm["arm"]]
        assert boundary["checkpoint"] == ref(arm["target"])
        assert boundary["step"] == 8000 and boundary["planned_updates"] == 160000
        assert boundary["finite_model_EMA_Adam"] and boundary["fresh_initialization"]
        assert (
            boundary["original_schedule_verified"] and boundary["source_recipe_manifests_verified"]
        )
        assert boundary["metrics"] == ref(boundary["metrics"]["path"])
        assert boundary["actual_training"] == ref(boundary["actual_training"]["path"])
        actual = read(boundary["actual_training"]["path"])
        assert actual["fresh"]
        if arm["arm"] == "dino":
            assert actual["genuine_DINO_unchanged_and_gradient_free"]
        recipe = yaml.safe_load(Path(arm["config"]).read_text())
        state = torch.load(arm["target"], map_location="cpu", weights_only=True, mmap=True)
        assert state["step"] == 8000 and state["config"]["steps"] == 160000
        assert "initialized_from" not in state["config"]
        assert state["config"]["source_sha256"] == plan["source_bundle_sha256"]
        assert (
            ModelConfig.from_checkpoint(state["model_config"]).to_dict()
            == ModelConfig(**recipe["model"]).to_dict()
        )
        count = 863 if arm["arm"] == "dino" else 852
        assert len(state["optimizer"]["state"]) == count
        assert actual["all_trainable_tensors_changed_and_finite_gradients"] == count
        assert all(torch.isfinite(v).all() for k in ["model", "ema"] for v in state[k].values())
        for item in state["optimizer"]["state"].values():
            assert int(item["step"]) == 8000
            assert all(torch.isfinite(v).all() for v in item.values())
        observations.append(training_observations(boundary["metrics"]["path"]))
        constructions.append(
            read(Path(training["plan"]).parent / (arm["arm"] + "-fresh-construction.json"))
        )
        checkpoints.append(
            {
                **boundary["checkpoint"],
                "arm": arm["arm"],
                "step": 8000,
                "initialization": "fresh",
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-{arm['arm']}-first32000examples",
            }
        )
        del state
    for records in observations:
        assert [r["step"] for r in records] == [1, *range(25, 8001, 25)]
    for first, second in zip(*observations, strict=True):
        assert all(first[k] == second[k] for k in ["step", "domain", "lr", "batch_sha256"])
    for key in [
        "initial_raw_restoration_sha256",
        "global_torch_RNG_sha256",
        "global_Python_RNG_sha256",
    ]:
        assert constructions[0][key] == constructions[1][key]
    assert [c["arm"] for c in checkpoints] == ["no-dino", "dino"]
    return training, plan, checkpoints


def reference_descriptor(label, digest, model_label, report, cases, summary, records):
    """Publisher weights are shared by two explicitly named gain adapters."""
    matches = [
        m
        for m in summary["models"]
        if m.get("sha256", m.get("weight_sha256")) == digest
        and m["label"] in (model_label, "RawNIND")
    ]
    assert len(matches) == 1 and model_label in {r["model"] for r in records}
    return {
        "label": label,
        "checkpoint_sha256": digest,
        "report": str(report),
        "cases": str(cases),
        "summary": summary,
        "rows": records,
        "model_label": model_label,
    }


def scores(plan, checkpoints, output):
    statistics, comparisons, sources, witnesses = {}, [], [], []
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        folder = Path(plan["outputs"][panel])
        statistics[panel] = (
            audit_photo(folder, 9)
            if panel == "full427"
            else audit_real(
                folder,
                4 if panel == "known" else 5,
                8 if panel == "known" else 10,
                72 if panel == "known" else 90,
                9,
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
            for c in plan["references"]
        ]
        labels = (
            ["RawNIND:CFA-LS", "RawNIND:CFA-channel"]
            if panel == "full427"
            else ["RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"]
        )
        raw = [
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
        pairs = [(current[1], current[0])]
        pairs += [(model, reference) for model in current for reference in [*references, *raw]]
        assert len(pairs) == 9
        for first, second in pairs:
            results, source, witness = compare_pair(panel, first, second)
            comparisons.extend(results)
            sources.append(source)
            witnesses.append(witness)
    assert len(comparisons) == 108 and len(sources) == len(witnesses) == 27
    return {
        "status": STATISTICS_STATUS,
        "statistics": statistics,
        "comparisons": comparisons,
        "sources": sources,
        "matched_classical_control_witnesses": witnesses,
        "scope": "Same saved observations and source-balanced means. DINO/no-DINO is a "
        "matched fresh trial; V43/V63 have different histories and are external quality "
        "references. Two RawNIND publisher adapters share weights and use observed CFA "
        "gain fits, never clean targets. Bootstrap sources are not certified independent "
        "scenes; this is not training-repeat uncertainty, convergence or SOTA evidence.",
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
        plan["grid_inputs"], workflow, output, records, parent["sha256"], expected_step=8000
    )


def artifacts(plan, checkpoints):
    selected = [
        {"sha256": c["sha256"], "arm": c["label"]} for c in [*checkpoints, *plan["references"]]
    ]
    result = audit_panels(
        plan["outputs"],
        selected,
        replay_extra_models=True,
        old_registry=plan["artifact_parent_registry"]["path"],
    )
    # audit_panels checks all selected NN RGB16s. Verify the additional shared
    # RawNIND adapters' actual full exports as well.
    already = {item["path"] for item in result["full_RGB16_files"]}
    folder = Path(plan["outputs"]["gfx"])
    report = read(folder / "report.json")
    assert len(report["full_frames"]) == 6
    extra = []
    for frame in report["full_frames"]:
        assert len(frame["files"]) == 2 and frame["display_exposure"] == 4
        for item in frame["files"]:
            path = folder / item["path"]
            if str(path) in already:
                continue
            assert ref(path)["sha256"] == item["sha256"]
            with tifffile.TiffFile(path) as tif:
                page = tif.pages[0]
                assert page.shape == (8746, 11662, 3) and page.bitspersample == 16
                desc = json.loads(page.description)
                assert desc["bits_per_sample"] == 16
                if "srgb16" in path.name:
                    assert desc["color_space"] == "sRGB" and 34675 in page.tags
                else:
                    assert desc["color_space"] == "linear-camera-RGB"
            value = tifffile.memmap(path, mode="r")
            assert value.dtype == np.uint16 and np.unique(value[::97, ::101]).size > 256
            extra.append({**item, "path": str(path)})
    assert len(extra) == 4 and len(result["full_RGB16_files"]) == 8
    result["additional_RawNIND_RGB16_exports"] = extra
    result["status"] = "completed-fresh-RAW-shared-observation-native-artifact-audit"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["scores", "hue", "artifacts", "training"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = read(args.plan)
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path
    training, _, checkpoints = completed(plan["training_workflow"])
    assert training["controller"] == plan["previous_owner"]
    if args.mode == "hue":
        hue(plan, checkpoints, args.workflow, args.output)
        return
    torch.set_num_threads(2)
    if args.mode == "scores":
        result = scores(plan, checkpoints, args.output)
    elif args.mode == "artifacts":
        result = artifacts(plan, checkpoints)
    else:
        result = {
            "status": "completed-independent-fresh-boundary-state-and-input-checks",
            "checkpoints": checkpoints,
            "training": ref(plan["training_workflow"]),
        }
    output = writable_path(args.output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
