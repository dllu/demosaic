"""Independent sample geometry and exact state/RNG isolation of the initializer."""

import numpy as np
import pytest
import torch
from spread_matching_offsets import initialize_spread_offsets

from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail


def model():
    pytest.importorskip("einops")
    return LateLocalNoiseMatchingDetail()


def test_only_five_bias_vectors_change_and_sample_grid_matches_numpy():
    module = model()
    before = {k: v.clone() for k, v in module.state_dict().items()}
    rng = torch.get_rng_state().clone()
    names = initialize_spread_offsets(module, spacing=8)
    after = module.state_dict()
    changed = [k for k in before if not torch.equal(before[k], after[k])]
    assert changed == ["network." + name for name in names]
    assert len(changed) == 5 and len(before) == 188
    assert sum(int((before[k] != after[k]).sum()) for k in changed) == 60
    assert torch.equal(rng, torch.get_rng_state())
    grid = np.asarray([(y, x) for y in [-1, 0, 1] for x in [-1, 0, 1]], np.float64)
    for name in names:
        bias = dict(module.network.named_parameters())[name].detach().numpy().reshape(9, 2)
        np.testing.assert_allclose(bias, np.arctanh(7 * grid / 9), rtol=2e-6, atol=1e-7)
        actual = grid + 9 * np.tanh(bias.astype(np.float64))
        np.testing.assert_allclose(actual, 8 * grid, rtol=2e-6, atol=1e-6)
    assert module.network.tail.weight.count_nonzero() == 0
    assert sum(p.numel() for p in module.network.parameters()) == 2088906
    assert len(module.network.state_dict()) == 141
    assert not any(p.requires_grad for p in module.frozen.parameters())


def test_unit_spacing_is_exact_original_initial_state():
    module = model()
    before = {k: v.clone() for k, v in module.state_dict().items()}
    initialize_spread_offsets(module, spacing=1)
    assert all(torch.equal(before[k], v) for k, v in module.state_dict().items())


def test_trained_or_repeated_initialization_rejects_without_mutation():
    module = model()
    initialize_spread_offsets(module, spacing=8)
    before = {k: v.clone() for k, v in module.state_dict().items()}
    with pytest.raises(ValueError, match="fresh"):
        initialize_spread_offsets(module, spacing=8)
    assert all(torch.equal(before[k], v) for k, v in module.state_dict().items())


@pytest.mark.parametrize("spacing", [0, -1, True, float("nan"), float("inf"), 10, "wide"])
def test_invalid_spacing_rejects_before_any_state_change(spacing):
    module = model()
    before = {k: v.clone() for k, v in module.state_dict().items()}
    with pytest.raises((TypeError, ValueError)):
        initialize_spread_offsets(module, spacing=spacing)
    assert all(torch.equal(before[k], v) for k, v in module.state_dict().items())
