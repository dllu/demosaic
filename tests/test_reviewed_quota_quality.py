"""Endpoint and saved-control contracts using metadata fixtures, never neural calls."""

import copy
import os

import pytest
import queue_quality_comparisons as comparisons
import torch
from queue_matched_quality_predictions import (
    execution_arms,
    training_execution_binding,
    verify_quota_training_state,
)
from train_directional_bank_trial import ref, save


def state_fixture():
    values = {f"restoration.{i}": torch.zeros(1) for i in range(91)}
    control = {"path": "saved-control", "sha256": "a" * 64}
    snapshot = {
        "step": 20000,
        "config": {
            "steps": 20000,
            "seed": 70,
            "reviewed_roi_fraction": 0.05,
            "noise_pair_draws": 1,
            "conditional_mean_weight": 0,
            "reviewed_shadow_fraction": 0,
            "normalized_band_weight": 0,
        },
        "model_config": {"raw_spatial_features": False},
        "model": values,
        "ema": copy.deepcopy(values),
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(20000), "exp_avg": torch.zeros(1)} for i in range(89)
            }
        },
    }
    actual = {
        "status": "completed-reviewed-quota-training-phase",
        "phase": "train",
        "arm": "V133",
        "updates": 20000,
        "counts": {
            "training_forwards": 20000,
            "optimizer_steps": 20000,
            "prepared_training_batches": 20000,
            "validation_forwards": 640,
            "encoder_forwards": 20640,
            "target_contexts": 320000,
        },
        "initial_checks": [
            {"official_encoder_exact": True, "91_parent_or_resume_tensors_exact": True}
        ],
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "model_EMA_tensor_count": 91,
        "matched_control_result": control,
        "observed_inputs": [{"step": i} for i in range(1, 20001)],
    }
    proof = {
        "status": "passed-quota-only-unaffected-batch-and-example-proof",
        "control": control,
        "counts": {
            "native_steps": 4965,
            "native_whole_batches_exact": 4965,
            "paired_steps": 4989,
            "paired_whole_batches_exact": 4989,
            "commons_steps": 10046,
            "commons_whole_batches_exact": 30,
            "Commons_batches_with_expected_selection_changes": 10016,
            "exact_unaffected_prepared_values": 1,
        },
    }
    return actual, snapshot, proof


def test_complete_quota_contract_needs_no_neural_constructor(monkeypatch):
    actual, snapshot, proof = state_fixture()

    def forbidden(*args, **kwargs):
        raise AssertionError("State verification must precede neural construction")

    monkeypatch.setattr(torch.nn.Module, "__init__", forbidden)
    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)
    verify_quota_training_state(actual, snapshot, proof)


@pytest.mark.parametrize(
    "damage",
    [
        "partial",
        "quota",
        "seed",
        "noise",
        "shadow",
        "finite",
        "adam",
        "native",
        "commons",
        "proof",
        "control",
    ],
)
def test_incomplete_changed_or_unmatched_quota_endpoint_rejects(damage):
    actual, snapshot, proof = state_fixture()
    if damage == "partial":
        snapshot["step"] = 1000
    elif damage == "quota":
        snapshot["config"]["reviewed_roi_fraction"] = 0.5
    elif damage == "seed":
        snapshot["config"]["seed"] = 67
    elif damage == "noise":
        snapshot["config"]["noise_pair_draws"] = 2
    elif damage == "shadow":
        snapshot["config"]["reviewed_shadow_fraction"] = 0.5
    elif damage == "finite":
        snapshot["ema"]["restoration.0"].fill_(float("nan"))
    elif damage == "adam":
        snapshot["optimizer"]["state"][0]["step"].fill_(19999)
    elif damage == "native":
        proof["counts"]["native_whole_batches_exact"] -= 1
    elif damage == "commons":
        proof["counts"]["Commons_batches_with_expected_selection_changes"] -= 1
    elif damage == "proof":
        proof["status"] = "unfinished"
    else:
        proof["control"] = {"path": "different control"}
    with pytest.raises(AssertionError):
        verify_quota_training_state(actual, snapshot, proof)


def test_controller_receipt_selects_its_real_nondefault_plan(tmp_path):
    real, decoy = tmp_path / "controller-plan-v1.json", tmp_path / "plan.json"
    save(real, {"actual": True})
    save(decoy, {"actual": False})
    binding, shared = training_execution_binding(tmp_path, {"plan": ref(real)})
    assert binding == ref(real) and shared
    real.write_text("unexpected replacement")
    with pytest.raises(AssertionError):
        training_execution_binding(tmp_path, {"plan": binding})


