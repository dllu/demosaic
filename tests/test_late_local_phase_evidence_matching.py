"""Local matching features against independent NumPy projection/interpolation."""

import numpy as np
import pytest
import torch
from local_phase_projection import local_phase_projection
from phase_frequency_holdout import describe_phase_holdout
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import color_indices
from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail
from demosaic.late_local_phase_evidence_matching import (
    LateLocalPhaseEvidenceMatchingDetail,
    _geometry,
    _interpolate_grid,
    local_phase_evidence_maps,
    local_projection_grid,
)
from demosaic.late_phase_evidence_matching import phase_evidence_maps


def fixture(pattern="RGGB", dtype=torch.float64):
    rng = np.random.default_rng(18001)
    raw = rng.normal(0.02, 0.001, (1, 4, 24, 32))
    y, x = np.indices(raw.shape[-2:])
    for phase in range(4):
        raw[0, phase] += 0.002 * np.cos(
            2 * np.pi * (5 * (2 * x + phase % 2) / 64 + 4 * (2 * y + phase // 2) / 48) + 0.3
        )
    return (
        torch.tensor(raw, dtype=dtype),
        torch.tensor(rng.uniform(1e-6, 3e-6, raw.shape), dtype=dtype),
        color_indices(pattern),
    )


def independent_maps(raw, variance, colors, *, peaks=4, window=9, stride=8, selections=None):
    raw, variance = (
        raw.detach().cpu().double().numpy()[0],
        variance.detach().cpu().double().numpy()[0],
    )
    colors = colors.cpu().numpy()
    if selections is None:
        selections = describe_phase_holdout(raw, variance, colors, count=peaks)
    height, width = raw.shape[-2:]
    ay, ax = [np.unique([*range(0, size, stride), size - 1]) for size in [height, width]]
    centers = np.array([[y, x] for y in ay for x in ax])
    y, x = np.indices((height, width))
    output, centers_power = [], []
    for direction in selections:
        direction_power = []
        for peak in direction["peaks"]:
            coefficients, power = [], []
            fx, fy = peak["principal_native_fxy"]
            for phase in [direction["selection_phase"], direction["other_phase"]]:
                local = local_phase_projection(
                    raw[phase], variance[phase], peak["bin_yx"], window=window, centers_yx=centers
                )
                z = (
                    local["coefficient"]
                    / np.maximum(local["noise_variance"], (1 / 65535) ** 2) ** 0.5
                )
                grid = z.reshape(len(ay), len(ax))
                power.append(abs(grid) ** 2)
                horizontal = np.array(
                    [
                        np.interp(np.arange(width), ax, row.real)
                        + 1j * np.interp(np.arange(width), ax, row.imag)
                        for row in grid
                    ]
                )
                field = np.array(
                    [
                        np.interp(np.arange(height), ay, col.real)
                        + 1j * np.interp(np.arange(height), ay, col.imag)
                        for col in horizontal.T
                    ]
                ).T
                coefficients.append(
                    field * np.exp(-2j * np.pi * (fy * (phase // 2) + fx * (phase % 2)))
                )
            first, second = coefficients
            pa, pb = abs(first) ** 2, abs(second) ** 2
            cross = first * second.conj() / np.sqrt((1 + pa) * (1 + pb))
            carrier = np.exp(4j * np.pi * (fy * y + fx * x))
            wa, wb = first * carrier, second * carrier
            strength = (pa + pb) / (1 + pa + pb)
            output.extend(
                [
                    np.arcsinh(wa.real),
                    np.arcsinh(wa.imag),
                    np.arcsinh(wb.real),
                    np.arcsinh(wb.imag),
                    np.log1p(pa),
                    np.log1p(pb),
                    cross.real,
                    cross.imag,
                    fx * strength,
                    fy * strength,
                ]
            )
            direction_power.append(np.stack(power))
        centers_power.append(np.stack(direction_power))
    return np.stack(output)[None], np.stack(centers_power)[None], selections


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_all_local_channels_and_center_powers_match_independent_numpy(pattern, dtype):
    raw, variance, colors = fixture(pattern, dtype)
    actual, aux = local_phase_evidence_maps(raw, variance, colors, window=9, stride=8)
    expected, powers, selections = independent_maps(raw, variance, colors)
    tolerance = 2e-6 if dtype == torch.float32 else 2e-10
    np.testing.assert_allclose(actual.numpy(), expected, rtol=tolerance, atol=tolerance)
    np.testing.assert_allclose(aux["local_center_power"].numpy(), powers, rtol=2e-10, atol=2e-10)
    assert aux["bin_yx"].tolist()[0] == [
        [p["bin_yx"] for p in direction["peaks"]] for direction in selections
    ]


def test_torch_projection_grid_matches_numpy_with_different_batch_bins():
    rng = np.random.default_rng(18002)
    raw = rng.normal(size=(2, 2, 17, 23))
    variance = rng.uniform(0.001, 0.3, raw.shape)
    ay, ax, boxes = _geometry(17, 23, 9, 8, "cpu")
    bins = torch.tensor([[3, 5], [12, 17]])
    coefficient, noise = local_projection_grid(
        torch.tensor(raw), torch.tensor(variance), bins, boxes
    )
    centers = np.array([[y, x] for y in ay.numpy() for x in ax.numpy()])
    for batch in range(2):
        for phase in range(2):
            expected = local_phase_projection(
                raw[batch, phase],
                variance[batch, phase],
                bins[batch].numpy(),
                window=9,
                centers_yx=centers,
            )
            np.testing.assert_allclose(
                coefficient[batch, phase].numpy(), expected["coefficient"], rtol=2e-11, atol=2e-11
            )
            np.testing.assert_allclose(
                noise[batch, phase].numpy(), expected["noise_variance"], rtol=2e-11, atol=2e-11
            )


def test_interpolation_uses_actual_last_gap_and_hits_measured_centers():
    ay, ax = torch.tensor([0, 8, 15]), torch.tensor([0, 8, 16, 19])
    values = torch.arange(12, dtype=torch.float64).reshape(1, 1, 3, 4).to(torch.complex128)
    field = _interpolate_grid(values, ay, ax, 16, 20)
    torch.testing.assert_close(field[..., ay[:, None], ax[None, :]], values, rtol=0, atol=0)
    torch.testing.assert_close(
        field[0, 0, 15, 17],
        values[0, 0, 2, 2] * 2 / 3 + values[0, 0, 2, 3] / 3,
        rtol=0,
        atol=4e-15,
    )


def test_only_selecting_phase_controls_its_global_bins_and_local_coefficients():
    raw, variance, colors = fixture()
    _, before = local_phase_evidence_maps(raw, variance, colors, window=9, stride=8)
    changed, noise = raw.clone(), variance.clone()
    changed[:, 2] = changed[:, 2].flip(-1) * 20
    noise[:, 2] *= 17
    _, after = local_phase_evidence_maps(changed, noise, colors, window=9, stride=8)
    assert torch.equal(before["bin_yx"][:, 0], after["bin_yx"][:, 0])
    assert torch.equal(
        before["global_nominal_power"][:, 0, :, 0], after["global_nominal_power"][:, 0, :, 0]
    )
    assert torch.equal(
        before["local_center_power"][:, 0, :, 0], after["local_center_power"][:, 0, :, 0]
    )
    assert not torch.equal(
        before["local_center_power"][:, 0, :, 1], after["local_center_power"][:, 0, :, 1]
    )


def test_constant_and_ADC_features_are_finite_and_exhausted_slots_zero():
    raw = torch.arange(4, dtype=torch.float32)[None, :, None, None].expand(1, 4, 8, 8).clone()
    maps, aux = local_phase_evidence_maps(
        raw, torch.zeros_like(raw), color_indices("RGGB"), peaks=8
    )
    assert maps.count_nonzero() == 0 and torch.isfinite(maps).all() and (~aux["valid"]).any()
    raw, _, colors = fixture(dtype=torch.float32)
    maps, _ = local_phase_evidence_maps(raw, torch.zeros_like(raw), colors)
    assert torch.isfinite(maps).all()


def test_local_fields_vanish_far_from_noise_free_supported_input():
    y, x = torch.meshgrid(
        torch.arange(64, dtype=torch.float64), torch.arange(64, dtype=torch.float64), indexing="ij"
    )
    raw = torch.full((1, 4, 64, 64), 0.02, dtype=torch.float64)
    signal = 0.002 * torch.cos(2 * torch.pi * (8 * y / 64 + 10 * x / 64))
    raw[..., 24:48, 24:48] += signal[24:48, 24:48]
    variance = torch.full_like(raw, 1e-6)
    colors = color_indices("RGGB")
    local, _ = local_phase_evidence_maps(raw, variance, colors, peaks=1, window=9, stride=8)
    global_maps, _ = phase_evidence_maps(raw, variance, colors, peaks=1)
    assert local[..., :8, :8].abs().max() < 1e-12
    assert local[..., 24:48, 24:48].abs().max() > 0
    assert global_maps[..., :8, :8].abs().max() > 0


def test_mixed_layouts_match_separate_inputs():
    a, va, ca = fixture("RGGB")
    b, vb, cb = fixture("GBRG")
    result, _ = local_phase_evidence_maps(
        torch.cat([a, b]), torch.cat([va, vb]), torch.stack([ca, cb]), window=9, stride=8
    )
    first, _ = local_phase_evidence_maps(a, va, ca, window=9, stride=8)
    second, _ = local_phase_evidence_maps(b, vb, cb, window=9, stride=8)
    torch.testing.assert_close(result, torch.cat([first, second]), rtol=1e-12, atol=1e-12)


class Frozen(nn.Module):
    def forward(self, base, packed, variance, colors, wb):
        return base * 0.75


class Matching(nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = nn.Parameter(
            torch.arange(12 * 39, dtype=torch.float32).reshape(12, 39, 1, 1) / 1000
        )
        self.calls = 0

    def forward(self, features):
        self.calls += 1
        return F.conv2d(features, self.weight)


def matched(monkeypatch):
    monkeypatch.setattr("demosaic.late_local_noise_matching.enable_sampler_autograd", lambda: None)
    monkeypatch.setattr(
        "demosaic.late_local_phase_evidence_matching.enable_sampler_autograd", lambda: None
    )
    old, new = LateLocalNoiseMatchingDetail(), LateLocalPhaseEvidenceMatchingDetail()
    for model in [old, new]:
        model.frozen = Frozen()
        model.network = Matching()
    return old, new


def test_zero_adapter_parity_and_gradients_into_both_trainable_fixture_parts(monkeypatch):
    old, new = matched(monkeypatch)
    raw, variance, colors = fixture(dtype=torch.float32)
    base = torch.full((1, 3, 48, 64), 0.02)
    before = old(base, raw, variance, colors)
    after = new(base, raw, variance, colors)
    assert torch.equal(before.view(torch.int32), after.view(torch.int32))
    after.square().mean().backward()
    assert (
        torch.isfinite(new.phase_evidence_in.weight.grad).all()
        and new.phase_evidence_in.weight.grad.count_nonzero() > 0
    )
    assert (
        torch.isfinite(new.network.weight.grad).all()
        and new.network.weight.grad.count_nonzero() > 0
    )


def test_ADC_bypass_and_mixed_zero_cells_with_nonzero_adapter(monkeypatch):
    _, new = matched(monkeypatch)
    raw, variance, colors = fixture(dtype=torch.float32)
    base = torch.full((1, 3, 48, 64), 0.02)
    with torch.no_grad():
        new.phase_evidence_in.weight.fill_(0.01)
    result, aux = new(base, raw, torch.zeros_like(raw), colors, return_aux=True)
    assert (
        torch.equal(result, (base * 0.75))
        and new.network.calls == 0
        and aux["phase_evidence"] is None
    )
    variance[..., :8] = 0
    result = new(base, raw, variance, colors)
    assert torch.equal(result[..., :16], base[..., :16] * 0.75) and not torch.equal(
        result[..., 16:], base[..., 16:] * 0.75
    )


def test_strict_old_weights_same_parameter_budget_frozen_mode_and_RNG():
    before = torch.get_rng_state().clone()
    old, new = LateLocalNoiseMatchingDetail(), LateLocalPhaseEvidenceMatchingDetail()
    assert torch.equal(before, torch.get_rng_state())
    new.initialize_from_local_matching(old.state_dict())
    assert all(torch.equal(value, new.state_dict()[key]) for key, value in old.state_dict().items())
    assert (
        new.phase_evidence_in.weight.numel() == 3120
        and new.phase_evidence_in.weight.count_nonzero() == 0
    )
    assert sum(p.numel() for p in new.parameters() if p.requires_grad) == 2092026
    new.train()
    assert not new.frozen.training and not any(p.requires_grad for p in new.frozen.parameters())
    with pytest.raises(ValueError):
        new.initialize_from_local_matching({})


@pytest.mark.parametrize("damage", ["window", "stride", "peaks", "shape", "dtype", "layout", "nan"])
def test_invalid_inputs_reject(damage):
    raw, variance, colors = fixture()
    options = {"window": 9, "stride": 8, "peaks": 4}
    if damage == "window":
        options["window"] = 8
    elif damage == "stride":
        options["stride"] = 0
    elif damage == "peaks":
        options["peaks"] = 0
    elif damage == "shape":
        raw = raw[:, :3]
    elif damage == "dtype":
        variance = variance.float()
    elif damage == "layout":
        colors = torch.tensor([0, 0, 1, 2])
    else:
        raw[0, 0, 0, 0] = torch.nan
    with pytest.raises(ValueError):
        local_phase_evidence_maps(raw, variance, colors, **options)
