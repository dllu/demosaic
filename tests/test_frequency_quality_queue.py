import copy

import pytest
import torch
from queue_matched_quality_predictions import execution_arms, verify_frequency_training_state


def test_frequency_training_arms_bind_the_actual_shared_plan():
    binding = {"path": "/cache/plan.json", "sha256": "a" * 64}
    execution = {"arms": {"V122": {}, "V123": {}}, "arm_scopes": {"V122": True, "V123": False}}
    assert execution_arms(execution, binding, "learned-frequency-scopes-v1") == [
        {"arm": "V122", "training_plan": binding},
        {"arm": "V123", "training_plan": binding},
    ]
    execution["arm_scopes"]["V123"] = True
    with pytest.raises(AssertionError):
        execution_arms(execution, binding, "learned-frequency-scopes-v1")


def test_existing_execution_arm_descriptors_are_preserved():
    arms = [{"arm": "V120", "training_plan": {"path": "old-plan.json", "sha256": "old"}}]
    assert execution_arms({"arms": arms}, {}, "matched-execution-v1") is arms


def state_fixture(only):
    snapshot = {
        "step": 20000,
        "config": {"raw_frequency_only": only},
        "model": {"common": torch.tensor([0.2]), "adapter": torch.tensor([0.01])},
        "ema": {"common": torch.tensor([0.2]), "adapter": torch.tensor([0.005])},
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(20000.0), "exp_avg": torch.tensor([0.1])}
                for i in range(5 if only else 94)
            }
        },
    }
    actual = {
        "status": "completed-frequency-training-phase",
        "phase": "train",
        "updates": 20000,
        "counts": dict.fromkeys(
            ("training_forwards", "optimizer_steps", "prepared_training_batches"), 20000
        ),
        "initial_checks": [{"official_encoder_exact": True}],
        "common91_model_and_EMA_exact_to_parent": only,
    }
    return actual, snapshot, {"ema": {"common": torch.tensor([0.2])}}


@pytest.mark.parametrize("only", [False, True])
def test_completed_frequency_state_is_verified_without_neural_calls(monkeypatch, only):
    def forbidden(*args, **kwargs):
        raise AssertionError("State verification must not execute a neural module")

    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)
    verify_frequency_training_state(*state_fixture(only), only)


@pytest.mark.parametrize(
    "change", ["engineering", "short", "scope", "optimizer", "nonfinite", "encoder"]
)
def test_incomplete_or_changed_frequency_state_cannot_enter_quality(change):
    actual, snapshot, parent = state_fixture(True)
    if change == "engineering":
        actual["phase"] = "CUDA"
    elif change == "short":
        actual["counts"]["optimizer_steps"] = 19999
    elif change == "scope":
        snapshot["config"]["raw_frequency_only"] = False
    elif change == "optimizer":
        snapshot["optimizer"]["state"][0]["step"] = torch.tensor(19999.0)
    elif change == "nonfinite":
        snapshot["ema"]["adapter"] = torch.tensor([float("nan")])
    else:
        actual["initial_checks"][0]["official_encoder_exact"] = False
    with pytest.raises(AssertionError):
        verify_frequency_training_state(actual, snapshot, parent, True)


@pytest.mark.parametrize("field", ["model", "ema"])
def test_frequency_only_rejects_common_state_drift(field):
    actual, snapshot, parent = state_fixture(True)
    snapshot = copy.deepcopy(snapshot)
    snapshot[field]["common"].add_(1e-6)
    with pytest.raises(AssertionError):
        verify_frequency_training_state(actual, snapshot, parent, True)
