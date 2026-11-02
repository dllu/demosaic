"""Phase-aware patch correction keeps CFA geometry and exact bypasses explicit."""

import numpy as np
import pytest
from phase_harmonic_patch import correct_patch


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_coherent_native_wave_uses_physical_phase_coordinates(colors):
    y, x = np.mgrid[:256, :256]
    wave = 0.002 * np.cos(2 * np.pi * (0.0625 * x + 0.09375 * y))
    base = np.full((3, 256, 256), 0.02)
    target = base + wave[None]
    packed = np.stack([target[color, p // 2 :: 2, p % 2 :: 2] for p, color in enumerate(colors)])
    candidate, info = correct_patch(packed, np.full_like(packed, 1e-7), colors, base)
    assert info["peaks"] and any(g["gate"] > 0.9 for g in info["gates"])
    region = (..., slice(48, 208), slice(48, 208))
    assert np.mean((candidate[region] - target[region]) ** 2) < 0.4 * np.mean(
        (base[region] - target[region]) ** 2
    )


def test_uniform_observation_and_exact_ADC_bypass_preserve_parent_values():
    base = np.full((3, 256, 256), 0.02)
    packed = np.full((4, 128, 128), 0.02)
    for variance in [np.zeros_like(packed), np.full_like(packed, 1e-5)]:
        result, info = correct_patch(packed, variance, [0, 1, 1, 2], base)
        np.testing.assert_array_equal(result, base)
        assert info["peaks"] == []


@pytest.mark.parametrize("change", ["shape", "CFA", "negative", "nonfinite"])
def test_invalid_patch_rejects_before_regression(change):
    base = np.full((3, 256, 256), 0.02)
    packed = np.full((4, 128, 128), 0.02)
    variance = np.ones_like(packed)
    colors = [0, 1, 1, 2]
    if change == "shape":
        base = base[:, :128]
    if change == "CFA":
        colors = [0, 0, 1, 2]
    if change == "negative":
        variance[0, 0, 0] = -1
    if change == "nonfinite":
        packed[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        correct_patch(packed, variance, colors, base)
