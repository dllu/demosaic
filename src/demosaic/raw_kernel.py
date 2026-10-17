"""Feature-conditioned RAW reconstruction with constant-color-preserving differences.

This is an experimental discrete single-frame head, not an ACKN implementation.
Each learned term multiplies a difference between same-color sensor samples.
Consequently it cannot add an RGB offset to a clean constant-color Bayer field.
This does not imply unbiased estimates for noisy inputs or a quality improvement.
"""

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear
from .precision import ieee_fp32


def constant_preserving_box_mean(value, window):
    """Replicated separable box mean evaluated as differences from each center.

    Algebraically this is a box average. Subtracting before accumulating keeps
    an exactly constant phase exactly unchanged in FP32, including borders.
    """
    if type(window) is not int or window < 1 or window % 2 != 1:
        raise ValueError("RAW kernel windows must be positive odd integers")
    if window == 1:
        return value
    radius = window // 2
    for axis in [-1, -2]:
        height, width = value.shape[-2:]
        padding = (radius, radius, 0, 0) if axis == -1 else (0, 0, radius, radius)
        padded = F.pad(value, padding, mode="replicate")
        difference = torch.zeros_like(value)
        for start in range(window):
            if start == radius:
                continue
            neighbor = (
                padded[..., start : start + width]
                if axis == -1
                else padded[..., start : start + height, :]
            )
            difference = difference + (neighbor - value)
        value = value + difference / window
    return value


class AdaptiveRawKernel(nn.Module):
    """Bilinear baseline plus learned, same-color-centered RAW sample differences.

    Three spatial supports provide local detail and wider noise averages. A
    native-grid feature map predicts signed coefficients; all final filtering
    stays in camera-linear IEEE FP32. Coefficients are bounded by tanh, but the
    resulting filter need not be positive or noise-unbiased.
    """

    def __init__(self, feature_channels, windows=(1, 5, 17)):
        super().__init__()
        windows = tuple(windows)
        if (
            not windows
            or windows[0] != 1
            or any(type(w) is not int or w < 1 or w % 2 != 1 for w in windows)
            or tuple(sorted(set(windows))) != windows
        ):
            raise ValueError(
                "RAW kernel windows must start at 1 and be distinct increasing odd integers"
            )
        self.windows = windows
        self.coefficients = nn.Conv2d(feature_channels, 3 * len(windows) * 4 * 9, 1)
        nn.init.zeros_(self.coefficients.weight)
        nn.init.zeros_(self.coefficients.bias)

    def forward(self, packed, colors, features):
        if packed.ndim != 4 or packed.shape[1] != 4:
            raise ValueError("Expected four packed Bayer phases")
        batch, _, height, width = packed.shape
        if features.shape[0] != batch or features.shape[-2:] != (height * 2, width * 2):
            raise ValueError("RAW kernel features must use the native RGB grid")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Expected four CFA color labels per image")
        with torch.autocast(device_type=packed.device.type, enabled=False), ieee_fp32():
            raw = packed.float()
            # Use an actual sample, rather than a rounded local mean, as the
            # reference for each input color. The first green phase is arbitrary;
            # coefficients can use both green phases through their differences.
            channels = torch.arange(3, device=raw.device)[None, :, None]
            phase = (colors[:, None] == channels).long().argmax(-1)
            reference = raw.gather(1, phase[..., None, None].expand(-1, -1, height, width))
            reference = reference.gather(1, colors[..., None, None].expand(-1, -1, height, width))
            reference = reference.repeat_interleave(2, -2).repeat_interleave(2, -1)
            coefficients = (
                self.coefficients(features.float())
                .tanh()
                .reshape(batch, 3, len(self.windows), 4, 9, height * 2, width * 2)
            )
            prediction = bilinear(raw, colors)
            for index, window in enumerate(self.windows):
                pooled = constant_preserving_box_mean(raw, window)
                samples = F.unfold(F.pad(pooled, (1, 1, 1, 1), mode="replicate"), 3)
                samples = samples.reshape(batch, 4, 9, height, width)
                samples = samples.repeat_interleave(2, -2).repeat_interleave(2, -1)
                differences = samples - reference[:, :, None]
                prediction = prediction + torch.einsum(
                    "bopkhw,bpkhw->bohw", coefficients[:, :, index], differences
                )
            return prediction
