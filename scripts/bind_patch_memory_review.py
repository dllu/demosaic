"""Bind V140's actual endpoint and inherit completed V139 comparisons without inference."""

import argparse
import os
import shutil
from copy import deepcopy
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save
from train_patch_memory_pilot import quality_dependency_ready
from train_v43_quality_trial import live

CONTROL_LABELS = ["V120", "V129 1k EMA", "V136 1k EMA", "V137 1k EMA", "V138 1k EMA"]


def require_completed_training(status, queue, owner_live):
    """Reject an incomplete or substituted owner before importing Torch or loading weights."""
    assert status["plan"] == queue["training_plan"]
    assert status["controller"] == queue["training_owner"]
    assert not owner_live, "Original training owner is still live"
    assert status["status"] == "completed-training-awaiting-model-comparisons"
    assert status.get("child") is None or not live(status["child"])
    return status["completed"]["train-V140"]


def require_training_result(actual):
    assert actual["status"] == "completed-patch-memory-global-pilot-training-phase"
    assert actual["phase"] == "train" and actual["arm"] == "V140"
    assert actual["updates"] == actual["all_AdamW_steps"] == 1000
    assert actual["optimizer_state_count"] == 16 and actual["model_EMA_tensor_count"] == 107
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert actual["raw_global_only"] and actual["frozen_parent91_model_and_EMA_exact"]
    assert actual["all_observed_inputs_match_saved_control"]
    assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 1000
    assert actual["counts"]["encoder_forwards"] == 1064
    assert actual["counts"]["validation_forwards"] == 64
    assert actual["initial_global_offsets"][0]["all_zero"]


def matching_batches(actual, control):
    assert len(actual["observed_inputs"]) == len(control["observed_inputs"]) == 1000
    for i, (a, b) in enumerate(
        zip(actual["observed_inputs"], control["observed_inputs"], strict=True), 1
    ):
        assert a["step"] == b["step"] == i
        assert all(a[k] == b[k] for k in ("domain", "clean_sha256", "batch_sha256"))


def inherit_controls(declared, inherited, predictions, checkpoint, checked=ref):
    """Keep fixed observation fields and four controls, adopt V138, then append V139."""
    assert len(declared) == len(inherited) == len(predictions)
    ids = [o["id"] for o in declared]
    assert len(set(ids)) == len(ids)
    assert [o["id"] for o in inherited] == ids
    predicted = {p["id"]: p for p in predictions}
    assert len(predicted) == len(predictions) and set(predicted) == set(ids)
    result = []
    for original, previous in zip(declared, inherited, strict=True):
        assert {k: v for k, v in original.items() if k != "controls"} == {
            k: v for k, v in previous.items() if k != "controls"
        }, original["id"]
        assert len(original["controls"]) == 4 and len(previous["controls"]) == 5
        assert previous["controls"][:4] == original["controls"]
        labels = []
        for control in previous["controls"]:
            if "model" in control:
                label = control["model"]["label"]
                assert control.get("label", label) == label
            else:
                assert original["kind"] == "mesh"
                label = control["label"]
                expected = "V120-profile3879" if original["id"] == "mesh-profile3879" else "V120"
                assert label == expected
                label = "V120"
            labels.append(label)
        assert labels == CONTROL_LABELS
        observation = deepcopy(previous)
        for control in observation["controls"]:
            assert checked(control["prediction"]["path"]) == control["prediction"]
        prediction = predicted[original["id"]]["prediction"]
        assert checked(prediction["path"]) == prediction
        observation["controls"].append(
            {
                "model": {"label": "V139 1k EMA", "sha256": checkpoint["sha256"], "step": 1000},
                "prediction": deepcopy(prediction),
            }
        )
        result.append(observation)
    return result


