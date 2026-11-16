import copy

import pytest
import torch
from torch import nn

from demosaic.cfa import color_indices
from demosaic.competing_phase import exclude_nearby_bins
from demosaic.experiments.artifacts import reference
from demosaic.experiments.training import initialize_model
from demosaic.models.compat import build_component
from demosaic.models.wave import legacy_state_dict, load_legacy_state_dict, readout_state_prefix


class FrozenFixture(nn.Module):
    def forward(self, base, *args):
        return base * 0.9 + 0.001


class NetworkFixture(nn.Module):
    def forward(self, value):
        return value[:, :12] * 0.02


def test_exclusion_checks_conjugates_wraparound_and_only_valid_inherited_bins():
    new = torch.tensor([[[[1, 3], [2, 4]], [[31, 29], [8, 8]]]])
    old = torch.tensor([[[[1, 2], [8, 8]], [[17, 20], [18, 22]]]])
    valid = torch.ones(1, 2, 2, dtype=torch.bool)
    occupied = torch.tensor([[[True, False], [True, True]]])
    actual = exclude_nearby_bins(new, valid, old, occupied, (32, 32))
    assert actual.tolist() == [[[False, True], [False, True]]]
    assert torch.equal(new, torch.tensor([[[[1, 3], [2, 4]], [[31, 29], [8, 8]]]]))


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_complete_nonzero_baseline_is_retained_at_initialization_and_adc(pattern):
    torch.set_num_threads(2)
    model = build_component(
        "complementary-cfa-wave",
        {
            "evidence_window": 9,
            "evidence_stride": 8,
            "support_windows": (7, 3),
            "support_stride": 4,
        },
    )
    matching = model.anchor.anchor.matching
    matching.frozen, matching.network = FrozenFixture(), NetworkFixture()
    with torch.no_grad():
        model.anchor.anchor.readout.mixing.bias.fill_(0.13)
        model.anchor.readout.gates.bias.fill_(0.17)
    model.train()
    assert not model.anchor.training and all(not p.requires_grad for p in model.anchor.parameters())
    rng = torch.Generator().manual_seed(20101)
    raw = torch.randn(1, 4, 12, 17, generator=rng) * 0.003 + 0.02
    base = torch.randn(1, 3, 24, 34, generator=rng) * 0.003 + 0.02
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    colors = color_indices(pattern)
    with torch.no_grad():
        expected = model.anchor(base, raw, variance, colors)
    actual, aux = model(base, raw, variance, colors, return_aux=True)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
    assert torch.equal(aux["anchor_output"], expected)
    assert aux["anchor_aux"]["frozen_output"].shape == base.shape
    assert aux["cfa_context"].shape[2] == 36
    assert aux["wave_selection"]["valid"].sum() <= aux["wave_selection"]["proposed_valid"].sum()
    (actual - base).square().mean().backward()
    trainable = [p for p in model.parameters() if p.requires_grad]
    assert len(trainable) == 4 and sum(p.numel() for p in trainable) == 643
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in trainable)
    assert all(p.grad is None for p in model.anchor.parameters())
    with torch.no_grad():
        model.readout.gates.bias.fill_(0.3)
        expected = model.anchor(base, raw, variance * 0, colors)
        actual, aux = model(base, raw, variance * 0, colors, return_aux=True)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
    assert aux["cfa_context"] is None and not aux["matching_evaluated"]


def test_full_v200_initializer_and_new_head_have_explicit_separate_tensor_names(tmp_path):
    anchor = build_component("scale-supported-cfa-wave")
    with torch.no_grad():
        anchor.readout.gates.bias.fill_(0.17)
    state = legacy_state_dict(anchor)
    path = tmp_path / "trained-v200.pt"
    torch.save({"state_dict": state}, path)
    model = initialize_model(
        {
            "kind": "complementary-cfa-wave",
            "initializer": reference(path),
            "initialization": "anchor",
        }
    )
    full = legacy_state_dict(model)
    assert len(full) == 201 and readout_state_prefix(model) == "complement_readout."
    assert all(torch.equal(value, full[name]) for name, value in state.items())
    assert torch.count_nonzero(full["complement_readout.gates.bias"]) == 0
    clone = build_component("complementary-cfa-wave")
    load_legacy_state_dict(clone, full)
    assert all(
        torch.equal(value, clone.state_dict()[name]) for name, value in model.state_dict().items()
    )
    invalid = copy.copy(full)
    invalid["complement_readout.gates.bias"] = torch.zeros(4)
    with pytest.raises(ValueError, match="Incompatible"):
        load_legacy_state_dict(clone, invalid)
