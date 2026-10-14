import numpy as np
import pytest
import torch
from PIL import Image

from demosaic.cfa import PATTERNS, bilinear, color_indices, mosaic, pack, unpack
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
