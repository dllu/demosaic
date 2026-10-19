"""Keep engineering states out of quality panels and preserve per-case ADC gates."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("review_context_trial")


@pytest.mark.parametrize("stage", [None, "known", "full427", "hue", "gfx"])
def test_engineering_states_cannot_enter_quality_workers(review, tmp_path, stage):
    plan = tmp_path / "plan.json"
    plan.write_text('{"engineering_preflight": true}')
    with pytest.raises(ValueError, match="cannot produce quality evidence"):
        review.run(plan, stage)


@pytest.mark.parametrize(
    "status",
    [
        "running-source-frozen-context-training-arm",
        "failed-context-trial-no-automatic-retry",
        "completed-context-engineering-preflight",
    ],
)
def test_incomplete_or_engineering_terminal_cannot_be_production(review, tmp_path, status):
    path = tmp_path / "status.json"
    path.write_text('{"status": "' + status + '"}')
    with pytest.raises(RuntimeError, match="Both fixed context budgets"):
        review.require_completed({"training_status": str(path)})


def test_context_ADC_scoring_preserves_a_hidden_individual_failure(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    score = importlib.import_module("score_context_eligibility")
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
        for model in ["base", "context"]
        for level in [0.01, 0.18]
        for contrast in [0.02, 0.1]
        for period in [4, 8, 16]
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]
        for draw in range(4)
    ]
    rows[-1]["metrics"]["in_phase_gain"] = 0.44
    result = score.adc_detail(rows, {"control": "base", "context": "context"})
    assert len(result["cases"]) == 192 and len(result["group_means"]) == 12
    assert all(r["context_minus_control_gain"] > -0.05 for r in result["group_means"])
    assert not result["no_ADC_case_loses_more_than_.05"]
