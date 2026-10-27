import numpy as np
from analyze_retained_faint_detail import enhanced_pixels, error_components, original_source_strata


def arrays():
    return {"wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}


def test_constant_channel_offsets_are_mean_error_and_checkerboard_is_spatial():
    target = np.full((1, 3, 4, 6), 0.2)
    offset = np.array([0.01, -0.02, 0.03])[None, :, None, None]
    result = error_components(target + offset, target)
    np.testing.assert_allclose(result["MSE"], np.mean(offset**2), rtol=1e-14)
    assert result["spatial_MSE"] < 1e-32
    np.testing.assert_allclose(result["DC_fraction"], 1, rtol=1e-14)
    checker = np.tile(np.array([[1, -1], [-1, 1]]), (2, 3)) * 0.01
    result = error_components(target + checker, target)
    np.testing.assert_allclose(result["MSE"], 1e-4, rtol=1e-14)
    assert result["DC_MSE"] == 0 and result["DC_fraction"] == 0


def test_original_masks_separate_reference_detail_from_faint_transform_and_gain():
    x = np.arange(256) + 0.5
    texture = np.cos(np.pi * x * 6 / 16)[None, None, None] * 0.004
    original = np.broadcast_to(0.2 + texture, (1, 3, 256, 256)).copy()
    target = 0.2 + 0.025 * (original - 0.2)
    prediction = 0.2 + 0.75 * (target - 0.2)
    rows = original_source_strata(original, prediction, target, arrays())
    assert len(rows) == 1 and rows[0]["original_bin"] == 0 and rows[0]["blocks"] == 100
    np.testing.assert_allclose(rows[0]["gain"], 0.75, atol=1e-12)
    np.testing.assert_allclose(rows[0]["relative_band_error"], 0.25, atol=1e-12)
    second = original_source_strata(original, target, target, arrays())
    assert second[0]["mask_sha256"] == rows[0]["mask_sha256"]
    np.testing.assert_allclose(second[0]["gain"], 1, atol=1e-15)
    assert second[0]["relative_band_error"] == 0


def test_spatial_constants_have_no_eligible_fine_band():
    source = np.full((1, 3, 256, 256), 0.2)
    assert original_source_strata(source, source + 0.001, source, arrays()) == []


def test_shared40x_display_restores_faint_target_contrast_without_resizing():
    x = np.arange(256) + 0.5
    texture = np.cos(np.pi * x * 6 / 16)[None, None, None] * 0.004
    original = np.broadcast_to(0.2 + texture, (1, 3, 256, 256)).copy()
    dc = original.mean((-1, -2), keepdims=True)
    faint = dc + 0.025 * (original - dc)
    actual = enhanced_pixels(faint, original, arrays())
    expected = enhanced_pixels(original, original, arrays(), factor=1)
    assert actual.shape == (160, 160, 3) and actual.dtype == np.uint8
    np.testing.assert_array_equal(actual, expected)
