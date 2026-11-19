"""Separate a sensor-conditioned luminance correction from the RGB restorer."""

import hashlib
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import mosaic, pack
from .experiments.artifacts import checked
from .paired_detail import DetailBlock
from .precision import ieee_fp32
from .scene_inference import load_scene_checkpoint


class FactoredLuminanceDetail(nn.Module):
    """A bounded proposal with optional band filtering after its confidence gate."""

    def __init__(self, *, band_limited, width=40, gain_floor=0.0):
        super().__init__()
        if not 0.0 <= gain_floor <= 1.0:
            raise ValueError("Require a confidence gain floor between zero and one")
        self.band_limited = band_limited
        self.gain_floor = gain_floor
        self.stem = nn.Conv2d(19, width, 3, padding=1)
        self.blocks = nn.Sequential(*(DetailBlock(width, d) for d in (1, 2, 4, 8)))
        self.output = nn.Conv2d(width, 8, 3, padding=1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)
        self.register_buffer("luma", torch.tensor([0.2126, 0.7152, 0.0722]), persistent=False)
        for name, radius, sigma in (("short", 2, 0.65), ("long", 12, 6.0)):
            axis = torch.arange(-radius, radius + 1, dtype=torch.float32)
            taps = torch.softmax(-0.5 * (axis / sigma).square(), dim=0)
            self.register_buffer(name, taps, persistent=False)

    def features(self, base, packed, variance, colors, wb, matrix):
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            sigma = variance.clamp_min(1e-10).sqrt()
            weights = (self.luma @ matrix) * wb
            native = (base * weights[:, :, None, None]).sum(1, keepdim=True)
            guide = F.avg_pool2d(native, 2)
            background = F.avg_pool2d(guide, 17, stride=1, padding=8, count_include_pad=False)
            contrast = (pack(native) - background) / sigma
            activity = F.avg_pool2d(
                contrast.square().mean(1, keepdim=True),
                17,
                stride=1,
                padding=8,
                count_include_pad=False,
            )
            residual = (packed - mosaic(base, colors)) / sigma
            color_codes = 0.5 * colors[:, :, None, None].to(packed.dtype).expand_as(packed)
            frames = torch.cat(
                (
                    residual.clamp(-12, 12),
                    sigma.log().clamp(-12, 0) / 8,
                    color_codes,
                    contrast.clamp(-12, 12),
                    (background.clamp_min(0) + 1e-4).log() / 4,
                    (1 + activity).log(),
                    guide,
                ),
                dim=1,
            )
            scale = F.interpolate(sigma.mean(dim=1, keepdim=True), scale_factor=2, mode="nearest")
            # The proposal is zero well beyond the projection radius at saturated CFA cells.
            saturated = (packed >= 0.98).any(dim=1, keepdim=True).to(packed.dtype)
            valid = 1 - F.max_pool2d(saturated, 15, stride=1, padding=7)
            valid = F.interpolate(valid, scale_factor=2, mode="nearest")
            neutral = torch.ones_like(wb).unsqueeze(-1)
            direction = torch.linalg.solve(matrix, neutral).squeeze(-1) / wb
        return frames, scale * valid, direction[:, :, None, None]

    @staticmethod
    def blur(field, taps):
        radius = taps.numel() // 2
        field = F.conv2d(
            F.pad(field, (radius, radius, 0, 0), mode="replicate"), taps.view(1, 1, 1, -1)
        )
        return F.conv2d(
            F.pad(field, (0, 0, radius, radius), mode="replicate"), taps.view(1, 1, -1, 1)
        )

    def logits(self, frames):
        activation = self.output(self.blocks(F.silu(self.stem(frames))))
        return F.pixel_shuffle(activation.float(), 2).split(1, dim=1)

    def deliver(self, detail, confidence, scale):
        with torch.autocast(detail.device.type, enabled=False), ieee_fp32():
            gain = confidence.sigmoid()
            if self.gain_floor:
                gain = torch.lerp(gain, torch.ones_like(gain), self.gain_floor)
            proposal = detail.tanh() * gain * scale
            if self.band_limited:
                return self.blur(proposal, self.short) - self.blur(proposal, self.long)
            return proposal

    def correction(self, frames, scale):
        return self.deliver(*self.logits(frames), scale)

    def forward(self, base, packed, variance, colors, wb, matrix):
        frames, scale, direction = self.features(base, packed, variance, colors, wb, matrix)
        return base + direction * self.correction(frames, scale)


class FactoredSceneRestorer(nn.Module):
    """Load a frozen scene restorer and apply a separate native correction."""

    def __init__(self, parent, detail):
        super().__init__()
        self.parent = parent.eval().requires_grad_(False)
        self.detail = detail

    @property
    def base(self):
        return self.parent.base

    @property
    def mode(self):
        return self.parent.mode

    def train(self, mode=True):
        super().train(mode)
        self.parent.eval()
        return self

    def encode_scene(self, *args, **kwargs):
        return self.parent.encode_scene(*args, **kwargs)

    def forward(self, packed, variance, colors, wb, matrix, **kwargs):
        with torch.no_grad():
            base = self.parent(packed, variance, colors, wb, matrix, **kwargs)
        return self.detail(base, packed, variance, colors, wb, matrix)


def load_detail_checkpoint(path, *, weights="ema", expected_sha256=None):
    """Load correction tensors and their declared frozen checkpoint binding."""
    if weights not in ("ema", "model"):
        raise ValueError("Choose EMA or raw correction weights explicitly")
    with Path(path).open("rb") as stream:
        state = torch.load(stream, map_location="cpu", weights_only=True)
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Correction checkpoint digest differs")
    if state["parent_weights"] != "ema":
        raise ValueError("Require the frozen parent EMA used for training")
    detail = FactoredLuminanceDetail(
        band_limited=state["band_limited"], gain_floor=state.get("gain_floor", 0.0)
    )
    detail.load_state_dict(state[weights])
    state["loaded_sha256"] = digest
    state["loaded_weights"] = weights
    return detail.eval(), state


def load_factored_scene_checkpoint(path, *, device="cpu", weights="ema", expected_sha256=None):
    """Restore a composed endpoint with its exact frozen RGB parent."""
    detail, state = load_detail_checkpoint(path, weights=weights, expected_sha256=expected_sha256)
    parent = state["parent"]
    restoration, _ = load_scene_checkpoint(
        checked(parent), device=device, weights="ema", expected_sha256=parent["sha256"]
    )
    return FactoredSceneRestorer(restoration, detail.to(device)).eval(), state
