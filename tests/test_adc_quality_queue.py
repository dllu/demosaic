import copy

import pytest
from queue_v95_adc_quality import KEYS, TERMINAL, completed_results, training_ready
from train_directional_bank_trial import ref, save

PLAN = {"path": "/frozen/plan.json", "sha256": "a" * 64}
OWNER = {"pid": 111, "created": 1.0}
CHILD = {"pid": 222, "created": 2.0}


def state():
    return {
        "plan": copy.deepcopy(PLAN),
        "controller": copy.deepcopy(OWNER),
        "child": copy.deepcopy(CHILD),
        "status": TERMINAL,
        "completed": dict.fromkeys(KEYS),
    }


@pytest.mark.parametrize("live_owners", [[], [OWNER], [CHILD], [OWNER, CHILD]])
def test_complete_coverage_releases_only_after_both_exact_owners_exit(live_owners):
    assert training_ready(state(), PLAN, OWNER, is_live=lambda owner: owner in live_owners) is (
        not live_owners
    )


def test_running_training_waits_while_its_controller_is_alive():
    current = state()
    current.update(status="running-ADC-training-stage", completed={})
    assert not training_ready(current, PLAN, OWNER, is_live=lambda owner: owner == OWNER)
    with pytest.raises(AssertionError, match="exited before completion"):
        training_ready(current, PLAN, OWNER, is_live=lambda owner: owner == CHILD)


@pytest.mark.parametrize("damage", ["plan", "PID-reuse", "failed", "missing", "extra"])
def test_wrong_identity_failed_or_incomplete_training_cannot_release(damage):
    current = state()
    if damage == "plan":
        current["plan"]["sha256"] = "b" * 64
    elif damage == "PID-reuse":
        current["controller"]["created"] += 1
    elif damage == "failed":
        current["status"] = "failed-ADC-training-preserved-no-automatic-retry"
    elif damage == "missing":
        current["completed"].pop("train-V99")
    else:
        current["completed"]["train-V100"] = None
    with pytest.raises(AssertionError):
        training_ready(current, PLAN, OWNER, is_live=lambda owner: False)


@pytest.mark.parametrize("damage", [None, "bytes", "plan", "arm", "engineering", "owner"])
def test_all_six_result_receipts_are_checked_before_audits(tmp_path, monkeypatch, damage):
    current = state()
    for key in KEYS:
        phase, arm = key.split("-")
        result = {
            "phase": phase,
            "arm": arm,
            "plan": PLAN,
            "engineering_only": phase != "train",
            "owner": CHILD,
        }
        if key == "train-V99":
            if damage == "plan":
                result["plan"] = {}
            elif damage == "arm":
                result["arm"] = "V98"
            elif damage == "engineering":
                result["engineering_only"] = True
        path = tmp_path / f"{key}.json"
        save(path, result)
        current["completed"][key] = ref(path)
        if damage == "bytes" and key == "train-V99":
            path.write_text(path.read_text() + "\n")
    monkeypatch.setattr("queue_v95_adc_quality.live", lambda owner: damage == "owner")
    if damage is None:
        completed_results(current, PLAN)
    else:
        with pytest.raises(AssertionError):
            completed_results(current, PLAN)
