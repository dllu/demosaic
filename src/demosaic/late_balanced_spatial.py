"""Remove broad learned RGB displacement while retaining the spectral path."""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .late_bounded_support import LateBoundedSupportDetail
from .precision import ieee_fp32


class SpatialHighpass(nn.Module):
    """Native-pixel Gaussian complement, with replicated boundaries.

    The fixed default has sigma8 and radius24 native pixels. It operates only
    on a learned correction, not the parent image. It can remove useful coarse
    corrections too; it is not a detail detector or a flat-safety guarantee.
    Centering on one value makes every constant correction exactly zero even
    in FP32. The kernel is derived, nonpersistent and adds no trainable state.
    """

    def __init__(self, sigma=8.0, radius=24):
        super().__init__()
        if isinstance(sigma, bool) or not isinstance(sigma, (int, float)):
            raise ValueError("Expected a finite positive Gaussian sigma")
        if not math.isfinite(sigma) or sigma <= 0:
            raise ValueError("Expected a finite positive Gaussian sigma")
        if isinstance(radius, bool) or not isinstance(radius, int) or radius < 1:
            raise ValueError("Expected a positive integer Gaussian radius")
        self.sigma, self.radius = float(sigma), radius
        offsets = torch.arange(-radius, radius + 1, dtype=torch.float64)
        kernel = torch.exp(-0.5 * (offsets / sigma).square())
        self.register_buffer("kernel", kernel / kernel.sum(), persistent=False)

    def forward(self, correction):
        if correction.ndim != 4 or min(correction.shape) < 1:
            raise ValueError("Expected nonempty NCHW correction")
        if correction.dtype not in (torch.float32, torch.float64):
            raise ValueError("Expected FP32 or FP64 correction")
        with torch.autocast(correction.device.type, enabled=False), ieee_fp32():
            centered = correction - correction[..., :1, :1]
            radius, channels = self.radius, correction.shape[1]
            kernel = self.kernel.to(device=correction.device, dtype=correction.dtype)
            horizontal = kernel.view(1, 1, 1, -1).expand(channels, 1, 1, -1)
            vertical = kernel.view(1, 1, -1, 1).expand(channels, 1, -1, 1)
            value = torch.cat((centered[..., :1].expand(*centered.shape[:-1], radius),
                               centered,
                               centered[..., -1:].expand(*centered.shape[:-1], radius)), -1)
            value = F.conv2d(value, horizontal, groups=channels)
            value = torch.cat((value[..., :1, :].expand(*value.shape[:-2], radius, value.shape[-1]),
                               value,
                               value[..., -1:, :].expand(*value.shape[:-2], radius, value.shape[-1])), -2)
            lowpass_centered = F.conv2d(value, vertical, groups=channels)
            return centered - lowpass_centered


class LateBalancedSpatialDetail(LateBoundedSupportDetail):
    """V168 weights with a fixed balanced direct RGB path; no added weights.

    Training and held-out references never enter this forward. Disabled mode
    returns the original result and auxiliaries bit-for-bit for replay checks.
    Trained V168 states load strictly; transfer quality is measured separately
    from any future training with the constrained path.
    """

    def __init__(self, max_window=256, support_floor=0.25, balance_spatial=True):
        if not isinstance(balance_spatial, bool):
            raise ValueError("Expected Boolean balance_spatial")
        super().__init__(max_window, support_floor)
        self.balance_spatial = balance_spatial
        self.spatial_highpass = SpatialHighpass()

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        output, aux = super().forward(base, packed, variance, colors, wb, return_aux=True)
        if not self.balance_spatial:
            return (output, aux) if return_aux else output
        spatial = aux["spatial_correction"]
        balanced = self.spatial_highpass(spatial)
        result = base + aux["spectral_correction"] + balanced
        if return_aux:
            aux["unbalanced_output"] = output
            aux["unbalanced_spatial_correction"] = spatial
            aux["spatial_correction"] = balanced
            aux["correction"] = aux["spectral_correction"] + balanced
            return result, aux
        return result
