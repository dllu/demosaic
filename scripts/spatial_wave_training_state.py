"""Factor future frozen V183 state out of spatial-context head checkpoints."""

import copy

import torch
from lossless_native import checked
from phase_wave_training_state import readout_parameters


def inherited_state(binding):
    exported = torch.load(checked(binding), map_location="cpu", weights_only=True)
    state = exported["state_dict"]
    if len(state) != 189 or any(n.startswith("wave_readout.") for n in state):
        raise ValueError("Expected the exact 189-tensor V183 EMA export")
    return state


def pack_checkpoint(payload, initializer):
    """Keep head/Adam/EMA/RNG; bind every omitted tensor to a checked export."""
    source = inherited_state(initializer)
    state = payload["models"]
    frozen = {n: v for n, v in state.items() if not n.startswith("wave_readout.")}
    if set(frozen) != set(source) or any(
        v.dtype != source[n].dtype
        or v.shape != source[n].shape
        or not torch.equal(v.detach().cpu(), source[n])
        for n, v in frozen.items()
    ):
        raise ValueError("Cannot factor a changed inherited tensor")
    head = {n: v for n, v in state.items() if n.startswith("wave_readout.")}
    if len(head) != 4 or set(head) != set(payload["ema"]):
        raise ValueError("Expected exactly four raw and EMA head tensors")
    return {
        **{k: v for k, v in payload.items() if k != "models"},
        "format": "frozen-V183-plus-spatial-head-v1",
        "initializer": initializer,
        "head": head,
    }


def expand_checkpoint(checkpoint):
    """Reconstruct strict full state on CPU without inference or optimizer work."""
    if checkpoint.get("format") != "frozen-V183-plus-spatial-head-v1":
        raise ValueError("Expected factored spatial-head checkpoint")
    source = inherited_state(checkpoint["initializer"])
    head = checkpoint["head"]
    if len(head) != 4 or any(not n.startswith("wave_readout.") for n in head):
        raise ValueError("Expected only four wave readout tensors")
    if set(head) != set(checkpoint["ema"]):
        raise ValueError("Raw and EMA head names differ")
    result = {k: v for k, v in checkpoint.items() if k not in ["head", "format", "initializer"]}
    result["models"] = {**source, **head}
    return result


def restore_factored(module, checkpoint, *, lr, weight_decay):
    from phase_wave_training_state import restore_state

    expanded = expand_checkpoint(checkpoint)
    if set(expanded["models"]) != set(module.state_dict()):
        raise ValueError("Factored checkpoint has incompatible strict state names")
    if set(checkpoint["head"]) != set(readout_parameters(module)):
        raise ValueError("Factored checkpoint has incompatible trainable names")
    return restore_state(module, copy.deepcopy(expanded), lr=lr, weight_decay=weight_decay)
