"""New measurement math, trained-anchor embedding and isolated head gradients."""

import numpy as np
import pytest
import torch
from innovation_frequency_selection import pooled_score, select_pooled
from test_late_local_phase_evidence_matching import fixture

from demosaic.cfa import color_indices, mosaic
from demosaic.late_innovation_wave import LateInnovationWaveDetail, innovation_phase_bins
from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail, pooled_phase_bins


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("lower", [1 / 64, 1 / 16])
def test_selector_against_independent_numpy_and_old_band(pattern, dtype, lower):
    raw, variance, colors = fixture(pattern, dtype)
    bins, valid, aux = innovation_phase_bins(raw, variance, colors, peaks=2, lower=lower)
    c = colors[None].numpy() if colors.ndim == 1 else colors.numpy()
    score = pooled_score(raw.double().numpy(), variance.double().numpy(), c)
    expected = select_pooled(score, lower, count=4)
    rank = bins[0].transpose(0, 1).reshape(-1, 2).numpy().tolist()
    assert rank == expected["bins_yx_rank_order"] and valid.all()
    values = aux["pooled_score"][0].T.flatten().numpy()
    tol = 3e-6 if dtype == torch.float32 else 2e-10
    np.testing.assert_allclose(values, expected["nominal_scores"], rtol=tol, atol=tol)
    if lower == 1 / 16:
        old, ov, oa = pooled_phase_bins(raw, variance, colors, peaks=2)
        assert torch.equal(bins, old) and torch.equal(valid, ov)
        assert all(torch.equal(aux[k], oa[k]) for k in aux)


@pytest.mark.parametrize("measurement", ["RAW", "innovation"])
@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_trained_anchor_zero_embedding_gradients_and_ADC(measurement, pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture

    config = {
        "evidence_window": 9,
        "evidence_stride": 8,
        "support_windows": (7, 3),
        "support_stride": 4,
    }
    old = LatePooledPhaseWaveDetail(**config)
    with torch.no_grad():
        old.wave_readout.mixing.bias.fill_(0.13)
        old.wave_readout.mixing.weight.fill_(0.003)
    new = LateInnovationWaveDetail(measurement=measurement, **config)
    new.initialize_anchor(old.state_dict())
    assert len(new.state_dict()) == 197
    assert sum(p.numel() for p in new.parameters() if p.requires_grad) == 508
    assert all(
        n.startswith("innovation_readout.") for n, p in new.named_parameters() if p.requires_grad
    )
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    rng = np.random.default_rng(19701)
    base = torch.tensor(rng.uniform(0.001, 0.02, (1, 3, 16, 22)), dtype=torch.float32)
    raw = torch.tensor(rng.uniform(0.001, 0.02, (1, 4, 8, 11)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    colors = color_indices(pattern)
    old.eval()
    expected = old(base, raw, variance, colors)
    new.train()
    actual, aux = new(base, raw, variance, colors, return_aux=True)
    assert torch.equal(expected.view(torch.int32), actual.view(torch.int32))
    expected_field = raw if measurement == "RAW" else raw - mosaic(expected, colors)
    assert torch.equal(aux["measurement_field"], expected_field)
    assert (
        not new.wave_readout.training
        and new.innovation_readout.training
        and not new.network.training
        and not new.frozen.training
    )
    (actual - base).square().mean().backward()
    assert any(
        p.grad is not None and bool(p.grad.count_nonzero())
        for p in new.innovation_readout.parameters()
    )
    assert all(
        p.grad is None for n, p in new.named_parameters() if not n.startswith("innovation_readout.")
    )
    with torch.no_grad():
        new.innovation_readout.mixing.bias.fill_(0.17)
    trained, aux = new(base, raw, variance, colors, return_aux=True)
    adc = (aux["sigma"] == 0).expand_as(trained)
    assert torch.equal(trained[adc], expected[adc])
    assert not torch.equal(trained[~adc], expected[~adc])
    all_ADC, aux = new(base, raw, variance * 0, colors, return_aux=True)
    assert aux["wave_selection"] is aux["wave_evidence_features"] is aux["wave_support"] is None
    assert torch.equal(all_ADC, old(base, raw, variance * 0, colors))


def test_fresh_state_RNG_strict_anchor_and_invalid_configuration():
    before = torch.get_rng_state().clone()
    module = LateInnovationWaveDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert len(module.state_dict()) == 197
    with pytest.raises(ValueError):
        module.initialize_anchor({})
    for config in [
        {"measurement": "GT"},
        {"lower": 0},
        {"lower": float("nan")},
        {"lower": 0.5},
    ]:
        with pytest.raises(ValueError):
            LateInnovationWaveDetail(**config)
    raw, variance, colors = fixture()
    for config in [{"lower": 0}, {"lower": 0.5}, {"peaks": 0}]:
        with pytest.raises(ValueError):
            innovation_phase_bins(raw, variance, colors, **config)
