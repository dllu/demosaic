"""Pretrained RGB restoration trunk adapted to spatially conditioned Bayer data.

The weight-compatible DRUNet topology is adapted from Noise2VST's implementation
at 02b839dae08e6304441ef9e5b3452262c36c4550, inspired by KAIR/DPIR.
Copyright (c) 2025 Sebastien Herbreteau; copyright (c) 2019 Kai Zhang.
MIT notices: third_party/gaussian/{Noise2VST-LICENSE,KAIR-LICENSE}.

The physical feature construction, per-image normalization, measurement/camera
adapter and DINO fusion are this project's experimental joint reconstruction.
This is a single-pass trainable model, not the frozen GAT/HQS comparator.
"""

import hashlib
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear, malvar
from .color import render
from .precision import ieee_fp32
from .prior import box_mean


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.res = nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, 3, padding=1, bias=False),
        )

    def forward(self, x):
        return x + self.res(x)


class RgbRestorationTrunk(nn.Module):
    """Original RGB DRUNet tensor names/topology for strict pretrained loading.

    Inputs are already normalized and padded to multiples of eight. Noise can
    vary spatially. Optional offsets start at zero in the joint model.
    """

    def __init__(self):
        super().__init__()
        self.m_head = nn.Conv2d(4, 64, 3, padding=1, bias=False)
        for level, (a, b) in enumerate(zip((64, 128, 256), (128, 256, 512)), 1):
            setattr(
                self,
                f"m_down{level}",
                nn.Sequential(
                    *(ResidualBlock(a) for _ in range(4)),
                    nn.Conv2d(a, b, 2, stride=2, bias=False),
                ),
            )
            setattr(
                self,
                f"m_up{level}",
                nn.Sequential(
                    nn.ConvTranspose2d(b, a, 2, stride=2, bias=False),
                    *(ResidualBlock(a) for _ in range(4)),
                ),
            )
        self.m_body = nn.Sequential(*(ResidualBlock(512) for _ in range(4)))
        self.m_tail = nn.Conv2d(64, 3, 3, padding=1, bias=False)

    def forward(self, rgb, noise, *, head_offset=None, middle_offset=None):
        # Preserve weak native RGB variations through the first skip even when
        # deep features use BF16/FP16. Absolute RGB is projected in IEEE FP32.
        with torch.autocast(rgb.device.type, enabled=False), ieee_fp32():
            x1 = self.m_head(torch.cat((rgb.float(), noise.float()), dim=1))
            if head_offset is not None:
                x1 = x1 + head_offset.float()
        x2 = self.m_down1(x1)
        x3 = self.m_down2(x2)
        x4 = self.m_down3(x3)
        if middle_offset is not None:
            x4 = x4 + middle_offset
        x = self.m_up3(self.m_body(x4) + x4)
        x = self.m_up2(x + x3)
        x = self.m_up1(x + x2)
        with torch.autocast(rgb.device.type, enabled=False), ieee_fp32():
            return self.m_tail(x.float() + x1)


def physical_rgb_features(packed, variance, colors, wb=None, matrix=None):
    """Build normalized camera RGB and actual CFA/camera metadata in IEEE FP32.

    No input fitting, reference or learned denoiser is used here. The spatial
    noise map is a marginal measurement-noise proxy, not an assertion that
    demosaiced RGB noise is independent. Affine scales are per image so batches
    cannot change an image's normalization.
    """
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed, variance = packed.float(), variance.float()
        batch, _, h, w = packed.shape
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        rgb = malvar(packed, colors, wb)
        offset = rgb.amin((1, 2, 3), keepdim=True)
        rgb_variance = bilinear(box_mean(variance.clamp_min(0), 7), colors)
        sigma = rgb_variance.mean(1, keepdim=True).clamp_min(0).sqrt()
        image_range = rgb.amax((1, 2, 3), keepdim=True) - offset
        # A quantized/clipped flat does not provide a useful contrast scale.
        # Preserve the original prior's unit fallback for constant RGB. For
        # nearly flat tiles, a conservative eight-sigma floor avoids feeding
        # an arbitrarily large normalized noise level to the pretrained trunk.
        span = torch.maximum(image_range, 8 * sigma.amax((1, 2, 3), keepdim=True))
        span = torch.where(image_range <= 1e-6, torch.ones_like(span), span.clamp_min(1e-4))
        normalized = (rgb - offset) / span
        noise = sigma / span
        phase_masks = F.one_hot(colors, 3).transpose(1, 2)[..., None, None].float()
        mask = F.pixel_shuffle(phase_masks.expand(-1, -1, -1, h, w).reshape(batch, 12, h, w), 2)
        measured = F.pixel_shuffle((phase_masks * packed[:, None]).reshape(batch, 12, h, w), 2)
        measured = (measured - offset * mask) / span
        balance = packed.new_ones(batch, 3) if wb is None else wb.float()
        transform = (
            torch.eye(3, device=packed.device)[None].expand(batch, -1, -1)
            if matrix is None
            else matrix.float()
        )
        camera = torch.cat((balance.clamp_min(1e-6).log2(), transform.flatten(1)), dim=1)
        log_noise = (rgb_variance.clamp_min(1e-12).log() + 12) / 6
        condition = torch.cat(
            (
                measured,
                mask,
                log_noise,
                camera[:, :, None, None].expand(-1, -1, 2 * h, 2 * w),
            ),
            dim=1,
        )
        return rgb, normalized, noise, condition, offset, span


class PretrainedRgbDemosaic(nn.Module):
    """One trainable RGB pass with CFA/noise/camera input and frozen DINO context."""

    def __init__(self):
        super().__init__()
        self.network = RgbRestorationTrunk()
        self.measurement_adapter = nn.Conv2d(21, 64, 1)
        nn.init.zeros_(self.measurement_adapter.weight)
        nn.init.zeros_(self.measurement_adapter.bias)

    def forward(self, packed, variance, colors, wb=None, matrix=None, context=None):
        rgb, normalized, noise, condition, offset, span = physical_rgb_features(
            packed, variance, colors, wb, matrix
        )
        h, w = rgb.shape[-2:]
        pad = (0, -w % 8, 0, -h % 8)
        normalized, noise, condition = (
            F.pad(value, pad, mode="replicate") for value in (normalized, noise, condition)
        )
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            head_offset = self.measurement_adapter(condition)
        middle_offset = None
        if context is not None:
            middle_offset = context(
                render(rgb, wb, matrix),
                (normalized.shape[-2] // 8, normalized.shape[-1] // 8),
            )
        prediction = self.network(
            normalized, noise, head_offset=head_offset, middle_offset=middle_offset
        )[..., :h, :w]
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            return prediction.float() * span + offset


def initialize_rgb_prior(model, receipt, *, archive=None):
    """Strictly transfer verified original RGB weights, retaining trainability."""
    from .gaussian import load_gaussian_prior

    if model.config.restoration_backbone != "pretrained-rgb":
        raise ValueError("Gaussian initialization requires the pretrained-rgb backbone")
    prior = load_gaussian_prior(receipt, archive=archive)
    model.pretrained_rgb.network.load_state_dict(prior.network.state_dict(), strict=True)
    return {
        "type": "verified RGB Gaussian restoration pretraining",
        "path": str(Path(receipt).resolve()),
        "sha256": hashlib.sha256(Path(receipt).read_bytes()).hexdigest(),
        "prior": prior.receipt,
        "new_adapters": "Zero measurement/camera projection and zero DINO fusion gate",
        "physical_representation": "Affine-normalized linear camera RGB; spatial noise proxy; no GAT",
    }
