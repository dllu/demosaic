"""Protect calibration identity and serialization of the additional native views."""

import copy
import json

import pytest
from evaluate_v95_native_photo_conditions import (
    COMPLETE,
    CONDITIONS,
    check_effective_config,
    check_native_checkpoints,
    condition_protocols,
    dependency_ready,
    measure_native_adc,
)


def test_effective_model_config_accepts_checkpoint_sequences_after_json_roundtrip():
    from demosaic.model import ModelConfig

    actual = ModelConfig(dino=True, variance_stabilization=True).to_dict()
    recorded = json.loads(json.dumps(actual))
    assert actual != recorded  # Tuple defaults become lists in completed reports.
    before = copy.deepcopy(actual)
    check_effective_config(actual, recorded)
    assert actual == before


@pytest.mark.parametrize("changed", ["width", "flag", "blocks", "missing", "extra", "nan"])
def test_effective_model_config_still_rejects_real_changes(changed):
    actual = {"width": 64, "dino": True, "encoder_blocks": (2, 2, 4)}
    recorded = json.loads(json.dumps(actual))
    if changed == "width":
        recorded["width"] = 32
    elif changed == "flag":
        recorded["dino"] = False
    elif changed == "blocks":
        recorded["encoder_blocks"][2] = 5
    elif changed == "missing":
        recorded.pop("width")
    elif changed == "extra":
        recorded["unknown"] = None
    else:
        recorded["width"] = float("nan")
    with pytest.raises(ValueError):
        check_effective_config(actual, recorded)


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
    [
        "missing-condition",
        "duplicate",
        "missing-RGGB",
        "exposure",
        "ADC-noise",
        "negative",
        "nan",
        "zero-ISO100",
    ],
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
    elif case == "zero-ISO100":
        value["conditions"][1].update(shot=0, read=0)
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


def adc_checkpoints():
    result = [
        {"arm": arm, "path": f"/{arm}.pt", "sha256": str(i) * 64}
        for i, arm in enumerate(("V43", "V95", "V98", "V99"))
    ]
    initializer = {"step": 20000, **{k: result[1][k] for k in ("path", "sha256")}}
    for checkpoint in result[2:]:
        checkpoint.update(
            expected_adc_projection=True,
            expected_lineage={"step": 4000, "initialized_from": copy.deepcopy(initializer)},
        )
    result[2]["training_checkpoint"] = {"path": "/V98-unprojected.pt", "sha256": "a" * 64}
    return result


def test_only_declared_studies_are_accepted_with_common_adc_policy_and_final_lineage():
    current = adc_checkpoints()
    before = copy.deepcopy(current)
    assert check_native_checkpoints(current) is True
    assert current == before
    legacy = [{"arm": arm} for arm in ("V43", "V95", "V96", "V97")]
    assert check_native_checkpoints(legacy) is False
    legacy[-1]["expected_adc_projection"] = True
    with pytest.raises(ValueError, match="historical"):
        check_native_checkpoints(legacy)


@pytest.mark.parametrize(
    "damage",
    [
        "raw-control",
        "unprojected-candidate",
        "nonbool-flag",
        "changed-reference",
        "intermediate",
        "wrong-parent",
        "missing-export-origin",
        "unchanged-export-hash",
        "wrong-arm",
    ],
)
def test_unmatched_adc_native_comparisons_fail_before_model_loading(damage):
    current = adc_checkpoints()
    if damage == "raw-control":
        current[2]["expected_adc_projection"] = False
    elif damage == "unprojected-candidate":
        current[3]["expected_adc_projection"] = False
    elif damage == "nonbool-flag":
        current[3]["expected_adc_projection"] = 1
    elif damage == "changed-reference":
        current[1]["expected_adc_projection"] = True
    elif damage == "intermediate":
        current[3]["expected_lineage"]["step"] = 3000
    elif damage == "wrong-parent":
        current[2]["expected_lineage"]["initialized_from"]["sha256"] = "b" * 64
    elif damage == "missing-export-origin":
        del current[2]["training_checkpoint"]
    elif damage == "unchanged-export-hash":
        current[2]["training_checkpoint"]["sha256"] = current[2]["sha256"]
    else:
        current[3]["arm"] = "V97"
    with pytest.raises(ValueError):
        check_native_checkpoints(current)


@pytest.mark.parametrize("batched_colors", [False, True])
def test_native_adc_observer_checks_selected_samples_and_preserves_inputs_and_rng(batched_colors):
    import torch

    from demosaic.cfa import PATTERNS, color_indices, mosaic

    colors = (
        torch.stack([color_indices(p) for p in PATTERNS])
        if batched_colors
        else color_indices("RGGB")
    )
    target = torch.rand(4, 3, 8, 12, generator=torch.Generator().manual_seed(58)) * 0.6 + 0.2
    packed = mosaic(target, colors)
    args = (
        packed,
        torch.zeros_like(packed),
        colors,
        torch.ones(4, 3),
        torch.eye(3).repeat(4, 1, 1),
    )
    before = [x.clone() for x in args]
    rng = torch.get_rng_state()
    original = target.clone()
    result = measure_native_adc(target, args, [(None, 1, False)])
    assert result["observations"] == 4 and result["valid_CFA_values"] == packed.numel()
    assert result["maximum_absolute_error_sensor_units"] == 0
    selected = measure_native_adc(target, args, [(None, 1, False), (None, 1, True)] * 2)
    assert selected["observations"] == 2 and selected["valid_CFA_values"] == packed.numel() // 2
    with pytest.raises(ValueError, match="does not preserve"):
        measure_native_adc(target + 0.01, args, [(None, 1, False)])
    noisy = measure_native_adc(target + 0.01, args, [(None, 1, True)])
    assert noisy == {
        "observations": 0,
        "valid_CFA_values": 0,
        "maximum_absolute_error_sensor_units": None,
    }
    assert torch.equal(target, original) and torch.equal(rng, torch.get_rng_state())
    assert all(torch.equal(x, y) for x, y in zip(args, before, strict=True))
