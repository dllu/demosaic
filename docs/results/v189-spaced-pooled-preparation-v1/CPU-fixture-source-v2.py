"""Pooled selection, fixed-bin waves and inherited-state routing versus NumPy."""

import numpy as np
import pytest
import torch
from green_phase_spectrum import tapered_spectrum
from spectral_selection_diversity import select_pooled
from test_late_local_phase_evidence_matching import fixture, independent_maps
from test_late_spatial_context_wave import selections_for

from demosaic.cfa import color_indices
from demosaic.late_spaced_pooled_wave import (
    LateSpacedPooledPhaseWaveDetail,
    fixed_bin_wave_maps,
    spaced_pooled_phase_bins,
)
from demosaic.late_spatial_context_wave import LateSpatialContextWaveDetail


def numpy_selection(raw, variance, colors, peaks, window=65):
    rows = []
    score_rows = []
    phase_power = []
    for image, v, layout in zip(
        raw.detach().double().numpy(),
        variance.detach().double().numpy(),
        np.broadcast_to(colors.numpy(), (len(raw), 4)),
        strict=True,
    ):
        greens = np.flatnonzero(layout == 1)
        s = [tapered_spectrum(image[g] - image[g, 0, 0], v[g]) for g in greens]
        p = np.stack(
            [abs(a["spectrum"]) ** 2 / np.maximum(a["noise_variance"], (1 / 65535) ** 2) for a in s]
        )
        mean = p.mean(0)
        score = sum(np.roll(mean, (y, x), (0, 1)) for y in [-1, 0, 1] for x in [-1, 0, 1]) / 9
        bins = select_pooled(
            score, count=2 * peaks, radius=int(np.ceil(max(score.shape) / window))
        )["bins"]
        assert len(bins) == 2 * peaks
        groups = np.asarray(bins).reshape(peaks, 2, 2).transpose(1, 0, 2)
        rows.append(groups)
        score_rows.append(np.array([[score[y, x] for y, x in group] for group in groups]))
        phase_power.append(
            np.array(
                [
                    [[p[a, y, x], p[b, y, x]] for y, x in group]
                    for (a, b), group in zip([(0, 1), (1, 0)], groups, strict=True)
                ]
            )
        )
    return np.stack(rows), np.stack(score_rows), np.stack(phase_power)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_pooled_bins_score_and_per_phase_power_match_numpy(pattern, dtype):
    raw, variance, colors = fixture(pattern, dtype)
    bins, valid, aux = spaced_pooled_phase_bins(raw, variance, colors, peaks=2, window=9)
    expected, score, powers = numpy_selection(raw, variance, colors, 2, window=9)
    np.testing.assert_array_equal(bins.numpy(), expected)
    assert valid.all()
    tol = 3e-6 if dtype == torch.float32 else 2e-10
    np.testing.assert_allclose(aux["pooled_score"].numpy(), score, rtol=tol, atol=tol)
    np.testing.assert_allclose(aux["global_nominal_power"].numpy(), powers, rtol=tol, atol=tol)
    np.testing.assert_array_equal(aux["rank"].numpy(), [[[0, 2], [1, 3]]])


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_new_selected_wave_channels_match_independent_numpy(dtype):
    raw, variance, colors = fixture("GBRG", dtype)
    bins, valid, _ = spaced_pooled_phase_bins(raw, variance, colors, peaks=2, window=9)
    actual, aux = fixed_bin_wave_maps(raw, variance, colors, bins, valid, window=9, stride=8)
    expected, power, _ = independent_maps(
        raw,
        variance,
        colors,
        peaks=2,
        window=9,
        stride=8,
        selections=selections_for(bins, colors, *raw.shape[-2:]),
    )
    tol = 3e-6 if dtype == torch.float32 else 3e-10
    np.testing.assert_allclose(actual.numpy(), expected, rtol=tol, atol=tol)
    np.testing.assert_allclose(aux["local_center_power"].numpy(), power, rtol=3e-10, atol=3e-10)


def test_pooling_is_symmetric_and_both_phases_can_change_selection():
    raw, variance, colors = fixture(dtype=torch.float64)
    green = torch.where(colors == 1)[0]
    bins, valid, aux = spaced_pooled_phase_bins(raw, variance, colors, peaks=2, window=9)
    changed = raw.clone()
    v = variance.clone()
    changed[:, green] = raw[:, green.flip(0)]
    v[:, green] = variance[:, green.flip(0)]
    other, ov, oa = spaced_pooled_phase_bins(changed, v, colors, peaks=2)
    assert (
        torch.equal(bins, other)
        and torch.equal(valid, ov)
        and torch.equal(aux["pooled_score"], oa["pooled_score"])
    )
    y, x = torch.meshgrid(torch.arange(32).double(), torch.arange(32).double(), indexing="ij")
    raw = torch.full((1, 4, 32, 32), 0.02, dtype=torch.float64)
    v = torch.full_like(raw, 1e-6)
    raw[:, green[1]] += 0.01 * torch.cos(2 * torch.pi * (3 * y + 11 * x) / 32)
    first, _, _ = spaced_pooled_phase_bins(raw, v, colors, peaks=1)
    raw[:, green[1]] = 0.02 + 0.01 * torch.cos(2 * torch.pi * (9 * y + 9 * x) / 32)
    second, _, _ = spaced_pooled_phase_bins(raw, v, colors, peaks=1)
    assert first[0, 0, 0].tolist() == [3, 11] and second[0, 0, 0].tolist() == [9, 9]


