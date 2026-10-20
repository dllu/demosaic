"""Reject early quality evidence and preserve per-case/recovery invariants."""

import copy
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("review_spectral_trial")


@pytest.mark.parametrize(
    "stage",
    [
        None,
        "known",
        "unseen",
        "full427",
        "statistics",
        "sensitivity",
        "gfx",
        "analytic",
        "hue",
        "highlights",
    ],
)
def test_discarded_engineering_states_cannot_enter_any_quality_stage(review, tmp_path, stage):
    path = tmp_path / "plan.json"
    path.write_text('{"engineering_preflight":true}')
    with pytest.raises(ValueError, match="cannot produce quality evidence"):
        review.run(path, stage)


@pytest.mark.parametrize(
    "status",
    [
        "running-source-frozen-spectral-arm",
        "waiting-for-spectral-resources",
        "failed-spectral-trial-no-automatic-retry",
        "completed-spectral-engineering-preflight",
    ],
)
def test_incomplete_or_engineering_status_is_not_production_completion(review, tmp_path, status):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": status}))
    with pytest.raises(RuntimeError, match="Both fixed spectral budgets"):
        review.require_completed({"training_status": str(path)})


def test_terminal_file_cannot_override_a_live_training_owner(review, tmp_path, monkeypatch):
    owner = {"pid": 12, "created": 34}
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": review.TERMINAL, "controller": owner, "child": owner}))
    monkeypatch.setattr(review.panels, "alive", lambda _: True)
    with pytest.raises(AssertionError):
        review.require_completed({"training_status": str(path), "training_owner": owner})


def test_ADC_group_mean_cannot_hide_a_single_layout_draw_failure(review):
    score = importlib.import_module("score_spectral_eligibility")
    rows = [
        {
            "model": model,
            "kind": "carrier",
            "condition": "adc-only",
            "level": level,
            "contrast": contrast,
            "period": period,
            "pattern": pattern,
            "draw": draw,
            "metrics": {"in_phase_gain": 0.5},
        }
        for model in ["baseline", "spectral"]
        for level in [0.01, 0.18]
        for contrast in [0.02, 0.1]
        for period in [4, 8, 16]
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]
        for draw in range(4)
    ]
    rows[-1]["metrics"]["in_phase_gain"] = 0.44
    result = score.adc_detail(rows, {"control": "baseline", "spectral": "spectral"})
    assert len(result["cases"]) == 192 and len(result["group_means"]) == 12
    assert all(g["spectral_minus_control_gain"] > -0.05 for g in result["group_means"])
    assert not result["no_ADC_case_loses_more_than_.05"]
    assert len([r for r in result["cases"] if not r["gain_loss_at_most_.05"]]) == 1


def test_recovery_requires_exact_saved_prefix_and_explicit_handoff(review, tmp_path, monkeypatch):
    monkeypatch.setattr(review.panels, "alive", lambda _: False)
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"Provenance-only fixture, not model weights")
    original = tmp_path / "original.json"
    original.write_text("{}")
    metric = tmp_path / "metrics.jsonl"
    metric.write_text("{}\n")
    prefix = [{"step": s} for s in [*range(1, 17), *range(25, 1001, 25)]]
    prefix_path = tmp_path / "prefix.json"
    prefix_path.write_text(json.dumps(prefix))
    resume = {
        "step": 1000,
        "checkpoint": review.ref(checkpoint),
        "observations": review.ref(prefix_path),
    }
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "status": "completed-verified-checkpoint-handoff-original-owners-exited",
                "controller": {},
                "training_owners": {"controller": {}, "child": {}},
                "training_plan": review.ref(original),
                "checkpoint": resume["checkpoint"],
                "observations": resume["observations"],
                "metrics": review.ref(metric),
            }
        )
    )
    training = {
        "resume": {"control": resume},
        "handoff": review.ref(handoff),
        "recovery_of": review.ref(original),
        "arm_timeout_seconds": {"control": 13462},
        "planned_updates": 4000,
        "boundary_updates": 4000,
    }
    case = {
        "resume": resume,
        "captures": [{"resuming": True, "initial_output_exact_parent": False}],
    }
    assert (
        review.check_recovery(training, {"name": "control"}, case, prefix)["preserved_observations"]
        == 56
    )
    changed = copy.deepcopy(prefix)
    changed[-1]["step"] = 999
    with pytest.raises(AssertionError):
        review.check_recovery(training, {"name": "control"}, case, changed)


@pytest.mark.parametrize("mutation", ["source", "loss"])
def test_discarded_work_must_replay_exact_observations_and_metrics(review, tmp_path, mutation):
    observed = [{"step": 1025, "source_sha256": "abc"}]
    oldrow = {
        "step": 1025,
        "domain": "commons",
        "lr": 1e-5,
        "batch_sha256": "abc",
        "loss": 0.02,
        "grad_norm": 0.1,
    }
    obs = tmp_path / "discarded.json"
    obs.write_text(json.dumps(observed))
    metrics = tmp_path / "discarded.jsonl"
    metrics.write_text(json.dumps(oldrow) + "\n")
    training = {"discarded_observations": review.ref(obs), "discarded_metrics": review.ref(metrics)}
    assert (
        review.check_replayed_work(training, observed, [oldrow])["replayed_recorded_observations"]
        == 1
    )
    changed_obs, changed_row = copy.deepcopy(observed), copy.deepcopy(oldrow)
    if mutation == "source":
        changed_obs[0]["source_sha256"] = "changed"
    else:
        changed_row["loss"] += 0.001
    with pytest.raises(AssertionError):
        review.check_replayed_work(training, changed_obs, [changed_row])
