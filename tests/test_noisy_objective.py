import numpy as np
import pytest
import torch
from noisy_objective import ADC_only, apply_ADC_weight, coefficient_loss, peak_weights
from train_objective_floor_trial import spectral_loss_with_floor

from demosaic.cfa import color_indices, mosaic
from demosaic.late_spectral_matrix import LateSpectralMatrixDetail


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("noise", [0.0, 1e-5])
def test_peak_weighted_complex_value_and_gradient_against_numpy(pattern, noise):
    module = LateSpectralMatrixDetail(8)
    generator = torch.Generator().manual_seed(151)
    target = torch.rand(1, 3, 16, 16, generator=generator) * 0.02
    colors = color_indices(pattern)[None]
    clean, geometry = module.analysis(mosaic(target, colors))
    parent = clean * 0.7
    delta = (
        torch.complex(
            torch.randn(clean.shape, generator=generator),
            torch.randn(clean.shape, generator=generator),
        )
        * 0.001
    )
    delta.requires_grad_()
    power = torch.full(clean.shape[:2], noise)
    aux = {
        "spectral_delta": delta,
        "geometry": geometry,
        "parent_spectrum": parent,
        "noise_power": power,
    }
    legacy = spectral_loss_with_floor(module, target, colors, aux, 16)
    control = coefficient_loss(module, target, colors, aux, 16)
    old_gradient = torch.autograd.grad(legacy, delta, retain_graph=True)[0]
    control_gradient = torch.autograd.grad(control, delta, retain_graph=True)[0]
    assert torch.equal(legacy, control) and torch.equal(old_gradient, control_gradient)
    weighted = coefficient_loss(module, target, colors, aux, 16, 7)
    gradient = torch.autograd.grad(weighted, delta)[0]
    c, d, p = [v.detach().numpy().astype(np.complex128) for v in [clean, delta, parent]]
    variance = np.maximum(power.numpy().astype(float)[:, :, None, None], (16 / 65535) ** 2)
    band = module.band_8.numpy().astype(float)
    ratio = (np.abs(c) ** 2).sum(1, keepdims=True) / variance.sum(1, keepdims=True)
    weights = 1 + 7 * ratio / (1 + ratio)
    denominator = band.sum() * len(c) * 4
    error = d - (c - p)
    expected = (np.abs(error) ** 2 / variance * band * weights).sum() / denominator
    expected_gradient = 2 * error / variance * band * weights / denominator
    np.testing.assert_allclose(float(weighted.detach()), expected, rtol=2e-6)
    np.testing.assert_allclose(gradient.numpy(), expected_gradient, rtol=3e-6, atol=1e-6)
    assert weights.min() >= 1 and weights.max() <= 8


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_flat_target_has_exact_baseline_weights_and_loss(pattern):
    module = LateSpectralMatrixDetail(8)
    target = torch.tensor([0.01, 0.02, 0.03])[None, :, None, None].expand(1, 3, 16, 16)
    colors = color_indices(pattern)[None]
    clean, geometry = module.analysis(mosaic(target, colors))
    noise = torch.full(clean.shape[:2], 1e-5)
    variance = noise[:, :, None, None]
    assert clean.count_nonzero() == 0
    assert torch.equal(peak_weights(clean, variance, 7), torch.ones_like(clean[:, :1].real))
    delta = torch.full_like(clean, 0.001).requires_grad_()
    aux = {
        "spectral_delta": delta,
        "geometry": geometry,
        "parent_spectrum": clean,
        "noise_power": noise,
    }
    plain = coefficient_loss(module, target, colors, aux, 16)
    focused = coefficient_loss(module, target, colors, aux, 16, 7)
    assert torch.equal(plain, focused)
    a = torch.autograd.grad(plain, delta, retain_graph=True)[0]
    b = torch.autograd.grad(focused, delta)[0]
    assert torch.equal(a, b)


def test_ADC_loss_routing_preserves_graph_and_optimizer_clock():
    adc, noisy = {"shot": 0.0, "read": 0.0}, {"shot": 0.0, "read": 1e-9}
    assert ADC_only(adc) and not ADC_only(noisy)
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    optimizer = torch.optim.AdamW([parameter], lr=0.01, weight_decay=0)
    loss = parameter.square()
    assert apply_ADC_weight(loss, adc, 1) is loss
    assert apply_ADC_weight(loss, noisy, 0) is loss
    loss.backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    before = parameter.detach().clone()
    ignored = apply_ADC_weight(parameter.square(), adc, 0)
    ignored.backward()
    assert ignored == 0 and parameter.grad is not None and parameter.grad == 0
    optimizer.step()
    assert optimizer.state[parameter]["step"] == 2
    assert parameter != before  # Existing Adam momentum continues on a zero-gradient step.
