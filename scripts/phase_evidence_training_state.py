"""Preserve V172 Adam/EMA history while introducing a new evidence parameter.

The old network's optimizer clock continues;the adapter starts at zero. Target
pixels and quality decisions do not enter these state-management functions.
"""

import copy

import torch
from train_local_noise_matching_trial import tree_equal


def matching_parameters(module):
    parameters = {name: p for name, p in module.named_parameters() if p.requires_grad}
    allowed = {"network." + name for name, _ in module.network.named_parameters()}
    if hasattr(module, "phase_evidence_in"):
        allowed.update(
            "phase_evidence_in." + name for name, _ in module.phase_evidence_in.named_parameters()
        )
    if set(parameters) != allowed or any(p.requires_grad for p in module.frozen.parameters()):
        raise ValueError(
            "Expected trainable matching network/optional evidence and frozen component"
        )
    return parameters


def optimizer_for(module, *, lr, weight_decay):
    matching_parameters(module)
    optimizer = torch.optim.AdamW(module.network.parameters(), lr=lr, weight_decay=weight_decay)
    if hasattr(module, "phase_evidence_in"):
        optimizer.add_param_group({"params": list(module.phase_evidence_in.parameters())})
    return optimizer


def _validate_ema(parameters, ema):
    if set(ema) != set(parameters):
        raise ValueError("EMA must include every trainable network/evidence tensor")
    for name, parameter in parameters.items():
        if ema[name].shape != parameter.shape or ema[name].dtype != parameter.dtype:
            raise ValueError("EMA shape/dtype differs from the parameter")


def adam_clocks(module, optimizer):
    output = {
        "network": {"tensors": 0, "states": 0, "steps": []},
        "adapter": {"tensors": 0, "states": 0, "steps": []},
    }
    for name, parameter in matching_parameters(module).items():
        group = output["network" if name.startswith("network.") else "adapter"]
        group["tensors"] += 1
        state = optimizer.state.get(parameter)
        if state:
            if "step" not in state or not all(
                torch.isfinite(v).all() for v in state.values() if isinstance(v, torch.Tensor)
            ):
                raise ValueError("Invalid or nonfinite Adam state")
            group["states"] += 1
            group["steps"].append(float(state["step"]))
    for group in output.values():
        group["steps"] = sorted(set(group["steps"]))
    return output


