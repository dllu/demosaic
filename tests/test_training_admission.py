"""Existing owners must obtain their declared admission before new long jobs."""

import copy

import pytest
import train_quality_recipes as runner


def fixture():
    dependency = {
        "plan": {"path": "fixture", "sha256": "a" * 64},
        "controller": {"pid": 1, "created": 1},
        "arm": "V125",
        "running_status": "running-noise-pair-training",
        "completed_phases": [
            "CPU-V124",
            "CPU-V125",
            "CUDA-V124",
            "CUDA-V125",
            "train-V124",
            "train-V125",
        ],
    }
    state = {
        "plan": dependency["plan"],
        "controller": dependency["controller"],
        "child": {"pid": 2, "created": 2},
        "phase": "train",
        "arm": "V124",
        "status": "running-noise-pair-training",
        "completed": {},
    }
    return state, dependency


def test_releases_only_after_target_arm_is_actually_live(monkeypatch):
    state, dependency = fixture()
    monkeypatch.setattr(runner, "live", lambda owner: owner is not None)
    assert not runner.training_admission_ready(state, dependency)
    state["arm"] = "V125"
    state["status"] = "waiting-for-training-headroom"
    assert not runner.training_admission_ready(state, dependency)
    state["status"] = dependency["running_status"]
    assert runner.training_admission_ready(state, dependency)
    state["child"] = None
    assert not runner.training_admission_ready(state, dependency)


@pytest.mark.parametrize("change", ["plan", "owner", "failure", "exited"])
def test_drift_failure_or_exit_cannot_release_training(monkeypatch, change):
    state, dependency = fixture()
    state = copy.deepcopy(state)
    monkeypatch.setattr(runner, "live", lambda owner: change != "exited")
    if change == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif change == "owner":
        state["controller"]["created"] = 99
    elif change == "failure":
        state["status"] = "failed-training-preserved-no-automatic-retry"
    with pytest.raises(AssertionError):
        runner.training_admission_ready(state, dependency)


def test_successful_completion_requires_all_phases_and_exited_owners(monkeypatch):
    state, dependency = fixture()
    state["status"] = "completed-training-awaiting-model-comparisons"
    monkeypatch.setattr(runner, "live", lambda owner: False)
    with pytest.raises(AssertionError):
        runner.training_admission_ready(state, dependency)
    state["completed"] = dict.fromkeys(dependency["completed_phases"])
    assert runner.training_admission_ready(state, dependency)
    monkeypatch.setattr(runner, "live", lambda owner: True)
    assert not runner.training_admission_ready(state, dependency)
