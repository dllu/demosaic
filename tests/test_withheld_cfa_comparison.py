"""Calibration must exclude test data; sufficient statistics retain exact error."""

import numpy as np
import pytest
from compare_withheld_cfa import calibration_null_threshold, increment_error


def test_threshold_uses_only_calibration_null_step_fits():
    rows = [
        {"cohort": "calibration", "kind": "edge", "nuisance": "step", "min_validation_z": 3.0},
        {"cohort": "test", "kind": "edge", "nuisance": "step", "min_validation_z": 1000.0},
        {
            "cohort": "calibration",
            "kind": "two-wave",
            "nuisance": "step",
            "min_validation_z": 100.0,
        },
        {"cohort": "calibration", "kind": "flat", "nuisance": "affine", "min_validation_z": 500.0},
    ]
    expected = np.nextafter(3.0, np.inf)
    assert calibration_null_threshold(rows) == expected
    rows[1]["min_validation_z"] = -1000.0
    assert calibration_null_threshold(rows) == expected
    rows[0]["min_validation_z"] = -1.0
    assert calibration_null_threshold(rows) == 2.0


@pytest.mark.parametrize("active", [False, True])
def test_increment_error_agrees_with_direct_pixel_error_including_off_target_energy(active):
    rng = np.random.default_rng(1794)
    directions = [rng.normal(size=(32, 32)) for _ in range(2)]
    signal = sum(directions)
    correction = 0.3 * directions[0] + 0.6 * directions[1] + rng.normal(size=signal.shape) * 0.4
    row = {
        "correction_RMS_DN16": float(np.sqrt(np.mean(correction**2)) * 65535),
        "direction_gains": [float(np.sum(correction * d) / np.sum(d**2)) for d in directions],
    }
    expected = np.sqrt(np.mean((active * correction - signal) ** 2)) * 65535
    assert increment_error(row, signal, directions, active) == pytest.approx(expected, rel=2e-15)
