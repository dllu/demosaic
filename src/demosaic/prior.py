"""Variance-adaptive filtering of spatial Bayer phases before interpolation."""

import torch
from torch.nn import functional as F

from .precision import ieee_fp32


def wiener_packed(packed, variance, window=7):
    """Local linear-MMSE prior, applied independently to each sensor phase.

    The signal-power estimate subtracts the expected heteroscedastic
    noise contribution after removing the local mean. Flat regions shrink
    toward their local mean; high-contrast regions retain their measurements.
    Zero-variance samples are returned exactly. This is a prior, not a claim
    that weak texture can be distinguished perfectly from sensor noise.
    """
    if window < 3 or window % 2 == 0 or min(packed.shape[-2:]) <= window // 2:
        raise ValueError("Use an odd window >=3 smaller than twice the packed dimensions")
    if packed.shape != variance.shape:
        raise ValueError("Packed observations and variance maps must have matching shapes")
    with torch.autocast(device_type=packed.device.type, enabled=False), ieee_fp32():
        packed, variance = packed.float(), variance.float().clamp_min(0)

        def mean(x):
            radius = window // 2
            x = F.pad(x, (radius, radius, radius, radius), mode="reflect")
            return F.avg_pool2d(F.avg_pool2d(x, (1, window), stride=1), (window, 1), stride=1)

        local_mean = mean(packed)
        power = (mean(packed.square()) - local_mean.square()).clamp_min(0)
        signal = (power - mean(variance) * (1 - 1 / window**2)).clamp_min(0)
        gain = signal / (signal + variance).clamp_min(1e-12)
        filtered = local_mean + gain * (packed - local_mean)
        return torch.where(variance > 0, filtered, packed)
