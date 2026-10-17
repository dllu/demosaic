from types import SimpleNamespace

import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices, unpack
from demosaic.inference import restore_tiled
from demosaic.model import JointDemosaic, ModelConfig


@pytest.mark.parametrize("shape", [(70, 74), (69, 73)])
@pytest.mark.parametrize("overlap", [16, 18])
def test_actual_packed_trunk_preserves_its_quarter_lattice_at_final_tiles(shape, overlap):
    torch.set_num_threads(2)
    net = JointDemosaic(
        ModelConfig(
            restoration_backbone="packed-isotropic",
            camera_conditioning=True,
            width=4,
            isotropic_groups=1,
            isotropic_blocks=1,
            isotropic_local_width=4,
        )
    ).eval()
    # Make the actual pixel-shuffle paths emit a known native4-period residual.
    # It has no spatial filtering, so differences cannot be blamed on halos.
    with torch.no_grad():
        for parameter in net.parameters():
            parameter.zero_()
        net.packed_isotropic.up[0].bias[:4].copy_(torch.arange(4) * 0.001)
        net.packed_isotropic.head.weight[:, 0, 1, 1] = 1
    colors = color_indices("GBRG")
    color = torch.tensor([0.2, 0.3, 0.6])
    y, x = torch.meshgrid(torch.arange(shape[0]), torch.arange(shape[1]), indexing="ij")
    raw = color[colors.reshape(2, 2)[y % 2, x % 2]].numpy()
    actual, stats = restore_tiled(
        net,
        raw,
        colors,
        shot=0,
        read=0,
        tile=64,
        overlap=overlap,
        batch_size=3,
        device="cpu",
    )
    expected = color[:, None, None] + ((y // 2 % 2) * 2 + x // 2 % 2) * 0.001
    torch.testing.assert_close(actual, expected, rtol=0, atol=2e-7)
    assert actual.shape == (3, *shape)
    assert stats["tile_grid_alignment"] == 4
    assert stats["tile_stride"] % 4 == 0 and 64 - stats["tile_stride"] >= overlap


class LatticeModel(torch.nn.Module):
    def __init__(self, period, *, packed, dino):
        super().__init__()
        self.period = period
        self.config = SimpleNamespace(
            restoration_backbone="packed-isotropic" if packed else "local", dino=dino
        )

    def forward(self, packed, *_args):
        values = unpack(packed)
        height, width = values.shape[-2:]
        y, x = torch.meshgrid(torch.arange(height), torch.arange(width), indexing="ij")
        residual = ((y % self.period) + (x % self.period)) * 0.0001
        return (values + residual).expand(-1, 3, -1, -1)


@pytest.mark.parametrize("overlap", [16, 18])
def test_packed_dino_context_keeps_the_32_pixel_grid(overlap):
    model = LatticeModel(32, packed=True, dino=True)
    raw = np.linspace(0.1, 0.2, 69 * 73, dtype=np.float32).reshape(69, 73)
    actual, stats = restore_tiled(
        model,
        raw,
        color_indices("RGGB"),
        shot=0,
        read=0,
        tile=64,
        overlap=overlap,
        batch_size=3,
        device="cpu",
    )
    y, x = torch.meshgrid(torch.arange(69), torch.arange(73), indexing="ij")
    expected = (torch.from_numpy(raw) + ((y % 32) + (x % 32)) * 0.0001).expand(3, -1, -1)
    torch.testing.assert_close(actual, expected, rtol=0, atol=2e-7)
    assert stats["tile_grid_alignment"] == stats["tile_stride"] == 32


def test_legacy_model_keeps_the_existing_bayer_grid_and_stride():
    model = LatticeModel(2, packed=False, dino=False)
    raw = np.full((69, 73), 0.2, dtype=np.float32)
    actual, stats = restore_tiled(
        model,
        raw,
        color_indices("RGGB"),
        shot=0,
        read=0,
        tile=64,
        overlap=18,
        batch_size=3,
        device="cpu",
    )
    y, x = torch.meshgrid(torch.arange(69), torch.arange(73), indexing="ij")
    expected = (0.2 + ((y % 2) + (x % 2)) * 0.0001).expand(3, -1, -1)
    torch.testing.assert_close(actual, expected, rtol=0, atol=2e-7)
    assert stats["tile_grid_alignment"] == 2 and stats["tile_stride"] == 46


@pytest.mark.parametrize("tile,overlap", [(48, 16), (64, 62)])
def test_invalid_packed_dino_grid_reports_geometry_error(tile, overlap):
    with pytest.raises(ValueError, match="32"):
        restore_tiled(
            LatticeModel(32, packed=True, dino=True),
            np.ones((70, 74)),
            color_indices("RGGB"),
            shot=0,
            read=0,
            tile=tile,
            overlap=overlap,
            device="cpu",
        )
