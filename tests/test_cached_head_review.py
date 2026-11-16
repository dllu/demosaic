"""Matched review refuses incomplete/mispaired evidence and real GT scoring."""

import copy

import pytest
from review_cached_head_trial import (
    evaluation_overlay,
    paired_comparison,
    recipe_changes,
    verify_frozen_extension,
)


def test_evaluator_overlay_keeps_original_numerical_modules_even_when_checkout_differs(tmp_path):
    original, current, review = [tmp_path / name for name in ["training", "current", "review"]]
    relative = "src/demosaic/experiments/evaluation/runner.py"
    for root in [original, current]:
        (root / relative).parent.mkdir(parents=True)
    (original / relative).write_text("OLD_EVALUATOR = True\n")
    (current / relative).write_text("CORRECTED_METADATA = True\n")
    (original / "src/kernel.py").write_text("ORIGINAL_NUMERICS = True\n")
    (current / "src/kernel.py").write_text("UNRELATED_NEW_NUMERICS = True\n")
    review.mkdir()
    overlay, files, receipt = evaluation_overlay({"work": str(original)}, review, current)
    assert (overlay / relative).read_bytes() == (current / relative).read_bytes()
    assert (overlay / "src/kernel.py").read_bytes() == (original / "src/kernel.py").read_bytes()
    assert (original / relative).read_text() == "OLD_EVALUATOR = True\n"
    assert receipt["other_original_Python_files_exact"] == 1 and len(files) == 2


def test_frozen_extension_keeps_data_fixed_and_requires_the_scored_export_history():
    control = {
        "model": {
            "kind": "scale-supported-cfa-wave",
            "config": {"width": 16},
            "initializer": {"sha256": "V195"},
        },
        "cache": {"sha256": "same-data"},
    }
    new = copy.deepcopy(control)
    new["model"].update(
        kind="complementary-cfa-wave", initialization="anchor", initializer={"sha256": "V200"}
    )
    new["model"]["config"]["family_degrees"] = 20
    assert recipe_changes(new, control, frozen_baseline_extension=True) == ["model"]
    changed = copy.deepcopy(new)
    changed["cache"]["sha256"] = "different-data"
    with pytest.raises(ValueError, match="Unmatched"):
        recipe_changes(changed, control, frozen_baseline_extension=True)
    payload = {
        "component": "LateScaleSupportedCFAWaveDetail",
        "endpoint": "EMA",
        "method": "scored-EMA",
        "source_checkpoint": {"sha256": "trained"},
        "training_plan": {"sha256": "plan"},
        "frozen_V195_anchor": {"export": control["model"]["initializer"]},
    }
    baseline = {
        "checkpoints": {"scale": payload["source_checkpoint"]},
        "plan": payload["training_plan"],
    }
    verify_frozen_extension(payload, baseline, control, ["scored-EMA"] * 2)
    for key in ["source_checkpoint", "training_plan", "endpoint", "frozen_V195_anchor"]:
        changed = dict(payload, **{key: None})
        with pytest.raises(ValueError):
            verify_frozen_extension(changed, baseline, control, ["scored-EMA"] * 2)
    with pytest.raises(ValueError):
        verify_frozen_extension(payload, baseline, control, ["scored-raw", "scored-EMA"])


def test_model_intervention_cannot_silently_change_data_or_initializer():
    control = {
        "model": {"kind": "old", "initializer": {"sha256": "fixed"}, "initialization": "anchor"},
        "cache": {"sha256": "data"},
        "pair_units": {"sha256": "units"},
    }
    new = copy.deepcopy(control)
    new["model"]["kind"] = "new"
    assert recipe_changes(new, control, model_intervention=True) == ["model"]
    with pytest.raises(ValueError, match="Unmatched"):
        recipe_changes(new, control)
    changed = copy.deepcopy(new)
    changed["cache"]["sha256"] = "different"
    with pytest.raises(ValueError, match="Unmatched"):
        recipe_changes(changed, control, model_intervention=True)
    changed = copy.deepcopy(new)
    changed["model"]["initializer"]["sha256"] = "different"
    with pytest.raises(ValueError, match="initializer"):
        recipe_changes(changed, control, model_intervention=True)


def documents():
    rows = [
        {
            "id": name,
            "kind": "mesh",
            "present": True,
            "cohort": None,
            "method": "control",
            "template_gain": gain,
            "full_error_RMS_DN16": error,
        }
        for name, gain, error in (("a", 0.1, 2.0), ("b", 0.2, 3.0))
    ]
    baseline = {"rows": rows}
    candidate = copy.deepcopy(baseline)
    candidate["rows"].reverse()
    candidate["rows"][0].update(method="candidate", template_gain=0.4, full_error_RMS_DN16=5.0)
    candidate["rows"][1].update(method="candidate", template_gain=0.3, full_error_RMS_DN16=1.0)
    return candidate, baseline


def test_pairing_uses_case_identity_and_reports_mixed_error_tail():
    candidate, baseline = documents()
    results = paired_comparison(candidate, baseline, "control")
    indexed = {r["field"]: r for r in results}
    assert indexed["template_gain"]["mean_difference"] == pytest.approx(0.2)
    error = indexed["full_error_RMS_DN16"]
    assert error["mean_difference"] == 0.5
    assert (error["positive"], error["negative"], error["equal"]) == (1, 1, 0)
    assert error["largest_signed_differences"][0] == {"id": "b", "difference": 2.0}
    assert error["difference_quantiles"]["max"] == 2.0


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "condition", "identity"])
def test_missing_duplicated_or_mismatched_cases_cannot_be_summarized(mutation):
    candidate, baseline = documents()
    if mutation == "missing":
        candidate["rows"].pop()
    elif mutation == "duplicate":
        candidate["rows"][1]["id"] = candidate["rows"][0]["id"]
    elif mutation == "condition":
        candidate["rows"][0]["present"] = False
    else:
        candidate["rows"][0]["id"] = "unseen"
    with pytest.raises(ValueError):
        paired_comparison(candidate, baseline, "control")


def test_independent_real_references_are_excluded_from_error_comparison():
    row = {
        "id": "real",
        "kind": "real",
        "method": "control",
        "reference_scored": False,
        "correction_RMS_DN16": 40.0,
    }
    candidate = {"rows": [dict(row, method="candidate", correction_RMS_DN16=20.0)]}
    baseline = {"rows": [row]}
    assert paired_comparison(candidate, baseline, "control") == []
    candidate["rows"][0]["reference_scored"] = True
    with pytest.raises(ValueError, match="must not be scored"):
        paired_comparison(candidate, baseline, "control")


def test_nonfinite_metrics_are_rejected():
    candidate, baseline = documents()
    candidate["rows"][0]["template_gain"] = float("nan")
    with pytest.raises(ValueError, match="Nonfinite"):
        paired_comparison(candidate, baseline, "control")
