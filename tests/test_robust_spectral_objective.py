"""Independent dense spectral loss/adjoint checks and weak-error coverage."""

import numpy as np
import pytest
import torch
from delivered_spectral_objective import spectral_loss as old_loss
from robust_spectral_objective import charbonnier_power, spectral_loss
from test_delivered_spectral_objective import dense_analysis

from demosaic.cfa import color_indices, mosaic
from demosaic.late_spectral_relative import LateSpectralRelativeDetail


@pytest.mark.parametrize("epsilon", [0.01, 0.003])
@pytest.mark.parametrize("noise_level", [0, 1e-5])
@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_full_values_and_output_adjoint_match_independent_dense_DFT(epsilon, noise_level, pattern):
    rng = np.random.default_rng(15401)
    module = LateSpectralRelativeDetail(4)
    values = rng.normal(size=(2, 3, 10, 14)).astype("float32") * 0.0001
    output = torch.tensor(values, requires_grad=True)
    _, geometry = module.analysis(torch.zeros(2, 4, 5, 7))
    operator, band = dense_analysis()
    frames = len(operator)
    noise = rng.uniform(0.5, 2, (2 * frames, 4)).astype("float32") * noise_level
    aux = {"geometry": geometry, "noise_power": torch.tensor(noise)}
    actual = spectral_loss(
        module,
        output,
        torch.zeros_like(output),
        color_indices(pattern)[None].expand(2, -1),
        aux,
        16,
        "charbonnier",
        epsilon,
    )
    actual.backward()
    selections = [(c, y, x) for c in range(3) for y in range(2) for x in range(2)]
    packed = np.array(
        [[values[b, c, y::2, x::2].ravel() for c, y, x in selections] for b in range(2)],
        dtype=float,
    )
    spectrum = np.einsum("fki,bci->bfck", operator, packed)
    variance = np.maximum(np.tile(noise.astype(float), (1, 3)), (16 / 65535) ** 2).reshape(
        2, frames, 12, 1
    )
    power = abs(spectrum) ** 2 / variance
    radius = np.sqrt(power + epsilon**2)
    # np.hypot is independent stable evaluation of the desired radius.
    phi = power / (np.hypot(abs(spectrum) / np.sqrt(variance), epsilon) + epsilon)
    denominator = band.sum() * frames * 2 * 12
    expected = (phi * band).sum() / denominator
    spectral_grad = spectrum * band / (variance * radius)
    adjoint = np.einsum("fki,bfck->bci", operator.conj(), spectral_grad).real / denominator
    gradient = np.zeros_like(values, dtype=float)
    for b in range(2):
        for (c, y, x), plane in zip(selections, adjoint[b], strict=True):
            gradient[b, c, y::2, x::2] = plane.reshape(5, 7)
    np.testing.assert_allclose(actual.detach().numpy(), expected, rtol=3e-6, atol=1e-8)
    np.testing.assert_allclose(output.grad.numpy(), gradient, rtol=8e-5, atol=5e-6)


def test_MSE_control_replays_legacy_value_and_full_output_gradient_exactly():
    module = LateSpectralRelativeDetail(8)
    generator = torch.Generator().manual_seed(15402)
    output = (torch.rand(2, 3, 16, 16, generator=generator) * 0.03).requires_grad_()
    target = torch.rand(output.shape, generator=generator) * 0.03
    colors = color_indices("GRBG")[None].expand(2, -1)
    _, geometry = module.analysis(torch.zeros(2, 4, 8, 8))
    aux = {"geometry": geometry, "noise_power": torch.full((2 * geometry[5], 4), 1e-5)}
    legacy = old_loss(module, output, target, colors, aux, 16, "delivered-RGB")
    current = spectral_loss(module, output, target, colors, aux, 16, "mse", 0)
    assert torch.equal(legacy, current)
    a = torch.autograd.grad(legacy, output, retain_graph=True)[0]
    assert torch.equal(a, torch.autograd.grad(current, output)[0])


