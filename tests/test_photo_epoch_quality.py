"""A source-order setup or partial checkpoint cannot masquerade as trained quality."""

import copy

import pytest
from queue_green_mesh_review import deferred_mesh_arms
from queue_matched_quality_predictions import execution_arms, verify_photo_epoch_training_state
from test_reviewed_quota_quality import state_fixture


def fixture(arm):
    actual, snapshot, _ = state_fixture()
    actual.update(status="completed-photo-epoch-training-phase", arm=arm)
    proof = None
    if arm == "V135":
        snapshot["config"].update(
            photo_epoch_order="frozen-order", photo_epoch_order_sha256="a" * 64
        )
        proof = {
            "status": "passed-photo-epoch-unaffected-input-proof",
            "control": actual["matched_control_result"],
            "counts": {
                "checked_batches_before_model_forward": 18,
                "unaffected_first18_examples": 1,
                "exact_unaffected_prepared_values": 1,
                "exact_native_paired_whole_batches": 9954,
            },
        }
    else:
        actual["matched_control_result"] = None
    return actual, snapshot, proof, copy.deepcopy(snapshot["config"])


@pytest.mark.parametrize("arm", ["V134", "V135"])
def test_complete_endpoint_and_declared_policy(arm):
    verify_photo_epoch_training_state(*fixture(arm))


@pytest.mark.parametrize("damage", ["partial", "mode", "config", "native", "first18", "control"])
def test_incomplete_or_changed_order_endpoint_is_rejected(damage):
    actual, state, proof, expected = fixture("V135")
    if damage == "partial":
        state["step"] = 18
    elif damage == "mode":
        state["config"].pop("photo_epoch_order")
    elif damage == "config":
        expected["seed"] = 71
    elif damage == "native":
        proof["counts"]["exact_native_paired_whole_batches"] -= 1
    elif damage == "first18":
        proof["counts"]["checked_batches_before_model_forward"] -= 1
    else:
        proof["control"] = {"path": "different"}
    with pytest.raises(AssertionError):
        verify_photo_epoch_training_state(actual, state, proof, expected)


def test_exactly_the_two_declared_arms_are_evaluated():
    plan = {
        "arms": {"V134": {}, "V135": {}},
        "restoration_tensors_by_arm": {"V134": 91, "V135": 91},
        "paired_control_arm": "V134",
    }
    assert [r["arm"] for r in execution_arms(plan, {}, "matched-photographic-epoch-v1")] == [
        "V134",
        "V135",
    ]
    plan["arms"]["unexpected"] = {}
    with pytest.raises(AssertionError):
        execution_arms(plan, {}, "matched-photographic-epoch-v1")


def test_deferred_mesh_control_preserves_default_and_requires_explicit_new_arm():
    assert deferred_mesh_arms(["V131", "V132"]) == ["V131"]
    assert deferred_mesh_arms(["V133"], ["V133"]) == ["V133"]
    for requested in [None, [], ["V131"], ["V133", "V133"]]:
        with pytest.raises(ValueError):
            deferred_mesh_arms(["V133"], requested)
