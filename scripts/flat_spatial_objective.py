"""Training-only spatial-error supervision inside clean flat neighborhoods."""

import math

import torch
from nonlocal_residual_objective import objective as previous_objective
from torch.nn import functional as F


def flat_spatial_error_loss(output, target, mask, *, window=17, unit_DN16=4):
    """Pseudo-Huber of local error variance, with fixed DN16 training units.

    The mask is the existing clean-target neighborhood-range mask. Each selected
    center supervises the spatial error in that same truncated window. Channel
    means are removed independently, so uniform RGB error remains the job of
    the absolute/DC losses. Actual target gradients are retained, never zeroed.
    The whole-image mean keeps mask coverage as a weight. FP64 centered moments
    avoid cancellation from a large spatially constant color error; separable
    pooling avoids materializing windows. This is not an inference flat gate.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape) < 1
        or target.shape != output.shape
        or not output.is_floating_point()
        or not target.is_floating_point()
        or target.device != output.device
        or not torch.isfinite(output).all()
        or not torch.isfinite(target).all()
    ):
        raise ValueError("Expected matching finite floating-point N x 3 x H x W RGB")
    if (
        mask.dtype != torch.bool
        or mask.shape != (len(output), 1, *output.shape[-2:])
        or mask.device != output.device
    ):
        raise ValueError("Expected a matching boolean clean-neighborhood mask")
    if type(window) is not int or window < 1 or window % 2 != 1:
        raise ValueError("Window must be a positive odd integer")
    if isinstance(unit_DN16, bool) or not math.isfinite(unit_DN16) or unit_DN16 <= 0:
        raise ValueError("Spatial error units must be positive and finite")
    with torch.autocast(output.device.type, enabled=False):
        error = (output.double() - target.detach().double()) / (unit_DN16 / 65535)
        centered = error - error[..., :1, :1].detach()
        radius = window // 2

        def mean(value):
            value = F.avg_pool2d(
                value, (1, window), stride=1, padding=(0, radius), count_include_pad=False
            )
            return F.avg_pool2d(
                value, (window, 1), stride=1, padding=(radius, 0), count_include_pad=False
            )

        power = (mean(centered.square()) - mean(centered).square()).clamp_min(0)
        loss = (power / ((power + 1).sqrt() + 1) * mask).mean()
        return loss.to(torch.float64 if output.dtype == torch.float64 else torch.float32)


def objective(output, frozen, batch, pair_units, domain_weight):
    """Retain all seven V180 terms and add one flat spatial-error term at 0.25."""
    loss, terms, mask = previous_objective(output, frozen, batch, pair_units, domain_weight)
    spatial = flat_spatial_error_loss(output, batch["target"], mask, window=17, unit_DN16=4)
    return loss + (0.25 * domain_weight) * spatial, dict(terms, flat_spatial=spatial), mask
