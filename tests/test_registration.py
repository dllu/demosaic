import numpy as np
import pytest

from demosaic.cfa import PATTERNS
from demosaic.registration import Alignment, align_raw, calibrate_rgb, measured_reference


def sample(rgb, pattern):
    raw = np.zeros(rgb.shape[:2], dtype=np.float32)
    for phase, color in enumerate(PATTERNS[pattern]):
        y, x = divmod(phase, 2)
        raw[y::2, x::2] = rgb[y::2, x::2, color]
    return raw


def scene(size=192):
    rng = np.random.default_rng(42)
    y, x = np.mgrid[:size, :size].astype(np.float32) / size
    rgb = np.full((size, size, 3), 0.03, np.float32)
    for _ in range(18):
        cx, cy = rng.uniform(0.1, 0.9, 2)
        width = rng.uniform(0.01, 0.04)
        blob = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / width)
        rgb += blob[..., None] * rng.uniform(0.01, 0.08, 3).astype(np.float32)
    return rgb


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("shift", [(3, -5), (-6, 4), (0, 0)])
def test_registration_recovers_geometry_gain_with_noise_and_cfa_changes(pattern, shift):
    rgb = scene()
    reference = sample(rgb, "RGGB")
    moved = np.roll(rgb, shift, axis=(0, 1)) * 0.73
    observed = sample(moved, pattern)
    observed += np.random.default_rng(3).normal(0, 0.0005, observed.shape).astype(np.float32)
    result = align_raw(reference, observed, "RGGB", pattern, max_shift=16)
    assert (result.dy, result.dx) == shift
    assert abs(result.gain - 0.73) < 0.001
    assert result.green_l1 < 0.001


@pytest.mark.parametrize("pattern", PATTERNS)
def test_rgb_reference_calibration_preserves_sensor_units_without_mutating_inputs(pattern):
    truth = scene()
    raw = sample(truth, pattern)
    scaling = np.array([1.069, 1.03, 0.93], np.float32)
    encoded = np.rint(truth / scaling * 65535).astype(np.uint16).astype(np.float32) / 65535
    raw.setflags(write=False)
    encoded.setflags(write=False)
    calibrated, receipt = calibrate_rgb(encoded, raw, pattern)
    np.testing.assert_allclose(receipt["rgb_to_sensor_gains"], scaling, atol=1e-5, rtol=0)
    assert np.abs(calibrated - truth).max() < 1e-5


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("shift", [(1, 0), (0, 1), (1, -1), (2, -4)])
def test_measured_reference_uses_shifted_clean_cfa_colors(pattern, shift):
    rgb = scene()
    raw = sample(rgb, pattern)
    dy, dx = shift
    registration = Alignment(dy, dx, 0.8, 0, 1024, (0, 0))
    y, x, size = 32, 48, 64
    values, weights = measured_reference(raw, pattern, registration, y, x, size)
    truth = (rgb[y - dy : y - dy + size, x - dx : x - dx + size] * 0.8).transpose(2, 0, 1)
    np.testing.assert_array_equal(weights.sum(0), 1)
    np.testing.assert_allclose(
        values[weights.astype(bool)], truth[weights.astype(bool)], atol=0, rtol=0
    )


def test_flat_scene_registration_is_refused_instead_of_inventing_a_shift():
    raw = np.full((128, 128), 0.1, np.float32)
    with pytest.raises(ValueError, match="contrast"):
        align_raw(raw, raw, "RGGB", "RGGB", max_shift=16)
