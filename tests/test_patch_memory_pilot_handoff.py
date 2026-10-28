from copy import deepcopy

import pytest
from train_patch_memory_pilot import (
    QUALITY_STAGES,
    quality_dependency_ready,
    require_checked_result,
)


def completed_check():
    return {
        "status": "completed-patch-memory-global-implementation-check",
        "arm": "V140",
        "phase": "CPU",
        "updates": 18,
        "all_AdamW_steps": 18,
        "model_EMA_tensor_count": 107,
        "optimizer_state_count": 16,
        "raw_global_only": True,
        "frozen_parent91_model_and_EMA_exact": True,
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "all_observed_inputs_match_saved_control": True,
        "counts": {
            k: 18
            for k in [
                "training_forwards",
                "encoder_forwards",
                "optimizer_steps",
                "prepared_training_batches",
            ]
        },
        "changed_global_resume_rejections": {str(i): "rejected" for i in range(8)},
    }


def completed_quality(owner):
    return {
        "owner": owner,
        "status": "completed-memory-only1000-review-awaiting-actual-native-viewing",
        "completed": {stage: True for stage in QUALITY_STAGES},
        **{
            k: {"path": k, "sha256": k}
            for k in [
                "primary_report",
                "primary_audit",
                "faint_result",
                "faint_audit",
                "camera_JPEGs",
            ]
        },
    }


@pytest.mark.parametrize("phase", ["CPU", "CUDA"])
def test_original_complete_16_plus_2_check_is_adoptable(phase):
    result = completed_check()
    result["phase"] = phase
    require_checked_result(result)


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "running"),
        ("arm", "V139"),
        ("updates", 16),
        ("all_AdamW_steps", 16),
        ("model_EMA_tensor_count", 106),
        ("optimizer_state_count", 15),
        ("raw_global_only", False),
        ("frozen_parent91_model_and_EMA_exact", False),
        ("model_EMA_Adam_finite", False),
        ("frozen_encoder_no_gradients", False),
        ("all_observed_inputs_match_saved_control", False),
    ],
)
def test_missing_or_wrong_check_cannot_be_adopted(key, value):
    result = completed_check()
    result[key] = value
    with pytest.raises(AssertionError):
        require_checked_result(result)


def test_missing_forward_or_rejection_cannot_be_adopted():
    for key in ["forward", "rejection"]:
        result = deepcopy(completed_check())
        if key == "forward":
            result["counts"]["encoder_forwards"] = 17
        else:
            result["changed_global_resume_rejections"].pop("0")
        with pytest.raises(AssertionError):
            require_checked_result(result)


def test_waits_for_original_review_completion_and_owner_exit_without_score_threshold():
    owner = {"pid": 12, "created": 3.0}
    state = {"owner": owner, "status": "waiting-for-original-V139-training"}
    assert not quality_dependency_ready(state, owner, True)
    with pytest.raises(AssertionError, match="exited without"):
        quality_dependency_ready(state, owner, False)
    state = completed_quality(owner)
    assert not quality_dependency_ready(state, owner, True)
    assert quality_dependency_ready(state, owner, False)
    state["quality_score"] = -100
    assert quality_dependency_ready(state, owner, False)


@pytest.mark.parametrize(
    "change", ["owner", "failed", "stage_missing", "stage_false", "stage_truthy", "receipt_missing"]
)
def test_incomplete_or_different_review_rejects(change):
    owner = {"pid": 12, "created": 3.0}
    state = completed_quality(owner)
    if change == "owner":
        state["owner"] = {"pid": 12, "created": 4.0}
    elif change == "failed":
        state["status"] = "failed-preserved-no-automatic-retry"
    elif change == "stage_missing":
        state["completed"].pop("faint-audit")
    elif change == "stage_false":
        state["completed"]["faint-audit"] = False
    elif change == "stage_truthy":
        state["completed"]["faint-audit"] = 1
    else:
        state.pop("camera_JPEGs")
    with pytest.raises((AssertionError, KeyError)):
        quality_dependency_ready(state, owner, False)
