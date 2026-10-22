"""Protect calibration identity and serialization of the additional native views."""

import copy

import pytest
from evaluate_v95_native_photo_conditions import (
    COMPLETE,
    CONDITIONS,
    condition_protocols,
    dependency_ready,
)


def protocol():
    return {
        "patterns": ["RGGB", "BGGR", "GRBG", "GBRG"],
        "white_balance": [2.0, 1.0, 1.5],
        "camera_to_srgb": [[1.1, -0.05, -0.05], [-0.05, 1.1, -0.05], [-0.05, -0.05, 1.1]],
        "seed": 20261014,
        "border": 8,
        "adc_bits": 14,
        "conditions": [
            {"name": "adc-only", "shot": 0.0, "read": 0.0, "exposure": 1.0},
            {"name": "iso100-prior", "shot": 0.00002, "read": 1.6e-9, "exposure": 1.0},
            {"name": "iso12800-prior", "shot": 0.00256, "read": 2.62144e-5, "exposure": 1.0},
            {"name": "highlights", "shot": 0.00008, "read": 2.56e-8, "exposure": 4.0},
        ],
    }


def test_native_condition_selection_preserves_calibration_seed_and_adc_settings():
    source = protocol()
    before = copy.deepcopy(source)
    selected = condition_protocols(source)
    assert tuple(selected) == CONDITIONS
    for name, value in selected.items():
        assert value["patterns"] == ["RGGB"]
        assert value["conditions"] == [next(c for c in source["conditions"] if c["name"] == name)]
        for key in ("white_balance", "camera_to_srgb", "seed", "border", "adc_bits"):
            assert value[key] == before[key]
    selected["adc-only"]["white_balance"][0] = 9
    selected["adc-only"]["camera_to_srgb"][0][0] = 99
    assert source == before
    assert selected["iso100-prior"]["white_balance"] == before["white_balance"]
    assert selected["iso12800-prior"]["camera_to_srgb"] == before["camera_to_srgb"]


@pytest.mark.parametrize(
    "case",
    ["missing-condition", "duplicate", "missing-RGGB", "exposure", "ADC-noise", "negative", "nan"],
)
def test_invalid_native_protocol_fails_before_any_data_or_model_loading(case):
    value = protocol()
    if case == "missing-condition":
        value["conditions"].pop(1)
    elif case == "duplicate":
        value["conditions"].append(copy.deepcopy(value["conditions"][0]))
    elif case == "missing-RGGB":
        value["patterns"] = ["BGGR"]
    elif case == "exposure":
        value["conditions"][1]["exposure"] = 0.125
    elif case == "ADC-noise":
        value["conditions"][0]["shot"] = 0.01
    elif case == "negative":
        value["conditions"][1]["read"] = -1
    else:
        value["conditions"][1]["shot"] = float("nan")
    with pytest.raises(ValueError):
        condition_protocols(value)


def dependency(status=COMPLETE, controller=False, child=False):
    parent = {
        "reference": {"path": "frozen-parent-plan.json", "sha256": "parent"},
        "stages": ["photo", "known", "unseen", "texture", "color", "gfx", "gfx-highlights"],
    }
    state = {
        "plan": copy.deepcopy(parent["reference"]),
        "status": status,
        "controller": {"alive": controller},
        "child": {"alive": child},
        "completed": {s: {} for s in parent["stages"]},
    }
    return parent, state


@pytest.mark.parametrize("controller,child", [(True, False), (False, True), (True, True)])
def test_completed_status_cannot_release_a_still_live_parent_owner(controller, child):
    parent, state = dependency(controller=controller, child=child)
    assert not dependency_ready(state, parent, is_live=lambda p: p["alive"])


def test_only_all_stages_and_both_exited_owners_release_the_dependency():
    parent, state = dependency()
    assert dependency_ready(state, parent, is_live=lambda p: p["alive"])
    state["completed"].pop("photo")
    with pytest.raises(ValueError, match="lacks"):
        dependency_ready(state, parent, is_live=lambda p: p["alive"])


def test_live_running_parent_keeps_waiting_and_missing_or_failed_parent_is_an_error():
    parent, state = dependency(status="running-V43-quality-evaluation", controller=True, child=True)
    assert not dependency_ready(state, parent, is_live=lambda p: p["alive"])
    state["controller"]["alive"] = state["child"]["alive"] = False
    with pytest.raises(RuntimeError, match="missing"):
        dependency_ready(state, parent, is_live=lambda p: p["alive"])
    state["status"] = "failed-V43-evaluation-preserved-no-automatic-retry"
    with pytest.raises(RuntimeError, match="failed"):
        dependency_ready(state, parent, is_live=lambda p: p["alive"])


def test_other_plan_identity_cannot_satisfy_the_dependency():
    parent, state = dependency()
    state["plan"]["sha256"] = "other"
    with pytest.raises(ValueError, match="identity"):
        dependency_ready(state, parent, is_live=lambda p: p["alive"])
