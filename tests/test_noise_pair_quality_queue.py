import copy

import pytest
import torch
from queue_matched_quality_predictions import execution_arms, verify_noise_pair_training_state


def completed_state(weight):
    domains = {"commons": 10000, "native": 5000, "paired": 5000}
    snapshot = {
        "step": 20000,
        "config": {"noise_pair_draws": 2, "conditional_mean_weight": weight},
        "model": {str(k): torch.zeros(1) for k in range(91)},
        "ema": {str(k): torch.zeros(1) for k in range(91)},
        "optimizer": {
            "state": {
                k: {"step": torch.tensor(20000.0), "exp_avg": torch.zeros(1)} for k in range(89)
            }
        },
    }
    actual = {
        "status": "completed-noise-pair-training-phase",
        "phase": "train",
        "updates": 20000,
        "conditional_mean_weight": weight,
        "noise_pair_draws": 2,
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "initial_checks": [{"official_encoder_exact": True}],
        "domain_counts": domains,
        "counts": {
            "training_forwards": 20000,
            "optimizer_steps": 20000,
            "prepared_training_batches": 20000,
            "unique_target_contexts": 320000,
            "sensor_observations": 560000,
        },
    }
    return actual, snapshot


@pytest.mark.parametrize("weight", [0.0, 0.25])
def test_full_noise_pair_endpoint_acceptance_never_calls_a_model(monkeypatch, weight):
    def forbidden(*args, **kwargs):
        pytest.fail("Endpoint bookkeeping cannot execute a neural module")

    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)
    verify_noise_pair_training_state(*completed_state(weight), weight)


@pytest.mark.parametrize(
    "change",
    ["short", "engineering", "weight", "draws", "contexts", "observations", "optimizer", "nan"],
)
def test_partial_or_changed_noise_pair_endpoint_cannot_enter_quality(change):
    actual, snapshot = copy.deepcopy(completed_state(0.25))
    if change == "short":
        actual["counts"]["optimizer_steps"] -= 1
    elif change == "engineering":
        actual["phase"] = "CUDA"
    elif change == "weight":
        snapshot["config"]["conditional_mean_weight"] = 0
    elif change == "draws":
        snapshot["config"].update(noise_pair_draws=1, conditional_mean_weight=0)
    elif change in ("contexts", "observations"):
        key = "unique_target_contexts" if change == "contexts" else "sensor_observations"
        actual["counts"][key] -= 16
    elif change == "optimizer":
        snapshot["optimizer"]["state"][0]["step"] -= 1
    else:
        snapshot["ema"]["0"][:] = float("nan")
    with pytest.raises(AssertionError):
        verify_noise_pair_training_state(actual, snapshot, 0.25)


def test_noise_pair_arms_bind_the_actual_shared_plan():
    binding = {"path": "/cache/plan.json", "sha256": "a" * 64}
    execution = {"arms": {"V124": {}, "V125": {}}, "arm_weights": {"V124": 0.0, "V125": 0.25}}
    assert execution_arms(execution, binding, "independent-noise-mean-v1") == [
        {"arm": "V124", "training_plan": binding},
        {"arm": "V125", "training_plan": binding},
    ]
    execution["arm_weights"]["V125"] = 0.5
    with pytest.raises(AssertionError):
        execution_arms(execution, binding, "independent-noise-mean-v1")
