"""Independent native phase transport, derivatives and frozen-component routing."""

import copy
import math

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import color_indices
from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail
from demosaic.late_phase_wave_readout import LatePhaseWaveReadoutDetail, PhaseWaveReadout


def example(dtype=torch.float64, peaks=2):
    rng = np.random.default_rng(18402)
    fields = rng.normal(0, 0.4, (2, 2 * peaks, 10, 8, 11))
    fields[:, :, :4] = np.arcsinh(fields[:, :, :4])
    bins = rng.integers([0, 0], [8, 11], (2, 2, peaks, 2), dtype=np.int64)
    return torch.tensor(fields.reshape(2, 20 * peaks, 8, 11), dtype=dtype), torch.tensor(bins)


def nonzero_head(dtype=torch.float64):
    head = PhaseWaveReadout().to(dtype=dtype)
    with torch.no_grad():
        head.mixing.weight.copy_(
            torch.linspace(-0.05, 0.07, head.mixing.weight.numel(), dtype=dtype).reshape_as(
                head.mixing.weight
            )
        )
        head.mixing.bias.copy_(torch.linspace(-0.02, 0.03, 12, dtype=dtype))
    return head


def numpy_readout(head, evidence, bins):
    raw = evidence.detach().double().numpy()
    batch, channels, height, width = raw.shape
    count = channels // 10
    fields = raw.reshape(batch, count, 10, height, width)
    state = {n: v.detach().double().numpy() for n, v in head.state_dict().items()}
    output = np.zeros((batch, 3, 2 * height, 2 * width))
    for n in range(batch):
        for k in range(count):
            context = fields[n, k, 4:]
            hidden = np.einsum("oc,chw->ohw", state["context.weight"][:, :, 0, 0], context)
            hidden += state["context.bias"][:, None, None]
            hidden = hidden / (1 + np.exp(-hidden))
            mixing = np.einsum("oc,chw->ohw", state["mixing.weight"][:, :, 0, 0], hidden)
            mixing += state["mixing.bias"][:, None, None]
            mixing = mixing.reshape(3, 4, height, width)
            wave = np.sinh(fields[n, k, :4])
            a, b = wave[0] + 1j * wave[1], wave[2] + 1j * wave[3]
            z = (mixing[:, 0] + 1j * mixing[:, 1]) * a
            z += (mixing[:, 2] + 1j * mixing[:, 3]) * b
            by, bx = bins.numpy().reshape(batch, count, 2)[n, k]
            fy, fx = np.fft.fftfreq(height)[by] / 2, np.fft.fftfreq(width)[bx] / 2
            for dy in range(2):
                for dx in range(2):
                    output[n, :, dy::2, dx::2] += (
                        z * np.exp(2j * np.pi * (fy * dy + fx * dx))
                    ).real / count
    return output


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("peaks", [1, 2, 4, 8])
def test_all_native_pixels_match_independent_numpy(dtype, peaks):
    head = nonzero_head(dtype)
    evidence, bins = example(dtype, peaks)
    actual = head(evidence, bins).detach().double().numpy()
    expected = numpy_readout(head, evidence, bins)
    tol = 8e-8 if dtype == torch.float32 else 2e-15
    np.testing.assert_allclose(actual, expected, rtol=tol, atol=tol)


@pytest.mark.parametrize("bin_yx", [[2, 3], [6, 8], [4, 0], [0, 5]])
def test_known_wave_reconstructs_all_native_subpixels(bin_yx):
    height, width = 8, 11
    head = PhaseWaveReadout().double()
    with torch.no_grad():
        head.mixing.bias.reshape(3, 4)[:, 0] = 1
    fy = np.fft.fftfreq(height)[bin_yx[0]] / 2
    fx = np.fft.fftfreq(width)[bin_yx[1]] / 2
    yy, xx = np.indices((height, width))
    z = np.exp(2j * np.pi * (fy * 2 * yy + fx * 2 * xx) + 0.7j)
    evidence = np.zeros((1, 2, 10, height, width))
    evidence[0, :, 0] = np.arcsinh(z.real)
    evidence[0, :, 1] = np.arcsinh(z.imag)
    bins = torch.tensor([[bin_yx, bin_yx]]).reshape(1, 2, 1, 2)
    actual = head(torch.tensor(evidence.reshape(1, 20, height, width)), bins)
    y, x = np.indices((2 * height, 2 * width))
    expected = np.cos(2 * np.pi * (fy * y + fx * x) + 0.7)
    np.testing.assert_allclose(
        actual.detach().numpy(), np.broadcast_to(expected, actual.shape), atol=7e-15
    )


def test_initialization_has_zero_output_and_expected_first_step_gradient():
    evidence, bins = example()
    head = PhaseWaveReadout().double()
    actual = head(evidence, bins)
    assert actual.count_nonzero() == 0
    with torch.random.fork_rng():
        torch.manual_seed(18403)
        objective = (actual * torch.randn_like(actual)).sum()
    objective.backward()
    for name, p in head.named_parameters():
        assert p.grad is not None and torch.isfinite(p.grad).all()
        assert bool(p.grad.count_nonzero()) == name.startswith("mixing.")
    assert sum(p.numel() for p in head.parameters()) == 316


