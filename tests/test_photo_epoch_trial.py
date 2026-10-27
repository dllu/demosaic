"""Protect the matched recipe, unchanged examples and prior review ownership."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest
import train_photo_epoch_trial as trial
import yaml
from train_directional_bank_trial import ref


def test_matched_recipes_allow_only_declared_source_order():
    root = Path(__file__).resolve().parents[1]
    configs = [
        yaml.safe_load((root / f"configs/quality-v120-photo-epoch-v{v}.yaml").read_text())
        for v in (134, 135)
    ]
    trial.validate_recipes(configs)
    for key in [
        "model",
        "manifest",
        "reviewed_roi_catalogue",
        "steps",
        "seed",
        "lr",
        "reviewed_roi_fraction",
    ]:
        changed = copy.deepcopy(configs)
        changed[1][key] = "wrong"
        with pytest.raises(AssertionError, match="differs beyond"):
            trial.validate_recipes(changed)


def test_ordinary_changes_do_not_hide_unaffected_or_global_array_errors():
    mask = np.array([True, False, True, False])
    before = {"target": np.zeros((4, 3, 2, 2), np.float32), "global": np.array(7)}
    after = {k: v.copy() for k, v in before.items()}
    after["target"][~mask] = 1
    assert trial.compare_prepared_arrays(after, before, mask) == 25
    for key in ("target", "global"):
        bad = {k: v.copy() for k, v in after.items()}
        bad[key] += 1
        with pytest.raises(AssertionError):
            trial.compare_prepared_arrays(bad, before, mask)
    bad = {**after, "target": after["target"].astype(np.float64)}
    with pytest.raises(AssertionError):
        trial.compare_prepared_arrays(bad, before, mask)


def fixture(tmp_path):
    owner = {"pid": 1, "created": 2}
    plan = {"path": "frozen-plan", "sha256": "a" * 64}
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"owner": owner, "queue_plan": plan}))
    state = {
        "owner": owner,
        "plan": plan,
        "status": "completed-new-mesh-predictions-native-viewing-pending",
        "result": ref(result),
        "child": None,
    }
    return state, {"owner": owner, "plan": plan}


def test_prior_complete_review_must_exit_with_matching_result(tmp_path, monkeypatch):
    state, dependency = fixture(tmp_path)
    monkeypatch.setattr(trial, "live", lambda owner: True)
    assert not trial.review_ready(state, dependency)
    monkeypatch.setattr(trial, "live", lambda owner: False)
    assert trial.review_ready(state, dependency)
    state["result"]["sha256"] = "bad"
    with pytest.raises(AssertionError):
        trial.review_ready(state, dependency)


@pytest.mark.parametrize("damage", ["plan", "owner", "failed", "premature-exit"])
def test_changed_failed_or_incomplete_review_cannot_release_training(tmp_path, monkeypatch, damage):
    state, dependency = fixture(tmp_path)
    monkeypatch.setattr(trial, "live", lambda owner: False)
    if damage == "plan":
        state["plan"] = {**state["plan"], "sha256": "bad"}
    elif damage == "owner":
        state["owner"] = {**state["owner"], "created": 3}
    elif damage == "failed":
        state["status"] = "failed-mesh-review-preserved-no-automatic-retry"
    else:
        state["status"] = "running-explicit-mesh-child"
    with pytest.raises(AssertionError):
        trial.review_ready(state, dependency)
