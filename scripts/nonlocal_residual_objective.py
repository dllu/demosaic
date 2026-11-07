"""Paired weak-detail reconstruction with absolute and local flat-error losses.

Targets, pair membership and clean flat masks are used only after inference.
This objective does not establish noisy-flat safety on unseen observations.
"""

from flat_target_anchor import flat_target_anchor_loss, flat_target_mask
from local_excess_risk import local_excess_risk
from paired_common_objective import paired_common_error_loss
from paired_response_objective import paired_response_loss
from regional_dc_objective import regional_dc_excess


def objective(output, frozen, batch, pair_units, domain_weight):
    target = batch["target"]
    scale = batch["variance"].clamp_min(0).mean((1, 2, 3), keepdim=True).sqrt()
    scale = scale.clamp_min(16 / 65535)
    error = (output - target) / scale
    pixel = (error.square() + 0.01**2).sqrt().mean()
    derivatives = [error[..., 1:] - error[..., :-1], error[..., 1:, :] - error[..., :-1, :]]
    gradient = sum((v.square() + 0.003**2).sqrt().mean() for v in derivatives) / 2
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
