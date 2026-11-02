"""Longer training must retain honest prefix and saved-observation contracts."""

from copy import deepcopy

import pytest
from review_crossed_gradient5000 import matching_prefix, selected_steps
from review_standalone_patch_memory_pilot import (
    append_retained_control,
    review_step_spec,
    select_control_methods,
)


def test_old_default_and_explicit_progress_and_endpoint():
    assert review_step_spec(1000, None) == (1000, False)
    assert review_step_spec(5000, 1000) == (1000, True)
    assert review_step_spec(5000, 2500) == (2500, True)
    assert review_step_spec(5000, 5000) == (5000, False)


def test_remaining_review_subset_does_not_repeat_completed_prefix():
    assert selected_steps(1000) == (1000, 2500, 5000)
    assert selected_steps(2500) == (2500, 5000)
    assert selected_steps(5000) == (5000,)


@pytest.mark.parametrize("step", [True, 2500.0, 0, 1001, None])
def test_reject_undeclared_review_start(step):
    with pytest.raises(ValueError):
        selected_steps(step)


@pytest.mark.parametrize(
    "horizon,step",
    [(5000, None), (0, 1), (5000, 5001), (5000, 0), (5000, True), (5000, 1000.0), (True, 1)],
)
def test_reject_accidental_horizon_and_review_selection(horizon, step):
    with pytest.raises(ValueError):
        review_step_spec(horizon, step)


def control_fixture():
    obs = [
        {
            "id": "mesh",
            "arrays": {"path": "fixed", "sha256": "a"},
            "ROI": [2, 4, 160, 160],
            "noise": {"read": 0.001},
            "controls": [{"model": {"label": "V120"}}],
        }
    ]
    previous = {
        "observations": deepcopy(obs),
        "model_label": "V142 1k EMA",
        "step": 1000,
        "checkpoint": {"sha256": "weights"},
    }
    prediction = {"path": "retained", "sha256": "prediction"}
    collection = {"observations": [{"id": "mesh", "prediction": prediction}]}
    return obs, previous, collection, lambda _: prediction


def test_adopt_control_preserves_input_pixels_and_original_objects():
    obs, previous, collection, checked = control_fixture()
    result = append_retained_control(obs, previous, collection, checked=checked)
    assert len(obs[0]["controls"]) == 1 and len(result[0]["controls"]) == 2
    assert result[0]["controls"][-1]["model"] == {
        "label": "V142 1k EMA",
        "step": 1000,
        "sha256": "weights",
    }
    assert result[0]["arrays"] == obs[0]["arrays"]


@pytest.mark.parametrize("change", ["ROI", "noise", "arrays", "id", "duplicate", "prediction"])
def test_reject_substituted_saved_control(change):
    obs, previous, collection, checked = control_fixture()
    if change in ("ROI", "noise", "arrays"):
        previous["observations"][0][change] = "substituted"
    elif change == "id":
        collection["observations"][0]["id"] = "other"
    elif change == "duplicate":
        previous["model_label"] = "V120"
    else:
        checked = lambda _: {"path": "retained", "sha256": "changed"}
    with pytest.raises(AssertionError):
        append_retained_control(obs, previous, collection, checked=checked)


def input_rows(count):
    return [
        {"step": i, "domain": "commons", "clean_sha256": f"clean{i}", "batch_sha256": f"noisy{i}"}
        for i in range(1, count + 1)
    ]


def test_compare_whole_shared_prefix_without_claiming_full5000_match():
    actual, control = input_rows(2500), input_rows(1000)
    actual[1500]["batch_sha256"] = "not part of the measured shared prefix"
    assert matching_prefix(actual, control, 2500) == 1000


@pytest.mark.parametrize("change", ["clean_sha256", "batch_sha256", "domain", "step", "length"])
def test_reject_changed_last_shared_batch_or_missing_progress_input(change):
    actual, control = input_rows(2500), input_rows(1000)
    if change == "length":
        actual.pop()
    else:
        actual[999][change] = "changed"
    with pytest.raises(AssertionError):
        matching_prefix(actual, control, 2500)


def test_control_selection_orders_named_bindings_and_normalizes_only_mesh_parent_label():
    original = [
        {
            "controls": [
                {"model": {"label": "V141 1k EMA"}, "prediction": "loss"},
                {"label": "V120-profile3879", "prediction": "parent"},
                {"model": {"label": "V136 1k EMA"}, "prediction": "old-branch"},
            ]
        }
    ]
    selected = select_control_methods(original, ["V120", "V141 1k EMA"])
    assert [c["prediction"] for c in selected[0]["controls"]] == ["parent", "loss"]
    assert len(original[0]["controls"]) == 3


@pytest.mark.parametrize("labels", [["missing"], ["V120", "V120"], []])
def test_control_selection_rejects_missing_or_duplicate_names(labels):
    with pytest.raises(AssertionError):
        select_control_methods([{"controls": [{"label": "V120"}]}], labels)
