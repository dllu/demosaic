"""Fresh isolated Adam/EMA history, frozen state and actual CPU restoration."""

import copy

import pytest
import torch
from phase_wave_training_state import (
    clocks,
    fresh_state,
    inherited_hash,
    load_ema,
    readout_parameters,
    restore_state,
    update_ema,
)

from demosaic.late_phase_wave_readout import LatePhaseWaveReadoutDetail


def update(module, optimizer, ema, step):
    evidence = torch.linspace(-0.7, 0.9, 20 * 8 * 9).reshape(1, 20, 8, 9)
    bins = torch.tensor([[[[2, 3]], [[3, 5]]]])
    output = module.wave_readout(evidence, bins)
    target = torch.linspace(-0.3, 0.5, output.numel()).reshape_as(output)
    optimizer.zero_grad(set_to_none=True)
    (output - target).square().mean().backward()
    optimizer.step()
    return update_ema(module, ema, updates=step)


def test_adam_and_ema_cover_only_new_readout_and_preserve_frozen_state():
    module = LatePhaseWaveReadoutDetail()
    inherited = inherited_hash(module)
    optimizer, ema = fresh_state(module, lr=0.001, weight_decay=0.01)
    assert clocks(module, optimizer) == {"tensors": 4, "states": 0, "steps": []}
    assert set(ema) == set(readout_parameters(module))
    for step in [1, 2]:
        previous = copy.deepcopy(ema)
        decay = update(module, optimizer, ema, step)
        assert decay == (1 + step) / (10 + step)
        assert clocks(module, optimizer) == {"tensors": 4, "states": 4, "steps": [float(step)]}
        for name, p in readout_parameters(module).items():
            torch.testing.assert_close(
                ema[name], previous[name] * decay + p * (1 - decay), rtol=1e-6, atol=1e-8
            )
        assert inherited_hash(module) == inherited
        assert all(
            p.grad is None
            for n, p in module.named_parameters()
            if not n.startswith("wave_readout.")
        )


def test_restore_recovers_full_raw_state_four_adam_states_ema_and_rng_exactly():
    from train_local_noise_matching_trial import tree_equal

    module = LatePhaseWaveReadoutDetail()
    optimizer, ema = fresh_state(module, lr=0.001, weight_decay=0.01)
    update(module, optimizer, ema, 1)
    payload = copy.deepcopy(
        {
            "models": module.state_dict(),
            "optimizer": optimizer.state_dict(),
            "ema": ema,
            "updates": 1,
            "CPU_RNG": torch.get_rng_state().clone(),
            "CUDA_RNG": None,
            "inherited_hash": inherited_hash(module),
        }
    )
    restored = LatePhaseWaveReadoutDetail()
    new_optimizer, new_ema = restore_state(restored, payload, lr=0.001, weight_decay=0.01)
    assert tree_equal(restored.state_dict(), module.state_dict())
    assert tree_equal(new_optimizer.state_dict(), optimizer.state_dict())
    assert tree_equal(new_ema, ema)
    assert torch.equal(torch.get_rng_state(), payload["CPU_RNG"])
    raw_inherited = inherited_hash(restored)
    load_ema(restored, ema)
    assert inherited_hash(restored) == raw_inherited
    for n, p in readout_parameters(restored).items():
        assert torch.equal(p, ema[n])


def test_unfreezing_any_inherited_parameter_is_rejected():
    module = LatePhaseWaveReadoutDetail()
    next(module.network.parameters()).requires_grad_(True)
    with pytest.raises(ValueError, match="Only the four"):
        fresh_state(module, lr=0.001, weight_decay=0.01)


def test_incomplete_optimizer_group_is_rejected_even_without_moments():
    module = LatePhaseWaveReadoutDetail()
    optimizer = torch.optim.AdamW([next(module.wave_readout.parameters())], lr=0.001)
    with pytest.raises(ValueError, match="only readout"):
        clocks(module, optimizer)


def test_wrong_ema_keys_and_shapes_are_rejected():
    module = LatePhaseWaveReadoutDetail()
    _, ema = fresh_state(module, lr=0.001, weight_decay=0.01)
    with pytest.raises(ValueError, match="exactly"):
        load_ema(module, {})
    bad = copy.deepcopy(ema)
    bad[next(iter(bad))] = torch.zeros(1)
    with pytest.raises(ValueError, match="shape"):
        update_ema(module, bad, updates=1)
