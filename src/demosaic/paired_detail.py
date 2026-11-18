"""Native luminance correction conditioned on the frozen parent's Bayer residual."""

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import mosaic


def fine_band(field):
    """Remove a narrow local mean without treating the frame border as black."""
    local = F.avg_pool2d(field, kernel_size=5, stride=1, padding=2, count_include_pad=False)
    return field - local


class DetailBlock(nn.Module):
    def __init__(self, width, dilation):
        super().__init__()
        self.spatial = nn.Conv2d(width, width, 3, padding=dilation, dilation=dilation)
        self.channel = nn.Conv2d(width, width, 1)

    def forward(self, field):
        return field + self.channel(F.silu(self.spatial(field)))


class PairedLuminanceDetail(nn.Module):
    """Give a frozen joint restorer a bounded, noise-conditioned luminance lift."""

    def __init__(self, width=32):
        super().__init__()
        self.stem = nn.Conv2d(14, width, 3, padding=1)
        self.blocks = nn.Sequential(*(DetailBlock(width, d) for d in (1, 2, 4, 2)))
        self.output = nn.Conv2d(width, 8, 3, padding=1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)
        self.register_buffer("luma", torch.tensor([0.2126, 0.7152, 0.0722]), persistent=False)

    def scene_luma(self, camera, wb, matrix):
        weights = torch.einsum("i,bij->bj", self.luma, matrix) * wb
        return (camera * weights[:, :, None, None]).sum(dim=1, keepdim=True)

    def luminance_delta(self, parent, packed, variance, colors, wb, matrix):
        sigma = variance.clamp_min(1e-10).sqrt()
        average_sigma = sigma.mean(dim=1, keepdim=True)
        guide = F.avg_pool2d(self.scene_luma(parent, wb, matrix), 2)
        guide_mid = F.avg_pool2d(guide, 17, stride=1, padding=8, count_include_pad=False)
        residual = (packed - mosaic(parent, colors)) / sigma
        color_codes = 0.5 * colors[:, :, None, None].to(packed.dtype).expand_as(packed)
        frames = torch.cat(
            (
                residual.clamp(-12, 12),
                sigma.log().clamp(-12, 0) / 8,
                color_codes,
                (guide_mid.clamp_min(0) + 1e-4).log().clamp(-10, 1) / 4,
                ((guide - guide_mid) / average_sigma).clamp(-12, 12),
            ),
            dim=1,
        )
        activation = self.output(self.blocks(F.silu(self.stem(frames))))
        detail, confidence = F.pixel_shuffle(activation, 2).split(1, dim=1)
        scale = 0.5 * F.interpolate(average_sigma, scale_factor=2, mode="nearest")
        width = 7
        saturated = (packed >= 0.98).any(dim=1, keepdim=True).to(packed.dtype)
        quiet_clipping = 1 - F.max_pool2d(saturated, width, stride=1, padding=width // 2)
        valid = F.interpolate(quiet_clipping, scale_factor=2, mode="nearest")
        return fine_band(detail.tanh() * confidence.sigmoid() * scale) * valid

    def forward(self, parent, packed, variance, colors, wb, matrix):
        delta = self.luminance_delta(parent, packed, variance, colors, wb, matrix)
        neutral = torch.ones_like(wb).unsqueeze(-1)
        direction = torch.linalg.solve(matrix, neutral).squeeze(-1) / wb
        return parent + direction[:, :, None, None] * delta
