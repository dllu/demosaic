"""Independent coordinate/adjoint checks and meaningful nonzero-head semantics."""

import math

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.late_harmonic_context import LateHarmonicContextDetail, dyadic_frequency_context
from demosaic.late_spatial_rgb import LateSpatialRgbDetail


@pytest.mark.parametrize("size", [4, 8, 16])
def test_coordinates_and_full_adjoint_against_numpy_loops(size):
    rng = np.random.default_rng(16101 + size)
    data = rng.normal(size=(2, 3, size, size))
    upstream = rng.normal(size=(2, 15, size, size))
    expected = np.zeros_like(upstream)
    adjoint = np.zeros_like(data)
    half = size // 2
    for n in range(2):
        for c in range(3):
            for branch in range(5):
                for y in range(size):
                    for x in range(size):
                        if branch == 0:
                            vertices = [(2 * y % size, 2 * x % size, 1.0)]
                        else:
                            py, px = divmod(branch - 1, 2)
                            sy, sx = y / 2 + py * half, x / 2 + px * half
                            iy, ix = math.floor(sy), math.floor(sx)
                            fy, fx = sy - iy, sx - ix
                            vertices = [
                                ((iy + dy) % size, (ix + dx) % size, wy * wx)
                                for dy, wy in [(0, 1 - fy), (1, fy)]
                                for dx, wx in [(0, 1 - fx), (1, fx)]
                            ]
                        out_channel = branch * 3 + c
                        for iy, ix, weight in vertices:
                            expected[n, out_channel, y, x] += weight * data[n, c, iy, ix]
                            adjoint[n, c, iy, ix] += weight * upstream[n, out_channel, y, x]
    value = torch.tensor(data, requires_grad=True)
    result = dyadic_frequency_context(value)
    (result * torch.tensor(upstream)).sum().backward()
    np.testing.assert_allclose(result.detach().numpy(), expected, rtol=2e-15, atol=2e-15)
    np.testing.assert_allclose(value.grad.numpy(), adjoint, rtol=2e-14, atol=2e-14)


def test_half_branch_interpolates_across_its_boundary():
    value = torch.zeros(1, 1, 8, 8)
    value[0, 0, 4, 4] = 1
    result = dyadic_frequency_context(value)
    assert result[0, 1, 7, 7] == 0.25
    assert result[0, 2, 7, 0] == 0.5
    assert result[0, 3, 0, 7] == 0.5
    assert result[0, 4, 0, 0] == 1


def inputs():
    generator = torch.Generator().manual_seed(16102)
    base = torch.rand(4, 3, 22, 26, generator=generator) * 0.01
    packed = torch.rand(4, 4, 11, 13, generator=generator) * 0.01
    variance = torch.rand(packed.shape, generator=generator) * 1e-5 + 1e-7
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    wb = torch.rand(4, 3, generator=generator) + 0.7
    return base, packed, variance, colors, wb


@pytest.mark.parametrize("pattern", PATTERNS)
def test_zero_adapter_embeds_nonzero_spatial_hybrid_exactly(pattern):
    state = torch.get_rng_state().clone()
    baseline, candidate = LateSpatialRgbDetail(8), LateHarmonicContextDetail(8)
    assert torch.equal(state, torch.get_rng_state())
    assert sum(p.numel() for p in candidate.parameters()) == 124397
    assert len(candidate.state_dict()) == 46 and len(baseline.state_dict()) == 45
    for name, value in baseline.state_dict().items():
        assert torch.equal(value, candidate.state_dict()[name])
    generator = torch.Generator().manual_seed(16103)
    with torch.no_grad():
        for name, parameter in baseline.named_parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.02)
            candidate.state_dict()[name].copy_(parameter)
    data = inputs()
    data = (*data[:3], color_indices(pattern), data[4])
    with torch.no_grad():
        expected = baseline(*data)
        actual = candidate(*data)
    assert not torch.equal(expected, data[0])
    assert actual.numpy().tobytes() == expected.numpy().tobytes()


@pytest.mark.parametrize("training", [False, True])
def test_activated_context_cannot_read_other_batch_members(training):
    module = LateHarmonicContextDetail(8).train(training)
    generator = torch.Generator().manual_seed(16104)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.02)
    base, packed, variance, colors, wb = inputs()
    fields = [v.requires_grad_() for v in [base, packed, variance, wb]]
    result = module(base, packed, variance, colors, wb)
    grads = torch.autograd.grad(result[0].square().sum(), fields)
    assert all(torch.isfinite(g).all() and g[1:].count_nonzero() == 0 for g in grads)
    changed = [v.detach().clone() for v in fields]
    for value in changed:
        value[1:] = value[1:].flip(0) * 4.2 + 0.003
    with torch.no_grad():
        other = module(changed[0], changed[1], changed[2], colors, changed[3])
    assert result[0].detach().numpy().tobytes() == other[0].numpy().tobytes()


def test_all_parameters_receive_finite_nonzero_gradients():
    module = LateHarmonicContextDetail(8)
    data = inputs()
    target = (
        data[0]
        + (torch.rand(data[0].shape, generator=torch.Generator().manual_seed(16105)) - 0.5) * 0.002
    )
    optimizer = torch.optim.AdamW(module.parameters(), lr=1e-3)
    maximum = {name: 0.0 for name, _ in module.named_parameters()}
    for _ in range(4):
        optimizer.zero_grad(set_to_none=True)
        loss = ((module(*data) - target) / 0.002).square().mean()
        loss.backward()
        for name, parameter in module.named_parameters():
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
            maximum[name] = max(maximum[name], float(parameter.grad.abs().max()))
        optimizer.step()
    assert len(maximum) == 46 and min(maximum.values()) > 0


def test_learned_context_preserves_noiseless_constants():
    module = LateHarmonicContextDetail(8)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.fill_(0.02)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    base = torch.tensor([0.01, 0.02, 0.013333])[None, :, None, None].expand(4, -1, 22, 26)
    packed = mosaic(base, colors)
    with torch.no_grad():
        result = module(base, packed, torch.zeros_like(packed), colors)
    assert torch.equal(result, base)


@pytest.mark.parametrize("shape", [(1, 1, 3, 3), (1, 1, 6, 6), (1, 1, 4, 8), (1, 0, 8, 8)])
def test_invalid_transport_geometry(shape):
    with pytest.raises(ValueError):
        dyadic_frequency_context(torch.zeros(shape))
