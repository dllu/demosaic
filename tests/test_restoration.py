import json

import numpy as np
import pytest
import tifffile
import torch

from demosaic.cfa import bilinear, color_indices, mosaic, unpack
from demosaic.color import render
from demosaic.data import camera_pair, degrade
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.io import camera_matrix, write_rgb16
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context
from demosaic.reference import RawNind, publisher_input_scale
from demosaic.safety import writable_path


@pytest.fixture
def small_model():
    torch.set_num_threads(2)
    return JointDemosaic(
        ModelConfig(width=8, encoder_blocks=(1, 1), middle_blocks=2, decoder_blocks=(1, 1))
    )


def test_model_gradient_and_initial_baseline(small_model):
    batch = degrade(torch.rand(2, 3, 32, 48))
    result, auxiliary = small_model(
        batch["packed"], batch["variance"], batch["colors"], auxiliary=True
    )
    torch.testing.assert_close(result, bilinear(batch["packed"], batch["colors"]))
    loss, _ = reconstruction_loss(result, batch, auxiliary)
    loss.backward()
    assert torch.isfinite(loss)
    assert small_model.head.weight.grad.abs().sum() > 0


def test_tiled_phase_borders_precision_and_odd_dimensions(small_model):
    color = torch.tensor([0.2, 0.3, 0.6])[None, :, None, None].expand(1, 3, 82, 110)
    colors = color_indices("GBRG")
    raw = unpack(mosaic(color, colors))[0, 0, :81, :109]
    rgb, timing = restore_tiled(
        small_model, raw, colors, shot=0, read=0, tile=32, overlap=16, batch_size=3, device="cpu"
    )
    assert rgb.shape == (3, 81, 109)
    torch.testing.assert_close(rgb, color[0, :, :81, :109], atol=1e-6, rtol=1e-6)
    assert timing["tiles"] > 1


def test_tiff_is_true_16bit(tmp_path):
    rgb = np.linspace(0, 1, 32 * 32 * 3, dtype=np.float32).reshape(32, 32, 3)
    output = tmp_path / "precision.tiff"
    write_rgb16(output, rgb, color_space="sRGB")
    with tifffile.TiffFile(output) as tif:
        result = tif.asarray()
        assert tif.pages[0].bitspersample == 16
        assert json.loads(tif.pages[0].description)["color_space"] == "sRGB"
        assert 34675 in tif.pages[0].tags
    assert result.dtype == np.uint16
    assert np.unique(result).size > 256
    assert np.max(np.abs(result.astype(np.float32) / 65535 - rgb)) <= 0.5 / 65535 + 1e-7


def test_checkpoint_load_matches_model(small_model, tmp_path):
    output = tmp_path / "checkpoint.pt"
    torch.save(
        {
            "model_config": small_model.config.to_dict(),
            "model": small_model.restoration_state_dict(),
        },
        output,
    )
    loaded, _ = load_checkpoint(output)
    for expected, actual in zip(small_model.parameters(), loaded.parameters()):
        assert torch.equal(expected, actual)


def test_forbidden_output_locations():
    for path in (
        "/home/dllu/pictures/cooked/test.tiff",
        "/tmp/demosaic-test",
        "/mnt/external/qi/new-file",
    ):
        with pytest.raises(ValueError):
            writable_path(path)


def test_libraw_camera_matrix_direction_and_neutral_response():
    rgb_to_xyz = np.array(
        [
            [0.412453, 0.357580, 0.180423],
            [0.212671, 0.715160, 0.072169],
            [0.019334, 0.119193, 0.950227],
        ]
    )
    # A camera whose primaries are sRGB must yield an identity transform.
    np.testing.assert_allclose(camera_matrix(np.linalg.inv(rgb_to_xyz)), np.eye(3), atol=1e-12)
    gfx = np.array(
        [[1.6212, -0.8423, -0.1583], [-0.4336, 1.2583, 0.1937], [-0.0195, 0.0726, 0.6199]]
    )
    matrix = camera_matrix(gfx)
    np.testing.assert_allclose(matrix @ np.ones(3), np.ones(3), atol=1e-12)
    assert np.max(np.abs(matrix)) < 3


def test_overexposed_neutral_reference_has_no_channel_clipping_fringe():
    ramp = torch.linspace(0, 3, 128)[None, None, None, :].expand(1, 3, 4, -1)
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    inverse = torch.tensor([[[0.9, 0.05, 0.05], [0.05, 0.9, 0.05], [0.05, 0.05, 0.9]]])
    matrix = torch.linalg.inv(inverse)
    sensor, target = camera_pair(ramp, inverse, wb, reconstruct_highlights=True)
    assert sensor.amax() > 1
    rendered = render(target, wb, matrix)
    torch.testing.assert_close(rendered[:, 0], rendered[:, 1])
    torch.testing.assert_close(rendered[:, 1], rendered[:, 2])
    bad_reference = render(sensor.clamp(0, 1), wb, matrix)
    assert (bad_reference[:, 0] - bad_reference[:, 1]).abs().max() > 0.01
    model = JointDemosaic(
        ModelConfig(
            width=4,
            encoder_blocks=(1,),
            middle_blocks=0,
            decoder_blocks=(1,),
            attention=False,
            camera_conditioning=True,
        )
    )
    batch = degrade(torch.rand(1, 3, 32, 32), reconstruct_highlights=True)
    output = model(
        batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
    )
    assert output.shape == (1, 3, 32, 32)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_reference_adapter_preserves_sensor_geometry(pattern):
    class CanonicalDemosaic(torch.nn.Module):
        def forward(self, packed):
            return bilinear(packed, color_indices("RGGB"))

    rgb = torch.rand(1, 3, 32, 48)
    colors = color_indices(pattern)
    sampled = mosaic(rgb, colors)
    adapter = RawNind(CanonicalDemosaic(), gain_mode="cfa-ls")
    output = adapter(sampled, torch.zeros_like(sampled), colors)
    torch.testing.assert_close(mosaic(output, colors), sampled)


