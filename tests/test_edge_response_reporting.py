import copy

import pytest
from report_edge_response import statistics


def fixture():
    rows = []
    for method in ["V200-raw", "V200-ema", "shared-raw", "shared-ema"]:
        for placement in ["near", "far"]:
            for source in range(8):
                for view in range(8):
                    delta = 0.1 if method.startswith("shared") else 0.0
                    rows.append(
                        {
                            "index": source * 16 + (placement == "far") * 8 + view,
                            "method": method,
                            "gain_scale": 1.0,
                            "placement": placement,
                            "source": source,
                            "pattern": view // 2,
                            "repeat": view % 2,
                            "weak_gain": source + delta,
                            "quiet_error_RMS_DN16": 10 + source - delta,
                        }
                    )
    return {"rows": rows}


def test_source_clusters_and_matching_noise_views_recover_paired_effect():
    summary, comparisons = statistics(fixture())
    assert all(
        r["sources"] == 8 and r["observations"] == 64 and r["images"] == 192 for r in summary
    )
    for row in comparisons:
        metric = row["metrics"]["weak_gain"]
        assert metric["difference"] == pytest.approx(0.1)
        assert metric["paired_source_bootstrap_95"] == pytest.approx([0.1, 0.1])
        assert row["metrics"]["quiet_error_RMS_DN16"]["difference"] == pytest.approx(-0.1)


def test_missing_or_duplicated_views_cannot_enter_uncertainty_summary():
    scores = fixture()
    duplicate = copy.deepcopy(scores)
    duplicate["rows"].append(duplicate["rows"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        statistics(duplicate)
    scores["rows"].pop()
    with pytest.raises(ValueError, match="four CFAs"):
        statistics(scores)


def test_extra_stage_both_endpoints_compare_to_the_same_frozen_ema():
    scores = fixture()
    for row in scores["rows"]:
        row["method"] = row["method"].replace("shared-", "complementary-")
        if row["method"] == "V200-raw":
            row["weak_gain"] += 10
    _, comparisons = statistics(
        scores, candidate="complementary", baseline_states={"raw": "ema", "ema": "ema"}
    )
    assert all(
        row["metrics"]["weak_gain"]["difference"] == pytest.approx(0.1) for row in comparisons
    )
