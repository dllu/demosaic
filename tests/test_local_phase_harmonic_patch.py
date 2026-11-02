"""Local support must follow CFA coordinates and independent-noise propagation."""

import numpy as np
import pytest
from local_phase_harmonic_patch import correct_local_patch, envelope_terms, native_envelope


def test_shifted_phase_sums_and_squared_kernel_variance_against_dense_native_geometry():
    height, width = 9, 11
    y, x = np.mgrid[:height, :width]
    colors = np.array([0, 1, 1, 2])
    residual = np.stack([0.001 * np.sin(0.7 * x + 0.3 * y + p) for p in range(4)])
    variance = np.stack([0.00001 * (1 + 0.03 * x + 0.02 * y + 0.1 * p) for p in range(4)])
    planes = np.stack([0.00003 * (x - y + p) for p in range(4)])
    coefficients = np.array([0.0013, -0.0008])
    frequency = (0.081, 0.057)
    sigma = 4.0
    sums = envelope_terms(residual, variance, colors, planes, coefficients, frequency, sigma)
    radius = int(np.ceil(4 * sigma / 2))
    coords = np.arange(-radius, radius + 1)
    for py, px in [(0, 0), (4, 5), (8, 10)]:
        expected = np.zeros(3)
        for phase in [1, 2]:
            oy, ox = divmod(phase, 2)
            # Direct weights use measured native coordinates and output center(2*p+.5).
            ky = np.exp(-0.5 * ((coords - (oy - 0.5) / 2) / (sigma / 2)) ** 2)
            kx = np.exp(-0.5 * ((coords - (ox - 0.5) / 2) / (sigma / 2)) ** 2)
            normalization = ky.sum() * kx.sum()
            weights = (
                np.exp(
                    -0.5
                    * (
                        ((2 * y + oy - (2 * py + 0.5)) / sigma) ** 2
                        + ((2 * x + ox - (2 * px + 0.5)) / sigma) ** 2
                    )
                )
                / normalization
            )
            weights *= (np.abs(y - py) <= radius) & (np.abs(x - px) <= radius)
            angle = 2 * np.pi * (frequency[0] * (2 * x + ox) + frequency[1] * (2 * y + oy))
            signal = coefficients[0] * np.cos(angle) + coefficients[1] * np.sin(angle)
            expected[0] += np.sum(
                weights * (residual[phase] - planes[phase]) * signal / variance[phase]
            )
            expected[1] += np.sum(weights * signal**2 / variance[phase])
            expected[2] += np.sum(weights**2 * signal**2 / variance[phase])
        np.testing.assert_allclose([v[py, px] for v in sums], expected, rtol=3e-14, atol=1e-16)


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_coherent_native_wave_remains_and_blank_ADC_is_exact(colors):
    y, x = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    target = base + 0.002 * np.cos(2 * np.pi * (0.0625 * x + 0.09375 * y))[None]
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    candidate, info = correct_local_patch(packed, np.full_like(packed, 1e-7), colors, base)
    region = (..., slice(48, 208), slice(48, 208))
    assert info["peaks"]
    assert np.mean((candidate[region] - target[region]) ** 2) < 0.01 * np.mean(
        (base[region] - target[region]) ** 2
    )
    unchanged, _ = correct_local_patch(packed, np.zeros_like(packed), colors, base)
    np.testing.assert_array_equal(unchanged, base)


def test_native_envelope_interpolates_cell_centers_without_moving_harmonics():
    small = np.arange(12, dtype=float).reshape(3, 4)
    actual = native_envelope(small)
    assert actual.shape == (6, 8)
    # Native interior(2,2) lies at packed(.75,.75).
    assert actual[2, 2] == pytest.approx(3.75)


def test_missing_green_variance_bypasses_and_float_CFA_rejects():
    base = np.full((3, 256, 256), 0.02)
    packed = np.full((4, 128, 128), 0.02)
    variance = np.ones_like(packed)
    variance[1:3] = 0
    result, info = correct_local_patch(packed, variance, [0, 1, 1, 2], base)
    np.testing.assert_array_equal(result, base)
    assert info["green_variance_unavailable"]
    with pytest.raises(ValueError):
        correct_local_patch(packed, np.ones_like(packed), [0.0, 1.0, 1.0, 2.0], base)
