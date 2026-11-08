import numpy as np
import pytest
from frequency_coverage import sample_camera_rgb
from green_phase_spectrum import tapered_spectrum
from innovation_frequency_selection import (
    fundamental_distances,
    measurement_fields,
    pooled_score,
    select_pooled,
)
from innovation_selection_reference import qr_spectrum, reference_score, reference_selection


@pytest.mark.parametrize("shape", [(9, 11), (16, 24), (32, 32)])
def test_qr_and_full_noise_operator(shape):
    rng = np.random.default_rng(19601)
    image = rng.normal(size=shape)
    variance = rng.uniform(0.01, 0.2, size=shape)
    actual = tapered_spectrum(image, variance)
    spectrum, noise = qr_spectrum(image, variance)
    np.testing.assert_allclose(spectrum, actual["spectrum"], rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(noise, actual["noise_variance"], rtol=2e-12, atol=1e-14)
    # Direct rows of F W (I - B(B'W²B)^-1 B'W²), including fitted-plane covariance.
    h, w = shape
    yy, xx = np.indices(shape)
    y, x = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    b = np.stack([np.ones(shape), x, y], -1).reshape(-1, 3)
    window = (np.hanning(h)[:, None] * np.hanning(w)[None]).ravel()
    inverse = np.linalg.inv(b.T @ (window[:, None] ** 2 * b))
    for ky, kx in [(0, 0), (1, 2), (h // 2, w // 2), (h - 1, 0)]:
        row = (np.exp(-2j * np.pi * (ky * yy / h + kx * xx / w)) / np.sqrt(h * w)).ravel() * window
        row = row - (row @ b) @ inverse @ (b.T * window**2)
        assert noise[ky, kx] == pytest.approx(np.sum(abs(row) ** 2 * variance.ravel()), abs=1e-14)


@pytest.mark.parametrize("colors", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
def test_camera_sampling_and_residual_cancellation(colors):
    yy, xx = np.indices((64, 64))
    rgb = np.stack([np.cos(2 * np.pi * xx / 8), np.cos(2 * np.pi * yy / 32), np.ones_like(xx)])[
        None
    ].astype(np.float32)
    colors = np.array([colors])
    raw = sample_camera_rgb(rgb, colors)
    views = measurement_fields(raw, rgb, colors)
    np.testing.assert_array_equal(views["innovation"], np.zeros_like(raw))
    variance = np.full_like(raw, 0.001)
    score = pooled_score(views["innovation"], variance, colors)
    assert np.count_nonzero(score) == 0
    # Ties have deterministic C-order ranks in both implementations.
    assert select_pooled(score, 1 / 64)["bins_yx_rank_order"] == reference_selection(score, 1 / 64)


@pytest.mark.parametrize("shape", [(32, 48), (64, 64)])
@pytest.mark.parametrize("lower", [1 / 64, 1 / 16])
def test_independent_pooled_score_and_selection(shape, lower):
    rng = np.random.default_rng(19602)
    field = rng.normal(size=(1, 4, *shape))
    variance = rng.uniform(0.001, 0.005, size=field.shape)
    colors = np.array([[0, 1, 1, 2]])
    actual = pooled_score(field, variance, colors)
    expected = reference_score(field, variance, colors)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-10)
    assert select_pooled(actual, lower)["bins_yx_rank_order"] == reference_selection(
        expected, lower
    )


def test_wide_band_can_find_missing_coarse_tone():
    h = w = 128
    yy, xx = np.indices((2 * h, 2 * w))
    strong = np.cos(2 * np.pi * xx / 8)
    weak = 0.3 * np.cos(2 * np.pi * yy / 32)
    rgb = np.repeat((strong + weak)[None, None], 3, 1)
    parent = np.repeat(strong[None, None], 3, 1)
    colors = np.array([[0, 1, 1, 2]])
    packed = sample_camera_rgb(rgb, colors)
    fields = measurement_fields(packed, parent, colors)
    score = pooled_score(fields["innovation"], np.full_like(packed, 0.01), colors)
    wide = select_pooled(score, 1 / 64)["bins_yx_rank_order"]
    current = select_pooled(score, 1 / 16)["bins_yx_rank_order"]
    assert (
        fundamental_distances((h, w), wide, [np.pi / 2], [32])[0]["minimum_distance_native_bins"]
        < 2
    )
    assert (
        fundamental_distances((h, w), current, [np.pi / 2], [32])[0]["minimum_distance_native_bins"]
        >= 8
    )


def test_affine_field_and_changed_parent_are_not_independent_noise():
    yy, xx = np.indices((32, 48))
    field = np.broadcast_to(3 + 0.2 * xx - 0.1 * yy, (1, 4, 32, 48)).copy()
    variance = np.full_like(field, 0.01)
    colors = np.array([[0, 1, 1, 2]])
    assert pooled_score(field, variance, colors).max() < 1e-22
    with pytest.raises(ValueError):
        measurement_fields(field, np.zeros((1, 3, 32, 48)), colors)


@pytest.mark.parametrize(
    "score,lower,count",
    [
        (np.full((16, 16), np.nan), 1 / 16, 8),
        (np.ones((16, 16)), 0, 8),
        (np.ones((16, 16)), 1 / 16, 0),
    ],
)
def test_invalid_selection(score, lower, count):
    with pytest.raises(ValueError):
        select_pooled(score, lower, count=count)
