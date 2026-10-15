import numpy as np
import pytest
import torch
from PIL import Image

from demosaic.cfa import PATTERNS, bilinear, color_indices, malvar, mosaic, pack, unpack
from demosaic.noise import Sensor, add_noise
from demosaic.prepare import bin_linear, free_license, split_for


@pytest.mark.parametrize("pattern", PATTERNS)
def test_cfa_sampling_roundtrip_and_sample_preservation(pattern):
    rgb = torch.rand(2, 3, 18, 22)
    colors = color_indices(pattern)
    sampled = mosaic(rgb, colors)
    assert torch.equal(pack(unpack(sampled)), sampled)
    reconstructed = bilinear(sampled, colors)
    assert torch.equal(mosaic(reconstructed, colors), sampled)
    for phase, channel in enumerate(colors):
        assert torch.equal(sampled[:, phase], rgb[:, channel, phase // 2 :: 2, phase % 2 :: 2])


@pytest.mark.parametrize("pattern", PATTERNS)
def test_bilinear_reconstructs_constant_camera_colors(pattern):
    rgb = torch.tensor([0.2, 0.4, 0.7])[None, :, None, None].expand(1, 3, 32, 32)
    colors = color_indices(pattern)
    result = bilinear(mosaic(rgb, colors), colors)
    torch.testing.assert_close(result, rgb)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_malvar_sampling_and_constant_colors(pattern):
    colors = color_indices(pattern)
    rgb = torch.rand(2, 3, 32, 48)
    sampled = mosaic(rgb, colors)
    torch.testing.assert_close(mosaic(malvar(sampled, colors), colors), sampled, atol=0, rtol=0)
    rgb = torch.tensor([0.2, 0.5, 0.8])[None, :, None, None].expand(1, 3, 32, 48)
    torch.testing.assert_close(malvar(mosaic(rgb, colors), colors), rgb, atol=1e-6, rtol=0)


def test_interpolation_preserves_fp32_precision_inside_bfloat16_autocast():
    packed = torch.rand(1, 4, 32, 48)
    colors = color_indices("RGGB")
    reference = bilinear(packed, colors)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = bilinear(packed, colors)
        legacy = bilinear(packed, colors, fp32=False)
    torch.testing.assert_close(actual, reference, atol=0, rtol=0)
    assert (legacy - reference).abs().max() > 1e-4


def test_binning_is_linear_and_preserves_sub_8bit_values():
    source = np.zeros((8, 16, 3), dtype=np.uint8)
    source[:, :4] = 255
    source[0, 8] = 255
    result = bin_linear(Image.fromarray(source), 8)
    assert abs(int(result[0, 0, 0]) - 32768) <= 1
    assert abs(int(result[0, 1, 0]) - 1024) <= 1
    assert result.dtype == np.uint16
    assert int(result[0, 1, 0]) % 257 != 0


def test_physical_noise_mean_and_variance():
    sensor = Sensor(full_well_e=10000, read_noise_e=3, iso=800)
    shot, read = sensor.coefficients()
    signal = torch.full((400000,), 0.3)
    noisy = add_noise(signal, shot, read, generator=torch.Generator().manual_seed(21))
    assert abs(float(noisy.mean()) - 0.3) < 0.00015
    assert abs(float(noisy.var()) / (shot * 0.3 + read) - 1) < 0.015


def test_clipping_and_zero_noise():
    clean = torch.tensor([-0.1, 0.2, 1.5])
    noisy = add_noise(clean, 0, 0)
    torch.testing.assert_close(noisy, clean.clamp(0, 1), atol=1 / 65535, rtol=0)


def test_adc_black_offset_preserves_negative_read_noise_and_saturates_white():
    dark = add_noise(
        torch.zeros(100000), 0, 1e-6, black_level=0.03, generator=torch.Generator().manual_seed(3)
    )
    assert (dark < 0).float().mean() > 0.48
    assert abs(float(dark.mean())) < 1e-5
    white = add_noise(torch.full((100,), 2.0), 0, 0, black_level=0.03)
    torch.testing.assert_close(white, torch.ones_like(white))


def test_manifest_license_and_splits():
    assert free_license("CC BY-SA 4.0")
    assert free_license("CC BY 2.0 de")
    assert not free_license("CC BY-NC 4.0")
    assert not free_license("CC BY-ND 4.0")
    assert not free_license(None)
    assert split_for("duplicate-image-sha") == split_for("duplicate-image-sha")


def test_reject_invalid_cfa_and_odd_packing():
    with pytest.raises(ValueError):
        color_indices("XTRANS")
    with pytest.raises(ValueError):
        pack(torch.zeros(1, 1, 3, 4))