@pytest.mark.parametrize("epsilon", [0.01, 0.003])
def test_tiny_complex_errors_remain_positive_and_zero_has_finite_derivatives(epsilon):
    errors = torch.tensor(
        [0, 1e-14 + 2e-14j, 1e-5 - 2e-5j, 0.01 + 0.02j], dtype=torch.complex128, requires_grad=True
    )
    loss = charbonnier_power(errors.abs().square(), epsilon).sum()
    loss.backward()
    expected = errors.detach().numpy() / np.sqrt(abs(errors.detach().numpy()) ** 2 + epsilon**2)
    np.testing.assert_allclose(errors.grad.numpy(), expected, rtol=2e-15, atol=1e-24)
    assert errors.grad[0] == 0 and torch.isfinite(errors.grad).all()
    power = torch.tensor([0, 1e-28, 1e-12, 1e-6, 1], dtype=torch.float32, requires_grad=True)
    values = charbonnier_power(power, epsilon)
    assert values[0] == 0 and (values[1:] > 0).all()
    gradient = torch.autograd.grad(values.sum(), power, create_graph=True)[0]
    expected = 1 / (2 * np.sqrt(power.detach().numpy().astype(float) + epsilon**2))
    np.testing.assert_allclose(gradient.detach().numpy(), expected, rtol=2e-7)
    assert torch.isfinite(torch.autograd.grad(gradient.sum(), power)[0]).all()
    assert gradient[1] > 49  # MSE d(power) is1, even at a weak nonzero error.


@pytest.mark.parametrize("epsilon", [0.01, 0.003])
def test_flat_target_errors_are_penalized_and_unsampled_colors_are_covered(epsilon):
    module = LateSpectralRelativeDetail(8)
    colors = color_indices("GBRG")[None]
    generator = torch.Generator().manual_seed(15403)
    error = torch.randn(1, 3, 16, 16, generator=generator) * 0.0001
    for phase, color in enumerate(colors[0]):
        y, x = divmod(phase, 2)
        error[:, color, y::2, x::2] = 0
    assert mosaic(error, colors).count_nonzero() == 0
    _, geometry = module.analysis(torch.zeros(1, 4, 8, 8))
    aux = {"geometry": geometry, "noise_power": torch.zeros(geometry[5], 4)}
    flat = torch.zeros_like(error)
    assert spectral_loss(module, flat, flat, colors, aux, 16, "charbonnier", epsilon) == 0
    assert spectral_loss(module, error, flat, colors, aux, 16, "charbonnier", epsilon) > 0


@pytest.mark.parametrize("epsilon", [0.01, 0.003])
def test_robust_delivered_gradient_reaches_spatial_support(epsilon):
    module = LateSpectralRelativeDetail(8)
    generator = torch.Generator().manual_seed(15404)
    with torch.no_grad():
        module.frequency_out.weight.copy_(
            torch.randn(module.frequency_out.weight.shape, generator=generator) * 0.1
        )
    base = torch.rand(1, 3, 16, 16, generator=generator) * 0.02
    raw = torch.rand(1, 4, 8, 8, generator=generator) * 0.02
    colors = color_indices("RGGB")[None]
    output, aux = module(base, raw, torch.full_like(raw, 1e-5), colors, return_aux=True)
    loss = spectral_loss(
        module, output, torch.zeros_like(output), colors, aux, 16, "charbonnier", epsilon
    )
    gradient = torch.autograd.grad(loss, module.local_out.weight)[0]
    assert torch.isfinite(gradient).all() and gradient.count_nonzero() > 0


@pytest.mark.parametrize("epsilon", [0, -1, float("nan"), float("inf")])
def test_invalid_robust_epsilon_is_rejected(epsilon):
    with pytest.raises(ValueError, match="finite and positive"):
        charbonnier_power(torch.zeros(1), epsilon)
