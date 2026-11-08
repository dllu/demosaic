"""Isolated fresh head clocks and compact snapshots above a checked V195 anchor."""

import copy
import hashlib

import torch
from lossless_native import checked

PREFIX = "innovation_readout."


def parameters(module):
    actual = {n: p for n, p in module.named_parameters() if p.requires_grad}
    expected = {PREFIX + n for n, _ in module.innovation_readout.named_parameters()}
    if (
        set(actual) != expected
        or len(actual) != 4
        or sum(p.numel() for p in actual.values()) != 508
    ):
        raise ValueError("Only four new head tensors /508parameters may train")
    return actual


def anchor_hash(module):
    digest = hashlib.sha256()
    for name, value in module.state_dict().items():
        if name.startswith(PREFIX):
            continue
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
        digest.update(flat.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def fresh(module, *, lr=0.001, weight_decay=0.01):
    values = parameters(module)
    return torch.optim.AdamW(values.values(), lr=lr, weight_decay=weight_decay), {
        n: p.detach().clone() for n, p in values.items()
    }


def clocks(module, optimizer):
    values = parameters(module)
    assert len(optimizer.param_groups) == 1 and set(optimizer.param_groups[0]["params"]) == set(
        values.values()
    )
    assert set(optimizer.state) <= set(values.values())
    steps = []
    for p in values.values():
        state = optimizer.state.get(p)
        if state:
            assert all(torch.isfinite(v).all() for v in state.values() if torch.is_tensor(v))
            steps.append(float(state["step"]))
    return {"tensors": 4, "states": len(steps), "steps": sorted(set(steps))}


def update_ema(module, ema, updates):
    values = parameters(module)
    assert type(updates) is int and updates > 0 and set(values) == set(ema)
    decay = min(0.999, (1 + updates) / (10 + updates))
    with torch.no_grad():
        for name, p in values.items():
            ema[name].lerp_(p, 1 - decay)
    return decay


def pack(payload, anchor):
    state = torch.load(checked(anchor), map_location="cpu", weights_only=True)["state_dict"]
    frozen = {n: v for n, v in payload["models"].items() if not n.startswith(PREFIX)}
    assert len(state) == 193 and set(state) == set(frozen)
    assert all(
        v.dtype == state[n].dtype
        and v.shape == state[n].shape
        and torch.equal(v.detach().cpu(), state[n])
        for n, v in frozen.items()
    )
    head = {n: v for n, v in payload["models"].items() if n.startswith(PREFIX)}
    assert len(head) == 4 and set(head) == set(payload["ema"])
    return {
        **{k: v for k, v in payload.items() if k != "models"},
        "format": "V195-anchor-plus-innovation-head-v1",
        "anchor": anchor,
        "head": head,
    }


def expand(checkpoint):
    assert checkpoint["format"] == "V195-anchor-plus-innovation-head-v1"
    source = torch.load(checked(checkpoint["anchor"]), map_location="cpu", weights_only=True)[
        "state_dict"
    ]
    head = checkpoint["head"]
    assert len(source) == 193 and len(head) == 4 and all(n.startswith(PREFIX) for n in head)
    assert set(head) == set(checkpoint["ema"])
    return {
        **{k: v for k, v in checkpoint.items() if k not in ["format", "anchor", "head"]},
        "models": {**source, **head},
    }


def restore(module, checkpoint, *, lr=0.001, weight_decay=0.01):
    from train_local_noise_matching_trial import tree_equal

    payload = expand(checkpoint)
    module.load_state_dict(payload["models"], strict=True)
    optimizer, _ = fresh(module, lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(copy.deepcopy(payload["optimizer"]))
    assert tree_equal(optimizer.state_dict(), payload["optimizer"])
    values = parameters(module)
    assert set(payload["ema"]) == set(values)
    ema = {n: v.detach().to(values[n].device).clone() for n, v in payload["ema"].items()}
    assert clocks(module, optimizer) == {
        "tensors": 4,
        "states": 4,
        "steps": [float(payload["updates"])],
    }
    assert anchor_hash(module) == payload["anchor_hash"]
    torch.set_rng_state(payload["CPU_RNG"])
    if payload.get("CUDA_RNG") is not None:
        torch.cuda.set_rng_state(payload["CUDA_RNG"])
    assert torch.equal(torch.get_rng_state(), payload["CPU_RNG"])
    if payload.get("CUDA_RNG") is not None:
        assert torch.equal(torch.cuda.get_rng_state(), payload["CUDA_RNG"])
    return optimizer, ema