def test_deep_noise_modulation_preserves_warm_start_and_receives_gradients(small_model):
    torch.nn.init.normal_(small_model.head.weight, std=0.01)
    config = small_model.config.to_dict()
    config["noise_modulation"] = True
    modulated = JointDemosaic(ModelConfig(**config))
    missing, unexpected = modulated.load_state_dict(small_model.state_dict(), strict=False)
    assert not unexpected and all(k.startswith("noise_") for k in missing)
    batch = degrade(torch.rand(2, 3, 32, 48))
    inputs = (batch["packed"], batch["variance"], batch["colors"])
    prediction = modulated(*inputs)
    torch.testing.assert_close(prediction, small_model(*inputs), atol=0, rtol=0)
    loss, _ = reconstruction_loss(prediction, batch)
    loss.backward()
    assert modulated.noise_encoder[0].affine[-1].weight.grad.abs().sum() > 0


def test_reference_per_channel_gain_removes_photometric_bias_without_target_access():
    class BiasedDemosaic(torch.nn.Module):
        def forward(self, packed):
            rgb = bilinear(packed, color_indices("RGGB"))
            return rgb * rgb.new_tensor([2.0, 0.6, 1.3])[None, :, None, None]

    rgb = torch.rand(1, 3, 32, 48)
    colors = color_indices("GRBG")
    sampled = mosaic(rgb, colors)
    model = RawNind(BiasedDemosaic(), gain_mode="cfa-channel")
    output = model(sampled, torch.zeros_like(sampled), colors)
    torch.testing.assert_close(mosaic(output, colors), sampled, atol=2e-7, rtol=1e-6)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_reference_preserves_signed_input_and_matches_original_sensor_units(pattern):
    class Observe(torch.nn.Module):
        def forward(self, packed):
            assert packed.min() < 0 and packed.max() > 1
            return bilinear(packed, color_indices("RGGB"))

    rgb = torch.linspace(-0.03, 1.3, 3 * 32 * 32).reshape(1, 3, 32, 32)
    colors = color_indices(pattern)
    packed = mosaic(rgb, colors)
    scale = [0.94 if c != 1 else 0.93 for c in colors]
    model = RawNind(Observe(), gain_mode="cfa-channel", input_scale=scale)
    actual = model(packed, torch.zeros_like(packed), colors)
    torch.testing.assert_close(mosaic(actual, colors), packed, atol=3e-7, rtol=1e-6)


def test_reference_normalization_converts_camera_white_to_publisher_adc_units():
    white = [15360.0, 15360.0, 15360.0, 15360.0]
    black = [512.0, 511.0, 513.0, 512.0]
    scale = publisher_input_scale(white, black, 16383.0)
    raw = np.array([-0.01, 0.1, 0.5, 1.03])
    counts = raw * (np.array(white) - black) + black
    expected = (counts - black) / (16383 - np.array(black))
    np.testing.assert_allclose(raw * scale, expected, rtol=0, atol=1e-16)


def test_color_transforms_preserve_precision_inside_autocast():
    rgb = torch.rand(2, 3, 32, 48)
    wb = torch.tensor([[2.0, 1.0, 1.5]]).expand(2, -1)
    matrix = torch.tensor([[[1.1, -0.05, -0.05], [-0.05, 1.1, -0.05], [-0.05, -0.05, 1.1]]]).expand(
        2, -1, -1
    )
    expected = render(rgb, wb, matrix)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = render(rgb, wb, matrix)
        legacy = render(rgb, wb, matrix, fp32=False)
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)
    assert (legacy - expected).abs().max() > 1e-4


def test_explicit_fp32_restores_outer_autocast_after_an_exception():
    # A requested FP32 reference must remain FP32 in an enclosing AMP scope.
    values = torch.linspace(0.1, 0.9, 64).reshape(8, 8)
    expected = values @ values
    with torch.autocast("cpu", dtype=torch.bfloat16):
        with pytest.raises(RuntimeError, match="diagnostic"), amp_context("cpu", dtype="float32"):
            actual = values @ values
            assert actual.dtype == torch.float32
            torch.testing.assert_close(actual, expected, atol=0, rtol=0)
            raise RuntimeError("diagnostic")
        assert (values @ values).dtype == torch.bfloat16


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA numerical precision check")
@pytest.mark.parametrize("precision", ["float16", "bfloat16"])
def test_half_compute_preserves_fine_16bit_baseline(small_model, precision):
    # Four-DN contrasts must survive half-precision neural compute and blending.
    axis = torch.arange(64, dtype=torch.float32)
    raw = 0.5 + (axis[:, None] + axis[None, :]).sin() * (4 / 65535)
    colors = color_indices("GRBG")
    expected = bilinear(torch.nn.functional.pixel_unshuffle(raw[None, None], 2), colors)[0]
    actual, timing = restore_tiled(
        small_model.cuda(),
        raw,
        colors,
        shot=0,
        read=0,
        tile=64,
        overlap=0,
        device="cuda",
        precision=precision,
    )
    torch.testing.assert_close(actual, expected, atol=2e-7, rtol=0)
    assert timing["compute_precision"] == precision
