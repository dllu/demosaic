"""Matched comparison identity, finite metrics and signed absent-gain handling."""

import copy

import pytest
from reduce_coherent_pair_evidence_trial import ALL_METHODS, comparisons


def fixture():
    rows = []
    for method in ALL_METHODS:
        change = 0.01 if method.startswith("V183-coherent-pair-") else 0
        for present in [True, False]:
            rows.append(
                {
                    "id": "present" if present else "absent",
                    "method": method,
                    "kind": "mesh",
                    "present": present,
                    "cohort": None,
                    "full_error_RMS_DN16": 2 + change,
                    "crop_spatial_RMS_DN16": 1 + change,
                    "crop_DC_RMS_DN16": 0.2 + change,
                    "blank_error_RMS_DN16": 1.2 + change,
                    "blank_spatial_RMS_DN16": 1 + change,
                    "blank_DC_RMS_DN16": 0.2 + change,
                    "template_gain": (0.1 if present else 0.001) + change,
                }
            )
        rows.append(
            {
                "id": "sky",
                "method": method,
                "kind": "real",
                "cohort": None,
                "reference_scored": False,
                "correction_RMS_DN16": 0.2 + change,
            }
        )
    return rows


def test_matched_endpoint_contrasts_preserve_pairs_and_do_not_score_real_refs():
    result = comparisons(fixture(), ALL_METHODS, ["present", "absent", "sky"])
    assert result["methods"] == 19 and result["metric_rows"] == 57 and result["contrasts"] == 32
    assert result["matched_endpoint_contrasts"] == 2 and result["real_references_scored"] is False
    assert result["paired_mean_and_difference_checks"] == 3 * len(result["groups"])
    assert all(group["kind"] != "real" for group in result["groups"])
    matched = [
        group
        for group in result["groups"]
        if group["comparison_role"] == "matched-loss-EMA"
        and group["condition"] is True
        and group["field"] == "template_gain"
    ]
    assert len(matched) == 1 and matched[0]["baseline"] == "V181-flat-spatial-EMA"
    assert matched[0]["mean_difference"] == pytest.approx(0.01)
    assert matched[0]["increased"] == 1 and matched[0]["decreased"] == 0


def test_signed_absent_gain_never_receives_a_relative_percentage():
    result = comparisons(fixture(), ALL_METHODS, ["present", "absent", "sky"])
    absent = [
        group
        for group in result["groups"]
        if group["condition"] is False and group["field"] == "template_gain"
    ]
    assert len(absent) == 32
    assert all(group["percent_change_of_means"] is None for group in absent)
    assert all(
        group["mean_difference"]
        == pytest.approx(0.01 if group["method"].startswith("V183-coherent-pair-") else 0)
        for group in absent
    )


def test_older_parent_quiet_dc_uses_the_existing_common_crop_field():
    rows = fixture()
    for method in ALL_METHODS:
        row = {
            "id": "quiet",
            "kind": "mixed-quiet",
            "noise": "iso6400-prior",
            "cohort": None,
            "method": method,
            "full_error_RMS_DN16": 3.0,
            "crop_spatial_RMS_DN16": 1.0,
            "crop_DC_RMS_DN16": 0.4,
            "quiet_error_RMS_DN16": 1.1,
            "quiet_spatial_RMS_DN16": 1.0,
        }
        if method != "parent":
            row["quiet_DC_RMS_DN16"] = 0.4
        rows.append(row)
    result = comparisons(rows, ALL_METHODS, ["present", "absent", "sky", "quiet"])
    dc = [
        g
        for g in result["groups"]
        if g["kind"] == "mixed-quiet"
        and g["baseline"] == "parent"
        and g["field"] == "crop_DC_RMS_DN16"
    ]
    assert len(dc) == 2 and all(group["mean_difference"] == 0 for group in dc)


@pytest.mark.parametrize("baseline", [0.0, -0.1])
def test_nonpositive_present_gain_baselines_preserve_absolute_difference(baseline):
    rows = fixture()
    for row in rows:
        if row["id"] == "present" and not row["method"].startswith("V183-coherent-pair-"):
            row["template_gain"] = baseline
    result = comparisons(rows, ALL_METHODS, ["present", "absent", "sky"])
    group = next(
        g
        for g in result["groups"]
        if g["comparison_role"] == "matched-loss-raw"
        and g["condition"] is True
        and g["field"] == "template_gain"
    )
    assert group["percent_change_of_means"] is None and group["mean_difference"] > 0


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "missing",
        "cohort",
        "kind",
        "condition",
        "metric",
        "nonfinite",
        "real_score",
        "real_error",
    ],
)
def test_missing_or_incompatible_paired_data_rejects(damage):
    rows = fixture()
    if damage == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif damage == "missing":
        rows.pop()
    elif damage == "cohort":
        rows[0]["cohort"] = "different-inputs"
    elif damage == "kind":
        rows[0]["kind"] = "photo"
    elif damage == "condition":
        rows[0]["present"] = False
    elif damage == "metric":
        rows[0].pop("blank_error_RMS_DN16")
    elif damage == "nonfinite":
        rows[0]["template_gain"] = float("nan")
    elif damage == "real_score":
        rows[2]["reference_scored"] = True
    else:
        rows[2]["full_error_RMS_DN16"] = 1
    with pytest.raises((AssertionError, KeyError)):
        comparisons(rows, ALL_METHODS, ["present", "absent", "sky"])
