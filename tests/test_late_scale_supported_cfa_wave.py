"""Nested initialization, independent native synthesis and isolated support learning."""

import numpy as np
import pytest
import torch
from readout_gate_interventions import native_basis, synthesize

from demosaic.cfa import color_indices, mosaic
from demosaic.late_cfa_innovation_wave import CFAInnovationWaveReadout, LateCFAInnovationWaveDetail
from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail
from demosaic.late_scale_supported_cfa_wave import (
    LateScaleSupportedCFAWaveDetail,
    ScaleSupportedCFAReadout,
)


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_readout_matches_independent_native_synthesis_with_active_support_weights(dtype):
    rng = np.random.default_rng(20011)
    context = torch.tensor(rng.normal(size=(2, 4, 36, 9, 14)), dtype=dtype)
    waves = torch.tensor(rng.normal(scale=0.003, size=(2, 4, 3, 2, 9, 14)), dtype=dtype)
    bins = torch.tensor([[[[1, 2], [2, 12]], [[3, 1], [1, 11]]]] * 2)
    head = ScaleSupportedCFAReadout().to(dtype)
    with torch.no_grad():
        head.context.weight[:, 24:].copy_(
            torch.tensor(rng.normal(scale=0.1, size=head.context.weight[:, 24:].shape), dtype=dtype)
        )
        head.gates.weight.copy_(
            torch.tensor(rng.normal(scale=0.1, size=head.gates.weight.shape), dtype=dtype)
        )
        head.gates.bias.copy_(torch.tensor([0.2, -0.1, 0.3], dtype=dtype))
        gate = head.gates(torch.nn.functional.silu(head.context(context.flatten(0, 1))))
        gate = gate.tanh().reshape(2, 4, 3, 9, 14)
        actual = head(context, waves, bins)
    expected = synthesize(native_basis(waves.numpy(), bins.numpy()), gate.numpy())
    np.testing.assert_allclose(actual.numpy(), expected, rtol=2e-5, atol=3e-9)
    # No physical wave in a color means no output in that color, whatever its context.
    waves[:, :, [0, 2]] = 0
    assert head(context, waves, bins)[:, [0, 2]].count_nonzero() == 0


def test_nested_initialization_rng_and_strict_states():
    before = torch.get_rng_state().clone()
    old, head = CFAInnovationWaveReadout(), ScaleSupportedCFAReadout()
    module = LateScaleSupportedCFAWaveDetail()
    assert torch.equal(before, torch.get_rng_state())
    assert torch.equal(old.context.weight, head.context.weight[:, :24])
    assert torch.equal(old.context.bias, head.context.bias)
    assert head.context.weight[:, 24:].count_nonzero() == 0
    assert head.gates.weight.count_nonzero() == head.gates.bias.count_nonzero() == 0
    assert len(module.state_dict()) == 197
    assert len([p for p in module.parameters() if p.requires_grad]) == 4
    assert sum(p.numel() for p in module.parameters() if p.requires_grad) == 643
    clone = LateScaleSupportedCFAWaveDetail()
    clone.load_state_dict(module.state_dict(), strict=True)
    with pytest.raises(ValueError):
        module.initialize_anchor({})
    with pytest.raises(ValueError):
        LateScaleSupportedCFAWaveDetail(evidence_window=17, support_windows=(33, 9))


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_anchor_ADC_old_measurements_and_isolated_extra_column_learning(pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture

    config = {
        "evidence_window": 9,
        "evidence_stride": 8,
        "support_windows": (7, 3),
        "support_stride": 4,
    }
    anchor = LatePooledPhaseWaveDetail(**config)
    old = LateCFAInnovationWaveDetail(**config).initialize_anchor(anchor.state_dict())
    new = LateScaleSupportedCFAWaveDetail(**config).initialize_anchor(anchor.state_dict())
    for m in (anchor, old, new):
        m.frozen, m.network = FrozenFixture(), NetworkFixture()
        m.train()
    rng = np.random.default_rng(20012)
    raw = torch.tensor(rng.normal(0.02, 0.003, (1, 4, 12, 17)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    base = torch.tensor(rng.normal(0.02, 0.003, (1, 3, 24, 34)), dtype=torch.float32)
    colors = color_indices(pattern)
    with torch.no_grad():
        expected, old_aux = old(base, raw, variance, colors, return_aux=True)
        actual, aux = new(base, raw, variance, colors, return_aux=True)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
    assert torch.equal(aux["measurement_field"], raw - mosaic(expected, colors))
    assert torch.equal(aux["cfa_waves"], old_aux["cfa_waves"])
    assert torch.equal(aux["cfa_context"][:, :, :24], old_aux["cfa_context"])
    assert (aux["cfa_context"][:, :, 24:].abs() <= 1 + 1e-6).all()
    assert not aux["cfa_context"].requires_grad and not aux["cfa_waves"].requires_grad
    optimizer = torch.optim.AdamW(new.cfa_readout.parameters(), lr=0.01)
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        output = new(base, raw, variance, colors)
        (output - base - 0.001).square().mean().backward()
        assert all(
            p.grad is None for n, p in new.named_parameters() if not n.startswith("cfa_readout.")
        )
        optimizer.step()
    assert new.cfa_readout.context.weight.grad[:, 24:].count_nonzero() > 0
    assert new.cfa_readout.context.weight[:, 24:].count_nonzero() > 0
    learned = new(base, raw, variance, colors)
    adc = (aux["sigma"] == 0).expand_as(learned)
    assert torch.equal(learned[adc], expected[adc])
    zero, zero_aux = new(base, raw, variance * 0, colors, return_aux=True)
    assert torch.equal(zero, anchor(base, raw, variance * 0, colors))
    assert (
        zero_aux["scale_support"] is zero_aux["cfa_context"] is zero_aux["wave_selection"] is None
    )
    assert not new.frozen.training and new.cfa_readout.training


def test_readout_rejects_incompatible_context_and_physical_waves():
    head = ScaleSupportedCFAReadout()
    context, waves = torch.zeros(1, 2, 36, 8, 11), torch.zeros(1, 2, 3, 2, 8, 11)
    bins = torch.tensor([[[[2, 3]], [[3, 4]]]])
    with pytest.raises(ValueError):
        head(context[:, :, :24], waves, bins)
    with pytest.raises(ValueError):
        head(context, waves[:, :, :, :, :, :10], bins)
    with pytest.raises(ValueError):
        head(context, waves, bins.float())
