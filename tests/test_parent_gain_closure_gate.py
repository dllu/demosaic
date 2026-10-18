"""Do not close partial or live shared-forward photo inference."""

import importlib.util
from pathlib import Path

import pytest


def fixture(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "gain_close", Path("scripts/close_parent_cfa_gain_review.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner = {"pid": 1, "created": 2}
    plan = {"path": "plan", "sha256": "digest"}
    status = {
        "controller": owner,
        "plan": plan,
        "status": module.TERMINAL,
        "sources_done": 443,
        "actual_network_forwards": 3108,
        "case_rows": 62020,
        "native_triplets": 4,
    }
    monkeypatch.setattr(module, "alive", lambda _: False)
    return module, status, owner, plan


def test_successful_counts_still_wait_for_actual_producer_exit(monkeypatch):
    m, s, o, p = fixture(monkeypatch)
    monkeypatch.setattr(m, "alive", lambda _: True)
    assert not m.ready(s, o, p)
    monkeypatch.setattr(m, "alive", lambda _: False)
    assert m.ready(s, o, p)


@pytest.mark.parametrize(
    "problem", ["failed", "partial", "owner", "plan", "sources", "forwards", "cases", "crops"]
)
def test_invalid_photo_state_cannot_close(monkeypatch, problem):
    m, s, o, p = fixture(monkeypatch)
    if problem == "failed":
        s["status"] = "failed-any-stage"
    elif problem == "partial":
        s["status"] = "running-photo-test"
    elif problem == "owner":
        s["controller"] = {"pid": 1, "created": 3}
    elif problem == "plan":
        s["plan"] = {"path": "other", "sha256": "digest"}
    else:
        key = {
            "sources": "sources_done",
            "forwards": "actual_network_forwards",
            "cases": "case_rows",
            "crops": "native_triplets",
        }[problem]
        s[key] -= 1
    with pytest.raises(RuntimeError):
        m.ready(s, o, p)
