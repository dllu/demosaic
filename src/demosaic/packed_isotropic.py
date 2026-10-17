"""Experimental RAW-native, quarter-resolution restoration trunk.

Pixel unshuffle rearranges samples without averaging. A half-resolution path
retains all four CFA phases, while an isotropic trunk handles spatial context.
This is an independent design using this project's existing gated blocks,
informed by Fan & Zhang's JD3Net (WACVW 2026), not an upstream reproduction.
"""

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear
from .color import render
from .model import GatedBlock
from .precision import ieee_fp32


def physical_features(packed, variance, colors, wb=None, matrix=None):
    """Fixed camera-linear coordinates, without per-image extrema/statistics."""
    batch, _, height, width = packed.shape
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed, variance = packed.float(), variance.float()
        labels = F.one_hot(colors, 3).float().flatten(1)
        balance = packed.new_ones(batch, 3) if wb is None else wb.to(packed).reshape(-1, 3)
        transform = (
            torch.eye(3, device=packed.device)[None]
            if matrix is None
            else matrix.to(packed).reshape(-1, 3, 3)
        )
        metadata = torch.cat(
            (
                labels,
                balance.expand(batch, -1).clamp_min(1e-6).log2(),
                transform.expand(batch, -1, -1).flatten(1),
            ),
            dim=1,
        )
        noise = (variance.clamp_min(1e-12).log() + 12) / 6
        return torch.cat(
            (packed, noise, metadata[:, :, None, None].expand(-1, -1, height, width)), 1
        )


class PackedIsotropic(nn.Module):
    """Predict a camera-RGB residual; never construct native dense kernels."""

    def __init__(self, width=96, groups=6, blocks=8, local_width=32):
        super().__init__()
        if any(type(x) is not int or x < 1 for x in (width, groups, blocks, local_width)):
            raise ValueError("Packed isotropic widths/groups/blocks must be positive integers")
        if min(width, local_width) < 4:
            raise ValueError("Packed isotropic widths must be at least four")
        self.local_stem = nn.Conv2d(32, local_width, 3, padding=1)
        self.local_blocks = nn.Sequential(*(GatedBlock(local_width) for _ in range(2)))
        self.stem = nn.Conv2d(128, width, 3, padding=1)
        self.groups = nn.ModuleList(
            nn.Sequential(
                *(GatedBlock(width) for _ in range(blocks)),
                nn.Conv2d(width, width, 3, padding=1),
            )
            for _ in range(groups)
        )
        self.up = nn.Sequential(nn.Conv2d(width, 4 * local_width, 1), nn.PixelShuffle(2))
        self.decoder = nn.Sequential(*(GatedBlock(local_width) for _ in range(2)))
        self.head = nn.Conv2d(local_width, 12, 3, padding=1)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, packed, variance, colors, wb=None, matrix=None, context=None):
        height, width = packed.shape[-2:]
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            baseline = bilinear(packed, colors)
            inputs = physical_features(packed, variance, colors, wb, matrix)
            # Extend whole packed cells; native CFA phase remains unchanged.
            inputs = F.pad(inputs, (0, -width % 2, 0, -height % 2), mode="replicate")
            local = self.local_stem(inputs)
            x = self.stem(F.pixel_unshuffle(inputs, 2))
        local = self.local_blocks(local)
        if context is not None:
            x = x + context(render(baseline, wb, matrix, fp32=True), x.shape[-2:])
        for group in self.groups:
            x = x + 0.1 * group(x)
        x = self.decoder(local + self.up(x).float())[..., :height, :width]
        # The measured signal skip and final residual arithmetic preserve FP32
        # precision even when the internal spatial blocks run in BF16/FP16.
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            return baseline + F.pixel_shuffle(self.head(x.float()), 2)
