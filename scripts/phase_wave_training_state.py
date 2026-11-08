"""Optimizer/EMA state for the isolated readout above frozen V183 EMA."""

import copy
import hashlib

import torch


def readout_parameters(module):
    parameters = {n: p for n, p in module.named_parameters() if p.requires_grad}
    expected = {"wave_readout." + n for n, _ in module.wave_readout.named_parameters()}
    if set(parameters) != expected or len(parameters) != 4:
        raise ValueError("Only the four readout tensors may train")
    return parameters


def inherited_hash(module):
    digest = hashlib.sha256()
    for name, value in module.state_dict().items():
        if name.startswith("wave_readout."):
            continue
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def fresh_state(module, *, lr, weight_decay):
    parameters = readout_parameters(module)
    optimizer = torch.optim.AdamW(parameters.values(), lr=lr, weight_decay=weight_decay)
    ema = {n: p.detach().clone() for n, p in parameters.items()}
    return optimizer, ema


def update_ema(module, ema, *, updates):
    parameters = readout_parameters(module)
    if set(ema) != set(parameters) or type(updates) is not int or updates < 1:
        raise ValueError("Expected all readout EMA tensors and a positive new-head clock")
    decay = min(0.999, (1 + updates) / (10 + updates))
    with torch.no_grad():
        for n, p in parameters.items():
            if p.shape != ema[n].shape or p.dtype != ema[n].dtype:
                raise ValueError("Readout EMA shape/dtype mismatch")
            ema[n].lerp_(p, 1 - decay)
    return decay


def load_ema(module, ema):
    parameters = readout_parameters(module)
    if set(parameters) != set(ema):
        raise ValueError("Expected exactly the four readout EMA tensors")
    with torch.no_grad():
        for n, p in parameters.items():
            if p.shape != ema[n].shape or p.dtype != ema[n].dtype:
                raise ValueError("Readout EMA shape/dtype mismatch")
            p.copy_(ema[n])


def clocks(module, optimizer):
    parameters = readout_parameters(module)
    if (
        len(optimizer.param_groups) != 1
        or len(optimizer.param_groups[0]["params"]) != 4
        or set(optimizer.param_groups[0]["params"]) != set(parameters.values())
        or set(optimizer.state) - set(parameters.values())
    ):
        raise ValueError("Optimizer must contain only readout state")
    steps = []
    for parameter in parameters.values():
        state = optimizer.state.get(parameter)
        if state:
            if not all(torch.isfinite(v).all() for v in state.values() if torch.is_tensor(v)):
                raise ValueError("Nonfinite readout Adam state")
            steps.append(float(state["step"]))
    return {"tensors": 4, "states": len(steps), "steps": sorted(set(steps))}


def restore_state(module, checkpoint, *, lr, weight_decay):
    from train_local_noise_matching_trial import tree_equal

    module.load_state_dict(checkpoint["models"], strict=True)
    optimizer, _ = fresh_state(module, lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(copy.deepcopy(checkpoint["optimizer"]))
    assert tree_equal(optimizer.state_dict(), checkpoint["optimizer"])
    parameters = readout_parameters(module)
    assert set(checkpoint["ema"]) == set(parameters)
    ema = {n: v.detach().to(parameters[n].device).clone() for n, v in checkpoint["ema"].items()}
    assert all(p.shape == ema[n].shape and p.dtype == ema[n].dtype for n, p in parameters.items())
    assert clocks(module, optimizer) == {
        "tensors": 4,
        "states": 4,
        "steps": [float(checkpoint["updates"])],
    }
    assert inherited_hash(module) == checkpoint["inherited_hash"]
    torch.set_rng_state(checkpoint["CPU_RNG"])
    if checkpoint.get("CUDA_RNG") is not None:
        torch.cuda.set_rng_state(checkpoint["CUDA_RNG"])
    assert torch.equal(torch.get_rng_state(), checkpoint["CPU_RNG"])
    if checkpoint.get("CUDA_RNG") is not None:
        assert torch.equal(torch.cuda.get_rng_state(), checkpoint["CUDA_RNG"])
    return optimizer, ema
