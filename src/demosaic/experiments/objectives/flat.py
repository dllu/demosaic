"""Training-only absolute RGB supervision inside locally flat clean targets."""

import math

import torch
from torch.nn import functional as F


def _rgb(value):
    return (
        value.ndim == 4
        and value.shape[1] == 3
        and min(value.shape) > 0
        and value.is_floating_point()
    )


@torch.no_grad()
def flat_target_mask(target, *, window=17, tolerance_DN16=1):
    """Select pixels whose truncated neighborhood range is small in every RGB channel.

    Channel offsets are preserved: a spatially constant colored field qualifies.
    The clean target supplies a training weight, never an inference input. A
    selected weak gradient is still supervised against its actual target rather
    than replaced with a constant. Separable maxima/minima are exact, including
    image borders; no averaging or variance cancellation defines eligibility.
    """
    if not _rgb(target) or not torch.isfinite(target).all():
        raise ValueError("Expected finite nonempty N x 3 x H x W clean targets")
    if not isinstance(window, int) or window < 1 or window % 2 != 1:
        raise ValueError("Flat-target window must be a positive odd integer")
    if not math.isfinite(tolerance_DN16) or tolerance_DN16 < 0:
        raise ValueError("Flat-target tolerance must be finite and nonnegative")
    value = target.detach().to(torch.float64 if target.dtype == torch.float64 else torch.float32)
    radius = window // 2

    def maximum(x):
        x = F.max_pool2d(x, (1, window), stride=1, padding=(0, radius))
        return F.max_pool2d(x, (window, 1), stride=1, padding=(radius, 0))

    ranges = maximum(value) + maximum(-value)
    return ranges.amax(1, keepdim=True) <= tolerance_DN16 / 65535


def flat_target_anchor_loss(output, target, mask, *, unit_DN16=16):
    """Mean pseudo-Huber RGB target error at fixed DN16 units under a clean mask.

    rho(z)=sqrt(1+z^2)-1, evaluated without small-error cancellation. The mean
    includes all image elements, so mask coverage controls the term's weight;
    an almost empty mask does not receive the weight of a completely flat image.
    Targets detach. This complements pair differences by penalizing common RGB
    errors in eligible regions, without penalizing corrections toward the target.
    """
    if not _rgb(output) or not _rgb(target) or output.shape != target.shape:
        raise ValueError("Expected matching nonempty floating-point RGB tensors")
    if output.device != target.device or mask.device != output.device:
        raise ValueError("Output, target and mask must share a device")
    if mask.dtype != torch.bool or mask.shape != (len(output), 1, *output.shape[-2:]):
        raise ValueError("Expected an N x 1 x H x W boolean eligibility mask")
    if not math.isfinite(unit_DN16) or unit_DN16 <= 0:
        raise ValueError("Anchor units must be positive and finite")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        error = (output.to(dtype) - target.detach().to(dtype)) / (unit_DN16 / 65535)
        power = error.square()
        return (power / ((power + 1).sqrt() + 1) * mask).mean()
