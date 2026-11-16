"""Training-only local RMS regret relative to a supplied frozen parent.

Targets only define the loss. This is not an inference gate or a flat-safety
guarantee. A lower whole-image error can coexist with worse local quiet regions.
"""

import math

import torch
from torch.nn import functional as F


def local_rms_regret(output, parent, target, scale, *, window=32, floor_DN16=1.0):
    """Stable smoothed local RMS(output) minus RMS(parent), in noise units.

    Native RGB boxes overlap by half their width. Replicated edge padding uses
    the same half-hop grid for every image, including nondivisible rectangles.
    The 1-DN16 default rounds the RMS norm, not the image. Physical noise scales
    provide training units, not calibrated confidence or expected excess risk.
    Parent, target and scales are detached; only output receives a derivative.
    """
    if output.ndim != 4 or output.shape[1] != 3 or min(output.shape) < 1:
        raise ValueError("Expected a nonempty N x 3 x H x W output")
    if parent.shape != output.shape or target.shape != output.shape:
        raise ValueError("Output, frozen parent and target must have identical RGB shapes")
    if scale.shape != (len(output), 1, 1, 1):
        raise ValueError("Expected one positive scalar scale per image")
    if type(window) is not int or window < 2 or window % 2:
        raise ValueError("Window must be an even integer at least two")
    if not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("RMS rounding must be positive and finite")
    if not all(v.is_floating_point() for v in (output, parent, target, scale)):
        raise ValueError("Expected floating-point values")
    if not torch.isfinite(scale).all() or not (scale > 0).all():
        raise ValueError("Scales must be positive and finite")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        value = output.to(dtype)
        base, clean, units = [v.detach().to(dtype) for v in (parent, target, scale)]
        before = (base - clean) / units
        delta = (value - base) / units
        after = (value - clean) / units
        hop = window // 2
        height, width = output.shape[-2:]
        padding = (hop, hop + (-width % hop), hop, hop + (-height % hop))

        def local_mean(v):
            return F.avg_pool2d(
                F.pad(v.mean(1, keepdim=True), padding, mode="replicate"), window, stride=hop
            )

        # Avoid subtracting two almost equal large squared errors or RMS values.
        difference = local_mean(delta * (2 * before + delta))
        rounding = (floor_DN16 / 65535 / units).square()
        old_norm = (local_mean(before.square()) + rounding).sqrt()
        new_norm = (local_mean(after.square()) + rounding).sqrt()
        return difference / (old_norm + new_norm)


def local_excess_risk(output, parent, target, scale, *, window=32, transition=1e-4):
    """Mean C1 hinge of local RMS regret; improving boxes receive zero penalty.

    Transition is in noise-normalized RMS units. Gradient is zero at unchanged
    parent output and grows linearly through [0, transition], then stays one.
    Its nonnegativity does not guarantee local safety on unobserved inputs.
    """
    if not math.isfinite(transition) or transition <= 0:
        raise ValueError("Hinge transition must be positive and finite")
    regret = local_rms_regret(output, parent, target, scale, window=window)
    positive = regret.clamp_min(0)
    return torch.where(
        positive < transition,
        positive.square() / (2 * transition),
        positive - transition / 2,
    ).mean()
