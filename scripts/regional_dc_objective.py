"""Training-only penalty for increases in regional camera-RGB mean error."""

import math

import torch
from torch.nn import functional as F


def regional_dc_regret(output, parent, target, scale, *, window=32):
    """Smoothed RGB bias-norm difference on the inherited overlapping box grid.

    Units are max(scale / (window/2), 1 DN16), using the nominal square root
    count of one Bayer phase in an interior box. This gives mean-error pressure
    stronger units than pixel error; it is not post-demosaic covariance or a
    calibrated boundary-noise estimate. Norm smoothing is independently 1 DN16.
    Parent, target and units are detached. No target/reference enters inference.
    """
    if output.ndim != 4 or output.shape[1] != 3 or min(output.shape) < 1:
        raise ValueError("Expected nonempty N x 3 x H x W camera RGB")
    if parent.shape != output.shape or target.shape != output.shape:
        raise ValueError("Output, parent and target RGB shapes must match")
    if scale.shape != (len(output), 1, 1, 1):
        raise ValueError("Expected one positive noise scale per image")
    if type(window) is not int or window < 2 or window % 2:
        raise ValueError("Window must be an even integer at least two")
    if not all(v.is_floating_point() for v in (output, parent, target, scale)):
        raise ValueError("Expected floating-point RGB and scales")
    if not torch.isfinite(scale).all() or not (scale > 0).all():
        raise ValueError("Noise scales must be positive and finite")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        value = output.to(dtype)
        base, clean, units = [v.detach().to(dtype) for v in (parent, target, scale)]
        units = (units / (window / 2)).clamp_min(1 / 65535)
        hop = window // 2
        height, width = value.shape[-2:]
        padding = (hop, hop + (-width % hop), hop, hop + (-height % hop))

        def mean_error(v):
            return F.avg_pool2d(F.pad(v, padding, mode="replicate"), window, stride=hop) / units

        before = mean_error(base - clean)
        delta = mean_error(value - base)
        after = mean_error(value - clean)
        # Rationalization preserves small positive changes in an existing bias.
        numerator = (delta * (2 * before + delta)).mean(1, keepdim=True)
        rounding = (1 / 65535 / units).square()
        old_norm = (before.square().mean(1, keepdim=True) + rounding).sqrt()
        new_norm = (after.square().mean(1, keepdim=True) + rounding).sqrt()
        return numerator / (old_norm + new_norm)


def regional_dc_excess(output, parent, target, scale, *, window=32, transition=1e-4):
    """Mean C1 positive hinge of regional bias regret; improvements are free.

    This soft empirical term cannot prevent redistribution within a box, fix
    an incorrect parent by itself, or guarantee quiet-region safety. The base
    RGB/local-error terms still supervise zero-mean texture and spatial error.
    """
    if not math.isfinite(transition) or transition <= 0:
        raise ValueError("Hinge transition must be positive and finite")
    regret = regional_dc_regret(output, parent, target, scale, window=window)
    positive = regret.clamp_min(0)
    return torch.where(
        positive < transition, positive.square() / (2 * transition), positive - transition / 2
    ).mean()
