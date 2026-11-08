"""Small fixed-bin context versus independent NumPy and inherited-wave algebra."""

import math

import numpy as np
import pytest
import torch
from test_late_local_phase_evidence_matching import fixture, independent_maps

from demosaic.cfa import color_indices
from demosaic.late_local_phase_evidence_matching import local_phase_evidence_maps
from demosaic.late_phase_wave_readout import PhaseWaveReadout
from demosaic.late_spatial_context_wave import (
    LateSpatialContextWaveDetail,
    SpatialContextWaveReadout,
    fixed_bin_support_context,
)


def selections_for(bins, colors, height, width):
    greens = np.flatnonzero(colors.numpy() == 1)
    result = []
    for direction, (a, b) in enumerate([greens, greens[::-1]]):
        result.append(
            {
                "selection_phase": int(a),
                "other_phase": int(b),
                "peaks": [
                    {
                        "bin_yx": [int(y), int(x)],
                        "principal_native_fxy": [
                            float(np.fft.fftfreq(width)[x] / 2),
                            float(np.fft.fftfreq(height)[y] / 2),
                        ],
                    }
                    for y, x in bins[0, direction].tolist()
                ],
            }
        )
    return result


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_both_small_context_scales_match_independent_numpy(pattern, dtype):
    raw, variance, colors = fixture(pattern, dtype)
    _, old = local_phase_evidence_maps(raw, variance, colors, peaks=2, window=9, stride=8)
    actual, aux = fixed_bin_support_context(
        raw, variance, colors, old["bin_yx"], old["valid"], windows=(9, 5), stride=4
    )
    selections = selections_for(old["bin_yx"], colors, *raw.shape[-2:])
    expected = []
    powers = []
    for window in [9, 5]:
        maps, power, _ = independent_maps(
            raw, variance, colors, peaks=2, window=window, stride=4, selections=selections
        )
        expected.append(maps.reshape(1, 4, 10, *raw.shape[-2:])[:, :, 4:])
        powers.append(power)
    expected = np.concatenate(expected, axis=2)
    tol = 3e-6 if dtype == torch.float32 else 3e-10
    np.testing.assert_allclose(actual.numpy(), expected, rtol=tol, atol=tol)
    np.testing.assert_allclose(
        aux["center_power"].numpy(), np.stack(powers, axis=1), rtol=3e-10, atol=3e-10
    )
    assert torch.equal(aux["bin_yx"], old["bin_yx"]) and torch.equal(aux["valid"], old["valid"])
    assert aux["boxes_xywh"].shape[0] == 2 and not actual.requires_grad


def test_fixed_bin_function_never_selects_or_calls_fft2(monkeypatch):
    raw, variance, colors = fixture()
    bins = torch.tensor([[[[3, 5]], [[5, 7]]]])
    valid = torch.ones((1, 2, 1), dtype=torch.bool)

    def forbidden(*args, **kwargs):
        raise AssertionError("No selection/FFT2 in fixed-bin measurement")

    monkeypatch.setattr(torch.fft, "fft2", forbidden)
    context, _ = fixed_bin_support_context(
        raw, variance, colors, bins, valid, windows=(9, 5), stride=4
    )
    assert torch.isfinite(context).all()


def test_smaller_support_does_not_see_a_distant_step_at_a_fixed_bin():
    raw = torch.full((1, 4, 64, 64), 0.02, dtype=torch.float64)
    raw[..., 40:] += 0.001
    variance = torch.full_like(raw, 2e-6)
    colors = color_indices("RGGB")
    bins = torch.tensor([[[[0, 8]], [[0, 8]]]])
    valid = torch.ones((1, 2, 1), dtype=torch.bool)
    small, _ = fixed_bin_support_context(
        raw, variance, colors, bins, valid, windows=(33, 17), stride=8
    )
    wide, _ = fixed_bin_support_context(
        raw, variance, colors, bins, valid, windows=(65, 63), stride=8
    )
    assert small[0, :, 0, 32, 16].abs().max() < 1e-20
    assert small[0, :, 6, 32, 16].abs().max() < 1e-20
    assert wide[0, :, 0, 32, 16].min() > 0.01


