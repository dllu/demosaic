import importlib.util
from pathlib import Path

import pytest
import torch
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, color_indices, mosaic

spec = importlib.util.spec_from_file_location(
    "probe_cfa_mean_consistency",
    Path(__file__).resolve().parents[1] / "scripts/probe_cfa_mean_consistency.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
box_sum = module.box_sum
cfa_mean_consistency = module.cfa_mean_consistency


def test_box_sum_matches_independent_float64_convolution_and_16bit_ramp():
    generator = torch.Generator().manual_seed(3)
    values = torch.rand(2, 3, 10, 14, generator=generator, dtype=torch.float64)
    values[..., ::2, ::2] += 1 / 65535
    for window in [3, 9, 63]:
        oracle = F.conv2d(
            values,
            torch.ones(3, 1, window, window, dtype=torch.float64),
            padding=window // 2,
            groups=3,
        )
        torch.testing.assert_close(box_sum(values, window), oracle, rtol=0, atol=1e-12)


def test_all_cfas_recover_constant_color_bias_without_checkerboards_or_edge_loss():
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    target = torch.tensor([0.2, 0.4, 0.6])[None, :, None, None].expand(4, -1, 12, 16)
    packed = mosaic(target, colors)
    prediction = target + torch.tensor([0.03, -0.02, 0.01])[None, :, None, None]
    actual = cfa_mean_consistency(prediction, packed, torch.zeros_like(packed), colors)
    torch.testing.assert_close(actual, target, rtol=0, atol=6e-8)
    torch.testing.assert_close(
        cfa_mean_consistency(target, packed, torch.zeros_like(packed), colors),
        target,
        rtol=0,
        atol=0,
    )


def test_threshold_uses_actual_color_counts_and_does_not_replicate_border_samples():
    colors = color_indices("RGGB")
    target = torch.full((1, 3, 8, 10), 0.4)
    packed = mosaic(target, colors)
    variance = torch.full_like(packed, 0.0001)
    prediction = target + 0.03
    # Window encompasses all samples:20 red/blue and40 green, even at borders.
    result = cfa_mean_consistency(prediction, packed, variance, colors, window=63)
    expected = (
        target + torch.tensor([0.03 / 20**0.5, 0.03 / 40**0.5, 0.03 / 20**0.5])[None, :, None, None]
    )
    torch.testing.assert_close(result, expected, rtol=0, atol=6e-8)
    below = target + 0.0001
    torch.testing.assert_close(
        cfa_mean_consistency(below, packed, variance, colors),
        below,
        rtol=0,
        atol=0,
    )


def test_clipped_empty_and_hdr_regions_stay_finite_and_unmodified():
    colors = color_indices("RGGB")
    prediction = torch.tensor([-0.2, 0.0, 1.0, 1.2])[None, None, None].expand(1, 3, 8, 4)
    packed = mosaic(prediction.clamp(0, 1), colors)
    result = cfa_mean_consistency(prediction, packed, torch.ones_like(packed) * 0.01, colors)
    torch.testing.assert_close(result, prediction, rtol=0, atol=0)
    assert torch.isfinite(result).all()


def test_native_16bit_signal_and_autocast_match_float32():
    colors = color_indices("GBRG")
    target = torch.full((1, 3, 16, 18), 0.35)
    wave = torch.sin(torch.arange(18).float() / 4)[None, None, None] / 65535
    target = target + wave
    packed = mosaic(target, colors)
    prediction = target + 2 / 65535
    reference = cfa_mean_consistency(prediction, packed, torch.zeros_like(packed), colors)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = cfa_mean_consistency(prediction, packed, torch.zeros_like(packed), colors)
    torch.testing.assert_close(actual, reference, rtol=0, atol=0)
    torch.testing.assert_close(actual, target, rtol=0, atol=6e-8)
    assert actual.unique().numel() > 5


@pytest.mark.parametrize("window", [0, 2, 4, 3.5])
def test_invalid_window_rejected(window):
    with pytest.raises(ValueError, match="odd integer"):
        box_sum(torch.ones(1, 1, 4, 4), window)


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError, match="threshold"):
        cfa_mean_consistency(None, torch.ones(1, 4, 3, 3), None, None, threshold=float("nan"))
