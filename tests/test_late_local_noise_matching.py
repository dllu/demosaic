"""Independent cell statistics,locality and phase-aligned output checks."""

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import color_indices
from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail, local_noise_features
from demosaic.late_nonlocal_residual import LateNonlocalResidualDetail
from demosaic.late_spatial_rgb import SpatialRgbResidual


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_features_match_independent_numpy_cell_statistics(pattern):
    rng = np.random.default_rng(17201)
    rgb = rng.uniform(0.001, 0.2, (2, 3, 16, 24)).astype(np.float32)
    packed = rng.uniform(-0.001, 0.03, (2, 4, 8, 12)).astype(np.float32)
    variance = rng.uniform(-1e-7, 4e-5, packed.shape).astype(np.float32)
    wb = np.asarray([[1.5, 1, 1.2], [1.2, 1.1, 1.6]], np.float32)
    colors = color_indices(pattern).numpy()
    actual, sigma = local_noise_features(
        torch.from_numpy(rgb),
        torch.from_numpy(packed),
        torch.from_numpy(variance),
        torch.from_numpy(colors),
        torch.from_numpy(wb),
    )
    phases = np.stack([rgb[..., y::2, x::2] for y in range(2) for x in range(2)], 2)
    mean = phases.mean(2)
    noise = np.maximum(variance, 0)
    units = np.sqrt(noise.mean(1, keepdims=True))
    unit = np.maximum(units, np.float32(16 / 65535))
    contrast = np.arcsinh(((phases - mean[:, :, None]).reshape(2, 12, 8, 12)) / unit)
    observed_base = np.stack([phases[:, int(c), p] for p, c in enumerate(colors)], 1)
    innovation = np.arcsinh((packed - observed_base) / unit)
    labels = np.zeros((2, 12, 8, 12), np.float32)
    for phase, color in enumerate(colors):
        labels[:, 3 * phase + color] = 1
    balance = np.broadcast_to(np.log(wb)[..., None, None], (2, 3, 8, 12))
    expected = np.concatenate(
        (
            contrast,
            innovation,
            np.log1p(noise / unit**2),
            labels,
            np.arcsinh(mean / unit),
            balance,
            np.log(unit * 65535),
        ),
        1,
    )
    np.testing.assert_allclose(actual.numpy(), expected, rtol=2e-6, atol=2e-6)
    np.testing.assert_array_equal(sigma.numpy(), units.repeat(2, -2).repeat(2, -1))


def test_distant_bright_content_cannot_change_local_features_or_units():
    base = torch.full((1, 3, 16, 24), 0.006)
    raw = torch.full((1, 4, 8, 12), 0.005)
    variance = torch.full_like(raw, 8e-6)
    colors = color_indices("RGGB")
    before, sigma = local_noise_features(base, raw, variance, colors)
    changed = base.clone()
    changed[..., 16:] = 0.8
    new_raw, new_variance = raw.clone(), variance.clone()
    new_raw[..., 8:] = 0.7
    new_variance[..., 8:] = 0.003
    after, after_sigma = local_noise_features(changed, new_raw, new_variance, colors)
    assert torch.equal(before[..., :8], after[..., :8])
    assert torch.equal(sigma[..., :16], after_sigma[..., :16])
    old_before, old_unit = SpatialRgbResidual.features(base, raw, variance, colors)
    old_after, old_after_unit = SpatialRgbResidual.features(changed, new_raw, new_variance, colors)
    assert not torch.equal(old_before[..., :8], old_after[..., :8])
    assert not torch.equal(old_unit, old_after_unit)


def test_uniform_fields_retain_the_original_feature_coordinates():
    base = torch.full((1, 3, 16, 24), 2**-6)
    raw = torch.full((1, 4, 8, 12), 2**-5)
    variance = torch.full_like(raw, 2**-16)
    colors = color_indices("RGGB")
    local, sigma = local_noise_features(base, raw, variance, colors)
    original, old_sigma = SpatialRgbResidual.features(base, raw, variance, colors)
    torch.testing.assert_close(local, original, rtol=2e-7, atol=2e-7)
    assert torch.equal(sigma, old_sigma.expand_as(sigma))


class FrozenFixture(nn.Module):
    def forward(self, base, packed, variance, colors, wb):
        return base * 0.75


class PhaseFixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.values = nn.Parameter(torch.arange(12, dtype=torch.float32)[None, :, None, None])
        self.calls = 0

    def forward(self, features):
        self.calls += 1
        return self.values.expand(len(features), -1, *features.shape[-2:])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_native_phase_output_uses_its_cell_noise_and_preserves_zero_cells(pattern, monkeypatch):
    pytest.importorskip("einops")
    monkeypatch.setattr("demosaic.late_local_noise_matching.enable_sampler_autograd", lambda: None)
    model = LateLocalNoiseMatchingDetail()
    model.frozen = FrozenFixture()
    model.network = PhaseFixture()
    base = torch.full((1, 3, 16, 24), 0.02)
    base[:, 0, 0, 0] = -0.0
    packed = torch.full((1, 4, 8, 12), 0.01)
    variance = torch.full_like(packed, 4e-6)
    variance[..., :4] = 0
    variance[..., 8:] = 16e-6
    output, aux = model(base, packed, variance, color_indices(pattern), return_aux=True)
    expected = np.empty((1, 3, 16, 24), np.float32)
    sigma = np.repeat(np.repeat(np.sqrt(variance.numpy().mean(1)), 2, -2), 2, -1)
    for channel in range(3):
        for phase in range(4):
            y, x = divmod(phase, 2)
            expected[:, channel, y::2, x::2] = (base.numpy() * np.float32(0.75))[
                :, channel, y::2, x::2
            ] + sigma[:, y::2, x::2] * (4 * channel + phase)
    np.testing.assert_allclose(output.detach().numpy(), expected, rtol=2e-7, atol=2e-9)
    assert torch.equal(output[..., :8], base[..., :8] * 0.75)
    assert torch.equal(output[..., :8].view(torch.int32), (base[..., :8] * 0.75).view(torch.int32))
    assert aux["matching_evaluated"] and model.network.calls == 1
    output.sum().backward()
    assert model.network.values.grad is not None and torch.isfinite(model.network.values.grad).all()


def test_same_initial_tensors_as_V171_global_RNG_and_frozen_mode():
    pytest.importorskip("einops")
    before = torch.get_rng_state().clone()
    old, local = LateNonlocalResidualDetail(), LateLocalNoiseMatchingDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert all(torch.equal(v, local.state_dict()[k]) for k, v in old.state_dict().items())
    assert local.network.tail.weight.count_nonzero() == 0
    local.train()
    assert local.network.training and not local.frozen.training
    assert not any(p.requires_grad for p in local.frozen.parameters())


def test_all_zero_variance_bypasses_matching():
    pytest.importorskip("einops")
    model = LateLocalNoiseMatchingDetail()
    model.frozen = FrozenFixture()
    model.network = PhaseFixture()
    base = torch.full((1, 3, 16, 24), 0.02)
    raw = torch.zeros((1, 4, 8, 12))
    output, aux = model(base, raw, raw, color_indices("RGGB"), return_aux=True)
    assert torch.equal(output, base * 0.75)
    assert not aux["matching_evaluated"] and model.network.calls == 0
