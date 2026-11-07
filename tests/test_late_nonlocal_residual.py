"""Independent phase geometry,zero-variance routing and frozen-parent checks."""

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import color_indices
from demosaic.late_nonlocal_residual import LateNonlocalResidualDetail


@pytest.fixture(autouse=True)
def stub_network_has_no_native_operator(monkeypatch):
    monkeypatch.setattr("demosaic.late_nonlocal_residual.enable_sampler_autograd", lambda: None)


class FrozenFixture(nn.Module):
    def forward(self, base, packed, variance, colors, wb):
        return base * 0.75


class PackedFixture(nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = nn.Parameter(value)
        self.calls = 0

    def forward(self, features):
        assert features.shape[1] == 39
        self.calls += 1
        return self.value.expand(len(features), -1, *features.shape[-2:])


def module():
    pytest.importorskip("einops")
    before = torch.get_rng_state().clone()
    model = LateNonlocalResidualDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert model.network.tail.weight.count_nonzero() == 0
    assert not any(p.requires_grad for p in model.frozen.parameters())
    model.train()
    assert not model.frozen.training and model.network.training
    model.frozen = FrozenFixture()
    model.network = PackedFixture(torch.arange(12, dtype=torch.float32).reshape(1, 12, 1, 1))
    return model


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_native_rgb_phase_order_and_noise_unit_without_target_input(pattern):
    model = module()
    base = torch.full((1, 3, 16, 24), 0.02)
    packed = torch.full((1, 4, 8, 12), 0.01)
    variance = torch.full_like(packed, 0.000004)
    output, aux = model(base, packed, variance, color_indices(pattern), return_aux=True)
    expected = np.empty((1, 3, 16, 24), np.float32)
    for channel in range(3):
        for phase in range(4):
            y, x = divmod(phase, 2)
            expected[:, channel, y::2, x::2] = np.float32(0.015) + np.float32(
                (4 * channel + phase) * 0.002
            )
    np.testing.assert_allclose(output.detach().numpy(), expected, rtol=2e-7, atol=2e-9)
    assert aux["matching_evaluated"] and model.network.calls == 1
    output.sum().backward()
    assert torch.isfinite(model.network.value.grad).all()
    assert model.network.value.grad.min() > 0


def test_ADC_bypass_is_exact_even_with_nonzero_learned_phase_values():
    model = module()
    base = torch.arange(3 * 16 * 24, dtype=torch.float32).reshape(1, 3, 16, 24) / 65535
    packed = torch.zeros((1, 4, 8, 12))
    output, aux = model(base, packed, packed, color_indices("RGGB"), return_aux=True)
    assert torch.equal(output, base * 0.75)
    assert not aux["matching_evaluated"] and model.network.calls == 0
    assert aux["correction"].count_nonzero() == 0


def test_zero_variance_member_of_mixed_batch_retains_frozen_result():
    model = module()
    base = torch.full((2, 3, 16, 24), 0.02)
    packed = torch.full((2, 4, 8, 12), 0.01)
    variance = torch.zeros_like(packed)
    variance[1] = 0.000004
    output = model(base, packed, variance, color_indices("RGGB"))
    assert torch.equal(output[0], base[0] * 0.75)
    assert not torch.equal(output[1], base[1] * 0.75)
