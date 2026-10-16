import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from demosaic.cfa import PATTERNS

spec = importlib.util.spec_from_file_location(
    "diagnose_paired_residuals",
    Path(__file__).resolve().parents[1] / "scripts/diagnose_paired_residuals.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def image(dx=0, dy=0):
    y, x = np.mgrid[:128, :160].astype(np.float64)
    x, y = x + dx, y + dy
    base = 0.2 + 0.055 * np.sin(2 * np.pi * x / 80) + 0.045 * np.cos(2 * np.pi * y / 64)
    return np.stack([base, base * 0.8 + 0.03, base * 0.6 + 0.05])


def measured(rgb, pattern):
    raw = np.empty(rgb.shape[1:])
    valid = np.zeros_like(rgb, bool)
    for phase, color in enumerate(PATTERNS[pattern]):
        y, x = divmod(phase, 2)
        raw[y::2, x::2] = rgb[color, y::2, x::2]
        valid[color, y::2, x::2] = True
    return raw, valid


@pytest.mark.parametrize("pattern", PATTERNS)
def test_known_fractional_offset_is_detected_without_modifying_arrays(pattern):
    reference = image()
    raw, valid = measured(image(dx=0.3, dy=-0.25), pattern)
    raw += np.random.default_rng(13).normal(0, 0.0001, raw.shape)
    original = [x.copy() for x in [raw, reference, valid]]
    result = module.residual_diagnostics(raw, reference, valid, pattern, 0, 1e-8)
    np.testing.assert_allclose(
        result["first_order_shift_xy_sensor_pixels"], [0.3, -0.25], atol=0.015
    )
    assert result["mean_phase_lag_correlation"] > 0.9
    for actual, previous in zip([raw, reference, valid], original):
        np.testing.assert_array_equal(actual, previous)


def test_white_noise_flat_has_no_structural_shift_or_large_lag_correlation():
    reference = np.full((3, 128, 160), 0.2)
    raw, valid = measured(reference, "RGGB")
    raw += np.random.default_rng(12).normal(0, 0.001, raw.shape)
    result = module.residual_diagnostics(raw, reference, valid, "RGGB", 0, 1e-6)
    assert result["first_order_shift_xy_sensor_pixels"] is None
    assert abs(result["mean_phase_lag_correlation"]) < 0.05
    for phase in result["phases"]:
        assert abs(phase["rms_noise_units"] - 1) < 0.05


def test_sharpness_mismatch_can_correlate_without_a_translation():
    reference = image()
    blurred = (
        sum(np.roll(reference, offset, axis=axis) for axis in [1, 2] for offset in [-2, 2]) / 4
    )
    raw, valid = measured(blurred, "RGGB")
    result = module.residual_diagnostics(raw, reference, valid, "RGGB", 0, 1e-8)
    assert result["mean_phase_lag_correlation"] > 0.9
    np.testing.assert_allclose(result["first_order_shift_xy_sensor_pixels"], [0, 0], atol=0.01)


def test_invalid_or_unmeasured_data_does_not_create_a_shift():
    reference = image()
    raw, valid = measured(reference, "RGGB")
    valid.fill(False)
    result = module.residual_diagnostics(raw, reference, valid, "RGGB", 0, 0)
    assert result["samples"] == 0 and result["first_order_shift_xy_sensor_pixels"] is None
    with pytest.raises(ValueError, match="nonnegative"):
        module.residual_diagnostics(raw, reference, valid, "RGGB", -1, 0)
    with pytest.raises(ValueError, match="matching"):
        module.residual_diagnostics(raw, reference[:, :-1], valid, "RGGB", 0, 0)


@pytest.mark.parametrize("split", ["development", "test"])
def test_heldout_data_diagnostic_is_rejected_before_output_creation(tmp_path, split):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"split": split, "cases": []}))
    with pytest.raises(ValueError, match="held-out"):
        module.diagnose(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()
