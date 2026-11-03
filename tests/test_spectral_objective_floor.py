import pytest
import torch
from train_objective_floor_trial import spectral_loss_with_floor

from demosaic.cfa import color_indices, mosaic
from demosaic.late_spectral_matrix import LateSpectralMatrixDetail


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("noise", [0.0, 1e-5])
def test_loss_floor_preserves_legacy_and_has_expected_ADC_gradient_scale(pattern, noise):
    module = LateSpectralMatrixDetail(8)
    random = torch.Generator().manual_seed(150)
    target = torch.rand(1, 3, 16, 16, generator=random) * 0.02
    colors = color_indices(pattern)[None]
    parent = target * 0.7
    spectrum, geometry = module.analysis(mosaic(parent, colors))
    delta = (torch.rand(spectrum.shape, generator=random) * 0.001).to(torch.complex64)
    delta.requires_grad_()
    aux = {
        "spectral_delta": delta,
        "geometry": geometry,
        "parent_spectrum": spectrum,
        "noise_power": torch.full(spectrum.shape[:2], noise),
    }
    legacy = module.spectral_supervision(target, colors, aux)
    current = spectral_loss_with_floor(module, target, colors, aux, 2)
    candidate = spectral_loss_with_floor(module, target, colors, aux, 16)
    old_grad = torch.autograd.grad(legacy, delta, retain_graph=True)[0]
    current_grad = torch.autograd.grad(current, delta, retain_graph=True)[0]
    new_grad = torch.autograd.grad(candidate, delta)[0]
    assert torch.equal(legacy, current) and torch.equal(old_grad, current_grad)
    if noise:
        assert torch.equal(current, candidate) and torch.equal(current_grad, new_grad)
    else:
        torch.testing.assert_close(candidate * 64, current, rtol=1e-6, atol=0)
        torch.testing.assert_close(new_grad * 64, current_grad, rtol=1e-6, atol=0)
    assert torch.isfinite(new_grad).all() and new_grad.abs().max() > 0
