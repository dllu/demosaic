import pytest
import torch

from demosaic.cfa import color_indices, mosaic
from demosaic.factored_detail import FactoredLuminanceDetail


@pytest.mark.parametrize("band_limited", [False, True])
def test_zero_start_and_neutral_rgb_correction(band_limited):
    head = FactoredLuminanceDetail(band_limited=band_limited, width=4)
    base = torch.full((1, 3, 64, 64), 0.12)
    colors = color_indices("RGGB")[None]
    raw = mosaic(base, colors)
    raw[:, :, 16, 16] = 1
    variance = torch.full_like(raw, 0.003)
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor([[[1.2, -0.2, 0.0], [-0.1, 1.2, -0.1], [0.0, -0.2, 1.2]]])
    args = (base, raw, variance, colors, wb, matrix)
    torch.testing.assert_close(head(*args), base, rtol=0, atol=0)

    with torch.no_grad():
        head.output.bias[:4] = torch.tensor([0.35, -0.3, 0.15, -0.05])
        difference = head(*args) - base
    assert difference.abs().max() > 5e-5
    torch.testing.assert_close(difference[..., 32:34, 32:34], torch.zeros((1, 3, 2, 2)))
    rendered = torch.einsum("bij,bjhw->bihw", matrix, difference * wb[:, :, None, None])
    torch.testing.assert_close(rendered, rendered[:, :1].expand_as(rendered), atol=3e-8, rtol=0)


def test_post_gate_filter_rejects_constant_and_keeps_weak_mesh_fundamental():
    head = FactoredLuminanceDetail(band_limited=True, width=4)
    constant = torch.full((1, 1, 96, 96), 0.025)
    smooth_axis = torch.arange(96) * (2 * torch.pi / 27.69)
    mesh = smooth_axis.sin().view(1, 1, 1, -1).expand_as(constant) * 0.025
    project = lambda field: head.blur(field, head.short) - head.blur(field, head.long)
    torch.testing.assert_close(project(constant), torch.zeros_like(constant), atol=1e-8, rtol=0)
    interior = (..., slice(12, -12), slice(12, -12))
    gain = (project(mesh)[interior] * mesh[interior]).sum() / mesh[interior].square().sum()
    assert 0.5 < gain < 0.8


def test_gain_floor_keeps_proposal_trainable_when_confidence_saturates():
    head = FactoredLuminanceDetail(band_limited=False, width=4, gain_floor=0.25)
    with torch.no_grad():
        head.output.bias[4:] = -100
    frames = torch.zeros((1, 19, 16, 16))
    scale = torch.ones((1, 1, 32, 32))
    delta = head.correction(frames, scale)
    torch.testing.assert_close(delta, torch.zeros_like(scale), rtol=0, atol=0)
    delta.mean().backward()
    torch.testing.assert_close(head.output.bias.grad[:4], torch.full((4,), 0.25 / 4))
