"""Independent dense-DFT values/adjoints and delivered-loss color/support coverage."""

from functools import lru_cache

import numpy as np
import pytest
import torch
from delivered_spectral_objective import spectral_loss
from noisy_objective import coefficient_loss

from demosaic.cfa import color_indices, mosaic
from demosaic.late_spectral_relative import LateSpectralRelativeDetail


@lru_cache
def dense_analysis(height=5, width=7, size=4):
    """Explicit replicated sampling and weighted plane projection, then dense DFT."""
    y, x = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
    window = (np.sin(np.pi * y / size) * np.sin(np.pi * x / size)).ravel()
    basis = np.stack([np.ones_like(x), 2 * x / (size - 1) - 1, 2 * y / (size - 1) - 1], -1).reshape(
        -1, 3
    )
    projection = basis @ np.linalg.solve(
        basis.T @ (window[:, None] ** 2 * basis), basis.T * window**2
    )
    dft = (
        np.exp(
            -2j
            * np.pi
            * (y.ravel()[:, None] * y.ravel()[None] + x.ravel()[:, None] * x.ravel()[None])
            / size
        )
        / size
    )
    dft[0] = 0
    transform = (dft * window) @ (np.eye(size * size) - projection)
    hop = size // 2
    operators = []
    for top in range(0, height + hop + (-height % hop), hop):
        for left in range(0, width + hop + (-width % hop), hop):
            row = np.clip(top + y.ravel() - hop, 0, height - 1)
            col = np.clip(left + x.ravel() - hop, 0, width - 1)
            sampling = np.eye(height * width)[row * width + col]
            operators.append(transform @ sampling)
    frequency = np.fft.fftfreq(size)
    radius = np.hypot(frequency[:, None], frequency[None])
    band = np.sin(np.pi / 2 * np.clip((radius - 1 / 32) / (1 / 32), 0, 1)) ** 2
    band *= np.sin(np.pi / 2 * np.clip((0.45 - radius) / 0.05, 0, 1)) ** 2
    return np.array(operators), band.ravel()


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("noise_level", [0, 1e-5])
@pytest.mark.parametrize("site", ["delivered-mosaic", "delivered-RGB"])
def test_delivered_values_and_full_adjoint_match_dense_numpy(pattern, noise_level, site):
    rng = np.random.default_rng(15301)
    module = LateSpectralRelativeDetail(4)
    colors = color_indices(pattern)[None]
    values = rng.normal(size=(1, 3, 10, 14)).astype("float32") * 0.001
    output = torch.tensor(values, requires_grad=True)
    _, geometry = module.analysis(torch.zeros(1, 4, 5, 7))
    operator, band = dense_analysis()
    noise = rng.uniform(0.5, 2, (len(operator), 4)).astype("float32") * noise_level
    aux = {"geometry": geometry, "noise_power": torch.tensor(noise)}
    actual = spectral_loss(module, output, torch.zeros_like(output), colors, aux, 16, site)
    actual.backward()
    selections = (
        [(int(colors[0, phase]), *divmod(phase, 2)) for phase in range(4)]
        if site == "delivered-mosaic"
        else [(c, dy, dx) for c in range(3) for dy in range(2) for dx in range(2)]
    )
    packed = np.array([values[0, c, dy::2, dx::2].ravel() for c, dy, dx in selections], dtype=float)
    spectrum = np.einsum("fki,ci->fck", operator, packed)
    variance = np.maximum(
        np.tile(noise.astype(float), (1, len(selections) // 4)), (16 / 65535) ** 2
    )
    denominator = band.sum() * len(operator) * len(selections)
    expected = (abs(spectrum) ** 2 * band / variance[..., None]).sum() / denominator
    adjoint = (
        2
        * np.einsum("fki,fck->ci", operator.conj(), spectrum * band / variance[..., None]).real
        / denominator
    )
    gradient = np.zeros_like(values, dtype=float)
    for (c, dy, dx), plane in zip(selections, adjoint, strict=True):
        gradient[0, c, dy::2, dx::2] = plane.reshape(5, 7)
    np.testing.assert_allclose(actual.detach().numpy(), expected, rtol=2e-6, atol=1e-8)
    np.testing.assert_allclose(output.grad.numpy(), gradient, rtol=3e-5, atol=8e-6)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_pre_support_wrapper_retains_exact_values_and_gradients(pattern):
    generator = torch.Generator().manual_seed(15302)
    module = LateSpectralRelativeDetail(8)
    target = torch.rand(1, 3, 16, 16, generator=generator) * 0.02
    colors = color_indices(pattern)[None]
    parent, geometry = module.analysis(mosaic(target / 2, colors))
    delta = (torch.randn(parent.shape, generator=generator) * 0.001).requires_grad_()
    aux = {
        "geometry": geometry,
        "parent_spectrum": parent,
        "spectral_delta": delta,
        "noise_power": torch.full(parent.shape[:2], 1e-5),
    }
    legacy = coefficient_loss(module, target, colors, aux, 16)
    current = spectral_loss(module, target / 2, target, colors, aux, 16, "pre-support")
    assert torch.equal(legacy, current)
    old_gradient = torch.autograd.grad(legacy, delta, retain_graph=True)[0]
    assert torch.equal(old_gradient, torch.autograd.grad(current, delta)[0])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_RGB_loss_sees_unsampled_color_error_that_mosaic_cannot(pattern):
    module = LateSpectralRelativeDetail(8)
    colors = color_indices(pattern)[None]
    generator = torch.Generator().manual_seed(15303)
    target = torch.zeros(1, 3, 16, 16)
    error = torch.randn(target.shape, generator=generator) * 0.001
    for phase, color in enumerate(colors[0]):
        dy, dx = divmod(phase, 2)
        error[:, color, dy::2, dx::2] = 0
    _, geometry = module.analysis(torch.zeros(1, 4, 8, 8))
    aux = {"geometry": geometry, "noise_power": torch.zeros(geometry[5], 4)}
    assert mosaic(error, colors).count_nonzero() == 0
    assert spectral_loss(module, error, target, colors, aux, 16, "delivered-mosaic") == 0
    assert spectral_loss(module, error, target, colors, aux, 16, "delivered-RGB") > 0


@pytest.mark.parametrize("site", ["delivered-mosaic", "delivered-RGB"])
def test_delivered_spectral_gradient_reaches_support_while_pre_support_does_not(site):
    module = LateSpectralRelativeDetail(8)
    generator = torch.Generator().manual_seed(15304)
    with torch.no_grad():
        module.frequency_out.weight.copy_(
            torch.randn(module.frequency_out.weight.shape, generator=generator) * 0.1
        )
    base = torch.rand(1, 3, 16, 16, generator=generator) * 0.02
    raw = torch.rand(1, 4, 8, 8, generator=generator) * 0.02
    colors = color_indices("GBRG")[None]
    output, aux = module(base, raw, torch.full_like(raw, 1e-5), colors, return_aux=True)
    target = torch.rand(base.shape, generator=generator) * 0.02
    before = coefficient_loss(module, target, colors, aux, 16)
    assert (
        torch.autograd.grad(before, module.local_out.weight, allow_unused=True, retain_graph=True)[
            0
        ]
        is None
    )
    delivered = spectral_loss(module, output, target, colors, aux, 16, site)
    grad = torch.autograd.grad(delivered, module.local_out.weight)[0]
    assert torch.isfinite(grad).all() and grad.count_nonzero() > 0


def test_invalid_site_is_rejected():
    with pytest.raises(ValueError, match="supervision site"):
        spectral_loss(None, None, None, None, None, 16, "unknown")