def bind(path):
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    path = Path(path)
    queue = read(path)
    guard(queue)
    assert ref(__file__) == queue["endpoint_binder"]
    root = Path(queue["root"])
    assert not (root / "plan-v1.json").exists()
    training = read(queue["training_plan"]["path"])
    status = read(Path(training["root"]) / "status.json")
    binding = require_completed_training(status, queue, live(queue["training_owner"]))
    assert ref(binding["path"]) == binding
    actual = read(binding["path"])
    assert not live(actual["owner"])
    require_training_result(actual)
    control_ref = actual["matched_control_result"]
    assert ref(control_ref["path"]) == control_ref
    control = read(control_ref["path"])
    assert control["arm"] == "V137"
    matching_batches(actual, control)

    baseline_root = Path(read(queue["baseline_quality"]["path"])["root"])
    previous_status = read(baseline_root / "status.json")
    assert previous_status["plan"] == queue["baseline_quality"]
    assert quality_dependency_ready(
        previous_status, queue["baseline_quality_owner"], live(queue["baseline_quality_owner"])
    )
    for key in ("primary_report", "primary_audit", "faint_result", "faint_audit", "camera_JPEGs"):
        assert ref(previous_status[key]["path"]) == previous_status[key]
    for key in ("primary_audit", "faint_audit"):
        assert read(previous_status[key]["path"])["status"].startswith("passed")
    previous_endpoint = read(baseline_root / "endpoint-verification-v1.json")
    previous_binding = previous_endpoint["training_result"]
    assert ref(previous_binding["path"]) == previous_binding
    previous_training = read(previous_binding["path"])
    assert previous_training["arm"] == "V139" and previous_training["updates"] == 1000
    assert previous_training["status"] == "completed-memory-only-global-pilot-training-phase"
    assert previous_training["model_EMA_tensor_count"] == 106
    assert previous_training["optimizer_state_count"] == 15
    assert previous_training["frozen_parent91_model_and_EMA_exact"]
    assert previous_endpoint["checkpoint"]["sha256"] == previous_training["checkpoint"]["sha256"]
    matching_batches(actual, previous_training)
    previous_plan = read(baseline_root / "plan-v1.json")
    guard(previous_plan)
    assert previous_plan["model_label"] == "V139 1k EMA"
    assert previous_plan["checkpoint"] == previous_endpoint["checkpoint"]
    previous_collection = read(baseline_root / "collection-v1.json")
    assert previous_collection["plan"] == ref(baseline_root / "plan-v1.json")
    assert previous_collection["counts"] == {"root": 102, "encoder": 102}
    observations = inherit_controls(
        queue["observations"],
        previous_plan["observations"],
        previous_collection["observations"],
        previous_endpoint["checkpoint"],
    )
    assert len(observations) == 102 and sum(len(o["controls"]) for o in observations) == 612

    # No model construction or neural calls are needed to verify the saved state.
    import torch

    def forbidden(*args, **kwargs):
        raise RuntimeError("Neural module calls are forbidden in the endpoint binder")

    torch.nn.Module._call_impl = forbidden
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    snapshot = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    assert snapshot["step"] == snapshot["config"]["steps"] == 1000
    assert snapshot["config"]["initialized_from"] == {**training["parent"], "step": 20000}
    assert snapshot["model_config"]["raw_global_features"] is True
    assert snapshot["model_config"]["raw_global_conditioning"] == "patch-memory-v4"
    assert not snapshot["model_config"].get("raw_spatial_features", False)
    assert snapshot["config"]["raw_global_only"] is True and snapshot["config"]["lr"] == 1e-3
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    assert len(parent["ema"]) == 91
    for field in ("model", "ema"):
        assert all(torch.equal(snapshot[field][k], v) for k, v in parent["ema"].items())
    trained = Path(snapshot["config"]["source_snapshot"])
    module_files = list((Path(queue["work"]) / "src/demosaic").glob("*.py"))
    assert len(module_files) == 69
    assert all((trained / p.name).read_bytes() == p.read_bytes() for p in module_files)
    assert actual["gradient_observation_steps"] == training["gradient_observation_steps"]
    assert len(actual["global_gradient_snapshots"]) == 56
    assert len(snapshot["model"]) == len(snapshot["ema"]) == 107
    assert snapshot["model"].keys() == snapshot["ema"].keys()
    assert len(snapshot["optimizer"]["state"]) == 16
    assert all(float(s["step"]) == 1000 for s in snapshot["optimizer"]["state"].values())
    values = [*snapshot["model"].values(), *snapshot["ema"].values()]
    values += [
        v
        for s in snapshot["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    ]
    assert all(torch.isfinite(v).all() for v in values)
    keys = [k for k in snapshot["ema"] if k.startswith("pretrained_rgb.raw_global.")]
    assert len(keys) == 16 and all(actual["gradient_maxima"][k] > 0 for k in keys)
    assert snapshot["ema"]["pretrained_rgb.raw_global.project.weight"].count_nonzero() > 0
    assert snapshot["ema"]["pretrained_rgb.raw_global.patch_embed.weight"].count_nonzero() > 0
    assert not torch.cuda.is_initialized()
    dest = root / "V140-step1000-inference.pt"
    with dest.open("xb") as target, Path(checkpoint["path"]).open("rb") as source:
        shutil.copyfileobj(source, target)
    dest.chmod(0o444)
    assert ref(dest)["sha256"] == checkpoint["sha256"]
    adopted = [
        ref(baseline_root / name)
        for name in (
            "status.json",
            "endpoint-verification-v1.json",
            "plan-v1.json",
            "collection-v1.json",
        )
    ] + [
        previous_binding,
        *[
            previous_status[k]
            for k in (
                "primary_report",
                "primary_audit",
                "faint_result",
                "faint_audit",
                "camera_JPEGs",
            )
        ],
    ]
    adopted += [c["prediction"] for o in observations for c in o["controls"]]
    plan = {
        **queue,
        "observations": observations,
        "checkpoint": ref(dest),
        "step": 1000,
        "training_horizon": 1000,
        "progress_checkpoint": False,
        "model_label": "V140 1k EMA",
        "raw_frequency_features": False,
        "raw_spatial_features": False,
        "raw_global_features": True,
        "raw_global_conditioning": "patch-memory-v4",
        "EMA_tensors": 107,
        "expected_lineage": {**training["parent"], "step": 20000},
        "expected_backbone": training["backbones"]["V140"],
        "inputs": [*queue["inputs"], binding, checkpoint, ref(dest), control_ref, *adopted],
    }
    save(
        root / "endpoint-verification-v1.json",
        {
            "training_result": binding,
            "checkpoint": ref(dest),
            "all1000_clean_and_noisy_batches_match_saved_V137": True,
            "all1000_clean_and_noisy_batches_match_actual_V139": True,
            "EMA_tensors": 107,
            "Adam_states": 16,
            "Adam_steps": 1000,
            "finite_state_values": sum(v.numel() for v in values),
            "global_branch_tensors": 16,
            "frozen_parent91_model_and_EMA_exact": True,
            "exact_trained_source_modules": 69,
            "observation_fields_and_existing_control_prefix_exact": True,
            "reused_control_predictions": 612,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
        },
    )
    plan["inputs"].append(ref(root / "endpoint-verification-v1.json"))
    save(root / "plan-v1.json", plan)
    guard(plan)
    print({"endpoint": ref(dest), "plan": ref(root / "plan-v1.json"), "new_neural_forwards": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    bind(parser.parse_args().queue.resolve())
