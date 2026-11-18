import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.paired_detail import PairedLuminanceDetail


def inputs():
    torch.set_num_threads(1)
    generator = torch.Generator().manual_seed(624)
    parent = 0.15 + 0.025 * torch.rand((4, 3, 48, 64), generator=generator)
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    packed = mosaic(parent, colors)
    variance = torch.full_like(packed, 8e-5)
    wb = torch.tensor([1.5, 1.0, 1.8]).repeat(4, 1)
    matrix = torch.tensor([[1.2, -0.15, -0.05], [-0.1, 1.2, -0.1], [0.04, -0.2, 1.16]])
    return parent, packed, variance, colors, wb, matrix.repeat(4, 1, 1)


def test_detail_starts_with_bit_exact_parent_for_all_bayer_layouts():
    head = PairedLuminanceDetail(width=8)
    example = inputs()
    torch.testing.assert_close(head(*example), example[0], rtol=0, atol=0)


def test_detail_is_achromatic_and_clipped_neighborhood_returns_parent():
    parent, packed, variance, colors, wb, matrix = inputs()
    head = PairedLuminanceDetail(width=8)
    with torch.no_grad():
        head.output.bias[:4] = torch.tensor([0.25, -0.25, 0.125, -0.125])
        packed[:, :, 9:13, 10:14] = 1
        corrected = head(parent, packed, variance, colors, wb, matrix)
    change = corrected - parent
    assert float(change.abs().max()) > 1e-4
    torch.testing.assert_close(
        corrected[:, :, 12:32, 14:34], parent[:, :, 12:32, 14:34], rtol=0, atol=0
    )
    rgb_change = torch.einsum("bij,bjhw->bihw", matrix, change * wb[:, :, None, None])
    torch.testing.assert_close(rgb_change, rgb_change[:, :1].expand_as(rgb_change), rtol=0, atol=3e-8)
