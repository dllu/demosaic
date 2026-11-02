import numpy as np
from report_pilot_flat_safety import sky_metrics, spatial_metrics


def test_uniform_color_error_stays_in_dc_and_coarse_error_stays_spatial():
    bias = np.array([0.001, -0.002, 0.004])[None, :, None, None]
    # Five 32-pixel blocks with exactly zero spatial mean.
    stripe = np.repeat(np.array([-2, -1, 0, 1, 2], dtype=float), 32) * 1e-4
    error = np.broadcast_to(bias + stripe[None, None, None, :], (1, 3, 160, 160))
    measured = spatial_metrics(error)
    np.testing.assert_allclose(measured["DC_RGB"], bias.ravel(), atol=1e-17)
    np.testing.assert_allclose(measured["DC_MSE"], np.mean(bias**2), rtol=1e-13)
    np.testing.assert_allclose(measured["spatial_MSE"], 2e-8, rtol=1e-13)
    # A broad splotch must survive every tested block size, including32.
    np.testing.assert_allclose(list(measured["block_RMS"].values()), np.sqrt(2e-8), rtol=1e-13)


def test_alternating_error_has_no_coarse_component_and_sky_plane_is_removed():
    stripe = np.tile([-0.001, 0.001], 80)
    error = np.broadcast_to(stripe[None, None, None, :], (1, 3, 160, 160))
    measured = spatial_metrics(error)
    np.testing.assert_allclose(measured["block_RMS"]["1"], 0.001, rtol=1e-13)
    assert all(measured["block_RMS"][str(s)] == 0 for s in (4, 16, 32))
    y, x = np.mgrid[-1:1:160j, -1:1:160j]
    plane = np.stack([0.02 + 0.01 * x, 0.1 + 0.003 * y, 0.07 + 0.002 * x - 0.004 * y])[None]
    detrended = sky_metrics(plane)["detrended_variation"]
    assert detrended["MSE"] < 1e-26
    np.testing.assert_allclose(spatial_metrics(plane)["DC_RGB"], [0.02, 0.1, 0.07], atol=1e-15)
