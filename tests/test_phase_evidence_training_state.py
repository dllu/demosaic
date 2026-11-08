"""Independent histories,per-parameter clocks,and EMA restoration on real AdamW."""

import copy

import pytest
import torch
from phase_evidence_training_state import (
    adam_clocks,
    load_matching_ema,
    matching_parameters,
    restore_matching_state,
    update_matching_ema,
    warm_start_matching,
)
from torch import nn
from train_local_noise_matching_trial import tree_equal


class Fixture(nn.Module):
    def __init__(self, candidate=False):
        super().__init__()
        self.frozen = nn.Linear(2, 2).requires_grad_(False)
        self.network = nn.Linear(2, 1)
        with torch.no_grad():
            self.network.weight.fill_(0.1)
            self.network.bias.fill_(0.03)
        if candidate:
            self.phase_evidence_in = nn.Linear(1, 2, bias=False)
            nn.init.zeros_(self.phase_evidence_in.weight)

    def initialize_from_local_matching(self, state):
        with torch.no_grad():
            self.phase_evidence_in.weight.zero_()
        self.load_state_dict(
            dict(
                state,
                **{"phase_evidence_in.weight": self.phase_evidence_in.weight.detach().clone()},
            ),
            strict=True,
        )

    def forward(self):
        x = torch.ones(2, 2)
        if hasattr(self, "phase_evidence_in"):
            x = x + self.phase_evidence_in(torch.ones(2, 1))
        return self.network(x).square().mean()


def old_checkpoint():
    module = Fixture()
    optimizer = torch.optim.AdamW(module.network.parameters(), lr=0.003, weight_decay=0.01)
    for _ in range(4):
        optimizer.zero_grad(set_to_none=True)
        module().backward()
        optimizer.step()
    return {
        "models": copy.deepcopy(module.state_dict()),
        "optimizer": copy.deepcopy(optimizer.state_dict()),
        "ema": {
            name: value.detach().clone() * 0.8
            for name, value in module.network.state_dict().items()
        },
        "updates": 4,
    }


@pytest.mark.parametrize("candidate", [False, True])
def test_warmstart_preserves_moments_and_adds_no_fake_history(candidate):
    checkpoint = old_checkpoint()
    before = copy.deepcopy(checkpoint)
    module = Fixture(candidate)
    optimizer, ema, metadata = warm_start_matching(module, checkpoint, lr=1e-4, weight_decay=0.01)
    assert tree_equal(before, checkpoint)
    clocks = adam_clocks(module, optimizer)
    assert clocks["network"] == {"tensors": 2, "states": 2, "steps": [4.0]}
    assert clocks["adapter"] == {"tensors": int(candidate), "states": 0, "steps": []}
    assert len(optimizer.state) == 2
    assert all(group["lr"] == 1e-4 for group in optimizer.param_groups)
    for name, value in checkpoint["ema"].items():
        assert torch.equal(ema["network." + name], value)
    if candidate:
        assert ema["phase_evidence_in.weight"].count_nonzero() == 0
    assert metadata["original_moments_exact"]


def test_separate_arms_do_not_share_checkpoint_moment_or_EMA_storage():
    checkpoint = old_checkpoint()
    before = copy.deepcopy(checkpoint)
    control, candidate = Fixture(), Fixture(True)
    opt_control, ema_control, _ = warm_start_matching(
        control, checkpoint, lr=1e-4, weight_decay=0.01
    )
    opt_candidate, ema_candidate, _ = warm_start_matching(
        candidate, checkpoint, lr=1e-4, weight_decay=0.01
    )
    frozen_control = copy.deepcopy(opt_control.state_dict())
    opt_candidate.zero_grad(set_to_none=True)
    candidate().backward()
    opt_candidate.step()
    update_matching_ema(candidate, ema_candidate, total_updates=5, maximum_decay=0.999)
    assert tree_equal(checkpoint, before)
    assert tree_equal(opt_control.state_dict(), frozen_control)
    assert all(
        torch.equal(value, checkpoint["ema"][name.removeprefix("network.")])
        for name, value in ema_control.items()
    )


