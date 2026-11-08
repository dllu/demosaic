"""Initialize existing matching offsets on a wider grid; no inference changes."""

import math

import torch
from torch import nn


@torch.no_grad()
def initialize_spread_offsets(module, *, spacing=8):
    """Seed the existing 3x3 sampler at offsets spacing*[-1,0,1].

    The operator already adds a unit 3x3 grid. Its learned residual therefore
    starts at (spacing-1)*grid, encoded through inverse tanh. Only five existing
    bias vectors change. No parameters/buffers, forward hooks or RNG draws are
    added. Call once on a fresh network before loading any checkpoint.
    """
    if isinstance(spacing, bool) or not isinstance(spacing, (int, float)):
        raise TypeError("Spacing must be a finite number at least one")
    if not math.isfinite(spacing) or spacing < 1:
        raise ValueError("Spacing must be a finite number at least one")
    network = module.network
    blocks = [
        (name, child)
        for name, child in network.named_modules()
        if type(child).__name__ == "NonlocalBlock"
    ]
    if len(blocks) != 5:
        raise ValueError("Expected the existing five-block matching network")
    planned = []
    for name, child in blocks:
        final = child.offset_cnn.cnn[-1]
        if (
            child.neighbours != [3, 3]
            or not isinstance(final, nn.Conv2d)
            or final.bias is None
            or final.out_channels != 18
        ):
            raise ValueError("Expected a three-by-three, single-group offset predictor")
        if final.weight.count_nonzero() or final.bias.count_nonzero():
            raise ValueError("Initialize only fresh zero offset predictors")
        bound = float(child.max_search_dist)
        if not math.isfinite(bound) or spacing - 1 >= bound:
            raise ValueError("Spacing residual must lie strictly inside the search bound")
        grid = final.bias.new_tensor([(y, x) for y in [-1, 0, 1] for x in [-1, 0, 1]])
        bias = ((spacing - 1) * grid / bound).atanh().flatten()
        planned.append((name, final, bias))
    # Validate every block before mutating any state.
    for _, final, bias in planned:
        final.bias.copy_(bias)
    return [f"{name}.offset_cnn.cnn.10.bias" for name, _, _ in planned]
