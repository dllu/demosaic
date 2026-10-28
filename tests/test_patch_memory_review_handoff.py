"""Exercise the future five-control handoff without model inference or saved weights."""

from copy import deepcopy

import pytest
from bind_patch_memory_review import (
    CONTROL_LABELS,
    inherit_controls,
    matching_batches,
    require_completed_training,
    require_training_result,
)


def comparison_inputs():
    def control(label):
        return {"model": {"label": label}, "prediction": {"path": label, "sha256": label}}

    declared = [
        {
            "id": str(i),
            "ROI_xywh": [48, 48, 160, 160],
            "noise": {"shot": 0, "read": 0},
            "display_exposure": 1,
            "input_fingerprints": {"packed": "saved-input"},
            "controls": [control(label) for label in CONTROL_LABELS[:4]],
        }
        for i in range(2)
    ]
    inherited = deepcopy(declared)
    for observation in inherited:
        observation["controls"].append(control(CONTROL_LABELS[-1]))
    predictions = [
        {"id": str(i), "prediction": {"path": "V139", "sha256": "V139"}} for i in range(2)
    ]
    return declared, inherited, predictions, {"sha256": "V139-checkpoint"}


def identity_ref(path):
    return {"path": path, "sha256": path}


@pytest.mark.parametrize("profile", ["mesh-nominal", "mesh-profile3879"])
def test_preserves_legacy_mesh_V120_metadata_and_profile_label(profile):
    declared, inherited, predictions, checkpoint = comparison_inputs()
    label = "V120-profile3879" if profile == "mesh-profile3879" else "V120"
    legacy = {
        "label": label,
        "checkpoint": "saved-V120",
        "prediction": {"path": "V120", "sha256": "V120"},
    }
    for collection in (declared, inherited):
        collection[0].update(id=profile, kind="mesh")
        collection[0]["controls"][0] = deepcopy(legacy)
    predictions[0]["id"] = profile
    result = inherit_controls(declared, inherited, predictions, checkpoint, checked=identity_ref)
    assert result[0]["controls"][0] == legacy
    assert result[0]["controls"][4]["model"]["label"] == "V138 1k EMA"
    assert result[0]["controls"][5]["model"]["label"] == "V139 1k EMA"


def test_adopts_inherited_fifth_control_then_new_prediction_without_mutating_inputs():
    inputs = comparison_inputs()
    saved = deepcopy(inputs)
    result = inherit_controls(*inputs, checked=identity_ref)
    assert inputs == saved
    assert len(result) == 2
    for observation in result:
        assert [c["model"]["label"] for c in observation["controls"]] == CONTROL_LABELS + [
            "V139 1k EMA"
        ]
        assert observation["controls"][-1] == {
            "model": {"label": "V139 1k EMA", "sha256": "V139-checkpoint", "step": 1000},
            "prediction": {"path": "V139", "sha256": "V139"},
        }
        assert "label" not in observation["controls"][-1]
        assert observation["ROI_xywh"] == [48, 48, 160, 160]


@pytest.mark.parametrize("field", ["ROI_xywh", "noise", "display_exposure", "input_fingerprints"])
def test_rejects_changed_observation_support(field):
    declared, inherited, predictions, checkpoint = comparison_inputs()
    inherited[0][field] = "changed"
    with pytest.raises(AssertionError):
        inherit_controls(declared, inherited, predictions, checkpoint, checked=identity_ref)


@pytest.mark.parametrize(
    "change",
    [
        "prefix",
        "fifth_label",
        "stale_label",
        "missing_tail",
        "duplicate",
        "order",
        "prediction_id",
        "hash",
    ],
)
def test_rejects_missing_replaced_or_mislabeled_control(change):
    declared, inherited, predictions, checkpoint = comparison_inputs()
    if change == "prefix":
        inherited[0]["controls"][0]["prediction"]["sha256"] = "changed"
    elif change == "fifth_label":
        inherited[0]["controls"][4]["model"]["label"] = "V137 1k EMA"
    elif change == "stale_label":
        inherited[0]["controls"][4]["label"] = "V120"
    elif change == "missing_tail":
        inherited[0]["controls"].pop()
    elif change == "duplicate":
        declared[1]["id"] = declared[0]["id"]
    elif change == "order":
        inherited.reverse()
    elif change == "prediction_id":
        predictions[1]["id"] = predictions[0]["id"]
    else:
        predictions[0]["prediction"]["sha256"] = "changed"
    with pytest.raises(AssertionError):
        inherit_controls(declared, inherited, predictions, checkpoint, checked=identity_ref)


def test_requires_exact_original_training_owner_and_completed_receipt():
    queue = {"training_plan": {"sha256": "plan"}, "training_owner": {"pid": 10, "created": 2}}
    status = {
        "plan": queue["training_plan"],
        "controller": queue["training_owner"],
        "status": "completed-training-awaiting-model-comparisons",
        "child": None,
        "completed": {"train-V140": {"path": "result", "sha256": "result"}},
    }
    with pytest.raises(AssertionError, match="still live"):
        require_completed_training(status, queue, True)
    assert require_completed_training(status, queue, False) == status["completed"]["train-V140"]
    for field, value in [
        ("controller", {"pid": 11, "created": 2}),
        ("plan", {}),
        ("status", "running"),
    ]:
        changed = {**status, field: value}
        with pytest.raises(AssertionError):
            require_completed_training(changed, queue, False)


def completed_result():
    return {
        "status": "completed-patch-memory-global-pilot-training-phase",
        "phase": "train",
        "arm": "V140",
        "updates": 1000,
        "all_AdamW_steps": 1000,
        "optimizer_state_count": 16,
        "model_EMA_tensor_count": 107,
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "raw_global_only": True,
        "frozen_parent91_model_and_EMA_exact": True,
        "all_observed_inputs_match_saved_control": True,
        "counts": {
            "training_forwards": 1000,
            "optimizer_steps": 1000,
            "encoder_forwards": 1064,
            "validation_forwards": 64,
        },
        "initial_global_offsets": [{"all_zero": True}],
    }


def test_original_full_endpoint_is_accepted():
    require_training_result(completed_result())


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "completed-patch-memory-global-implementation-check"),
        ("phase", "CUDA"),
        ("updates", 18),
        ("all_AdamW_steps", 999),
        ("optimizer_state_count", 15),
        ("model_EMA_tensor_count", 106),
        ("frozen_parent91_model_and_EMA_exact", False),
        ("all_observed_inputs_match_saved_control", False),
    ],
)
def test_check_states_and_incomplete_endpoints_are_rejected(field, value):
    with pytest.raises(AssertionError):
        require_training_result({**completed_result(), field: value})


@pytest.mark.parametrize("step", [1, 500, 1000])
@pytest.mark.parametrize("field", ["step", "domain", "clean_sha256", "batch_sha256"])
def test_every_training_batch_identity_is_required(step, field):
    result = {
        "observed_inputs": [
            {"step": i, "domain": "commons", "clean_sha256": str(i), "batch_sha256": str(i)}
            for i in range(1, 1001)
        ]
    }
    control = deepcopy(result)
    matching_batches(result, control)
    control["observed_inputs"][step - 1][field] = "changed"
    with pytest.raises(AssertionError):
        matching_batches(result, control)


def test_complete_training_input_stream_cannot_be_truncated():
    with pytest.raises(AssertionError):
        matching_batches({"observed_inputs": []}, {"observed_inputs": []})
