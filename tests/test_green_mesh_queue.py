import copy

import pytest
from queue_green_mesh_review import REPORT_TERMINAL, endpoint_methods, report_ready

DEPENDENCY = {
    "owner": {"pid": 100, "created": 5.0},
    "plan": {"path": "plan.json", "sha256": "a" * 64},
}


def state():
    return {
        "owner": copy.deepcopy(DEPENDENCY["owner"]),
        "plan": copy.deepcopy(DEPENDENCY["plan"]),
        "status": REPORT_TERMINAL,
    }


@pytest.mark.parametrize("alive", [True, False])
def test_mesh_waits_for_the_actual_comparison_owner(alive):
    assert report_ready(state(), DEPENDENCY, is_live=lambda _: alive) is (not alive)


@pytest.mark.parametrize("damage", ["owner", "plan", "failed", "incomplete"])
def test_bad_comparison_boundary_cannot_trigger_mesh_inference(damage):
    current = state()
    if damage == "owner":
        current["owner"]["created"] += 1
    elif damage == "plan":
        current["plan"]["sha256"] = "b" * 64
    elif damage == "failed":
        current["status"] = "failed-comparisons"
    else:
        current["status"] = "joining-rows"
    with pytest.raises((ValueError, RuntimeError)):
        report_ready(current, DEPENDENCY, is_live=lambda _: False)


@pytest.mark.parametrize("suffix", ["", "-profile3879"])
def test_only_new_endpoint_methods_are_declared(suffix):
    checkpoints = {
        arm: {"path": arm + ".pt", "sha256": str(index) * 64}
        for index, arm in enumerate(("V120", "V121"), 1)
    }
    methods = endpoint_methods(checkpoints, ["V120", "V121"], suffix)
    assert [m["label"] for m in methods] == ["V120" + suffix, "V121" + suffix]
    assert all(m["expected_step"] == 20000 and "prediction" not in m for m in methods)
    assert [m["checkpoint"] for m in methods] == list(checkpoints.values())


@pytest.mark.parametrize(
    "checkpoints, arms",
    [
        ({}, []),
        ({"V120": {"sha256": "a"}}, ["V120", "V121"]),
        ({"V120": {"sha256": "a"}, "V121": {"sha256": "a"}}, ["V120", "V121"]),
    ],
)
def test_missing_or_duplicate_mesh_endpoints_are_rejected(checkpoints, arms):
    with pytest.raises(ValueError):
        endpoint_methods(checkpoints, arms, "")
