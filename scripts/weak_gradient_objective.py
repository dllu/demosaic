"""Training-only amplitude-balanced gradient supervision above frozen V169.

Clean gradients define loss weights only. They never enter the model, and the
loss does not guarantee absence of false structure on unseen noisy inputs.
"""

import math

import torch
from flat_target_anchor import flat_target_anchor_loss, flat_target_mask
from local_excess_risk import local_excess_risk
from paired_common_objective import paired_common_error_loss
from paired_response_objective import paired_response_loss
from regional_dc_objective import regional_dc_excess


def weak_gradient_loss(output, target, *, floor_DN16=2.0):
    """Pseudo-Huber gradient error in local clean-gradient RMS units.

    Each horizontal/vertical edge has one RGB RMS unit, rounded by a 2-DN16
    floor. Weak and zero clean gradients receive the largest weights; strong
    edges retain pixel/pair supervision. The transition is one such unit.
    Physical derivatives are taken before normalization, so changing units do
    not introduce an artificial derivative of a constant RGB error.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape[-2:]) < 2
        or target.shape != output.shape
        or not output.is_floating_point()
        or not target.is_floating_point()
        or target.device != output.device
    ):
        raise ValueError("Expected matching floating-point N x 3 x H x W RGB, H/W >= 2")
    if isinstance(floor_DN16, bool) or not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("Gradient unit floor must be positive and finite")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        value = output.to(dtype)
        clean = target.detach().to(dtype)
        error = value - clean
        losses = []
        for axis in [-1, -2]:
            clean_gradient = clean.diff(dim=axis)
            units = (
                clean_gradient.square().mean(1, keepdim=True) + (floor_DN16 / 65535) ** 2
            ).sqrt()
            residual = error.diff(dim=axis) / units
            power = residual.square()
            losses.append((power / ((power + 1).sqrt() + 1)).mean())
        return sum(losses) / 2


def objective(output, frozen, batch, pair_units, domain_weight):
    """Keep V172's seven-term recipe; replace only gradient reconstruction."""
    target = batch["target"]
    scale = batch["variance"].clamp_min(0).mean((1, 2, 3), keepdim=True).sqrt()
    scale = scale.clamp_min(16 / 65535)
    error = (output - target) / scale
    pixel = (error.square() + 0.01**2).sqrt().mean()
    gradient = weak_gradient_loss(output, target, floor_DN16=2)
    local = local_excess_risk(output, frozen, target, scale, window=32, transition=1e-4)
    dc = regional_dc_excess(output, frozen, target, scale, window=32, transition=1)
    mask = flat_target_mask(target, window=17, tolerance_DN16=1)
    flat = flat_target_anchor_loss(output, target, mask, unit_DN16=16)
    pair = output.new_zeros(())
    common = output.new_zeros(())
    if len(batch["pair_indices"]):
        pair = paired_response_loss(
            output, target, pair_units, batch["pair_indices"], epsilon=0.003
        )
        common = paired_common_error_loss(output, target, batch["pair_indices"], unit_DN16=16)
    terms = {
        "pixel": pixel,
        "gradient": gradient,
        "local_regret": local,
        "DC_regret": dc,
        "flat_anchor": flat,
        "pair_difference": pair,
        "pair_common": common,
    }
    loss = domain_weight * (pixel + 0.25 * gradient + local + dc + 0.25 * flat + pair + common)
    return loss, terms, mask
