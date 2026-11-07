"""Coupled training members must not communicate through the head's batch axis."""

import pytest
import torch

from demosaic.late_spatial_rgb import LateSpatialRgbDetail


@pytest.mark.parametrize("training", [False, True])
def test_nonzero_head_output_and_input_adjoints_are_per_image(training):
    generator = torch.Generator().manual_seed(16051)
    module = LateSpatialRgbDetail(8).train(training)
    # Activate both paths; the all-zero initial correction would hide mixing.
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.02)
    base = (torch.rand(4, 3, 22, 26, generator=generator) * 0.01).requires_grad_()
    packed = (torch.rand(4, 4, 11, 13, generator=generator) * 0.01).requires_grad_()
    variance = (torch.rand(packed.shape, generator=generator) * 1e-5 + 1e-7).requires_grad_()
    wb = (torch.rand(4, 3, generator=generator) + 0.7).requires_grad_()
    colors = torch.tensor([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    output = module(base, packed, variance, colors, wb)
    assert not torch.equal(output, base)
    fields = (base, packed, variance, wb)
    grads = torch.autograd.grad(output[0].square().sum(), fields)
    assert all(torch.isfinite(g).all() and g[1:].count_nonzero() == 0 for g in grads)
    changed = [field.detach().clone() for field in fields]
    for field in changed:
        field[1:] = field[1:].flip(0) * 4.2 + 0.003
    with torch.no_grad():
        other_output = module(changed[0], changed[1], changed[2], colors, changed[3])
    assert torch.equal(output[0], other_output[0])
