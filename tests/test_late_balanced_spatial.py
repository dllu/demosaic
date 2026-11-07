"""Independent filter oracle and exact embedding of the trained predecessor."""

import numpy as np
import pytest
import torch
from test_late_bounded_support import PATTERNS, batch

from demosaic.late_balanced_spatial import LateBalancedSpatialDetail, SpatialHighpass
from demosaic.late_bounded_support import LateBoundedSupportDetail


def numpy_highpass(value, sigma=8.0, radius=24):
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    result = value.astype(np.float64)
    for axis in [-1, -2]:
        padding = [(0, 0)] * 4
        padding[axis] = (radius, radius)
        padded = np.pad(result, padding, mode="edge")
        result = np.apply_along_axis(lambda v: np.convolve(v, kernel, mode="valid"), axis, padded)
    return value - result


@pytest.mark.parametrize("shape", [(1, 3, 1, 1), (2, 3, 7, 11), (1, 3, 65, 67)])
def test_filter_matches_independent_numpy_convolution_and_annihilates_constants(shape):
    value = np.random.default_rng(16901).normal(size=shape)
    module = SpatialHighpass()
    actual = module(torch.from_numpy(value)).numpy()
    np.testing.assert_allclose(actual, numpy_highpass(value), atol=5e-15, rtol=1e-13)
    constant = torch.tensor([0.03, -0.005, 0.1234], dtype=torch.float32)[
        None, :, None, None
    ].expand(shape)
    assert module(constant).count_nonzero() == 0


def test_fine_wire_retention_and_coarse_rejection_interior():
    module = SpatialHighpass()
    x = torch.arange(512, dtype=torch.float64)
    # The 8px carrier is substantially finer than the prescribed Gaussian scale.
    fine = torch.cos(x * (2 * np.pi / 8))[None, None, None].expand(1, 3, 65, -1)
    coarse = torch.cos(x * (2 * np.pi / 256))[None, None, None].expand_as(fine)
    for value, minimum, maximum in [(fine, 0.995, 1.005), (coarse, 0.015, 0.025)]:
        interior = (..., slice(24, -24), slice(24, -24))
        result = module(value)
        gain = ((result[interior] * value[interior]).sum() / value[interior].square().sum()).item()
        assert minimum < gain < maximum


@pytest.mark.parametrize("pattern", PATTERNS)
def test_disabled_trained_embedding_exact_values_auxiliaries_and_gradients(pattern):
    original = LateBoundedSupportDetail(8)
    candidate = LateBalancedSpatialDetail(8, balance_spatial=False)
    generator = torch.Generator().manual_seed(16902)
    with torch.no_grad():
        for parameter in original.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.01)
    candidate.load_state_dict(original.state_dict(), strict=True)
    values = batch(pattern)
    first, a = original(*values, return_aux=True)
    second, b = candidate(*values, return_aux=True)
    assert torch.equal(first, second) and a.keys() == b.keys()
    for key in a:
        assert torch.equal(a[key], b[key]) if isinstance(a[key], torch.Tensor) else a[key] == b[key]
    first.square().sum().backward()
    second.square().sum().backward()
    for (name, x), (other, y) in zip(
        original.named_parameters(), candidate.named_parameters(), strict=True
    ):
        assert name == other and torch.equal(x.grad, y.grad)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_balanced_path_initializes_exactly_and_nonzero_state_has_finite_gradients(pattern):
    before = torch.get_rng_state().clone()
    module = LateBalancedSpatialDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert len(module.state_dict()) == 47 and sum(p.numel() for p in module.parameters()) == 124909
    values = batch(pattern)
    output = module(*values)
    assert torch.equal(output, values[0])
    generator = torch.Generator().manual_seed(16903)
    with torch.no_grad():
        for p in module.parameters():
            p.copy_(torch.randn(p.shape, generator=generator) * 0.01)
    output, aux = module(*values, return_aux=True)
    assert torch.isfinite(output).all() and aux["unbalanced_spatial_correction"].count_nonzero()
    assert torch.equal(
        aux["spatial_correction"], module.spatial_highpass(aux["unbalanced_spatial_correction"])
    )
    output.square().sum().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in module.parameters())
    base, packed, variance, colors, wb = values
    _result, aux = module(base, packed, torch.zeros_like(variance), colors, wb, return_aux=True)
    assert (
        aux["unbalanced_spatial_correction"].count_nonzero()
        == aux["spatial_correction"].count_nonzero()
        == 0
    )


@pytest.mark.parametrize(
    "sigma,radius", [(0, 24), (-1, 24), (True, 24), (float("nan"), 24), (8, 0), (8, True), (8, 2.5)]
)
def test_invalid_filter_settings_rejected(sigma, radius):
    with pytest.raises(ValueError):
        SpatialHighpass(sigma, radius)
