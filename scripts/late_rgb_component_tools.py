"""Observe a frozen late RGB head and reuse its actual trunk/DINO inputs.

These are diagnostic counterfactuals of jointly trained checkpoints, never
models trained without the head. Physical inverse replay must match the
actual complete forward exactly before any component output is used.
"""

from unittest.mock import patch

import torch

import demosaic.pretrained_rgb as rgb_module
from demosaic.precision import ieee_fp32

INPUTS = ("packed", "variance", "colors", "wb", "matrix")


def compatible(model):
    rgb = model.pretrained_rgb
    if (
        model.training
        or rgb.processing_scale != 1
        or any(
            value is not None for value in [rgb.raw_kernel, rgb.raw_directional, rgb.raw_spectral]
        )
        or rgb.adc_projection
    ):
        raise ValueError("Component replay requires an eval full-resolution RGB-only checkpoint")
    return rgb


def inverse_tail(rgb, normalized, offset, span):
    """Replay only the actual final physical operations, with no target input."""
    with torch.autocast(normalized.device.type, enabled=False), ieee_fp32():
        value = normalized.float() * span + offset
        profiles = rgb._noise_profiles
        if profiles is not None:
            if len(profiles) not in (1, len(value)):
                raise ValueError("Noise profiles do not match the captured image batch")
            profiles = profiles * len(value) if len(profiles) == 1 else profiles
            value = torch.cat(
                [
                    transform.inverse(value[b : b + 1])
                    if transform is not None
                    else (value[b : b + 1].double() * scale).float()
                    for b, (transform, scale, _stochastic) in enumerate(profiles)
                ]
            )
        return value


def capture_forward(model, arguments):
    """Non-modifying hooks capture one full forward; remove them on every exit."""
    if set(arguments) != set(INPUTS):
        raise ValueError("Forward arguments must be exactly the five measurement/camera fields")
    rgb = compatible(model)
    if rgb.rgb_refinement is None:
        return model(*(arguments[k] for k in INPUTS)), None
    capture = {"physical_calls": 0, "head_calls": 0}
    original = rgb_module.physical_rgb_features

    def physical(*args, **kwargs):
        result = original(*args, **kwargs)
        capture["physical_calls"] += 1
        capture["offset"], capture["span"] = result[-2:]
        return result

    def before(_module, args):
        capture["head_arguments"] = args

    def after(_module, _args, output):
        capture["head_calls"] += 1
        capture["normalized_output"] = output

    handles = [
        rgb.rgb_refinement.register_forward_pre_hook(before),
        rgb.rgb_refinement.register_forward_hook(after),
    ]
    try:
        with patch.object(rgb_module, "physical_rgb_features", physical):
            output = model(*(arguments[k] for k in INPUTS))
    finally:
        for handle in handles:
            handle.remove()
    assert capture["physical_calls"] == capture["head_calls"] == 1
    reconstructed = inverse_tail(
        rgb, capture["normalized_output"], capture["offset"], capture["span"]
    )
    if not torch.equal(output, reconstructed):
        raise RuntimeError(
            "Captured physical tail does not replay the actual full RGB output exactly"
        )
    return output, capture


def component_outputs(model, full, capture):
    """Reuse captured inputs; no restoration-trunk or DINO invocation here."""
    rgb = compatible(model)
    if capture is None:
        assert rgb.rgb_refinement is None
        return {"full": full}
    head = rgb.rgb_refinement
    args = capture["head_arguments"]
    replay = head(*args)
    if not torch.equal(replay, capture["normalized_output"]):
        raise RuntimeError("Direct head replay differs from the actual captured head")
    with patch.object(head, "mode", "global"):
        pooled = head(*args)
    result = {
        "full": full,
        "bypass": inverse_tail(rgb, args[0], capture["offset"], capture["span"]),
    }
    if head.mode == "global":
        if not torch.equal(pooled, replay):
            raise RuntimeError("Pooling an already global head is not an exact identity")
    else:
        assert head.mode == "spatial"
        result["pooled"] = inverse_tail(rgb, pooled, capture["offset"], capture["span"])
    return result
