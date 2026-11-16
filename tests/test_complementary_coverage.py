"""Coverage joins must preserve observations, the full V200 zero point and arithmetic."""

import copy
import math

import numpy as np
import pytest
from analyze_complementary_coverage import (
    METRICS,
    SELECTORS,
    category,
    independent_distances,
    join_metrics,
    summarize,
    unique,
)


def fixture():
    closed = []
    geometry = []
    scores = []
    baselines = {}
    cache = []
    recipe = {"size": 512, "wire_angles": [0.0, math.pi / 2], "periods": [8.0, 16.0]}
    for index in range(2):
        arrays = {"path": f"input{index}", "sha256": str(index) * 64}
        choices = {}
        for name, bin_ in [
            ("current", [0, 64] if index == 0 else [32, 0]),
            ("additional-only", [32, 0] if index == 0 else [0, 64]),
        ]:
            choices[name] = {
                "bins_yx": np.broadcast_to(bin_, (3, 2, 4, 2)).tolist(),
                "valid": np.ones((3, 2, 4), dtype=bool).tolist(),
            }
        choices["complementary"] = {
            k: np.concatenate(
                [np.asarray(choices[n][k]) for n in ["current", "additional-only"]], axis=2
            ).tolist()
            for k in ["bins_yx", "valid"]
        }
        closed.append({"profile": "fixture", "index": index, "arrays": arrays, "choices": choices})
        r = dict(recipe, source=index)
        cache.append(
            {"index": index, "arrays": arrays, "metadata": {"recipe": r, "placement": "far"}}
        )
        for name in SELECTORS:
            for (role, direction), distance in independent_distances(choices[name], r).items():
                geometry.append(
                    {
                        "profile": "fixture",
                        "index": index,
                        "source": index,
                        "placement": "far",
                        "selector": name,
                        "role": role,
                        "direction": direction,
                        "nearest_fundamental_native_bins": distance,
                    }
                )
        base = {
            "index": index,
            "source": index,
            "placement": "far",
            "pattern": "RGGB",
            "repeat": 0,
            **{k: (0.1 if index == 0 else 0.4) if k == "weak_gain" else 1.0 for k in METRICS},
        }
        baselines["fixture", index] = base
        for state in ["raw", "ema"]:
            for gain in [0.0, 0.25, 0.5, 0.75, 1.0]:
                row = dict(
                    base, profile="fixture", method="complementary-" + state, gain_scale=gain
                )
                row["weak_gain"] += gain * (0.2 if index == 0 else 0.1)
                scores.append(row)
    return closed, geometry, scores, baselines, {"fixture": {"rows": cache}}


def test_signed_native_coordinates_and_conjugates_have_expected_distances():
    recipe = {"size": 512, "wire_angles": [0.0, math.pi / 2], "periods": [8.0, 16.0]}
    choice = {
        "bins_yx": np.broadcast_to([224, 0], (3, 2, 4, 2)).tolist(),
        "valid": np.ones((3, 2, 4), dtype=bool).tolist(),
    }
    distances = independent_distances(choice, recipe)
    assert distances[2, 1] < 1e-12
    assert distances[2, 0] == pytest.approx(math.hypot(32, 64))


def test_groups_partition_observations_and_weighted_contributions_recover_mean():
    rows, audit = join_metrics(*fixture())
    groups = summarize(rows)
    assert audit["independent_distance_checks"] == 36
    assert audit["zero_gain_metric_checks"] == 24
    subset = [x for x in groups if x["state"] == "ema" and x["threshold_native_bins"] == 3]
    assert {x["category"] for x in subset} == {"added-only", "inherited"}
    assert sum(x["observations"] for x in subset) == 2
    assert sum(
        x["metrics"]["weak_gain"]["contribution_to_full_condition_difference"] for x in subset
    ) == pytest.approx(0.15)
    assert {x["sources"] for x in subset} == {1}
    assert next(x for x in subset if x["category"] == "added-only")["metrics"]["weak_gain"][
        "paired_difference"
    ] == pytest.approx(0.2)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_score",
        "missing_score",
        "duplicate_geometry",
        "missing_geometry",
        "source",
        "pattern",
        "arrays",
        "zero_anchor",
        "geometry_distance",
        "nonfinite_geometry",
        "negative_geometry",
        "concatenation",
        "nonfinite",
    ],
)
def test_changed_or_incomplete_evidence_rejected(change):
    closed, geometry, scores, baseline, caches = fixture()
    if change == "duplicate_score":
        scores.append(copy.deepcopy(scores[0]))
    elif change == "missing_score":
        scores.pop()
    elif change == "duplicate_geometry":
        geometry.append(copy.deepcopy(geometry[0]))
    elif change == "missing_geometry":
        geometry.pop()
    elif change == "source":
        scores[4]["source"] = 9
    elif change == "pattern":
        scores[4]["pattern"] = "BGGR"
    elif change == "arrays":
        closed[0]["arrays"] = {"path": "other", "sha256": "other"}
    elif change == "zero_anchor":
        scores[0]["weak_gain"] += 0.001
    elif change == "geometry_distance":
        geometry[0]["nearest_fundamental_native_bins"] += 1.0
    elif change == "nonfinite_geometry":
        geometry[1]["nearest_fundamental_native_bins"] = float("nan")
    elif change == "negative_geometry":
        geometry[1]["nearest_fundamental_native_bins"] = -1.0
    elif change == "concatenation":
        closed[0]["choices"]["complementary"]["valid"][0][0][0] = False
    else:
        scores[4]["weak_gain"] = float("nan")
    with pytest.raises(ValueError):
        join_metrics(closed, geometry, scores, baseline, caches)


def test_combined_bank_cannot_lose_inherited_coverage():
    with pytest.raises(ValueError):
        category(0.5, 4.0, 3.0)
    assert category(0.5, 0.5, 1.0) == "inherited"
    assert category(2.0, 0.5, 1.0) == "added-only"
    assert category(2.0, 1.5, 1.0) == "neither"


def test_duplicate_join_keys_never_silently_overwrite():
    with pytest.raises(ValueError):
        unique([{"id": 0}, {"id": 0}], lambda r: r["id"])
