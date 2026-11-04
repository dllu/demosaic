"""Test meaningful identity, noise routing, RGB capacity and feature coordinates."""

import numpy as np
import pytest
import torch
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, color_indices
from demosaic.late_spatial_rgb import LateSpatialRgbDetail, SpatialRgbResidual
from demosaic.late_spectral_relative import LateSpectralRelativeDetail


def inputs(height=7, width=11):
    generator = torch.Generator().manual_seed(15702)
    base = torch.rand(2, 3, 2 * height, 2 * width, generator=generator) * 0.01
    packed = torch.rand(2, 4, height, width, generator=generator) * 0.01
    variance = torch.rand(packed.shape, generator=generator) * 1e-5
    colors = torch.tensor([PATTERNS["BGGR"], PATTERNS["GRBG"]])
    wb = torch.tensor([[1.3, 1.0, 1.9], [1.1, 1.0, 1.7]])
    return base, packed, variance, colors, wb


def test_feature_coordinates_against_explicit_numpy():
    base, packed, variance, colors, wb = inputs(3, 5)
    features, sigma = SpatialRgbResidual.features(base, packed, variance, colors, wb)
    b, p, v, layouts, balances = [x.numpy() for x in (base, packed, variance, colors, wb)]
    expected = np.empty((2, 39, 3, 5), dtype=np.float64)
    for n in range(2):
        rms = np.sqrt(np.mean(v[n].astype(np.float64)))
        unit = max(rms, 16 / 65535)
        mean = b[n].astype(np.float64).mean((1, 2))
        for y in range(3):
            for x in range(5):
                centered, innovation = [], []
                for c in range(3):
                    for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                        centered.append(
                            np.arcsinh((b[n, c, 2 * y + dy, 2 * x + dx] - mean[c]) / unit)
                        )
                for phase, (dy, dx) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
                    innovation.append(
                        np.arcsinh(
                            (p[n, phase, y, x] - b[n, layouts[n, phase], 2 * y + dy, 2 * x + dx])
                            / unit
                        )
                    )
                layout = [float(c == layouts[n, phase]) for phase in range(4) for c in range(3)]
                expected[n, :, y, x] = (
                    centered
                    + innovation
                    + np.log1p(v[n, :, y, x] / unit**2).tolist()
                    + layout
                    + np.arcsinh(mean / unit).tolist()
                    + np.log(balances[n]).tolist()
                    + [np.log(unit * 65535)]
                )
        assert sigma[n].item() == pytest.approx(rms, rel=1e-6)
    np.testing.assert_allclose(features.numpy(), expected, atol=5e-7, rtol=2e-6)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_fresh_hybrid_embeds_fresh_spectral_parent(pattern):
    base, packed, variance, _, wb = inputs(9, 13)
    colors = color_indices(pattern)
    model, control = LateSpatialRgbDetail(8), LateSpectralRelativeDetail(8)
    for name, value in control.state_dict().items():
        assert torch.equal(model.state_dict()[name], value)
    with torch.no_grad():
        actual, aux = model(base, packed, variance, colors, wb, return_aux=True)
        expected = control(base, packed, variance, colors, wb)
    assert torch.equal(actual, expected) and torch.equal(actual, base)
    assert aux["spatial_correction"].count_nonzero() == 0


def test_direct_rgb_path_can_predict_constant_and_missing_color_modes():
    base, packed, variance, colors, wb = inputs()
    module = SpatialRgbResidual()
    # Biases specify all twelve C-major RGB phases independently. This includes
    # unsampled-color corrections outside a four-phase Malvar-only subspace.
    with torch.no_grad():
        module.output.bias.copy_(torch.arange(12).float() / 12)
        actual = module(base, packed, variance, colors, wb)
    scale = variance.double().mean((1, 2, 3), keepdim=True).sqrt().float()
    phases = torch.arange(12).float()[None, :, None, None].expand(2, -1, 7, 11) / 12
    expected = F.pixel_shuffle(phases, 2) * scale
    torch.testing.assert_close(actual, expected, rtol=2e-6, atol=1e-9)
    assert actual.mean() > 0


def test_learned_path_is_exactly_zero_for_zero_physical_noise():
    base, packed, variance, colors, wb = inputs(5, 9)
    module = SpatialRgbResidual()
    with torch.no_grad():
        module.output.weight.fill_(0.1)
        module.output.bias.fill_(-0.2)
        actual = module(base, packed, torch.zeros_like(variance), colors, wb)
    assert torch.isfinite(actual).all() and actual.count_nonzero() == 0


def test_broad_parent_error_reaches_new_path_and_trains_earlier_layers():
    base, packed, variance, colors, wb = inputs(8, 12)
    module = SpatialRgbResidual(width=8)
    optimizer = torch.optim.AdamW(module.parameters(), lr=1e-3)
    target = torch.full_like(base, -0.002)
    maximum = {name: 0.0 for name, _ in module.named_parameters()}
    initial = None
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        correction = module(base, packed, variance, colors, wb)
        loss = ((correction - target) / 0.002).square().mean()
        initial = loss.item() if initial is None else initial
        loss.backward()
        for name, parameter in module.named_parameters():
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
            maximum[name] = max(maximum[name], parameter.grad.abs().max().item())
        optimizer.step()
    assert all(value > 0 for value in maximum.values())
    assert loss.item() < initial


def test_initial_identity_gradient_and_constructor_preserves_cpu_rng():
    state = torch.get_rng_state().clone()
    module = SpatialRgbResidual()
    assert torch.equal(state, torch.get_rng_state())
    base, *other = inputs()
    base.requires_grad_()
    (base + module(base, *other)).sum().backward()
    assert torch.equal(base.grad, torch.ones_like(base))
