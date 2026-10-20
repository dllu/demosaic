"""Temporary, explicit precision policies for fixed mature-model research probes."""

from contextlib import contextmanager

import torch

from demosaic.precision import amp_context

POLICIES = ("fp32", "fp16", "fp16-hidden")


@contextmanager
def precision_policy(model, policy, device, *, cpu_probe=False):
    """Preserve weights/config and restore the hidden flag even on exceptions.

    CPU half execution is an explicitly enabled engineering emulation. Production
    CPU inference remains FP32; CUDA accuracy/performance needs separate proof.
    """
    if policy not in POLICIES:
        raise ValueError(f"Expected one of {POLICIES}")
    device = torch.device(device)
    if device.type not in ("cpu", "cuda"):
        raise ValueError("Precision probe requires CPU or CUDA")
    if device.type == "cpu" and policy != "fp32" and not cpu_probe:
        raise ValueError("CPU half probe must be explicitly enabled")
    cfg = model.config
    if model.training or cfg.restoration_backbone != "pretrained-rgb":
        raise ValueError("Precision probe requires an eval pretrained RGB model")
    if (
        not cfg.variance_stabilization
        or not cfg.physical_anchors
        or not cfg.physical_fp32
        or cfg.rgb_processing_scale != 1
        or cfg.rgb_hidden_autocast
        or cfg.raw_kernel_reconstruction
        or cfg.raw_directional_residual
        or cfg.raw_spectral_residual
        or cfg.late_rgb_refinement != "none"
        or cfg.adc_cfa_projection
    ):
        raise ValueError("Precision probe requires the original mature anchored RGB path")
    network = model.pretrained_rgb.network
    previous = network.hidden_autocast
    if previous:
        raise ValueError("Precision probe cannot hide a preexisting policy override")
    try:
        network.hidden_autocast = policy == "fp16-hidden"
        context = (
            torch.autocast("cpu", dtype=torch.float16)
            if device.type == "cpu" and policy != "fp32"
            else amp_context(device, dtype="float32" if policy == "fp32" else "float16")
        )
        with context:
            yield {
                "policy": policy,
                "hidden_autocast_override": network.hidden_autocast,
                "CPU_half_emulation_only": device.type == "cpu" and policy != "fp32",
                "physical_head_tail_inverse": "Original guarded IEEE FP32 implementation",
            }
    finally:
        network.hidden_autocast = previous
