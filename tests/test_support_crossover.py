"""Check fixed component composition against independent signed Malvar stencils."""

import numpy as np
import pytest
import torch
from diagnose_support_crossover import METHODS, compose

from demosaic.archive_metrics import noisy_malvar
from demosaic.cfa import color_indices


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_crossed_and_full_outputs_match_numpy_and_linear_partition(pattern):
    rng = np.random.default_rng(15301)
    base = rng.uniform(0.01, 0.04, (1, 3, 24, 32)).astype("float32")
    colors = color_indices(pattern)[None]
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    proposals = {
        key: torch.tensor(rng.normal(size=(1, 4, 12, 16)).astype("float32") * 0.0001)
        for key in ["native", "relative"]
    }
    maps = {
        key: torch.tensor(rng.uniform(0, 1, (1, 1, 12, 16)).astype("float32")) for key in proposals
    }
    for proposal, support in METHODS.values():
        gate = None if support == "full" else maps[support]
        actual = compose(torch.tensor(base), proposals[proposal], gate, colors, wb)
        packed = (
            proposals[proposal].numpy() if gate is None else (proposals[proposal] * gate).numpy()
        )
        expected = base.astype(np.float64) + noisy_malvar(
            {"packed": packed, "colors": colors.numpy(), "wb": wb.numpy()}
        )
        np.testing.assert_allclose(actual.numpy(), expected, atol=3e-9, rtol=2e-7)
        if gate is not None:
            complementary = compose(torch.tensor(base), proposals[proposal], 1 - gate, colors, wb)
            full = compose(torch.tensor(base), proposals[proposal], None, colors, wb)
            np.testing.assert_allclose(
                (actual + complementary - torch.tensor(base)).numpy(), full.numpy(), atol=8e-9
            )


def test_bad_map_shape_is_rejected():
    with pytest.raises(ValueError, match="one spatial support"):
        compose(
            torch.zeros(1, 3, 16, 16),
            torch.zeros(1, 4, 8, 8),
            torch.zeros(1, 4, 8, 8),
            color_indices("RGGB")[None],
            torch.ones(1, 3),
        )