def test_old_and_new_adam_clocks_and_ema_include_evidence():
    checkpoint = old_checkpoint()
    module = Fixture(True)
    optimizer, ema, _ = warm_start_matching(module, checkpoint, lr=1e-4, weight_decay=0.01)
    optimizer.zero_grad(set_to_none=True)
    module().backward()
    optimizer.step()
    clocks = adam_clocks(module, optimizer)
    assert clocks["network"]["steps"] == [5.0] and clocks["adapter"]["steps"] == [1.0]
    previous = {name: value.clone() for name, value in ema.items()}
    decay = update_matching_ema(module, ema, total_updates=5, maximum_decay=0.999)
    assert decay == 0.4
    for name, parameter in matching_parameters(module).items():
        torch.testing.assert_close(
            ema[name], previous[name] * 0.4 + parameter.detach() * 0.6, rtol=2e-7, atol=2e-8
        )
    assert ema["phase_evidence_in.weight"].count_nonzero() > 0
    frozen = copy.deepcopy(module.frozen.state_dict())
    load_matching_ema(module, ema)
    assert tree_equal(frozen, module.frozen.state_dict())
    for name, parameter in matching_parameters(module).items():
        assert torch.equal(parameter, ema[name])


@pytest.mark.parametrize("candidate", [False, True])
def test_genuine_restore_preserves_distinct_clocks_adapter_ema_and_rng(candidate):
    checkpoint = old_checkpoint()
    module = Fixture(candidate)
    optimizer, ema, _ = warm_start_matching(module, checkpoint, lr=1e-4, weight_decay=0.01)
    for update in range(1, 3):
        optimizer.zero_grad(set_to_none=True)
        module().backward()
        optimizer.step()
        update_matching_ema(module, ema, total_updates=4 + update, maximum_decay=0.999)
    saved = {
        "models": copy.deepcopy(module.state_dict()),
        "optimizer": copy.deepcopy(optimizer.state_dict()),
        "ema": copy.deepcopy(ema),
        "initial_updates": 4,
        "updates": 2,
        "CPU_RNG": torch.get_rng_state().clone(),
        "CUDA_RNG": None,
    }
    restored = Fixture(candidate)
    restored_opt, restored_ema, proof = restore_matching_state(
        restored, saved, lr=1e-4, weight_decay=0.01
    )
    assert tree_equal(module.state_dict(), restored.state_dict())
    assert tree_equal(optimizer.state_dict(), restored_opt.state_dict())
    assert tree_equal(ema, restored_ema) and torch.equal(torch.get_rng_state(), saved["CPU_RNG"])
    assert proof["Adam_exact"] and proof["EMA_exact"] and proof["CPU_RNG_exact"]
    restored_opt.zero_grad(set_to_none=True)
    restored().backward()
    restored_opt.step()
    clocks = adam_clocks(restored, restored_opt)
    assert clocks["network"]["steps"] == [7.0]
    assert clocks["adapter"]["steps"] == ([3.0] if candidate else [])


@pytest.mark.parametrize("damage", ["updates", "EMA", "clock", "decay"])
def test_wrong_warmstart_contract_rejects(damage):
    checkpoint = old_checkpoint()
    module = Fixture(True)
    weight_decay = 0.01
    if damage == "updates":
        checkpoint["updates"] = 5
    elif damage == "EMA":
        checkpoint["ema"].pop("bias")
    elif damage == "clock":
        checkpoint["optimizer"]["state"][0]["step"].fill_(100)
    else:
        weight_decay = 0.02
    with pytest.raises(ValueError):
        warm_start_matching(module, checkpoint, lr=1e-4, weight_decay=weight_decay)


def test_incomplete_candidate_ema_is_never_silently_accepted():
    module = Fixture(True)
    _, ema, _ = warm_start_matching(module, old_checkpoint(), lr=1e-4, weight_decay=0.01)
    ema.pop("phase_evidence_in.weight")
    with pytest.raises(ValueError):
        load_matching_ema(module, ema)
    with pytest.raises(ValueError):
        update_matching_ema(module, ema, total_updates=5, maximum_decay=0.999)


@pytest.mark.parametrize("damage", ["shape", "dtype"])
def test_ema_metadata_error_rejects_before_any_weight_or_ema_change(damage):
    module = Fixture(True)
    _, ema, _ = warm_start_matching(module, old_checkpoint(), lr=1e-4, weight_decay=0.01)
    if damage == "shape":
        ema["phase_evidence_in.weight"] = torch.zeros(4)
    else:
        ema["phase_evidence_in.weight"] = ema["phase_evidence_in.weight"].double()
    weights = copy.deepcopy(module.state_dict())
    before = copy.deepcopy(ema)
    with pytest.raises(ValueError):
        load_matching_ema(module, ema)
    with pytest.raises(ValueError):
        update_matching_ema(module, ema, total_updates=5, maximum_decay=0.999)
    assert tree_equal(weights, module.state_dict()) and tree_equal(before, ema)
