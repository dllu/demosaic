import numpy as np

from demosaic.wire_segment_support import (
    directional_windows,
    energy_matched_gain,
    soft_wire_support,
    window_contrast,
)


def test_directional_windows_keep_uniform_amplitude_and_allow_a_partial_break():
    x = np.array([-20, 0, 20])
    y = np.array([-40, 0, 40])
    w = directional_windows(x, y, 0, 20, 40)
    np.testing.assert_array_equal(w.sum(1), np.ones(3))
    w = directional_windows(np.zeros(3), y, 0, 20, 40)
    gains = np.ones((3, 5))
    gains[:, 2] = 0
    np.testing.assert_array_equal(w @ gains.ravel(), [1, 0, 1])


def test_window_contrast_rejects_an_affine_plane_and_competing_frequency():
    x = np.linspace(-1, 1, 121)
    carrier = np.cos(x * 19)
    nuisance = np.column_stack((np.ones_like(x), x, np.sin(14 * x)))
    taper = np.maximum(1 - 1.6 * abs(x), 0)
    samples = nuisance @ np.array([60, 8, 20]) + 3 * carrier
    selected, contrast, error = window_contrast(carrier, nuisance, taper)
    np.testing.assert_allclose(contrast @ samples[selected], 3, rtol=0, atol=2e-13)
    assert error > 0
    assert window_contrast(nuisance[:, -1], nuisance, taper)[1] is None


def test_support_requires_two_positive_estimates_and_uniform_control_matches_energy():
    amplitude = np.array([[0.8, -0.1, 1.0, 0.01], [0.8, 0.95, 0.95, 0.01]])
    error = np.array([[0.1, 0.1, np.inf, 0.01], [0.1, 0.95, 0.2, 0.01]])
    gains = soft_wire_support(amplitude, error, exterior=1.0)
    assert 0 < gains[0] < 1
    np.testing.assert_array_equal(gains[1:], 0)
    wave = np.array([1, -2, 3, -4])
    np.testing.assert_allclose(
        (gains * wave) @ (gains * wave), energy_matched_gain(gains, wave) ** 2 * (wave @ wave)
    )
