"""Known signal math and independent implementation parity for the fixed screen."""

import numpy as np
import pytest
from mature_precision_review_tools import (
    carrier_metrics,
    comparison_gates,
    display_metrics,
    flat_metrics,
    input_fingerprint,
    physical_difference,
)


def test_carrier_known_DC_signed_gain_and_quadrature():
    x = np.arange(256)[None, None, None]
    target = np.broadcast_to(0.18 + 0.0036 * np.cos(x * np.pi / 4), (2, 3, 256, 256)).copy()
    prediction = np.broadcast_to(
        0.181 + 0.0036 * (0.7 * np.cos(x * np.pi / 4) + 0.2 * np.sin(x * np.pi / 4)), target.shape
    ).copy()
    values = carrier_metrics(prediction, target, 8)
    np.testing.assert_allclose(values["in_phase_gain"], 0.7, atol=1e-12)
    np.testing.assert_allclose(values["quadrature_gain"], 0.2, atol=1e-12)
    np.testing.assert_allclose(values["dc_bias_abs"], 0.001, atol=1e-12)
    np.testing.assert_allclose(values["noncarrier_rms"], 0, atol=1e-12)


def test_flat_offset_is_not_false_spatial_structure():
    target = np.full((2, 3, 256, 256), 0.18)
    values = flat_metrics(target + 0.001, target)
    np.testing.assert_allclose(values["dc_bias_abs_rgb"], 0.001, atol=1e-12)
    np.testing.assert_allclose(values["linear_srgb_rmse"], 0.001, atol=1e-12)
    for key in ["spatial_luma_rms", "relative_band_rms", "relative_peak_band_contrast"]:
        np.testing.assert_allclose(values[key], 0, atol=1e-12)


def test_image_identity_and_physical_single_code_error():
    image = np.full((1, 3, 32, 40), 0.18)
    identity = display_metrics(image, image, np.ones((1, 3)), np.eye(3)[None])
    assert identity["srgb_psnr"][0] == 120
    np.testing.assert_allclose(identity["srgb_ssim"], 1, atol=1e-12)
    error = physical_difference(image + 1 / 65535, image)
    assert error["RGB_values"] == image.size
    assert abs(error["max_abs_DN16"] - 1) < 1e-10 and abs(error["RMS_DN16"] - 1) < 1e-10


def test_missing_pixels_and_nonfinite_values_are_rejected():
    value = np.zeros((1, 3, 16, 16))
    with pytest.raises(ValueError, match="ROI"):
        flat_metrics(value, value)
    with pytest.raises(ValueError, match="finite"):
        physical_difference(np.full_like(value, np.nan), value)


@pytest.mark.parametrize(
    "kind,baseline,current,key",
    [
        (
            "photo",
            {"srgb_psnr": 30.0, "srgb_ssim": 0.9},
            {"srgb_psnr": 29.949, "srgb_ssim": 0.9},
            "PSNR_loss_at_most_0.05dB",
        ),
        (
            "photo",
            {"srgb_psnr": 30.0, "srgb_ssim": 0.9},
            {"srgb_psnr": 30.0, "srgb_ssim": 0.899899},
            "SSIM_loss_at_most_0.0001",
        ),
        (
            "adc-carrier",
            {"in_phase_gain": 0.8},
            {"in_phase_gain": 0.749},
            "signed_gain_loss_at_most_0.05",
        ),
        (
            "weak-noisy-carrier",
            {"in_phase_gain": 0.8},
            {"in_phase_gain": 0.749},
            "signed_gain_loss_at_most_0.05",
        ),
        (
            "flat",
            {"spatial_luma_rms": 0.01},
            {"spatial_luma_rms": 0.01251},
            "flat_luma_RMS_at_most_1.25x",
        ),
        (
            "flat",
            {"spatial_luma_rms": 0.0},
            {"spatial_luma_rms": 1e-12},
            "flat_luma_RMS_at_most_1.25x",
        ),
    ],
)
def test_individual_regressions_fail_even_with_small_absolute_errors(kind, baseline, current, key):
    assert comparison_gates(kind, baseline, current)[key] is False
    assert all(comparison_gates(kind, baseline, baseline).values())


def test_input_trace_uses_five_physical_arguments_and_original_torch_headers():
    import torch

    from demosaic.train import batch_fingerprint

    values = {
        name: np.arange(24, dtype=np.float32).reshape(1, 4, 2, 3).swapaxes(-1, -2)
        for name in ["packed", "variance", "wb", "matrix"]
    }
    values["colors"] = np.arange(4, dtype=np.int64)[None]
    expected = batch_fingerprint({k: torch.from_numpy(v) for k, v in values.items()})
    assert input_fingerprint(values) == expected
    values["target"] = np.zeros((1, 3, 4, 6))
    assert input_fingerprint(values) == expected
    values["packed"] = values["packed"] + 1
    assert input_fingerprint(values) != expected
