"""The CPU closure cannot mistake partial or still-running inference for completion."""

import importlib.util
from pathlib import Path

import pytest


def operator():
    path = Path("scripts/close_reconstruction_objective_review.py")
    spec = importlib.util.spec_from_file_location("objective_closure", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(module):
    owner = {"pid": 1, "created": 10}
    status = {"status": module.TERMINAL, "controller": owner,
              "child": {"pid": 2, "created": 20}, "completed": sorted(module.STAGES)}
    return owner, status


def test_complete_status_still_waits_for_the_actual_owner_and_child(monkeypatch):
    m = operator()
    owner, status = fixture(m)
    monkeypatch.setattr(m, "alive", lambda _: True)
    assert not m.ready(status, owner)
    monkeypatch.setattr(m, "alive", lambda p: p["pid"] == 2)
    assert not m.ready(status, owner)
    monkeypatch.setattr(m, "alive", lambda _: False)
    assert m.ready(status, owner)


@pytest.mark.parametrize("problem", ["failed", "partial", "stage-missing", "stage-duplicate", "owner"])
def test_invalid_review_state_cannot_enter_closure(monkeypatch, problem):
    m = operator()
    owner, status = fixture(m)
    monkeypatch.setattr(m, "alive", lambda _: False)
    if problem == "failed":
        status["status"] = "failed-objective-review-no-automatic-retry"
    elif problem == "partial":
        status["status"] = "running-objective-quality-review"
    elif problem == "stage-missing":
        status["completed"].pop()
    elif problem == "stage-duplicate":
        status["completed"].append("known")
    else:
        status["controller"] = {"pid": 1, "created": 99}
    with pytest.raises(RuntimeError):
        m.ready(status, owner)
