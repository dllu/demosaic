"""Bound local spectral attenuation while preserving a half-open initializer."""

import math

import torch
from torch.nn import functional as F

from .cfa import malvar, mosaic
from .late_harmonic_phase import LateHarmonicPhaseDetail
from .precision import ieee_fp32


def validate_support_floor(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Support floor must be a finite scalar in [0, 0.5)")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value < 0.5:
        raise ValueError("Support floor must be a finite scalar in [0, 0.5)")
    return value


def bounded_support(logits, floor=0.25):
    """floor+(1-floor)*sigmoid(logits+log(1-2*floor)).

    Zero logits give support0.5 in exact arithmetic for every allowed floor.
    The zero-floor branch is the original sigmoid, including its value bits.
    A positive floor limits local attenuation; frequency gains can still vanish
    and the direct RGB path can cancel a correction. This is not confidence,
    guaranteed delivered detail or flat-field safety.
    """
    floor = validate_support_floor(floor)
    if logits.dtype not in (torch.float32, torch.float64) or not logits.numel():
        raise ValueError("Expected nonempty FP32 or FP64 support logits")
    if floor == 0:
        return logits.sigmoid()
    return floor + (1 - floor) * (logits + math.log1p(-2 * floor)).sigmoid()


class LateBoundedSupportDetail(LateHarmonicPhaseDetail):
    """Same47 weight tensors and124909 parameters;only support mapping changes.

    The spectral forward below preserves the inherited operation order. Keeping
    this isolated variant leaves all89 prior neural source files byte-identical.
    Floor0 must replay the existing head exactly, including parameter gradients.
    There is one spectral synthesis,one Malvar and one direct RGB evaluation.
    Training-only fixed-support common routing adds its existing replay outside
    this inference function. No target,reference or paired metadata enters here.
    """

    def __init__(self, max_window=256, support_floor=0.25):
        self.support_floor = validate_support_floor(support_floor)
        super().__init__(max_window)

    def _spectral_with_support(self, base, packed, variance, colors, wb):
        if packed.ndim != 4 or packed.shape[1] != 4 or packed.shape != variance.shape:
            raise ValueError("Late spectral detail needs matching four-phase RAW and variance")
        batch, _, height, width = packed.shape
        if min(batch, height, width) < 1 or min(height, width) < 4:
            raise ValueError("Late spectral detail needs at least4 packed pixels per axis")
        if base.shape != (batch, 3, 2 * height, 2 * width):
            raise ValueError("Late spectral detail needs matching native camera RGB")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Late spectral detail needs one CFA layout per image")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            base, packed, variance = base.float(), packed.float(), variance.float()
            parent = mosaic(base, colors)
            observed, geometry = self.analysis(packed)
            parent_spectrum, _ = self.analysis(parent, geometry[4])
            noise = self.noise_power(variance, geometry)
            count = geometry[5]
            layouts = colors[:, None].expand(-1, count, -1).reshape(batch * count, 4)
            innovation = observed - parent_spectrum
            gain = self.frequency_gain(observed, innovation, noise, layouts)
            spectral_delta = self.apply_frequency_gain(gain, innovation)
            proposal = self.synthesis(spectral_delta, geometry)
            local = self.local_features(packed, parent, variance, proposal, colors, observed, noise, geometry)
            local = F.silu(self.local_in(local))
            local = F.silu(self.local_middle(local))
            local = F.silu(self.local_wide(local))
            support = bounded_support(self.local_out(local), self.support_floor)
            correction = malvar(proposal * support, colors, wb)
            return base + correction, {
                "spectral_delta": spectral_delta, "parent_spectrum": parent_spectrum,
                "noise_power": noise, "geometry": geometry,
                "gain": gain, "support": support, "correction": correction,
            }

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        spectral, aux = self._spectral_with_support(base, packed, variance, colors, wb)
        correction = self.spatial_rgb(base, packed, variance, colors, wb)
        result = spectral + correction
        if return_aux:
            aux["spectral_correction"] = aux["correction"]
            aux["spatial_correction"] = correction
            aux["correction"] = aux["correction"] + correction
            return result, aux
        return result