def warm_start_matching(module, checkpoint, *, lr, weight_decay):
    """Load old raw/Adam/EMA exactly,then add a zero adapter with no Adam state.

    Deep-copy optimizer payloads even on CPU,where load_state_dict can otherwise
    share moment storage between a checkpoint and independently initialized arms.
    Learning rate intentionally changes for the new schedule;moments/steps do not.
    """
    initial_updates = checkpoint["updates"]
    if type(initial_updates) is not int or initial_updates < 1:
        raise ValueError("Expected a completed positive-step matching checkpoint")
    if len(checkpoint["optimizer"]["param_groups"]) != 1:
        raise ValueError("Expected the original single-network optimizer group")
    if hasattr(module, "phase_evidence_in"):
        module.initialize_from_local_matching(checkpoint["models"])
    else:
        module.load_state_dict(checkpoint["models"], strict=True)
    network_names = dict(module.network.named_parameters())
    if set(checkpoint["ema"]) != set(network_names):
        raise ValueError("Old EMA does not cover exactly the matching network")
    optimizer = torch.optim.AdamW(module.network.parameters(), lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(copy.deepcopy(checkpoint["optimizer"]))
    # Check the original optimizer before adding the new parameter group/LR.
    if not tree_equal(optimizer.state_dict(), checkpoint["optimizer"]):
        raise ValueError("Original Adam state did not load exactly")
    before = adam_clocks(module, optimizer)
    if (
        len(optimizer.state) != len(network_names)
        or before["network"]["states"] != len(network_names)
        or before["network"]["steps"] != [float(initial_updates)]
    ):
        raise ValueError("Existing Adam clocks do not match checkpoint updates")
    if hasattr(module, "phase_evidence_in"):
        optimizer.add_param_group({"params": list(module.phase_evidence_in.parameters())})
    for group in optimizer.param_groups:
        group["lr"] = lr
        if group["weight_decay"] != weight_decay:
            raise ValueError("Warm-start weight decay differs from the intended recipe")
    parameters = matching_parameters(module)
    ema = {
        "network." + name: value.detach().to(device=parameters["network." + name].device).clone()
        for name, value in checkpoint["ema"].items()
    }
    for name, parameter in parameters.items():
        if name.startswith("phase_evidence_in."):
            if parameter.count_nonzero():
                raise ValueError("Expected a zero evidence initializer")
            ema[name] = parameter.detach().clone()
    _validate_ema(parameters, ema)
    clocks = adam_clocks(module, optimizer)
    if clocks["adapter"]["states"] != 0:
        raise ValueError("New adapter unexpectedly has an Adam history")
    return (
        optimizer,
        ema,
        {
            "initial_updates": initial_updates,
            "Adam_clocks": clocks,
            "original_moments_exact": True,
            "new_adapter_has_no_Adam_state": True,
            "network_EMA_exact": True,
            "adapter_EMA_starts_zero": True,
        },
    )


def update_matching_ema(module, ema, *, total_updates, maximum_decay):
    if type(total_updates) is not int or total_updates < 1 or not 0 <= maximum_decay < 1:
        raise ValueError("Expected positive update count and EMA decay in[0,1)")
    parameters = matching_parameters(module)
    _validate_ema(parameters, ema)
    decay = min(maximum_decay, (1 + total_updates) / (10 + total_updates))
    with torch.no_grad():
        for name, parameter in parameters.items():
            ema[name].lerp_(parameter, 1 - decay)
    return decay


def load_matching_ema(module, ema):
    parameters = matching_parameters(module)
    _validate_ema(parameters, ema)
    with torch.no_grad():
        for name, parameter in parameters.items():
            parameter.copy_(ema[name])


def restore_matching_state(module, checkpoint, *, lr, weight_decay):
    """Restore a continuation checkpoint without reinitializing its adapter."""
    module.load_state_dict(checkpoint["models"], strict=True)
    parameters = matching_parameters(module)
    _validate_ema(parameters, checkpoint["ema"])
    optimizer = optimizer_for(module, lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(copy.deepcopy(checkpoint["optimizer"]))
    if not tree_equal(optimizer.state_dict(), checkpoint["optimizer"]):
        raise ValueError("Adam restoration differs")
    ema = {
        name: value.detach().to(device=parameters[name].device).clone()
        for name, value in checkpoint["ema"].items()
    }
    clocks = adam_clocks(module, optimizer)
    expected = checkpoint["initial_updates"] + checkpoint["updates"]
    if (
        len(optimizer.state) != len(parameters)
        or clocks["network"]["states"] != clocks["network"]["tensors"]
        or clocks["network"]["steps"] != [float(expected)]
    ):
        raise ValueError("Restored network clock is wrong")
    if clocks["adapter"]["tensors"] and (
        clocks["adapter"]["states"] != clocks["adapter"]["tensors"]
        or clocks["adapter"]["steps"] != [float(checkpoint["updates"])]
    ):
        raise ValueError("Restored new-parameter clock is wrong")
    torch.set_rng_state(checkpoint["CPU_RNG"])
    cuda = checkpoint.get("CUDA_RNG")
    if cuda is not None:
        torch.cuda.set_rng_state(cuda)
    return (
        optimizer,
        ema,
        {
            "Adam_clocks": clocks,
            "model_loaded_strictly": True,
            "Adam_exact": True,
            "EMA_exact": True,
            "CPU_RNG_exact": torch.equal(torch.get_rng_state(), checkpoint["CPU_RNG"]),
            "CUDA_RNG_exact": torch.equal(torch.cuda.get_rng_state().cpu(), cuda)
            if cuda is not None
            else None,
        },
    )
