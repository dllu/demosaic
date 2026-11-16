import math

import pytest
import torch

from demosaic.cfa import color_indices, mosaic
from demosaic.competing_phase import competing_phase_bins


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_two_families_keep_a_weaker_crossing_and_separate_their_roots(pattern):
    n = 128
    y, x = torch.meshgrid(torch.arange(2 * n), torch.arange(2 * n), indexing="ij")
    a = 2 * math.pi * (9 * y + 18 * x) / (2 * n)
    b = 2 * math.pi * (15 * y - 6 * x) / (2 * n)
    rgb = (0.02 + 0.003 * torch.cos(a) + 0.002 * torch.cos(2 * a) + 0.001 * torch.cos(b))[
        None, None
    ].expand(1, 3, -1, -1)
    colors = color_indices(pattern)[None]
    field = mosaic(rgb, colors)
    bins, valid, aux = competing_phase_bins(field, torch.full_like(field, 1e-6), colors)
    signed = torch.where(bins > n // 2, bins - n, bins).double()
    roots = signed[0, :, 0]
    assert valid.all() and bins.shape == (1, 2, 4, 2)
    cosine = abs(torch.dot(roots[0], roots[1]) / (roots[0].norm() * roots[1].norm()))
    assert cosine < math.cos(math.radians(20))
    assert min((r - torch.tensor([15.0, -6.0])).norm() for r in roots) < 2
    assert aux["global_nominal_power"].shape == (1, 2, 4, 2)


def test_configuration_errors_do_not_initialize_a_proposal():
    field = torch.zeros(1, 4, 32, 32)
    with pytest.raises(ValueError, match="angular"):
        competing_phase_bins(
            field, torch.ones_like(field), color_indices("RGGB")[None], family_degrees=90
        )
