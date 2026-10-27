import numpy as np
import pytest
from analyze_shadow_target_coverage import blocks, cell_indices, green_sensor_blocks


def test_block_layout_preserves_exact_native_pixel_coordinates():
    value = np.arange(256 * 256).reshape(1, 256, 256)
    tiled = blocks(value)
    assert tiled.shape == (1, 100, 16, 16)
    assert np.array_equal(tiled[0, 0], value[0, 48:64, 48:64])
    assert np.array_equal(tiled[0, 11], value[0, 64:80, 64:80])
    assert np.array_equal(tiled[0, 99], value[0, 192:208, 192:208])


def test_measured_green_phase_noise_matches_closed_form():
    target = np.full((1, 3, 256, 256), 0.004)
    values = green_sensor_blocks(target, [[0, 1, 1, 2]], [0.00128], [6.5536e-6])
    np.testing.assert_allclose(values["green_mean"], 0.004)
    variance = 0.004 * 0.00128 + 6.5536e-6
    np.testing.assert_allclose(values["pre_ADC_pixel_variance"], variance)
    np.testing.assert_allclose(values["relative_pixel_noise_RMS"], variance**0.5 / 0.004)
    assert values["green_target_valid"].all()


def test_phase_selection_uses_only_measured_green_and_handles_all_cfas():
    target = np.zeros((4, 3, 256, 256))
    for y in range(2):
        for x in range(2):
            target[:, 1, y::2, x::2] = 0.01 * (1 + y * 2 + x)
    layouts = [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]]
    stats = green_sensor_blocks(target, layouts, [0.01] * 4, [0] * 4)
    np.testing.assert_allclose(stats["green_mean"], 0.025)
    np.testing.assert_allclose(stats["pre_ADC_pixel_variance"], 0.00025)
    assert stats["green_target_valid"].all()
    target[0, 1, 49, 48] = 1
    assert not green_sensor_blocks(target, layouts, [0.01] * 4, [0] * 4)["green_target_valid"][0, 0]


def test_adc_only_keeps_zero_noise_instead_of_inventing_variance():
    stats = green_sensor_blocks(np.full((1, 3, 256, 256), 0.01), [[0, 1, 1, 2]], [0], [0])
    assert not stats["relative_pixel_noise_RMS"].any()


def test_condition_cells_are_right_open_with_explicit_boundaries():
    x, y = cell_indices(np.array([2**-10, 2**-8, 2**-6]), np.array([0.125, 0.5, 1]))
    assert x.tolist() == [2, 3, 4]
    assert y.tolist() == [1, 3, 4]


def test_invalid_profile_or_layout_is_rejected():
    target = np.full((1, 3, 256, 256), 0.01)
    with pytest.raises(ValueError, match="nonnegative"):
        green_sensor_blocks(target, [[0, 1, 1, 2]], [-1], [0])
    with pytest.raises(ValueError, match="Bayer"):
        green_sensor_blocks(target, [[0, 0, 1, 2]], [0], [0])
