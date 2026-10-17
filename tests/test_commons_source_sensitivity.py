import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def script():
    path = Path("scripts/report_commons_source_sensitivity.py")
    spec = importlib.util.spec_from_file_location("source_sensitivity", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def observations():
    rows = []
    for identity, offset in [("a", 1.0), ("b", 10.0)]:
        for condition, noise in [("low", 0.0), ("high", 2.0)]:
            for pattern, phase in [("RGGB", 0.0), ("BGGR", 0.5)]:
                rows.append(
                    {
                        "model": "m",
                        "kind": "photo",
                        "id": identity,
                        "condition": condition,
                        "pattern": pattern,
                        "metrics": {
                            "linear_psnr": offset + noise + phase,
                            "srgb_psnr": offset * 2 + noise + phase,
                            "srgb_ssim": offset / 100 + noise / 100 + phase / 100,
                        },
                    }
                )
    return rows


def test_actual_source_cell_coverage_is_complete_and_balanced():
    module = script()
    values = module.photo_scores(observations(), "m", ["a", "b"], ["low", "high"], ["RGGB", "BGGR"])
    assert values["a"]["linear_psnr"] == 2.25
    assert values["b"]["srgb_psnr"] == 21.25
    assert values["a"]["srgb_ssim"] == pytest.approx(0.0225)


@pytest.mark.parametrize("problem", ["duplicate", "missing", "wrong_source", "null"])
def test_invalid_observation_cannot_hide_behind_a_set_or_average(problem):
    module = script()
    rows = observations()
    if problem == "duplicate":
        rows.append(rows[0])
    elif problem == "missing":
        rows.pop()
    elif problem == "wrong_source":
        rows[-1] = {**rows[-1], "id": "other"}
    else:
        rows[-1] = {**rows[-1], "metrics": {**rows[-1]["metrics"], "srgb_psnr": None}}
    with pytest.raises(ValueError):
        module.photo_scores(rows, "m", ["a", "b"], ["low", "high"], ["RGGB", "BGGR"])


def test_exhaustive_two_source_bootstrap_has_known_interval_and_direction():
    module = script()
    # All four ordered size-two resamples of source deltas[0,2].
    indices = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    result = module.compare_values([1.0, 4.0], [1.0, 2.0], indices)
    assert result["first_source_balanced_mean"] == 2.5
    assert result["second_source_balanced_mean"] == 1.5
    assert result["mean_first_minus_second"] == 1.0
    np.testing.assert_allclose(
        result["source_bootstrap_95_interval"], [0.075, 1.925], atol=1e-12, rtol=0
    )
    same = module.compare_values([1.0, 4.0], [1.0, 4.0], indices)
    assert same["source_bootstrap_95_interval"] == [0.0, 0.0]
