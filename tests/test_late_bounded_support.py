"""Independent bounds/adjoints and exact zero-floor whole-head compatibility."""
import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices
from demosaic.late_bounded_support import LateBoundedSupportDetail, bounded_support
from demosaic.late_harmonic_phase import LateHarmonicPhaseDetail


@pytest.mark.parametrize("floor", [0, 0.125, 0.25, 0.49])
def test_independent_scalar_values_and_full_logit_adjoint(floor):
    values = np.linspace(-12, 12, 91).reshape(7, 13)
    upstream = np.sin(np.arange(values.size)).reshape(values.shape)
    logits = torch.tensor(values, requires_grad=True)
    result = bounded_support(logits, floor)
    offset = np.log1p(-2 * floor)
    sigmoid = 1 / (1 + np.exp(-(values + offset)))
    expected = floor + (1 - floor) * sigmoid
    expected_gradient = upstream * (1 - floor) * sigmoid * (1 - sigmoid)
    (result * torch.tensor(upstream)).sum().backward()
    np.testing.assert_allclose(result.detach().numpy(), expected, rtol=3e-15, atol=3e-16)
    np.testing.assert_allclose(logits.grad.numpy(), expected_gradient, rtol=2e-10, atol=3e-16)


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_quarter_floor_extreme_values_and_same_half_open_initializer(dtype):
    logits = torch.tensor([-1e30, -100, -10, 0, 10, 100, 1e30], dtype=dtype, requires_grad=True)
    result = bounded_support(logits, .25)
    assert result[0] == .25 and result[-1] == 1 and result[3] == .5
    assert torch.all((result >= .25) & (result <= 1))
    result.sum().backward()
    assert torch.isfinite(logits.grad).all() and torch.all(logits.grad >= 0)
    assert torch.equal(bounded_support(logits, 0), logits.sigmoid())


def batch(pattern):
    generator = torch.Generator().manual_seed(16701)
    base = torch.rand(2, 3, 22, 26, generator=generator) * .01
    packed = torch.rand(2, 4, 11, 13, generator=generator) * .01
    variance = torch.rand(packed.shape, generator=generator) * 1e-5 + 1e-7
    colors = color_indices(pattern)[None].expand(2, -1)
    wb = torch.tensor([[1.3, 1., 1.7]]).expand(2, -1)
    return base, packed, variance, colors, wb


@pytest.mark.parametrize("pattern", PATTERNS)
def test_zero_floor_replays_all_auxiliaries_and_full_parameter_gradients(pattern):
    original = LateHarmonicPhaseDetail(8)
    candidate = LateBoundedSupportDetail(8, support_floor=0)
    generator = torch.Generator().manual_seed(16702)
    with torch.no_grad():
        for parameter in original.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * .01)
    candidate.load_state_dict(original.state_dict(), strict=True)
    values = batch(pattern)
    first, a = original(*values, return_aux=True)
    second, b = candidate(*values, return_aux=True)
    assert torch.equal(first, second) and a.keys() == b.keys()
    for key in a:
        assert torch.equal(a[key], b[key]) if isinstance(a[key], torch.Tensor) else a[key] == b[key]
    first.square().sum().backward(); second.square().sum().backward()
    for (name, x), (other, y) in zip(original.named_parameters(), candidate.named_parameters(), strict=True):
        assert name == other and torch.equal(x.grad, y.grad), name


@pytest.mark.parametrize("pattern", PATTERNS)
def test_initializer_state_output_support_and_RNG_match_old_head(pattern):
    before = torch.get_rng_state().clone()
    original = LateHarmonicPhaseDetail(8)
    candidate = LateBoundedSupportDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert len(candidate.state_dict()) == 47
    assert sum(p.numel() for p in candidate.parameters()) == 124909
    assert all(torch.equal(v, candidate.state_dict()[k]) for k,v in original.state_dict().items())
    values = batch(pattern)
    first, a = original(*values, return_aux=True);second, b = candidate(*values, return_aux=True)
    assert torch.equal(first, values[0]) and torch.equal(first, second)
    assert torch.equal(a['support'], b['support']) and torch.all(b['support'] == .5)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_trained_nonzero_state_support_bounds_and_zero_variance_constant_RAW(pattern):
    module = LateBoundedSupportDetail(8)
    generator = torch.Generator().manual_seed(16703)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * .02)
        module.local_out.bias.fill_(-100)
    values = batch(pattern)
    result, aux = module(*values, return_aux=True)
    assert torch.all(aux['support'] == .25) and torch.isfinite(result).all()
    result.square().sum().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in module.parameters())
    base, packed, variance, colors, wb = values
    packed = torch.tensor([.001, .002, .003, .004])[None,:,None,None].expand_as(packed)
    result, aux = module(base, packed, torch.zeros_like(variance), colors, wb, return_aux=True)
    assert torch.equal(result, base) and aux['correction'].count_nonzero() == 0


@pytest.mark.parametrize("floor", [-.1, .5, 1., float('nan'), float('inf'), True, '0.25'])
def test_invalid_support_floor_rejected(floor):
    with pytest.raises(ValueError):LateBoundedSupportDetail(8, support_floor=floor)


@pytest.mark.parametrize("values", [torch.ones(3,dtype=torch.int64),torch.ones(3,dtype=torch.complex64),torch.empty(0)])
def test_invalid_logit_tensor_rejected(values):
    with pytest.raises(ValueError):bounded_support(values)