def test_constant_phases_invalid_peaks_and_noise_rescaling():
    raw, variance, colors = fixture()
    _, old = local_phase_evidence_maps(raw, variance, colors, peaks=2)
    args = (colors, old["bin_yx"], old["valid"])
    original, _ = fixed_bin_support_context(raw, variance, *args, windows=(9, 5), stride=4)
    scaled, _ = fixed_bin_support_context(raw * 2, variance * 4, *args, windows=(9, 5), stride=4)
    torch.testing.assert_close(original, scaled, rtol=2e-12, atol=2e-12)
    constants = (
        torch.arange(4, dtype=torch.float64)[None, :, None, None].expand_as(raw).clone() / 128
    )
    blank, _ = fixed_bin_support_context(constants, variance, *args, windows=(9, 5), stride=4)
    invalid, _ = fixed_bin_support_context(
        raw,
        variance,
        colors,
        old["bin_yx"],
        torch.zeros_like(old["valid"]),
        windows=(9, 5),
        stride=4,
    )
    assert blank.count_nonzero() == invalid.count_nonzero() == 0


def head_example(dtype=torch.float64):
    rng = np.random.default_rng(18502)
    evidence = torch.tensor(rng.normal(0, 0.3, (2, 40, 8, 11)), dtype=dtype)
    support = torch.tensor(rng.normal(0, 0.4, (2, 4, 12, 8, 11)), dtype=dtype)
    bins = torch.tensor(rng.integers([0, 0], [8, 11], (2, 2, 2, 2)), dtype=torch.int64)
    return evidence, bins, support


def nonzero_head(dtype=torch.float64):
    head = SpatialContextWaveReadout().to(dtype=dtype)
    with torch.no_grad():
        head.context.weight.copy_(
            torch.linspace(-0.09, 0.07, head.context.weight.numel(), dtype=dtype).reshape_as(
                head.context.weight
            )
        )
        head.mixing.weight.copy_(
            torch.linspace(-0.05, 0.07, head.mixing.weight.numel(), dtype=dtype).reshape_as(
                head.mixing.weight
            )
        )
        head.mixing.bias.copy_(torch.linspace(-0.02, 0.03, 12, dtype=dtype))
    return head


def numpy_readout(head, evidence, bins, support):
    raw = evidence.detach().double().numpy()
    extra = support.detach().double().numpy()
    batch, channels, height, width = raw.shape
    count = channels // 10
    fields = raw.reshape(batch, count, 10, height, width)
    state = {n: p.detach().double().numpy() for n, p in head.state_dict().items()}
    output = np.zeros((batch, 3, height * 2, width * 2))
    for n in range(batch):
        for k in range(count):
            context = np.concatenate((fields[n, k, 4:], extra[n, k]))
            hidden = (
                np.einsum("oc,chw->ohw", state["context.weight"][:, :, 0, 0], context)
                + state["context.bias"][:, None, None]
            )
            hidden = hidden / (1 + np.exp(-hidden))
            weights = (
                np.einsum("oc,chw->ohw", state["mixing.weight"][:, :, 0, 0], hidden)
                + state["mixing.bias"][:, None, None]
            )
            weights = weights.reshape(3, 4, height, width)
            wave = np.sinh(fields[n, k, :4])
            a, b = wave[0] + 1j * wave[1], wave[2] + 1j * wave[3]
            z = (weights[:, 0] + 1j * weights[:, 1]) * a + (weights[:, 2] + 1j * weights[:, 3]) * b
            y, x = bins.numpy().reshape(batch, count, 2)[n, k]
            fy, fx = np.fft.fftfreq(height)[y] / 2, np.fft.fftfreq(width)[x] / 2
            for dy in range(2):
                for dx in range(2):
                    output[n, :, dy::2, dx::2] += (
                        z * np.exp(2j * np.pi * (fy * dy + fx * dx))
                    ).real / count
    return output


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_readout_all_native_pixels_match_numpy(dtype):
    args = head_example(dtype)
    head = nonzero_head(dtype)
    np.testing.assert_allclose(
        head(*args).detach().numpy(),
        numpy_readout(head, *args),
        rtol=2e-6 if dtype == torch.float32 else 3e-14,
        atol=2e-8 if dtype == torch.float32 else 2e-16,
    )


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_zero_extended_context_preserves_old_nonzero_readout(dtype):
    old = PhaseWaveReadout().to(dtype=dtype)
    new = SpatialContextWaveReadout().to(dtype=dtype)
    with torch.no_grad():
        old.mixing.weight.fill_(0.03)
        old.mixing.bias.fill_(0.01)
        new.mixing.load_state_dict(old.mixing.state_dict())
    assert torch.equal(old.context.weight, new.context.weight[:, :6])
    assert (
        torch.equal(old.context.bias, new.context.bias)
        and new.context.weight[:, 6:].count_nonzero() == 0
    )
    evidence, bins, support = head_example(dtype)
    torch.testing.assert_close(
        new(evidence, bins, support),
        old(evidence, bins),
        rtol=2e-6 if dtype == torch.float32 else 1e-14,
        atol=1e-8 if dtype == torch.float32 else 1e-16,
    )


