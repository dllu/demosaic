"""Multiscale camera-RGB residual alongside the learned spectral estimator.

This independently implemented research path sees only observed RAW, supplied
parent RGB and physical conditioning. It can predict DC/coarse RGB corrections
without the spectral proposal's affine removal, band or Malvar color subspace.
"""

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import mosaic
from .late_spectral_relative import LateSpectralRelativeDetail
from .precision import ieee_fp32


class SpatialConv(nn.Conv2d):
    """Replicated borders using slices with deterministic CUDA backward."""

    def __init__(self, inputs, outputs):
        super().__init__(inputs, outputs, 3, device="cpu")

    def forward(self, value):
        value = torch.cat((value[..., :1], value, value[..., -1:]), -1)
        value = torch.cat((value[..., :1, :], value, value[..., -1:, :]), -2)
        return super().forward(value)


class SpatialResidualBlock(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.first = SpatialConv(width, width)
        self.second = SpatialConv(width, width)

    def forward(self, value):
        return value + self.second(F.silu(self.first(value)))


class SpatialRgbResidual(nn.Module):
    """Four packed-grid scales, phase-aligned RGB output and a zero final layer.

    The image-wide shot/read RMS supplies the output unit, with no learned
    amplitude bound. Exactly zero variance makes this new path exactly zero;
    the inherited spectral estimator is still evaluated normally. This routing
    preserves ADC behavior rather than pretending the new noisy-only path was
    supervised on ADC observations. It provides no noisy-flat safety guarantee.
    """

    def __init__(self, width=24):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(15701).get_state())
            self.input = SpatialConv(39, width)
            self.encoder = nn.ModuleList(SpatialResidualBlock(width) for _ in range(4))
            self.decoder = nn.ModuleList(SpatialResidualBlock(width) for _ in range(3))
            self.output = SpatialConv(width, 12)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    @staticmethod
    def features(base, packed, variance, colors, wb=None):
        batch, phases, height, width = packed.shape
        if phases != 4 or variance.shape != packed.shape:
            raise ValueError("Spatial RGB requires matching four-phase RAW and variance")
        if base.shape != (batch, 3, height * 2, width * 2):
            raise ValueError("Spatial RGB requires aligned native camera RGB")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Spatial RGB requires one CFA layout per image")
        if wb is None:
            wb = base.new_ones(batch, 3)
        wb = torch.as_tensor(wb, dtype=base.dtype, device=base.device)
        if wb.shape == (3,):
            wb = wb[None].expand(batch, -1)
        if wb.shape != (batch, 3):
            raise ValueError("Spatial RGB requires three white-balance values per image")
        sigma = variance.clamp_min(0).mean((1, 2, 3), keepdim=True).sqrt()
        unit = sigma.clamp_min(16 / 65535)
        mean = base.mean((-2, -1), keepdim=True)
        rgb = F.pixel_unshuffle(base - mean, 2) / unit
        innovation = (packed - mosaic(base, colors)) / unit
        noise = torch.log1p(variance.clamp_min(0) / unit.square())
        layout = F.one_hot(colors, 3).flatten(1).to(base.dtype)[:, :, None, None]
        condition = torch.cat(
            (
                layout,
                (mean / unit).asinh(),
                wb.clamp_min(1e-6).log()[:, :, None, None],
                (unit * 65535).log(),
            ),
            1,
        ).expand(-1, -1, height, width)
        return torch.cat((rgb.asinh(), innovation.asinh(), noise, condition), 1), sigma

    def forward(self, base, packed, variance, colors, wb=None):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            values, sigma = self.features(
                base.float(), packed.float(), variance.float(), colors, wb
            )
            value = F.silu(self.input(values))
            skips = []
            for index, block in enumerate(self.encoder):
                if index:
                    value = F.avg_pool2d(value, 2, ceil_mode=True, count_include_pad=False)
                value = block(value)
                skips.append(value)
            # Global context can adjust bias; no affine or mean removal follows.
            value = value + value.mean((-2, -1), keepdim=True)
            for block, skip in zip(self.decoder, reversed(skips[:-1]), strict=True):
                value = F.interpolate(
                    value, size=skip.shape[-2:], mode="bilinear", align_corners=False
                )
                value = block(value + skip)
            return F.pixel_shuffle(self.output(value), 2) * sigma


class LateSpatialRgbDetail(LateSpectralRelativeDetail):
    """Train the spectral estimator and direct RGB path together from scratch."""

    def __init__(self, max_window=256):
        super().__init__(max_window)
        self.spatial_rgb = SpatialRgbResidual()

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        spectral, aux = super().forward(base, packed, variance, colors, wb, return_aux=True)
        correction = self.spatial_rgb(base, packed, variance, colors, wb)
        result = spectral + correction
        if return_aux:
            aux["spectral_correction"] = aux["correction"]
            aux["spatial_correction"] = correction
            aux["correction"] = aux["correction"] + correction
            return result, aux
        return result