def test_all_explicit_frozen_recipe_settings_are_checked():
    actual, snapshot, proof = state_fixture()
    expected = {**snapshot["config"], "run": "portable output path", "experiment_notes": "metadata"}
    verify_quota_training_state(actual, snapshot, proof, expected)
    expected["manifest"] = "different data"
    with pytest.raises(AssertionError):
        verify_quota_training_state(actual, snapshot, proof, expected)


def test_quota_execution_declares_only_one_new_model():
    execution = {
        "arms": {"V133": {}},
        "restoration_tensors_by_arm": {"V133": 91},
        "saved_control_arm": "V131",
    }
    binding = {"path": "fixture", "sha256": "a" * 64}
    assert execution_arms(execution, binding, "reviewed-photographic-quota-v1") == [
        {"arm": "V133", "training_plan": binding}
    ]
    execution["arms"]["V131"] = {}
    with pytest.raises(AssertionError):
        execution_arms(execution, binding, "reviewed-photographic-quota-v1")


def fullframe_fixture(sha):
    return {
        "invariants": [
            {
                "checkpoint": {"sha256": sha},
                "calls": 130,
                "encoder_calls": 130,
                "input_sequence": [
                    {"packed": {"sha256": str(i), "dtype": "float32"}} for i in range(130)
                ],
            }
        ]
    }


def test_fullframe_matching_checks_all_actual_tile_batches():
    old, new = fullframe_fixture("old"), fullframe_fixture("new")
    assert (
        comparisons.matching_fullframe_inputs(old, new, "old", "new")["actual_tile_batches_exact"]
        == 130
    )
    new["invariants"][0]["input_sequence"][129]["packed"]["sha256"] = "changed"
    with pytest.raises(ValueError, match="inputs differ"):
        comparisons.matching_fullframe_inputs(old, new, "old", "new")


@pytest.mark.parametrize("damage", ["missing", "duplicate", "count", "encoder", "partial"])
def test_fullframe_input_coverage_cannot_be_inferred_from_a_grid_label(damage):
    old, new = fullframe_fixture("old"), fullframe_fixture("new")
    if damage == "missing":
        new["invariants"] = []
    elif damage == "duplicate":
        new["invariants"] *= 2
    elif damage == "count":
        new["invariants"][0]["calls"] = 129
    elif damage == "encoder":
        new["invariants"][0]["encoder_calls"] = 0
    else:
        new["invariants"][0]["input_sequence"].pop()
    with pytest.raises(ValueError):
        comparisons.matching_fullframe_inputs(old, new, "old", "new")


def deferred_fixture(tmp_path):
    def write(name, payload):
        p = tmp_path / name
        save(p, payload)
        return ref(p)

    owner = {"pid": os.getpid(), "created": 0}
    checkpoints = []
    for arm in ("V131", "V132"):
        p = tmp_path / (arm + ".txt")
        p.write_text("Protocol fixture only: " + arm)
        checkpoints.append({"arm": arm, **ref(p), "expected_lineage": {"step": 20000}})
    training = write("training.json", {"arms": {"V131": {}, "V132": {}}})
    quality = write("quality.json", {"training_execution": training})
    evaluation = write(
        "evaluation.json", {"training_execution": training, "checkpoints": checkpoints}
    )
    boundary = write("boundary.json", {"evaluation_plan": evaluation})
    audit = write(
        "audit.json",
        {
            "owner": owner,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "completed_evaluation": boundary,
        },
    )
    dependency = {
        "owner": owner,
        "plan": {"path": "fixture", "sha256": "a" * 64},
        "quality_plan": quality,
    }
    state = {
        "owner": owner,
        "plan": dependency["plan"],
        "status": comparisons.AUDIT_TERMINAL,
        "result": audit,
    }
    return state, dependency


def test_deferred_control_uses_completed_audit_and_declared_checkpoint(tmp_path):
    state, dependency = deferred_fixture(tmp_path)
    result = comparisons.deferred_reference(state, dependency, "V131")
    assert result["audit"] == state["result"] and result["checkpoint"]["path"].endswith("V131.txt")
    with pytest.raises(ValueError, match="not declared"):
        comparisons.deferred_reference(state, dependency, "V133")


@pytest.mark.parametrize("damage", ["owner", "plan", "failed", "incomplete", "result"])
def test_deferred_control_cannot_accept_replacement_or_unfinished_owner(tmp_path, damage):
    state, dependency = deferred_fixture(tmp_path)
    if damage == "owner":
        state["owner"] = {"pid": -1, "created": 0}
    elif damage == "plan":
        state["plan"] = {}
    elif damage == "failed":
        state["status"] = "failed"
    elif damage == "incomplete":
        state["status"] = "waiting"
    else:
        state["result"]["sha256"] = "b" * 64
    with pytest.raises((ValueError, RuntimeError)):
        comparisons.deferred_reference(state, dependency, "V131")
