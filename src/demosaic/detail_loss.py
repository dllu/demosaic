"""Optional clean-target band supervision; no inference-time target dependence."""

import math

import torch
from torch.nn import functional as F

from .precision import ieee_fp32


def validate_normalized_band_weight(value):
    try:
        weight = float(value)
    except (TypeError, ValueError):
        raise ValueError("Normalized band weight must be finite and nonnegative") from None
    if isinstance(value, bool) or not math.isfinite(weight) or not 0 <= weight <= torch.finfo(torch.float32).max:
        raise ValueError("Normalized band weight must be finite and nonnegative")
    return weight


def normalized_band_loss(prediction, target):
    """3×3 minus 9×9 band in native camera RGB, normalized per clean target.

    Every neighboring channel must be valid and unsaturated. The eight-pixel
    border is omitted. Scale is detached target RMS, floored at .001; the
    dimensionless Charbonnier epsilon is .1. Empty images contribute zero.
    """
    if prediction.shape != target.shape or prediction.ndim != 4 or prediction.shape[1] != 3 or min(prediction.shape[-2:]) <= 16:
        raise ValueError("Normalized band loss needs matching native B×3×H×W contexts larger than16")
    with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
        prediction, target = prediction.float(), target.detach().float()
        finite = torch.isfinite(target)
        valid = (finite & (target >= 0) & (target < .98)).all(1, keepdim=True).float()
        valid = (1-F.max_pool2d(1-valid, 9, 1, 4))[..., 8:-8, 8:-8].bool()
        safe_target = target.masked_fill(~finite, 0)
        def band(value):
            small = F.avg_pool2d(F.pad(value, (1, 1, 1, 1), mode="reflect"), 3, 1)
            large = F.avg_pool2d(F.pad(value, (4, 4, 4, 4), mode="reflect"), 9, 1)
            return (small-large)[..., 8:-8, 8:-8].masked_fill(~valid, 0)
        count = valid.flatten(1).sum(1)*3
        clean = band(safe_target)
        scale = (clean.square().flatten(1).sum(1)/count.clamp_min(1)).sqrt().clamp_min(.001)
        error = band(prediction-safe_target)/scale[:, None, None, None]
        values = ((error.square()+.1**2).sqrt()-.1).masked_fill(~valid, 0).flatten(1).sum(1)/count.clamp_min(1)
        return values.masked_fill(count == 0, 0).sum()/(count > 0).sum().clamp_min(1)
