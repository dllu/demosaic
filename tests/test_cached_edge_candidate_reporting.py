import copy

import pytest
from report_cached_edge_candidate import paired_rows


def data():
    old, new = [], []
    for state in ["raw", "ema"]:
        for gain in [0.0, 1.0]:
            row = {
                "index": 0,
                "method": "V200-" + state,
                "gain_scale": gain,
                "source": 0,
                "placement": "near",
                "pattern": "RGGB",
                "repeat": 0,
                "weak_gain": 0.1,
                "quiet_error_RMS_DN16": 10.0,
            }
            old.append(row)
            new.append(dict(row, method="competing-" + state, weak_gain=0.1 + gain))
    return old, new


def test_pairing_is_order_independent_and_retains_the_actual_model_effect():
    old, new = data()
    merged = paired_rows(list(reversed(new)), old)
    assert len(merged) == 8
    assert merged[-1]["method"].startswith("competing-")
    assert merged[-2]["weak_gain"] == 1.1


@pytest.mark.parametrize("problem", ["repeat", "duplicate", "missing", "anchor", "nonfinite"])
def test_candidate_cannot_change_observations_or_zero_gain_anchors(problem):
    old, new = data()
    new = copy.deepcopy(new)
    if problem == "repeat":
        new[0]["repeat"] = 1
    elif problem == "duplicate":
        new.append(new[0])
    elif problem == "missing":
        new.pop()
    elif problem == "anchor":
        new[0]["weak_gain"] = 0.2
    else:
        new[1]["weak_gain"] = float("nan")
    with pytest.raises(ValueError):
        paired_rows(new, old)
