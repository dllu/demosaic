"""Compact head checkpoints with strict frozen-state identity and complete RNG."""

import hashlib
import os
import random
import tempfile
from pathlib import Path

import numpy as np
import torch


def state_hash(state):
    digest = hashlib.sha256()
    for name, value in state.items():
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
        digest.update(flat.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def trainable_parameters(model):
    values = {n: p for n, p in model.named_parameters() if p.requires_grad}
    if not values:
        raise ValueError("Model has no trainable parameters")
    return values


def frozen_hash(model):
    trainable = trainable_parameters(model)
    return state_hash({n: v for n, v in model.state_dict().items() if n not in trainable})


def capture_rng():
    numpy = np.random.get_state()
    return {
        "python": random.getstate(),
        "numpy": [numpy[0], numpy[1].tolist(), *numpy[2:]],
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None,
    }


def load_torch(binding):
    """Hash the same opened inode that supplies the loaded tensor payload."""
    with Path(binding["path"]).open("rb") as stream:
        payload = torch.load(stream, map_location="cpu", weights_only=True)
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != binding["sha256"]:
        raise ValueError(f"Checkpoint digest mismatch: {binding['path']}")
    return payload


def restore_rng(state):
    random.setstate(state["python"])
    kind, keys, position, gaussian, cached = state["numpy"]
    np.random.set_state((kind, np.asarray(keys, dtype=np.uint32), position, gaussian, cached))
    torch.set_rng_state(state["torch"])
    if state["cuda"] is not None:
        torch.cuda.set_rng_state_all(state["cuda"])


def fresh_state(model, *, lr, weight_decay):
    values = trainable_parameters(model)
    optimizer = torch.optim.AdamW(values.values(), lr=lr, weight_decay=weight_decay)
    return optimizer, {n: p.detach().clone() for n, p in values.items()}


def update_ema(model, ema, updates):
    values = trainable_parameters(model)
    if set(ema) != set(values) or type(updates) is not int or updates < 1:
        raise ValueError("EMA identity/update count mismatch")
    decay = min(0.999, (1 + updates) / (10 + updates))
    with torch.no_grad():
        for name, parameter in values.items():
            ema[name].lerp_(parameter, 1 - decay)
    return decay


def save_checkpoint(path, model, optimizer, ema, *, plan, row, updates, skipped, anchor_hash):
    if frozen_hash(model) != anchor_hash:
        raise ValueError("Frozen model tensors changed")
    values = trainable_parameters(model)
    payload = {
        "format": "cached-head-training-v1",
        "plan": plan,
        "row": row,
        "updates": updates,
        "skipped": skipped,
        "frozen_hash": anchor_hash,
        "trainable": {n: p.detach().cpu().clone() for n, p in values.items()},
        "ema": {n: v.detach().cpu().clone() for n, v in ema.items()},
        "optimizer": optimizer.state_dict(),
        "rng": capture_rng(),
    }
    save_torch(path, payload)


def save_torch(path, payload):
    """Atomically publish an immutable tensor checkpoint or portable endpoint."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix="." + path.name, delete=False
        ) as stream:
            temporary = Path(stream.name)
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def restore_checkpoint(path, model, *, plan, lr, weight_decay):
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload["format"] != "cached-head-training-v1" or payload["plan"] != plan:
        raise ValueError("Checkpoint belongs to a different experiment plan")
    if frozen_hash(model) != payload["frozen_hash"]:
        raise ValueError("Checkpoint's frozen anchor differs")
    values = trainable_parameters(model)
    if set(values) != set(payload["trainable"]) or set(values) != set(payload["ema"]):
        raise ValueError("Checkpoint trainable tensor names differ")
    for name, parameter in values.items():
        for source in (payload["trainable"], payload["ema"]):
            if source[name].shape != parameter.shape or source[name].dtype != parameter.dtype:
                raise ValueError(f"Checkpoint tensor shape/dtype differs: {name}")
    with torch.no_grad():
        for name, parameter in values.items():
            parameter.copy_(payload["trainable"][name])
    optimizer, _ = fresh_state(model, lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(payload["optimizer"])
    ema = {n: v.to(values[n].device).clone() for n, v in payload["ema"].items()}
    restore_rng(payload["rng"])
    return optimizer, ema, payload
