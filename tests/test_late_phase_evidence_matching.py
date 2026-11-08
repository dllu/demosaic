"""Independent feature coordinates,strict initialization and real gradient routing."""

import numpy as np
import pytest
import torch
from green_phase_spectrum import tapered_spectrum
from phase_frequency_holdout import describe_phase_holdout
from torch import nn

from demosaic.cfa import color_indices
from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail
from demosaic.late_phase_evidence_matching import (
    LatePhaseEvidenceMatchingDetail,
    phase_evidence_maps,
)


def fixture(pattern="RGGB", dtype=torch.float64):
    rng = np.random.default_rng(17801)
    raw = rng.normal(0.02, 0.001, (1, 4, 24, 32))
    y, x = np.indices(raw.shape[-2:])
    for phase in range(4):
        raw[0, phase] += 0.002 * np.cos(
            2 * np.pi * (5 * (2 * x + phase % 2) / 64 + 4 * (2 * y + phase // 2) / 48) + 0.3
        )
    variance = rng.uniform(1e-6, 3e-6, raw.shape)
    return (
        torch.tensor(raw, dtype=dtype),
        torch.tensor(variance, dtype=dtype),
        color_indices(pattern),
    )


def independent_maps(raw, variance, colors, count):
    raw, variance, colors = raw.numpy()[0], variance.numpy()[0], colors.numpy()
    selection = describe_phase_holdout(raw, variance, colors, count=count)
    fields = {int(i): tapered_spectrum(raw[i], variance[i]) for i in np.flatnonzero(colors == 1)}
    height, width = raw.shape[-2:]
    y, x = np.indices((height, width))
    maps = []
    for direction in selection:
        coefficients = []
        for peak in direction["peaks"]:
            ky, kx = peak["bin_yx"]
            fx, fy = peak["principal_native_fxy"]
            for key in ["selection_phase", "other_phase"]:
                p = direction[key]
                field = fields[p]
                coefficients.append(
                    field["spectrum"][ky, kx]
                    / np.sqrt(field["noise_variance"][ky, kx])
                    * np.exp(-2j * np.pi * (fy * (p // 2) + fx * (p % 2)))
                )
            a, b = coefficients[-2:]
            pa, pb = abs(a) ** 2, abs(b) ** 2
            carrier = np.exp(4j * np.pi * (fy * y + fx * x))
            wa, wb = a * carrier, b * carrier
            cross = a * np.conj(b) / np.sqrt((1 + pa) * (1 + pb))
            strength = (pa + pb) / (1 + pa + pb)
            constants = [
                np.log1p(pa),
                np.log1p(pb),
                cross.real,
                cross.imag,
                fx * strength,
                fy * strength,
            ]
            maps.extend(
                [np.arcsinh(wa.real), np.arcsinh(wa.imag), np.arcsinh(wb.real), np.arcsinh(wb.imag)]
                + [np.full((height, width), v) for v in constants]
            )
    return np.stack(maps)[None], selection


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_all_feature_channels_match_independent_numpy(pattern, dtype):
    raw, variance, colors = fixture(pattern, dtype)
    actual, aux = phase_evidence_maps(raw, variance, colors)
    expected, selections = independent_maps(raw.double(), variance.double(), colors, 4)
    tolerance = 3e-5 if dtype == torch.float32 else 3e-12
    np.testing.assert_allclose(actual.numpy(), expected, rtol=tolerance, atol=tolerance)
    assert aux["bin_yx"].tolist()[0] == [[p["bin_yx"] for p in d["peaks"]] for d in selections]
    assert aux["valid"].all()


def test_changing_measured_phase_cannot_change_selecting_phase_bins_or_power():
    raw, variance, colors = fixture()
    _, before = phase_evidence_maps(raw, variance, colors)
    changed = raw.clone()
    noise = variance.clone()
    changed[:, 2] = changed[:, 2].flip(-1) * 20
    noise[:, 2] *= 17
    _, after = phase_evidence_maps(changed, noise, colors)
    assert torch.equal(before["bin_yx"][:, 0], after["bin_yx"][:, 0])
    assert torch.equal(before["nominal_power"][:, 0, :, 0], after["nominal_power"][:, 0, :, 0])
    assert not torch.equal(before["nominal_power"][:, 0, :, 1], after["nominal_power"][:, 0, :, 1])


def test_constant_phases_zero_features_and_finite_ADC_floor():
    raw = torch.arange(4, dtype=torch.float32)[None, :, None, None].expand(1, 4, 16, 24).clone()
    features, _ = phase_evidence_maps(raw, torch.zeros_like(raw), color_indices("RGGB"))
    assert features.count_nonzero() == 0 and torch.isfinite(features).all()
    raw, _, colors = fixture(dtype=torch.float32)
    features, _ = phase_evidence_maps(raw, torch.zeros_like(raw), colors)
    assert torch.isfinite(features).all()


def test_small_axis_exhausted_peak_slots_are_zero_and_marked():
    raw = torch.arange(4, dtype=torch.float64)[None, :, None, None].expand(1, 4, 8, 8).clone()
    features, aux = phase_evidence_maps(raw, torch.ones_like(raw), color_indices("GBRG"), peaks=8)
    assert features.shape == (1, 160, 8, 8)
    assert (~aux["valid"]).any()
    for d in range(2):
        for p in range(8):
            if not aux["valid"][0, d, p]:
                assert features[0, 10 * (8 * d + p) : 10 * (8 * d + p + 1)].count_nonzero() == 0


def test_mixed_layout_batch_matches_separate_calls():
    a, va, ca = fixture("RGGB")
    b, vb, cb = fixture("GBRG")
    batch, aux = phase_evidence_maps(torch.cat([a, b]), torch.cat([va, vb]), torch.stack([ca, cb]))
    first, _ = phase_evidence_maps(a, va, ca)
    second, _ = phase_evidence_maps(b, vb, cb)
    torch.testing.assert_close(batch, torch.cat([first, second]), rtol=1e-12, atol=1e-12)
    assert aux["green_phase_indices"].tolist() == [[1, 2], [0, 3]]


class FrozenFixture(nn.Module):
    def forward(self, base, packed, variance, colors, wb):
        return base * 0.75


class MatchingFixture(nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = nn.Parameter(
            torch.arange(12 * 39, dtype=torch.float32).reshape(12, 39, 1, 1) / 1000
        )
        self.calls = 0

    def forward(self, features):
        self.calls += 1
        return torch.nn.functional.conv2d(features, self.weight)


def matched_fixtures(monkeypatch):
    pytest.importorskip("einops")
    monkeypatch.setattr("demosaic.late_local_noise_matching.enable_sampler_autograd", lambda: None)
    monkeypatch.setattr(
        "demosaic.late_phase_evidence_matching.enable_sampler_autograd", lambda: None
    )
    old, new = LateLocalNoiseMatchingDetail(), LatePhaseEvidenceMatchingDetail()
    for m in [old, new]:
        m.frozen = FrozenFixture()
        m.network = MatchingFixture()
    return old, new


def test_zero_adapter_fixture_parity_and_new_gradient_can_learn(monkeypatch):
    old, new = matched_fixtures(monkeypatch)
    raw, variance, colors = fixture(dtype=torch.float32)
    base = torch.full((1, 3, 48, 64), 0.02)
    before = old(base, raw, variance, colors)
    after, aux = new(base, raw, variance, colors, return_aux=True)
    assert torch.equal(before.view(torch.int32), after.view(torch.int32))
    assert aux["phase_evidence"] is not None and aux["matching_evaluated"]
    loss = after.square().mean()
    loss.backward()
    assert torch.isfinite(new.phase_evidence_in.weight.grad).all()
    assert new.phase_evidence_in.weight.grad.count_nonzero() > 0
    assert new.network.weight.grad.count_nonzero() > 0


def test_zero_variance_bypasses_new_features_and_matching(monkeypatch):
    _, new = matched_fixtures(monkeypatch)
    monkeypatch.setattr(
        "demosaic.late_phase_evidence_matching.phase_evidence_maps",
        lambda *a, **kw: pytest.fail("ADC invoked evidence"),
    )
    raw, _, colors = fixture(dtype=torch.float32)
    base = torch.full((1, 3, 48, 64), 0.02)
    result, aux = new(base, raw, torch.zeros_like(raw), colors, return_aux=True)
    assert torch.equal(result.view(torch.int32), (base * 0.75).view(torch.int32))
    assert (
        new.network.calls == 0 and not aux["matching_evaluated"] and aux["phase_evidence"] is None
    )


def test_mixed_noisy_ADC_cells_retain_frozen_component_after_adapter_moves(monkeypatch):
    _, new = matched_fixtures(monkeypatch)
    with torch.no_grad():
        new.phase_evidence_in.weight.fill_(0.01)
    raw, variance, colors = fixture(dtype=torch.float32)
    variance[..., :8] = 0
    base = torch.full((1, 3, 48, 64), 0.02)
    result = new(base, raw, variance, colors)
    assert torch.equal(
        result[..., :16].view(torch.int32), (base[..., :16] * 0.75).view(torch.int32)
    )
    assert not torch.equal(result[..., 16:], base[..., 16:] * 0.75)


def test_rng_frozen_mode_and_strict_baseline_initialization():
    pytest.importorskip("einops")
    before = torch.get_rng_state().clone()
    old, new = LateLocalNoiseMatchingDetail(), LatePhaseEvidenceMatchingDetail()
    assert torch.equal(before, torch.get_rng_state())
    with torch.no_grad():
        new.phase_evidence_in.weight.fill_(1)
    new.initialize_from_local_matching(old.state_dict())
    assert new.phase_evidence_in.weight.count_nonzero() == 0
    assert new.phase_evidence_in.weight.numel() == 3120
    for key, value in old.state_dict().items():
        assert torch.equal(new.state_dict()[key], value)
    new.train()
    assert not new.frozen.training and new.network.training
    assert not any(p.requires_grad for p in new.frozen.parameters())
    with pytest.raises(ValueError):
        new.initialize_from_local_matching({})


@pytest.mark.parametrize("damage", ["shape", "small", "large", "layout", "nan", "dtype", "peaks"])
def test_invalid_contract(damage):
    raw, variance, colors = fixture()
    peaks = 4
    if damage == "shape":
        raw = raw[:, :3]
    elif damage == "small":
        raw = raw[..., :7, :]
        variance = variance[..., :7, :]
    elif damage == "large":
        raw = torch.zeros((1, 4, 513, 8), dtype=raw.dtype)
        variance = raw.clone()
    elif damage == "layout":
        colors = torch.tensor([0, 0, 1, 2])
    elif damage == "nan":
        raw[0, 1, 0, 0] = torch.nan
    elif damage == "dtype":
        variance = variance.float()
    else:
        peaks = 0
    with pytest.raises(ValueError):
        phase_evidence_maps(raw, variance, colors, peaks=peaks)
