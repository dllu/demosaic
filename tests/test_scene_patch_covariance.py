import numpy as np
import pytest

from demosaic.scene_patch_covariance import (
    MODES,
    SIZE,
    ExteriorPatches,
    PatchBand,
    build_exterior,
    confirmed_power,
    corrections,
    covariance,
    dense_exterior_grid,
    donor_validated_fields,
    encode,
    filter_innovation,
    patch_basis,
    sample_windows,
    signed_support,
)


def pack(grid, colors):
    return np.stack([grid[c, i // 2 :: 2, i % 2 :: 2] for i, c in enumerate(colors)])


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (1, 0, 2, 1), (1, 2, 0, 1), (2, 1, 1, 0)])
def test_each_actual_green_grid_recovers_native_basis(colors):
    basis = patch_basis(colors)
    count = len(basis.image)
    clean = basis.image + 0.4
    packed = np.stack([pack(np.stack([a, a, a]), colors) for a in clean])
    _, coefficients, _, _ = encode(packed, basis, 0.001, 0.00001)
    np.testing.assert_allclose(coefficients[:, 0], np.eye(count), atol=1e-13)
    np.testing.assert_allclose(coefficients[:, 1], np.eye(count), atol=1e-13)
    np.testing.assert_allclose(basis.image[basis.transpose], basis.image.transpose(0, 2, 1))


def test_exterior_reads_neither_the_query_nor_its_halo():
    colors = (2, 1, 1, 0)
    rng = np.random.default_rng(87)
    raw = rng.uniform(0.1, 0.5, size=(4, 64, 64)).astype(np.float32)
    box = (44, 36, 32, 32)
    atlas = build_exterior(raw, colors, box, 0.001, 0.00001)
    modified = raw.copy()
    modified[:, 10:42, 14:46] = 0.9
    other = build_exterior(modified, colors, box, 0.001, 0.00001)
    assert len(atlas.coords) > 16
    for name in ("coords", "features", "normalized"):
        np.testing.assert_array_equal(getattr(atlas, name), getattr(other, name))


def test_covariance_carries_no_donor_sign_and_zero_preserves_query():
    rng = np.random.default_rng(72)
    observed = rng.normal(size=(2, 12, 2, 5))
    weights = np.full((2, 12), 1 / 12)
    moment = covariance(observed, weights)
    np.testing.assert_array_equal(moment, moment.swapaxes(-1, -2))
    observed[:, ::2] *= -1
    np.testing.assert_array_equal(covariance(observed, weights), moment)
    np.testing.assert_array_equal(filter_innovation(moment, np.zeros((2, 5)), np.zeros(2)), 0)


def test_innovation_has_no_exterior_additive_content():
    colors = (0, 1, 1, 2)
    basis = patch_basis(colors)
    raw = np.full((4, SIZE // 2, SIZE // 2), 0.15)
    feature, _, _, _ = encode(sample_windows(raw, np.array([[0, 0]])), basis, 0.001, 1e-5)
    pattern = np.zeros(len(basis.image))
    pattern[0] = 2
    atlas = ExteriorPatches(
        np.column_stack((np.arange(1, 33) * SIZE, np.zeros(32, dtype=int))),
        np.repeat(feature, 32, axis=0),
        np.broadcast_to(pattern, (32, 2, len(pattern))),
    )
    parent = np.full((SIZE, SIZE), 0.15)
    box = (0, 0, SIZE, SIZE)
    result = corrections(raw, parent, colors, 0.001, 1e-5, box, atlas)
    assert tuple(result) == MODES
    for output in result.values():
        np.testing.assert_array_equal(output, 0)
    raw = pack(np.stack([parent + 0.02 * basis.image[0]] * 3), colors)
    result = corrections(raw, parent, colors, 0.001, 1e-5, box, atlas)
    assert np.vdot(result["matched"], basis.image[0]) > 0.001
    for value in corrections(raw, parent, colors, 0.001, 1e-5, box, None).values():
        np.testing.assert_array_equal(value, 0)


def test_signed_support_uses_the_less_supportive_green():
    observations = np.array([[[3.0, 2.0, -4.0, 9.0], [1.5, -1.0, -3.0, 9.0]]])
    proposal = np.array([[2.0, 1.0, -1.0, 0.0]])
    np.testing.assert_array_equal(signed_support(observations, proposal, 1.0), [[0.5, 0, 1, 0]])


def test_validation_rejects_unsupported_power_and_small_effective_groups():
    products = np.tile([9.0, -9.0, 0.0], (2, 4, 1))
    weights = np.array([[0.25] * 4, [1, 0, 0, 0]])
    power = confirmed_power(products, weights, np.ones(3))
    np.testing.assert_array_equal(power, [[8, 0, 0], [0, 0, 0]])


def test_donor_halves_validate_each_others_modes_and_preserve_the_query_sign():
    basis = patch_basis((0, 1, 1, 2))
    count = len(basis.image)
    coherent = np.zeros((1, 16, 2, count))
    tone = np.zeros((1, count))
    tone[0, 0] = 1
    weights = np.full((1, 16), 1 / 16)
    coherent[:, :, :, 0] = 8
    observation = np.broadcast_to(tone[:, None], (1, 2, count))
    signal = donor_validated_fields(coherent, weights, tone, observation, np.ones(1) * 0.1, basis)
    assert np.vdot(signal["donor_validated"], tone) > 0.8
    assert np.vdot(signal["donor_and_query"], tone) > 0.5
    np.testing.assert_allclose(signal["donor_validated"], signal["validated_diagonal"], atol=1e-15)
    different = coherent.copy()
    different[:, 1::2, :, 0] = 0
    different[:, 1::2, :, 1] = 8
    for result in donor_validated_fields(
        different, weights, tone, observation, np.ones(1), basis
    ).values():
        np.testing.assert_array_equal(result, 0)


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (1, 0, 2, 1), (1, 2, 0, 1), (2, 1, 1, 0)])
def test_wide_band_tracks_long_detail_on_both_greens(colors):
    low = patch_basis(colors, PatchBand(32, 0.022, 0.08))
    mid = patch_basis(colors, PatchBand(32, 0.08, 0.16))
    phase = (np.arange(32) + 0.5) * np.pi / 16
    rgb = np.broadcast_to(0.35 + 0.04 * np.cos(phase), (3, 32, 32))
    raw = pack(rgb, colors)
    view = sample_windows(raw, np.array([[0, 0]]), 32)
    _, long, _, _ = encode(view, low, 0.001, 0.00001)
    _, short, _, _ = encode(view, mid, 0.001, 0.00001)
    np.testing.assert_allclose(long[:, 0], long[:, 1], atol=1e-13)
    assert np.linalg.norm(long) > 0.1
    np.testing.assert_allclose(short, 0, atol=1e-13)


def test_near_and_far_atlas_patches_never_reuse_sites_or_touch_the_query_halo():
    band = PatchBand(32, 0.08, 0.16)
    box = (146, 138, 96, 96)
    height, width = 416, 608
    coords = dense_exterior_grid(height, width, band, box, 16, 66, 72)
    covered = np.zeros((height, width), dtype=np.int8)
    for y, x in coords:
        assert y % 2 == x % 2 == 0
        assert 0 <= y <= height - 32 and 0 <= x <= width - 32
        covered[y : y + 32, x : x + 32] += 1
    x, y, w, h = box
    assert len(coords) > 32 and covered.max() == 1
    assert not covered[y - 16 : y + h + 16, x - 16 : x + w + 16].any()
