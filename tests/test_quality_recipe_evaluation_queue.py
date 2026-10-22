import copy

import pytest
from queue_quality_recipe_evaluation import KEYS, TERMINAL, training_ready

PLAN = {"path": "/frozen/plan.json", "sha256": "a" * 64}
OWNER = {"pid": 100, "created": 1.0}
CHILD = {"pid": 200, "created": 2.0}


def completed():
    return {
        "plan": copy.deepcopy(PLAN),
        "controller": copy.deepcopy(OWNER),
        "child": copy.deepcopy(CHILD),
        "status": TERMINAL,
        "completed": dict.fromkeys(KEYS),
    }


@pytest.mark.parametrize("owners_alive", [[], [OWNER], [CHILD], [OWNER, CHILD]])
def test_evaluation_waits_for_both_training_processes_to_exit(owners_alive):
    assert training_ready(completed(), PLAN, OWNER, is_live=lambda x: x in owners_alive) is (
        not owners_alive
    )


@pytest.mark.parametrize("damage", ["plan", "owner", "missing-arm", "unexpected-arm", "failure"])
def test_bad_training_boundary_cannot_release_evaluation(damage):
    state = completed()
    if damage == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif damage == "owner":
        state["controller"]["created"] += 1
    elif damage == "missing-arm":
        state["completed"].pop("train-V101")
    elif damage == "unexpected-arm":
        state["completed"]["train-V102"] = None
    else:
        state["status"] = "failed-training-preserved-no-automatic-retry"
    with pytest.raises(AssertionError):
        training_ready(state, PLAN, OWNER, is_live=lambda _: False)


def test_incomplete_training_requires_its_original_controller_alive():
    state = completed()
    state.update(status="running-quality-training", completed={})
    assert not training_ready(state, PLAN, OWNER, is_live=lambda x: x == OWNER)
    with pytest.raises(AssertionError, match="exited before completion"):
        training_ready(state, PLAN, OWNER, is_live=lambda _: False)
