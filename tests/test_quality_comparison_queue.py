import copy
import json

import pytest
from queue_quality_comparisons import AUDIT_TERMINAL, audit_ready, endpoint_checkpoints, save_status

DEPENDENCY = {
    "owner": {"pid": 10, "created": 20.0},
    "plan": {"path": "plan.json", "sha256": "a" * 64},
}


def completed():
    return {
        "owner": copy.deepcopy(DEPENDENCY["owner"]),
        "plan": copy.deepcopy(DEPENDENCY["plan"]),
        "status": AUDIT_TERMINAL,
    }


def test_status_advances_without_overwriting_exclusive_result_receipts(tmp_path):
    path = tmp_path / "status.json"
    save_status(path, {"status": "waiting"})
    save_status(path, {"status": "completed", "result": "preserved-result.json"})
    assert json.loads(path.read_text()) == {
        "status": "completed",
        "result": "preserved-result.json",
    }
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize("alive", [True, False])
def test_terminal_audit_still_waits_for_its_actual_owner(alive):
    assert audit_ready(completed(), DEPENDENCY, is_live=lambda _: alive) is (not alive)


@pytest.mark.parametrize("damage", ["owner", "plan", "failed", "premature-exit"])
def test_invalid_audit_boundary_cannot_release_reports(damage):
    state = completed()
    if damage == "owner":
        state["owner"]["created"] += 1
    elif damage == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif damage == "failed":
        state["status"] = "failed-audit-with-preserved-output"
    else:
        state["status"] = "waiting-for-quality"
    with pytest.raises((ValueError, RuntimeError)):
        audit_ready(state, DEPENDENCY, is_live=lambda _: False)


def endpoints():
    return {
        "checkpoints": [
            {
                "arm": arm,
                "path": arm + ".pt",
                "sha256": str(index) * 64,
                "expected_lineage": {"step": 20000},
            }
            for index, arm in enumerate(("V122", "V123"), 1)
        ]
    }


def test_all_declared_endpoints_are_selected_by_identity():
    selected = endpoint_checkpoints(endpoints(), ["V122", "V123"])
    assert set(selected) == {"V122", "V123"}
    assert selected["V123"] == {"path": "V123.pt", "sha256": "2" * 64}


@pytest.mark.parametrize("damage", ["missing", "duplicate-arm", "duplicate-weights", "short"])
def test_engineering_or_incomplete_endpoints_cannot_enter_reports(damage):
    data = endpoints()
    if damage == "missing":
        data["checkpoints"].pop()
    elif damage == "duplicate-arm":
        data["checkpoints"][1]["arm"] = "V122"
    elif damage == "duplicate-weights":
        data["checkpoints"][1]["sha256"] = "1" * 64
    else:
        data["checkpoints"][1]["expected_lineage"]["step"] = 18
    with pytest.raises(ValueError):
        endpoint_checkpoints(data, ["V122", "V123"])
