import importlib.util
from pathlib import Path

import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic

spec = importlib.util.spec_from_file_location(
    "probe_adc_cfa_projection",
    Path(__file__).resolve().parents[1] / "scripts/probe_adc_cfa_projection.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
project = module.adc_cfa_projection


def fixture():
    generator = torch.Generator().manual_seed(23)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    rgb = torch.rand(4, 3, 16, 20, generator=generator) * 0.5 + 0.1
    packed = torch.rand(4, 4, 8, 10, generator=generator) * 0.8 + 0.05
    wb = torch.tensor([[2, 1, 1.5], [1.3, 1, 2.1], [1.7, 1, 1.1], [2.2, 1, 1.4]])
    return rgb, packed, colors, wb


def test_all_cfas_reproduce_nonclipped_observations():
    rgb, packed, colors, wb = fixture()
    corrected = project(rgb, packed, colors, wb)
    assert corrected.dtype == torch.float32 and torch.isfinite(corrected).all()
    torch.testing.assert_close(mosaic(corrected, colors), packed, rtol=0, atol=1e-7)


def test_clipped_and_near_black_measured_sites_keep_the_prediction():
    rgb, packed, colors, wb = fixture()
    packed[..., 0, :3] = packed.new_tensor([0, 1, 0.5 / 65535])
    sampled = mosaic(rgb, colors)
    valid = (packed > 1 / 65535) & (packed < 1 - 1 / 65535)
    actual = mosaic(project(rgb, packed, colors, wb), colors)
    torch.testing.assert_close(actual[valid], packed[valid], rtol=0, atol=1e-7)
    torch.testing.assert_close(actual[~valid], sampled[~valid], rtol=0, atol=0)


def test_zero_residual_is_exact_identity_and_does_not_clamp_hdr():
    rgb, _, colors, wb = fixture()
    rgb = rgb * 4 - 0.7
    assert rgb.min() < 0 and rgb.max() > 1
    actual = project(rgb, mosaic(rgb, colors), colors, wb)
    torch.testing.assert_close(actual, rgb, rtol=0, atol=0)


def test_autocast_keeps_native_code_variation_in_float32():
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    plane = 0.2 + torch.arange(32 * 40).reshape(32, 40) / 65535
    target = plane[None, None].expand(4, 3, -1, -1)
    packed = mosaic(target, colors)
    prediction = target + torch.tensor([0.01, -0.02, 0.03])[None, :, None, None]
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = project(prediction, packed, colors, torch.ones(4, 3))
    assert actual.dtype == torch.float32
    torch.testing.assert_close(mosaic(actual, colors), packed, rtol=0, atol=1e-7)
    assert (actual * 65535).round().unique().numel() > 256


@pytest.mark.parametrize("bad_cfa", [True, False])
def test_invalid_dimensions_rejected(bad_cfa):
    rgb, packed, colors, wb = fixture()
    with pytest.raises(ValueError):
        project(rgb, packed[:, :3] if bad_cfa else packed[..., :-1], colors, wb)
