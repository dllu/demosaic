"""Matched review refuses incomplete/mispaired evidence and real GT scoring."""

import copy

import pytest
from review_cached_head_trial import paired_comparison


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
