"""Matching residual with local physical features and local output noise units."""

import torch
from torch.nn import functional as F

from .cfa import mosaic
from .late_nonlocal_residual import LateNonlocalResidualDetail
from .nonlocal_autograd import enable_sampler_autograd
from .precision import ieee_fp32


def local_noise_features(base, packed, variance, colors, wb=None):
    """Keep the39 input coordinates while removing image-wide statistics.

    RGB is centered on its own Bayer-cell mean, which is also supplied. The
    quartet's mean physical variance defines its input/output unit. This is an
    amplitude convention, not calibrated post-demosaic covariance. Everything
    here depends on one2x2 native cell and supplied camera conditioning only.
    """
    batch, phases, height, width = packed.shape
    if phases != 4 or variance.shape != packed.shape:
        raise ValueError("Expected matching four-phase RAW and variance")
    if base.shape != (batch, 3, height * 2, width * 2):
        raise ValueError("Expected aligned native camera RGB")
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    if colors.shape != (batch, 4):
        raise ValueError("Expected one four-phase CFA per image")
    if wb is None:
        wb = base.new_ones(batch, 3)
    wb = torch.as_tensor(wb, dtype=base.dtype, device=base.device)
    if wb.shape == (3,):
        wb = wb[None].expand(batch, -1)
    if wb.shape != (batch, 3):
        raise ValueError("Expected three white-balance values per image")
    positive = variance.clamp_min(0)
    sigma = positive.mean(1, keepdim=True).sqrt()
    unit = sigma.clamp_min(16 / 65535)
    rgb = F.pixel_unshuffle(base, 2).reshape(batch, 3, 4, height, width)
    mean = rgb.mean(2)
    centered = (rgb - mean[:, :, None]).flatten(1, 2) / unit
    innovation = (packed - mosaic(base, colors)) / unit
    noise = torch.log1p(positive / unit.square())
    layout = F.one_hot(colors, 3).flatten(1).to(base.dtype)[:, :, None, None]
    layout = layout.expand(-1, -1, height, width)
    balance = wb.clamp_min(1e-6).log()[:, :, None, None].expand(-1, -1, height, width)
    condition = torch.cat((layout, (mean / unit).asinh(), balance, (unit * 65535).log()), 1)
    features = torch.cat((centered.asinh(), innovation.asinh(), noise, condition), 1)
    native_sigma = sigma.repeat_interleave(2, -2).repeat_interleave(2, -1)
    return features, native_sigma


class LateLocalNoiseMatchingDetail(LateNonlocalResidualDetail):
    """V171's exact initial weights with local inputs and output amplitude.

    No global mean/noise statistic enters the new feature transform. The frozen
    V169 component and the matching network can still use spatial context.
    Zero local supplied variance retains V169 at that cell, including mixed
    batches. This does not guarantee safety or correct detail in noisy regions.
    """

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
            evaluated = bool(torch.any(sigma > 0))
            if evaluated:
                if torch.is_grad_enabled():
                    enable_sampler_autograd()
                correction = F.pixel_shuffle(self.network(features), 2) * sigma
                output = torch.where(sigma > 0, restored + correction, restored)
            else:
                correction = torch.zeros_like(restored)
                output = restored
            if return_aux:
                return output, {
                    "frozen_output": restored,
                    "correction": correction,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                }
            return output
