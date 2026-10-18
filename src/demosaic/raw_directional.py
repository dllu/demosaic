"""A zero-initialized, measurement-derived residual around a mature RGB model."""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear, mosaic
from .precision import ieee_fp32

DIRECTIONS = ((0, 0), (0, 1), (1, 0), (1, 1), (1, -1))


def line_mean(value, direction, window=33):
    """Average same-phase samples along a line, preserving constants exactly."""
    if type(window) is not int or window < 1 or window % 2 != 1:
        raise ValueError("Directional window must be a positive odd integer")
    if direction not in DIRECTIONS:
        raise ValueError("Unknown RAW averaging direction")
    if direction == (0, 0) or window == 1:
        return value
    radius = window // 2
    height, width = value.shape[-2:]
    padded = F.pad(value, (radius,) * 4, mode="replicate")
    differences = torch.zeros_like(value)
    dy, dx = direction
    for step in range(-radius, radius + 1):
        if step:
            y, x = radius + step * dy, radius + step * dx
            differences = differences + (padded[..., y : y + height, x : x + width] - value)
    return value + differences / window


class RawDirectionalResidual(nn.Module):
    """Learn signed directional innovations and an ADC-censored color correction.

    Every fixed candidate uses measured same-CFA-phase samples. A small local
    network sees noise-unit innovation, variance and explicit CFA labels alongside
    the existing RGB/DINO-conditioned features. No target enters the forward.
    Zero heads preserve the complete parent prediction and common global RNG.
    Data-dependent filters are not claimed to be statistically unbiased.
    """

    def __init__(self, *, bank_context=False):
        super().__init__()
        if type(bank_context) is not bool:
            raise ValueError("Directional bank context must be a boolean")
        with torch.random.fork_rng(devices=[]):
            self.local = nn.Sequential(
                nn.Conv2d(20, 32, 3, padding=1, padding_mode="replicate"),
                nn.GELU(),
                nn.Conv2d(32, 64, 3, padding=1, padding_mode="replicate"),
                nn.GELU(),
                nn.PixelShuffle(2),
            )
        channels = 67 + 16
        # Direct zero parameters avoid random initialization/extra RNG draws.
        self.mix_weight = nn.Parameter(torch.zeros(3 * len(DIRECTIONS), channels, 1, 1))
        self.mix_bias = nn.Parameter(torch.zeros(3 * len(DIRECTIONS)))
        self.censored_weight = nn.Parameter(torch.zeros(3, channels, 1, 1))
        self.censored_bias = nn.Parameter(torch.zeros(3))
        self.bank = None
        if bank_context:
            # A separate zero logit correction preserves trained directional
            # heads too. The same measured candidate bank is reused below.
            with torch.random.fork_rng(devices=[]):
                self.bank = nn.Sequential(
                    nn.Conv2d(4 * len(DIRECTIONS), 32, 3, padding=1, padding_mode="replicate"),
                    nn.GELU(),
                    nn.Conv2d(32, 64, 3, padding=1, padding_mode="replicate"),
                    nn.GELU(),
                    nn.PixelShuffle(2),
                    nn.Conv2d(16, 3 * len(DIRECTIONS), 1),
                )
            nn.init.zeros_(self.bank[-1].weight)
            nn.init.zeros_(self.bank[-1].bias)

    def forward(self, base, packed, variance, colors, features):
        batch, phases, height, width = packed.shape
        if phases != 4 or base.shape != (batch, 3, height * 2, width * 2):
            raise ValueError("Directional residual needs matching packed CFA and native RGB")
        if variance.shape != packed.shape or features.shape != (batch, 67, height * 2, width * 2):
            raise ValueError("Directional residual variance/features have incompatible shape")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            base, packed, variance = base.float(), packed.float(), variance.float()
            measured_base = mosaic(base, colors)
            sample_std = variance.clamp_min(1e-8).sqrt()
            innovation = ((packed - measured_base) / sample_std).clamp(-8, 8)
            noise = (variance.clamp_min(1e-8).log() + 12) / 6
            labels = (
                F.one_hot(colors, 3)
                .float()
                .flatten(1)[:, :, None, None]
                .expand(-1, -1, height, width)
            )
            local = self.local(torch.cat((innovation, noise, labels), 1))
            context = torch.cat((features.float(), local), 1)
            logits = F.conv2d(context, self.mix_weight, self.mix_bias)
            # Keep the legacy path's operation order when the option is off.
            if self.bank is None:
                weights = logits.tanh().reshape(
                    batch, len(DIRECTIONS), 3, height * 2, width * 2
                ) / math.sqrt(len(DIRECTIONS))
            candidates = torch.cat([line_mean(packed, direction) for direction in DIRECTIONS], 0)
            if self.bank is not None:
                # Scale by the original measured-sample noise, not a claimed
                # calibrated error variance for the correlated candidate/base.
                bank_input = (
                    (
                        (
                            candidates.reshape(len(DIRECTIONS), batch, 4, height, width)
                            - measured_base[None]
                        )
                        / sample_std[None]
                    )
                    .clamp(-8, 8)
                    .permute(1, 0, 2, 3, 4)
                    .reshape(batch, 4 * len(DIRECTIONS), height, width)
                )
                weights = (logits + self.bank(bank_input)).tanh().reshape(
                    batch, len(DIRECTIONS), 3, height * 2, width * 2
                ) / math.sqrt(len(DIRECTIONS))
            candidates = bilinear(candidates, colors.repeat(len(DIRECTIONS), 1))
            candidates = candidates.reshape(
                len(DIRECTIONS), batch, 3, height * 2, width * 2
            ).transpose(0, 1)
            residual = (weights * (candidates - base[:, None])).sum(1)
            gate = bilinear((packed >= 1 - 0.5 / 65535).float(), colors)
            censored = F.conv2d(context, self.censored_weight, self.censored_bias)
            return base + residual + gate * censored
