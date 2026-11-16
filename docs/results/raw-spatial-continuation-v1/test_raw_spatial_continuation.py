import copy

import pytest
import torch
from resume_raw_spatial_trial import (
    HORIZON,
    PREFIX,
    equal_state,
    relocated_config,
    validate_prefix,
)


def prefix():
    state = {
        "step": PREFIX,
        "config": {"steps": HORIZON, "seed": 70, "data_seed_per_step": True},
        "model": {str(i): torch.zeros(1) for i in range(91)},
        "ema": {str(i): torch.zeros(1) for i in range(91)},
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(float(PREFIX)), "exp_avg": torch.ones(1)}
                for i in range(89)
            }
        },
        "torch_rng": torch.get_rng_state(),
        "python_rng": (),
        "cuda_rng": [torch.zeros(1, dtype=torch.uint8)],
    }
    failure = {
        "error": "RuntimeError('Stopping safely: only 31.6 GB system memory available')",
        "counts": {
            "prepared_training_batches": PREFIX,
            "training_forwards": PREFIX,
            "optimizer_steps": PREFIX,
            "validation_forwards": 448,
            "encoder_forwards": PREFIX + 448,
            "target_contexts": PREFIX * 16,
        },
        "observed_inputs": [{"step": i} for i in range(1, PREFIX + 1)],
    }
    return state, failure


def test_complete_saved_prefix_admitted():
    validate_prefix(*prefix())


@pytest.mark.parametrize(
    "change", ["step", "horizon", "adam", "ema", "rng", "trace", "counts", "nonfinite"]
)
def test_partial_or_changed_prefix_rejected(change):
    state, failure = prefix()
    if change == "step":
        state["step"] -= 1
    elif change == "horizon":
        state["config"]["steps"] += 1
    elif change == "adam":
        state["optimizer"]["state"][0]["step"] -= 1
    elif change == "ema":
        state["ema"].pop("0")
    elif change == "rng":
        state["cuda_rng"] = []
    elif change == "trace":
        failure["observed_inputs"][-1]["step"] -= 1
    elif change == "counts":
        failure["counts"]["encoder_forwards"] -= 1
    elif change == "nonfinite":
        state["model"]["0"][0] = float("nan")
    with pytest.raises(AssertionError):
        validate_prefix(state, failure)


def test_relocation_preserves_original_recipe_and_input():
    source = {
        "run": "old",
        "steps": HORIZON,
        "seed": 70,
        "data_seed_per_step": True,
        "min_available_gb": 32,
        "model": {"raw_spatial_features": False},
    }
    before = copy.deepcopy(source)
    result = relocated_config(source, "new")
    assert source == before
    assert result == dict(source, run="new")
    result["model"]["raw_spatial_features"] = True
    assert source == before


def test_nested_exact_state_checks_values_dtype_and_clock():
    state = {
        "state": {1: {"step": torch.tensor(14549.0), "exp_avg": torch.tensor([1.0, 2.0])}},
        "param_groups": [{"lr": 1e-5, "params": [1]}],
    }
    assert equal_state(state, copy.deepcopy(state))
    for change in ("dtype", "value", "clock", "lr"):
        altered = copy.deepcopy(state)
        if change == "dtype":
            altered["state"][1]["exp_avg"] = altered["state"][1]["exp_avg"].double()
        elif change == "value":
            altered["state"][1]["exp_avg"][0] += 1
        elif change == "clock":
            altered["state"][1]["step"] -= 1
        else:
            altered["param_groups"][0]["lr"] *= 2
        assert not equal_state(state, altered)


def test_controller_claim_prevents_automatic_relaunch(tmp_path, monkeypatch):
    import json

    import resume_raw_spatial_trial as trial

    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"root": str(tmp_path), "inputs": [], "frozen_files": {}}))
    (tmp_path / "controller.claim").write_text("preserved original attempt")
    monkeypatch.setattr(trial.subprocess, "Popen", lambda *a, **k: pytest.fail("Must not launch"))
    with pytest.raises(FileExistsError):
        trial.controller(path)
    assert (tmp_path / "controller.claim").read_text() == "preserved original attempt"


def test_changed_source_rejected_before_controller_claim(tmp_path, monkeypatch):
    import json

    import resume_raw_spatial_trial as trial

    source = tmp_path / "source.py"
    source.write_text("original")
    binding = trial.ref(source)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"root": str(tmp_path), "inputs": [binding], "frozen_files": {}}))
    source.write_text("changed")
    monkeypatch.setattr(trial.subprocess, "Popen", lambda *a, **k: pytest.fail("Must not launch"))
    with pytest.raises(AssertionError):
        trial.controller(path)
    assert not (tmp_path / "controller.claim").exists()