def test_constant_exhausted_invalid_slots_and_no_global_rng_change():
    raw = torch.ones((1, 4, 8, 8), dtype=torch.float64) * 0.02
    variance = torch.ones_like(raw) * 2e-6
    colors = color_indices("RGGB")
    before = torch.get_rng_state().clone()
    bins, valid, aux = spaced_pooled_phase_bins(raw, variance, colors, peaks=8)
    maps, _ = fixed_bin_wave_maps(raw, variance, colors, bins, valid, window=9, stride=4)
    assert (
        not valid.all() and maps.count_nonzero() == 0 and aux["pooled_score"].count_nonzero() == 0
    )
    module = LateSpacedPooledPhaseWaveDetail()
    old = LateSpatialContextWaveDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert (
        len(module.state_dict()) == 193
        and sum(p.numel() for p in module.parameters() if p.requires_grad) == 508
    )
    assert all(torch.equal(v, old.state_dict()[n]) for n, v in module.state_dict().items())
    module.train()
    assert (
        not module.frozen.training
        and not module.network.training
        and not module.phase_evidence_in.training
    )
    assert module.wave_readout.training


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_frozen_baseline_local_adc_and_new_context_routing(pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture

    old = LateSpatialContextWaveDetail(
        evidence_window=9, evidence_stride=8, support_windows=(7, 3), support_stride=4
    )
    new = LateSpacedPooledPhaseWaveDetail(
        evidence_window=9, evidence_stride=8, support_windows=(7, 3), support_stride=4
    )
    state = {n: v for n, v in old.state_dict().items() if not n.startswith("wave_readout.")}
    new.initialize_from_evidence(state)
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    rng = np.random.default_rng(18704)
    base = torch.tensor(rng.uniform(0.001, 0.02, (1, 3, 16, 22)), dtype=torch.float32)
    raw = torch.tensor(rng.uniform(0.001, 0.02, (1, 4, 8, 11)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    colors = color_indices(pattern)
    expected = old(base, raw, variance, colors)
    initial, aux = new(base, raw, variance, colors, return_aux=True)
    assert torch.equal(initial.view(torch.int32), expected.view(torch.int32))
    assert aux["wave_selection"] is not None and aux["wave_evidence_features"].shape == (
        1,
        80,
        8,
        11,
    )
    with torch.no_grad():
        new.wave_readout.mixing.bias.fill_(0.1)
    actual, aux = new(base, raw, variance, colors, return_aux=True)
    adc = (aux["sigma"] == 0).expand_as(actual)
    assert torch.equal(actual[adc], expected[adc]) and not torch.equal(actual[~adc], expected[~adc])
    actual.square().mean().backward()
    assert all(p.grad is None for p in new.phase_evidence_in.parameters())
    assert any(p.grad is not None and p.grad.count_nonzero() for p in new.wave_readout.parameters())
    actual, aux = new(base, raw, variance * 0, colors, return_aux=True)
    assert aux["wave_selection"] is aux["wave_evidence"] is aux["wave_support"] is None
    assert torch.equal(actual, new.frozen(base))


@pytest.mark.parametrize(
    "change", ["dtype", "shape", "nan", "colors", "peaks", "bins", "valid", "window"]
)
def test_invalid_contracts_reject(change):
    raw, variance, colors = fixture()
    bins, valid, _ = spaced_pooled_phase_bins(raw, variance, colors, peaks=2, window=9)
    if change == "dtype":
        variance = variance.float()
    if change == "shape":
        raw = raw[:, :3]
    if change == "nan":
        raw[0, 0, 0, 0] = float("nan")
    if change == "colors":
        colors = torch.tensor([0, 0, 0, 0])
    with pytest.raises(ValueError):
        if change in ["dtype", "shape", "nan", "colors", "peaks"]:
            spaced_pooled_phase_bins(raw, variance, colors, peaks=0 if change == "peaks" else 2)
        else:
            if change == "bins":
                bins[0, 0, 0, 0] = raw.shape[-2]
            if change == "valid":
                valid = valid.long()
            fixed_bin_wave_maps(
                raw, variance, colors, bins, valid, window=4 if change == "window" else 9
            )


@pytest.mark.parametrize("size", [128, 256, 384])
def test_native_suppression_radius_and_all_selected_separations(size):
    raw = torch.zeros((1, 4, size, size), dtype=torch.float32)
    variance = torch.full_like(raw, 1e-6)
    bins, valid, aux = spaced_pooled_phase_bins(raw, variance, color_indices("RGGB"))
    radius = int(np.ceil(size / 65))
    assert aux["suppression_radius"].item() == radius and valid.all()
    chosen = bins[0].reshape(-1, 2).tolist()
    for i, (y, x) in enumerate(chosen):
        for a, b in chosen[:i]:
            for cy, cx in [(a, b), ((-a) % size, (-b) % size)]:
                assert (
                    min(abs(y - cy), size - abs(y - cy)) > radius
                    or min(abs(x - cx), size - abs(x - cx)) > radius
                )


@pytest.mark.parametrize("window", [0, 4, True])
def test_invalid_spaced_selection_window_rejected(window):
    raw, var, colors = fixture()
    with pytest.raises(ValueError):
        spaced_pooled_phase_bins(raw, var, colors, window=window)