def test_zero_waves_have_no_rgb_bias_after_learning():
    evidence, bins = example()
    evidence.reshape(2, 4, 10, 8, 11)[:, :, :4] = 0
    assert nonzero_head()(evidence, bins).count_nonzero() == 0


def test_shared_head_is_invariant_to_rank_and_direction_permutation():
    evidence, bins = example()
    head = nonzero_head()
    order = torch.tensor([3, 1, 0, 2])
    changed = evidence.reshape(2, 4, 10, 8, 11)[:, order].reshape_as(evidence)
    changed_bins = bins.reshape(2, 4, 2)[:, order].reshape_as(bins)
    torch.testing.assert_close(
        head(changed, changed_bins), head(evidence, bins), rtol=1e-14, atol=1e-16
    )


@pytest.mark.parametrize(
    "name,index",
    [("context.weight", 7), ("context.bias", 3), ("mixing.weight", 59), ("mixing.bias", 5)],
)
def test_parameter_derivative_matches_independent_finite_difference(name, index):
    evidence, bins = example()
    head = nonzero_head()
    direction = torch.linspace(-0.3, 0.7, 2 * 3 * 16 * 22).reshape(2, 3, 16, 22).double()
    (head(evidence, bins) * direction).sum().backward()
    p = dict(head.named_parameters())[name]
    actual = float(p.grad.flatten()[index])
    original = float(p.detach().flatten()[index])
    values = []
    for delta in [-1e-5, 1e-5]:
        with torch.no_grad():
            p.flatten()[index] = original + delta
        values.append(float((numpy_readout(head, evidence, bins) * direction.numpy()).sum()))
    assert actual == pytest.approx((values[1] - values[0]) / 2e-5, rel=2e-7, abs=2e-9)


class FrozenFixture(nn.Module):
    def forward(self, base, *args):
        return base * 0.9 + 0.001


class NetworkFixture(nn.Module):
    def forward(self, x):
        return x[:, :12] * 0.02


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_wrapper_preserves_inherited_output_and_routes_local_adc_exactly(pattern):
    old = LateLocalPhaseEvidenceMatchingDetail(evidence_window=9, evidence_stride=8)
    new = LatePhaseWaveReadoutDetail(evidence_window=9, evidence_stride=8)
    new.initialize_from_evidence(old.state_dict())
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    rng = np.random.default_rng(18404)
    base = torch.tensor(rng.uniform(0.001, 0.02, (1, 3, 16, 22)), dtype=torch.float32)
    raw = torch.tensor(rng.uniform(0.001, 0.02, (1, 4, 8, 11)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    colors = color_indices(pattern)
    with torch.no_grad():
        expected = old(base, raw, variance, colors)
        actual, aux = new(base, raw, variance, colors, return_aux=True)
    assert torch.equal(actual, expected) and torch.equal(aux["inherited_output"], expected)
    with torch.no_grad():
        new.wave_readout.mixing.bias.fill_(0.1)
    trained, aux = new(base, raw, variance, colors, return_aux=True)
    adc = aux["sigma"].expand_as(trained) == 0
    assert torch.equal(trained[adc], expected[adc])
    assert aux["wave_correction"][adc].count_nonzero() == 0
    assert not torch.equal(trained[~adc], expected[~adc])
    trained.square().mean().backward()
    assert all(p.grad is None for p in new.phase_evidence_in.parameters())
    assert any(p.grad is not None and p.grad.count_nonzero() for p in new.wave_readout.parameters())


def test_wrapper_freezes_all_inherited_tensors_and_keeps_eval_modes():
    module = LatePhaseWaveReadoutDetail()
    module.train()
    assert not module.frozen.training and not module.network.training
    assert not module.phase_evidence_in.training and module.wave_readout.training
    assert {n for n, p in module.named_parameters() if p.requires_grad} == {
        "wave_readout.context.weight",
        "wave_readout.context.bias",
        "wave_readout.mixing.weight",
        "wave_readout.mixing.bias",
    }
    before = copy.deepcopy(module.state_dict())
    with pytest.raises(ValueError, match="exactly"):
        module.initialize_from_evidence({})
    assert all(torch.equal(v, module.state_dict()[k]) for k, v in before.items())


def test_constructor_does_not_change_global_cpu_rng():
    before = torch.get_rng_state().clone()
    PhaseWaveReadout()
    LatePhaseWaveReadoutDetail()
    assert torch.equal(before, torch.get_rng_state())


@pytest.mark.parametrize(
    "change", ["channels", "dtype", "nan", "bins_shape", "bins_dtype", "bins_range"]
)
def test_invalid_evidence_is_rejected(change):
    evidence, bins = example()
    if change == "channels":
        evidence = evidence[:, :21]
    if change == "dtype":
        evidence = evidence.long()
    if change == "nan":
        evidence[0, 0, 0, 0] = math.nan
    if change == "bins_shape":
        bins = bins[:, 0]
    if change == "bins_dtype":
        bins = bins.float()
    if change == "bins_range":
        bins[0, 0, 0, 0] = 8
    with pytest.raises(ValueError):
        PhaseWaveReadout().double()(evidence, bins)
