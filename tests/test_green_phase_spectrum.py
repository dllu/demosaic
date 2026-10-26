import numpy as np
import pytest
from green_phase_spectrum import cross_decomposition, green_pair, tapered_spectrum

PATTERNS = [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)]


def packed_field(image):
    return np.stack([image[y::2, x::2] for y, x in ((0, 0), (0, 1), (1, 0), (1, 1))])


def test_weighted_plane_and_noise_match_independent_dense_complex_DFT():
    height, width = 8, 10
    y, x = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    image = 0.18 + 0.01 * np.cos(x * 1.3 + y * 0.6) + 0.004 * x**2
    variance = 1e-4 * (1 + 0.4 * np.sin(x + y))
    before = image.copy(), variance.copy()
    q = np.stack([np.ones_like(x), 2 * x / (width - 1) - 1, 2 * y / (height - 1) - 1], -1).reshape(
        -1, 3
    )
    w = (np.hanning(height)[:, None] * np.hanning(width)[None, :]).ravel()
    f = np.exp(
        -2j
        * np.pi
        * (
            y.ravel()[:, None] * y.ravel()[None] / height
            + x.ravel()[:, None] * x.ravel()[None] / width
        )
    ) / np.sqrt(height * width)
    fit = q @ np.linalg.solve(q.T @ ((w * w)[:, None] * q), q.T * (w * w)[None])
    operator = f @ (w[:, None] * (np.eye(height * width) - fit))
    expected = operator @ image.ravel()
    noise = np.abs(operator) ** 2 @ variance.ravel()
    actual = tapered_spectrum(image, variance)
    np.testing.assert_allclose(actual["spectrum"].ravel(), expected, atol=4e-15, rtol=1e-12)
    np.testing.assert_allclose(actual["noise_variance"].ravel(), noise, atol=1e-18, rtol=1e-12)
    assert np.array_equal(before[0], image) and np.array_equal(before[1], variance)


def test_affine_field_removed_without_clipping_and_zero_noise_has_no_normalized_statistic():
    y, x = np.meshgrid(np.arange(32), np.arange(40), indexing="ij")
    image = -0.01 + 0.03 * x - 0.05 * y
    result = tapered_spectrum(image, np.zeros_like(image))
    # The plane fit and unitary FFT should leave only normwise FP64 roundoff.
    assert np.linalg.norm(result["spectrum"]) < 8 * np.finfo(float).eps * np.linalg.norm(image)
    pair = green_pair(packed_field(image), np.zeros((4, 16, 20)), PATTERNS[0])
    assert pair["noise_units_signed_cross"] is None
    assert pair["noise_units_mean_phase_power"] is None


@pytest.mark.parametrize("pattern", PATTERNS)
def test_subpixel_phase_compensation_resolves_low_frequency_carrier(pattern):
    y, x = np.meshgrid(np.arange(128), np.arange(160), indexing="ij")
    image = 0.18 + 0.0036 * np.cos(2 * np.pi * (5 * x / 160 + 3 * y / 128) + 0.4)
    packed = packed_field(image)
    result = green_pair(packed, np.full_like(packed, 1e-5), pattern)
    assert result["signed_coherence"][3, 5] > 0.998
    assert result["noise_units_signed_cross"][3, 5] > 1
    assert np.max(np.abs(result["complex_coherence"])) <= 1 + 1e-12


@pytest.mark.parametrize("pattern", PATTERNS)
def test_above_phase_Nyquist_signal_can_have_negative_aligned_cross_power(pattern):
    _y, x = np.meshgrid(np.arange(128), np.arange(160), indexing="ij")
    image = 0.18 + 0.0036 * np.cos(2 * np.pi * 3 * x / 8 + 0.4)
    packed = packed_field(image)
    result = green_pair(packed, np.full_like(packed, 1e-5), pattern)
    assert result["signed_coherence"][0, 20] < -0.998
    assert result["noise_units_signed_cross"][0, 20] < -1


@pytest.mark.parametrize("pattern", PATTERNS)
def test_four_pixel_carrier_can_vanish_in_one_measured_green_phase(pattern):
    _y, x = np.meshgrid(np.arange(128), np.arange(160), indexing="ij")
    image = 0.18 + 0.0036 * np.cos(2 * np.pi * x / 4)
    packed = packed_field(image)
    result = green_pair(packed, np.full_like(packed, 1e-5), pattern)
    strengths = result["power"][:, 0, 40]
    assert strengths.min() < 1e-24 and strengths.max() > 0.001
    assert abs(result["noise_units_signed_cross"][0, 40]) < 1e-8


@pytest.mark.parametrize("damage", ["negative_variance", "nonfinite", "non_bayer"])
def test_invalid_inputs_rejected(damage):
    packed, variance, colors = np.ones((4, 16, 20)), np.ones((4, 16, 20)), PATTERNS[0]
    if damage == "negative_variance":
        variance[1, 0, 0] = -1
    elif damage == "nonfinite":
        packed[1, 0, 0] = np.nan
    else:
        colors = (0, 0, 1, 2)
    with pytest.raises(ValueError):
        green_pair(packed, variance, colors)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_reference_residual_mixed_split_keeps_cancellation_and_negative_terms(pattern):
    y, x = np.meshgrid(np.arange(32), np.arange(40), indexing="ij")
    reference = packed_field(0.18 + 0.01 * np.cos(2 * np.pi * (3 * x / 40 + 2 * y / 32)))
    # A deterministic algebra fixture: observed contrast is reduced by half.
    observed = 0.18 + 0.5 * (reference - 0.18)
    before = reference.copy(), observed.copy()
    result = cross_decomposition(observed, reference, np.full_like(reference, 1e-4), pattern)
    parts = result["component_cross"]
    np.testing.assert_allclose(parts["residual"], 0.25 * parts["reference"], atol=1e-17)
    np.testing.assert_allclose(parts["mixed"], -parts["reference"], atol=1e-17)
    np.testing.assert_allclose(sum(parts.values()), result["observed"]["average_cross"], atol=1e-17)
    assert np.min(parts["mixed"].real) < 0
    assert np.array_equal(reference, before[0]) and np.array_equal(observed, before[1])


def test_reference_residual_split_has_zero_residual_for_identical_fields():
    y, x = np.meshgrid(np.arange(32), np.arange(40), indexing="ij")
    field = packed_field(0.18 + 0.01 * np.cos(2 * np.pi * x / 8 + y))
    result = cross_decomposition(field, field, np.zeros_like(field), PATTERNS[0])
    assert np.array_equal(result["component_cross"]["residual"], np.zeros((16, 20)))
    assert np.array_equal(result["component_cross"]["mixed"], np.zeros((16, 20)))
    assert result["noise_units_components"] is None