@pytest.mark.parametrize(
    "name,index",
    [
        ("context.weight", 7),
        ("context.weight", 12),
        ("context.weight", 17),
        ("context.bias", 3),
        ("mixing.weight", 59),
        ("mixing.bias", 5),
    ],
)
def test_parameter_derivatives_through_both_new_scales(name, index):
    args = head_example()
    head = nonzero_head()
    direction = torch.linspace(-0.3, 0.7, 2 * 3 * 16 * 22).reshape(2, 3, 16, 22).double()
    (head(*args) * direction).sum().backward()
    p = dict(head.named_parameters())[name]
    actual = float(p.grad.flatten()[index])
    saved = float(p.detach().flatten()[index])
    values = []
    for delta in [-1e-5, 1e-5]:
        with torch.no_grad():
            p.flatten()[index] = saved + delta
        values.append(float((numpy_readout(head, *args) * direction.numpy()).sum()))
    assert actual == pytest.approx((values[1] - values[0]) / 2e-5, rel=3e-7, abs=3e-9)


def test_initialization_count_rng_freezing_and_first_gradient():
    before = torch.get_rng_state().clone()
    module = LateSpatialContextWaveDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert sum(p.numel() for p in module.parameters() if p.requires_grad) == 508
    assert len(module.state_dict()) == 193
    assert {n for n, p in module.named_parameters() if p.requires_grad} == {
        "wave_readout." + n for n, _ in module.wave_readout.named_parameters()
    }
    module.train()
    assert (
        not module.frozen.training
        and not module.network.training
        and not module.phase_evidence_in.training
    )
    args = head_example(torch.float32)
    output = module.wave_readout(*args)
    assert output.count_nonzero() == 0
    with torch.random.fork_rng():
        torch.manual_seed(18503)
        (output * torch.randn_like(output)).sum().backward()
    for name, p in module.wave_readout.named_parameters():
        assert p.grad is not None and torch.isfinite(p.grad).all()
        assert bool(p.grad.count_nonzero()) == name.startswith("mixing.")


