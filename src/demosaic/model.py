"""Sensor-conditioned local restoration with optional frozen DINOv3 context."""

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear
from .color import render


@dataclass
class ModelConfig:
    width: int = 32
    encoder_blocks: tuple[int, ...] = (2, 2, 4)
    middle_blocks: int = 6
    decoder_blocks: tuple[int, ...] = (2, 2, 2)
    attention: bool = True
    dino: bool = False
    dino_model: str = "facebook/dinov3-vits16-pretrain-lvd1689m"
    dino_revision: str = "main"

    def to_dict(self):
        return asdict(self)


class PixelNorm(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.norm = nn.LayerNorm(channels)

    def forward(self, x):
        return self.norm(x.permute(0, 2, 3, 1)).permute(0, 3, 1, 2)


class GatedBlock(nn.Module):
    """Local gated mixing; per-pixel normalization avoids tile statistics."""

    def __init__(self, channels):
        super().__init__()
        self.norm1, self.norm2 = PixelNorm(channels), PixelNorm(channels)
        self.expand = nn.Conv2d(channels, 2 * channels, 1)
        self.spatial = nn.Conv2d(2 * channels, 2 * channels, 3, padding=1, groups=2 * channels)
        self.project = nn.Conv2d(channels, channels, 1)
        self.ffn = nn.Conv2d(channels, 2 * channels, 1)
        self.ffn_out = nn.Conv2d(channels, channels, 1)
        self.scale1 = nn.Parameter(torch.full((1, channels, 1, 1), 0.1))
        self.scale2 = nn.Parameter(torch.full((1, channels, 1, 1), 0.1))

    def forward(self, x):
        a, b = self.spatial(self.expand(self.norm1(x))).chunk(2, 1)
        x = x + self.project(a * b) * self.scale1
        a, b = self.ffn(self.norm2(x)).chunk(2, 1)
        return x + self.ffn_out(a * b) * self.scale2


class ChannelAttention(nn.Module):
    """Transposed attention: O(HW C²), used only on coarse spatial features."""

    def __init__(self, channels, heads=4):
        super().__init__()
        if channels % heads:
            raise ValueError("Attention width must be divisible by heads")
        self.heads = heads
        self.norm = PixelNorm(channels)
        self.qkv = nn.Conv2d(channels, 3 * channels, 1)
        self.local = nn.Conv2d(3 * channels, 3 * channels, 3, padding=1, groups=3 * channels)
        self.project = nn.Conv2d(channels, channels, 1)
        self.temperature = nn.Parameter(torch.ones(heads, 1, 1))
        self.scale = nn.Parameter(torch.full((1, channels, 1, 1), 0.1))

    def forward(self, x):
        batch, channels, h, w = x.shape
        q, k, v = (
            self.local(self.qkv(self.norm(x)))
            .reshape(batch, 3, self.heads, channels // self.heads, h * w)
            .unbind(1)
        )
        q, k = F.normalize(q.float(), dim=-1), F.normalize(k.float(), dim=-1)
        attention = ((q @ k.transpose(-2, -1)) * self.temperature).softmax(-1).to(v.dtype)
        mixed = (attention @ v).reshape(batch, channels, h, w)
        return x + self.project(mixed) * self.scale


class DinoContext(nn.Module):
    def __init__(self, config, channels):
        super().__init__()
        from transformers import AutoModel

        # No random fallback: access failures are actionable errors.
        self.backbone = AutoModel.from_pretrained(config.dino_model, revision=config.dino_revision)
        self.backbone.requires_grad_(False).eval()
        self.adapter = nn.Conv2d(self.backbone.config.hidden_size * 3, channels, 1)
        self.gate = nn.Parameter(torch.zeros(1, channels, 1, 1))
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406])[None, :, None, None])
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225])[None, :, None, None])

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self

    def forward(self, preview, size):
        # Keep native token geometry and pad to 16, without a classification crop.
        h, w = preview.shape[-2:]
        preview = F.pad(preview, (0, -w % 16, 0, -h % 16), mode="replicate")
        with torch.no_grad():
            outputs = self.backbone(
                pixel_values=(preview - self.mean) / self.std, output_hidden_states=True
            )
            hidden = outputs.hidden_states
            n = len(hidden) - 1
            selected = [hidden[max(1, n // 3)], hidden[max(1, 2 * n // 3)], hidden[-1]]
            ph, pw = preview.shape[-2] // 16, preview.shape[-1] // 16
            # CLS + register tokens precede patch tokens in DINOv3.
            features = torch.cat(
                [
                    s[:, -(ph * pw) :].transpose(1, 2).reshape(preview.shape[0], -1, ph, pw)
                    for s in selected
                ],
                dim=1,
            )
        return (
            F.interpolate(self.adapter(features), size=size, mode="bilinear", align_corners=False)
            * self.gate
        )


class JointDemosaic(nn.Module):
    def __init__(self, config: ModelConfig | None = None):
        super().__init__()
        self.config = config or ModelConfig()
        cfg = self.config
        if len(cfg.encoder_blocks) != len(cfg.decoder_blocks) or cfg.width < 4:
            raise ValueError("Invalid encoder/decoder configuration")
        self.multiple = 2 ** len(cfg.encoder_blocks)
        self.stem = nn.Conv2d(20, cfg.width, 3, padding=1)
        self.encoders, self.downs = nn.ModuleList(), nn.ModuleList()
        channels = cfg.width
        for count in cfg.encoder_blocks:
            self.encoders.append(nn.Sequential(*(GatedBlock(channels) for _ in range(count))))
            self.downs.append(nn.Conv2d(channels, channels * 2, 2, stride=2))
            channels *= 2
        blocks = []
        for i in range(cfg.middle_blocks):
            blocks.append(GatedBlock(channels))
            if cfg.attention and i % 2 == 1:
                blocks.append(ChannelAttention(channels))
        self.middle = nn.Sequential(*blocks)
        self.context = DinoContext(cfg, channels) if cfg.dino else None
        self.ups, self.decoders = nn.ModuleList(), nn.ModuleList()
        for count in cfg.decoder_blocks:
            self.ups.append(nn.Sequential(nn.Conv2d(channels, channels * 2, 1), nn.PixelShuffle(2)))
            channels //= 2
            self.decoders.append(nn.Sequential(*(GatedBlock(channels) for _ in range(count))))
        self.head = nn.Conv2d(channels, 12, 3, padding=1)
        self.mosaic_head = nn.Conv2d(channels, 4, 3, padding=1)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)
        nn.init.zeros_(self.mosaic_head.weight)
        nn.init.zeros_(self.mosaic_head.bias)

    def forward(self, packed, variance, colors, wb=None, matrix=None, *, auxiliary=False):
        batch, phases, height, width = packed.shape
        if phases != 4 or variance.shape != packed.shape:
            raise ValueError("Expected four packed phases and matching variance maps")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        baseline = bilinear(packed, colors)
        labels = F.one_hot(colors, 3).to(packed.dtype).reshape(batch, 12, 1, 1)
        inputs = torch.cat(
            (packed, variance.clamp_min(0).sqrt(), labels.expand(-1, -1, height, width)), dim=1
        )
        x = self.stem(
            F.pad(inputs, (0, -width % self.multiple, 0, -height % self.multiple), mode="replicate")
        )
        skips = []
        for encoder, down in zip(self.encoders, self.downs):
            x = encoder(x)
            skips.append(x)
            x = down(x)
        if self.context is not None:
            x = x + self.context(render(baseline, wb, matrix), x.shape[-2:])
        x = self.middle(x)
        for up, decoder, skip in zip(self.ups, self.decoders, reversed(skips)):
            x = decoder(up(x) + skip)
        x = x[..., :height, :width]
        prediction = baseline + F.pixel_shuffle(self.head(x), 2).float()
        if auxiliary:
            return prediction, packed + self.mosaic_head(x).float()
        return prediction

    def restoration_state_dict(self):
        return {k: v for k, v in self.state_dict().items() if not k.startswith("context.backbone.")}
