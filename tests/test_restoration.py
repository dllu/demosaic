import json

import numpy as np
import pytest
import tifffile
import torch

from demosaic.cfa import bilinear, color_indices, mosaic, unpack
from demosaic.data import degrade
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.io import write_rgb16
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
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
