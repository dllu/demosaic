from copy import deepcopy

import pytest
from train_memory_only_pilot import memory_dependency_ready, require_checked_result


def completed_check():
    return {
        "status": "completed-memory-only-global-implementation-check",
        "arm": "V139",
        "phase": "CPU",
        "updates": 18,
        "all_AdamW_steps": 18,
        "model_EMA_tensor_count": 106,
        "optimizer_state_count": 15,
        "raw_global_only": True,
        "frozen_parent91_model_and_EMA_exact": True,
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "all_observed_inputs_match_saved_control": True,
        "counts": {
            k: 18
            for k in (
                "training_forwards",
                "encoder_forwards",
                "optimizer_steps",
                "prepared_training_batches",
            )
        },
        "changed_global_resume_rejections": {str(i): "rejected" for i in range(7)},
    }


@pytest.mark.parametrize("phase", ["CPU", "CUDA"])
def test_completed_16_plus_2_check_is_eligible_for_adoption(phase):
    result = completed_check()
    result["phase"] = phase
    require_checked_result(result)


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "running"),
        ("updates", 16),
        ("all_AdamW_steps", 16),
        ("model_EMA_tensor_count", 109),
        ("optimizer_state_count", 18),
        ("raw_global_only", False),
        ("frozen_parent91_model_and_EMA_exact", False),
        ("model_EMA_Adam_finite", False),
        ("frozen_encoder_no_gradients", False),
        ("all_observed_inputs_match_saved_control", False),
    ],
)
def test_incomplete_or_different_check_cannot_be_adopted(key, value):
    result = completed_check()
    result[key] = value
    with pytest.raises(AssertionError):
        require_checked_result(result)


def test_missing_forward_or_resume_rejection_cannot_be_adopted():
    for change in ("forward", "rejection"):
        result = deepcopy(completed_check())
        if change == "forward":
            result["counts"]["encoder_forwards"] = 17
        else:
            result["changed_global_resume_rejections"].pop("0")
        with pytest.raises(AssertionError):
            require_checked_result(result)


def test_dependency_waits_for_completion_and_owner_exit_without_quality_threshold():
    owner = {"pid": 12, "created": 3.0}
    state = {"owner": owner, "status": "waiting-for-original-V138-faint-review"}
    assert not memory_dependency_ready(state, owner, True)
    with pytest.raises(AssertionError, match="exited without"):
        memory_dependency_ready(state, owner, False)
    state["status"] = "completed-V138-memory-diagnostic-awaiting-review"
    assert not memory_dependency_ready(state, owner, True)
    assert memory_dependency_ready(state, owner, False)
    state["quality_score"] = -100
    assert memory_dependency_ready(state, owner, False)


@pytest.mark.parametrize(
    "owner,status",
    [
        ({"pid": 12, "created": 4.0}, "completed-V138-memory-diagnostic-awaiting-review"),
        ({"pid": 12, "created": 3.0}, "failed-preserved-no-automatic-retry"),
    ],
)
def test_wrong_owner_or_failed_dependency_rejects(owner, status):
    with pytest.raises(AssertionError):
        memory_dependency_ready(
            {"owner": owner, "status": status}, {"pid": 12, "created": 3.0}, False
        )