@pytest.mark.parametrize(
    "change",
    [
        "raw_shape",
        "variance_dtype",
        "nan",
        "bins_shape",
        "bins_dtype",
        "bins_range",
        "valid_dtype",
        "windows",
        "stride",
        "colors",
    ],
)
def test_invalid_context_inputs_are_rejected(change):
    raw, variance, colors = fixture()
    bins = torch.tensor([[[[3, 5]], [[5, 7]]]])
    valid = torch.ones((1, 2, 1), dtype=torch.bool)
    windows = (9, 5)
    stride = 4
    if change == "raw_shape":
        raw = raw[:, :3]
    if change == "variance_dtype":
        variance = variance.float()
    if change == "nan":
        raw[0, 0, 0, 0] = math.nan
    if change == "bins_shape":
        bins = bins[:, 0]
    if change == "bins_dtype":
        bins = bins.float()
    if change == "bins_range":
        bins[0, 0, 0, 0] = raw.shape[-2]
    if change == "valid_dtype":
        valid = valid.long()
    if change == "windows":
        windows = (9, 9)
    if change == "stride":
        stride = 0
    if change == "colors":
        colors = torch.tensor([0, 0, 2, 2])
    with pytest.raises(ValueError):
        fixed_bin_support_context(
            raw, variance, colors, bins, valid, windows=windows, stride=stride
        )


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_wrapper_mixed_adc_and_frozen_routing(pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture

    from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail

    old = LateLocalPhaseEvidenceMatchingDetail(evidence_window=9, evidence_stride=8)
    new = LateSpatialContextWaveDetail(
        evidence_window=9, evidence_stride=8, support_windows=(7, 3), support_stride=4
    )
    new.initialize_from_evidence(old.state_dict())
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    rng = np.random.default_rng(18504)
    base = torch.tensor(rng.uniform(0.001, 0.02, (1, 3, 16, 22)), dtype=torch.float32)
    raw = torch.tensor(rng.uniform(0.001, 0.02, (1, 4, 8, 11)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    colors = color_indices(pattern)
    with torch.no_grad():
        expected = old(base, raw, variance, colors)
        initial, aux = new(base, raw, variance, colors, return_aux=True)
        assert torch.equal(initial.view(torch.int32), expected.view(torch.int32))
        assert aux["wave_support_context"].shape == (1, 8, 12, 8, 11)
        new.wave_readout.mixing.bias.fill_(0.1)
    actual, aux = new(base, raw, variance, colors, return_aux=True)
    adc = (aux["sigma"] == 0).expand_as(actual)
    assert torch.equal(actual[adc], expected[adc]) and not torch.equal(actual[~adc], expected[~adc])
    actual.square().mean().backward()
    assert all(p.grad is None for p in new.phase_evidence_in.parameters())
    assert any(p.grad is not None and p.grad.count_nonzero() for p in new.wave_readout.parameters())
    with torch.no_grad():
        actual, aux = new(base, raw, variance * 0, colors, return_aux=True)
    assert aux["wave_support"] is aux["wave_support_context"] is None
    assert not aux["matching_evaluated"] and torch.equal(actual, new.frozen(base))


def independent_support(raw, variance, colors, bins, *, windows, stride):
    batches, powers = [], []
    for n in range(len(raw)):
        layout = colors if colors.ndim == 1 else colors[n]
        selections = selections_for(bins[n : n + 1], layout, *raw.shape[-2:])
        scales, center_powers = [], []
        for window in windows:
            maps, power, _ = independent_maps(
                raw[n : n + 1],
                variance[n : n + 1],
                layout,
                peaks=bins.shape[2],
                window=window,
                stride=stride,
                selections=selections,
            )
            scales.append(
                maps.reshape(1, bins.shape[1] * bins.shape[2], 10, *raw.shape[-2:])[:, :, 4:]
            )
            center_powers.append(power)
        batches.append(np.concatenate(scales, axis=2))
        powers.append(np.stack(center_powers, axis=1))
    return np.concatenate(batches), np.concatenate(powers)


def test_independent_reference_handles_four_distinct_cfa_layouts_in_one_batch():
    items = [fixture(p, torch.float32) for p in ["RGGB", "BGGR", "GRBG", "GBRG"]]
    raw, variance, colors = (
        torch.cat([a[0] for a in items]),
        torch.cat([a[1] for a in items]),
        torch.stack([a[2] for a in items]),
    )
    _, old = local_phase_evidence_maps(raw, variance, colors, peaks=2, window=9, stride=8)
    actual, aux = fixed_bin_support_context(
        raw, variance, colors, old["bin_yx"], old["valid"], windows=(9, 5), stride=4
    )
    expected, powers = independent_support(
        raw, variance, colors, old["bin_yx"], windows=(9, 5), stride=4
    )
    np.testing.assert_allclose(actual.numpy(), expected, rtol=3e-6, atol=3e-6)
    np.testing.assert_allclose(aux["center_power"].numpy(), powers, rtol=3e-10, atol=3e-10)
