"""Sensor-conditioned local restoration with optional frozen DINOv3 context."""

from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear, malvar
from .color import render
from .precision import ieee_fp32
from .prior import box_mean, standardized_noise, wiener_packed


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
    camera_conditioning: bool = False
    noise_modulation: bool = False
    physical_fp32: bool = True
    baseline: str = "bilinear"
    prior_window: int = 7
    standardized_noise: bool = False
    noise_refinement: bool = False
    refinement_width: int = 24
    refinement_blocks: int = 4
    refinement_window: int = 63
    coarse_refinement_factor: int = 0
    coarse_refinement_width: int = 24
    coarse_refinement_blocks: int = 4
    coarse_refinement_window: int = 31

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_checkpoint(cls, values):
        values = dict(values)
        values.setdefault("physical_fp32", values.pop("baseline_fp32", False))
        return cls(**values)


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


class NoiseModulation(nn.Module):
    """Identity-initialized spatial scale/shift from log sensor variance."""

    def __init__(self, channels):
        super().__init__()
        self.affine = nn.Sequential(nn.Conv2d(4, 32, 1), nn.SiLU(), nn.Conv2d(32, channels * 2, 1))
        nn.init.zeros_(self.affine[-1].weight)
        nn.init.zeros_(self.affine[-1].bias)

    def forward(self, x, log_variance):
        condition = F.interpolate(log_variance, size=x.shape[-2:], mode="area")
        scale, shift = self.affine(condition).chunk(2, 1)
        return x * (1 + 0.5 * scale.tanh()) + shift


class RgbNoiseRefiner(nn.Module):
    """Predict a noise-scaled RGB correction from the actual restored estimate.

    Unit-scale local residuals expose weak noise without requiring the network
    to reproduce the nonlinear Bayer prior. Decoder features retain structural
    context. Zero initialization preserves the base model; zero sensor variance
    makes the correction exactly zero. This small branch keeps IEEE FP32 math.
    """

    def __init__(
        self,
        context_channels,
        width=24,
        blocks=4,
        window=63,
        *,
        normalization_floor=1e-4,
        variance_floor=1e-8,
    ):
        super().__init__()
        if width < 12 or blocks < 0 or window < 3 or window % 2 == 0:
            raise ValueError("Invalid RGB noise-refinement configuration")
        self.window = window
        self.normalization_floor = normalization_floor
        self.variance_floor = variance_floor
        self.context = nn.Conv2d(context_channels, 12, 1)
        self.stem = nn.Conv2d(36, width, 3, padding=1)
        self.blocks = nn.Sequential(*(GatedBlock(width) for _ in range(blocks)))
        self.head = nn.Conv2d(width, 12, 3, padding=1)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, rgb, variance, colors, features):
        with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
            rgb_variance = bilinear(box_mean(variance.float().clamp_min(0), 7), colors)
            return self.from_rgb_variance(rgb, rgb_variance, features)

    def from_rgb_variance(self, rgb, rgb_variance, features):
        """Correct dense RGB using a specified RGB noise-scale proxy."""
        with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
            rgb = rgb.float()
            rgb_variance = rgb_variance.float()
            scale = rgb_variance.clamp_min(0).sqrt()
            residual = (rgb - box_mean(rgb, self.window)) / scale.clamp_min(
                self.normalization_floor
            )
            noise = (rgb_variance.clamp_min(self.variance_floor).log() + 12) / 6
            inputs = torch.cat(
                (
                    F.pixel_unshuffle(residual.clamp(-8, 8), 2),
                    F.pixel_unshuffle(noise, 2),
                    self.context(features.float()),
                ),
                dim=1,
            )
            correction = F.pixel_shuffle(self.head(self.blocks(self.stem(inputs))), 2)
            return correction * scale


class CoarseRgbNoiseRefiner(nn.Module):
    """Predict a smooth correction from pooled RGB and decoder context.

    Pooled input variance supplies a scale proxy, not an assertion that the
    nonlinear restoration residual is independent noise. The learned correction
    is zero at initialization and at zero sensor variance. Fine detail bypasses
    this branch; its output is interpolated back to the original RGB geometry.
    """

    def __init__(self, context_channels, factor=8, width=24, blocks=4, window=31):
        super().__init__()
        if factor not in (2, 4, 8, 16):
            raise ValueError("Coarse RGB factor must be 2, 4, 8 or 16")
        self.factor = factor
        self.network = RgbNoiseRefiner(
            context_channels, width, blocks, window, normalization_floor=1e-6, variance_floor=1e-12
        )

    def forward(self, rgb, variance, colors, features):
        with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
            h, w = features.shape[-2:]
            factor = self.factor
            ph, pw = -h % factor, -w % factor
            rgb_variance = bilinear(box_mean(variance.float().clamp_min(0), 7), colors)
            rgb = F.pad(rgb.float(), (0, 2 * pw, 0, 2 * ph), mode="replicate")
            rgb_variance = F.pad(rgb_variance, (0, 2 * pw, 0, 2 * ph), mode="replicate")
            features = F.pad(features.float(), (0, pw, 0, ph), mode="replicate")
            pooled = F.avg_pool2d(rgb, factor, factor)
            proxy = F.avg_pool2d(rgb_variance, factor, factor) / factor**2
            context = F.avg_pool2d(features, factor, factor)
            correction = self.network.from_rgb_variance(pooled, proxy, context)
            return F.interpolate(
                correction, scale_factor=factor, mode="bilinear", align_corners=False
            )[..., : 2 * h, : 2 * w]


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
        # Frozen weights are loaded separately; pin the exact upstream revision.
        config.dino_revision = (
            getattr(self.backbone.config, "_commit_hash", None) or config.dino_revision
        )
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
        if cfg.baseline not in ("bilinear", "wiener-malvar"):
            raise ValueError("Unknown restoration baseline")
        self.multiple = 2 ** len(cfg.encoder_blocks)
        input_channels = (32 if cfg.camera_conditioning else 20) + (
            4 if cfg.standardized_noise else 0
        )
        self.stem = nn.Conv2d(input_channels, cfg.width, 3, padding=1)
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
        self.noise_encoder = nn.ModuleList()
        self.noise_decoder = nn.ModuleList()
        self.noise_middle = None
        if cfg.noise_modulation:
            widths = [cfg.width * 2**i for i in range(len(cfg.encoder_blocks))]
            self.noise_encoder.extend(NoiseModulation(c) for c in widths)
            self.noise_middle = NoiseModulation(cfg.width * self.multiple)
            self.noise_decoder.extend(NoiseModulation(c) for c in reversed(widths))
        self.refiner = (
            RgbNoiseRefiner(
                cfg.width, cfg.refinement_width, cfg.refinement_blocks, cfg.refinement_window
            )
            if cfg.noise_refinement
            else None
        )
        self.coarse_refiner = (
            CoarseRgbNoiseRefiner(
                cfg.width,
                cfg.coarse_refinement_factor,
                cfg.coarse_refinement_width,
                cfg.coarse_refinement_blocks,
                cfg.coarse_refinement_window,
            )
            if cfg.coarse_refinement_factor
            else None
        )

    def forward(self, packed, variance, colors, wb=None, matrix=None, *, auxiliary=False):
        batch, phases, height, width = packed.shape
        if phases != 4 or variance.shape != packed.shape:
            raise ValueError("Expected four packed phases and matching variance maps")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        auxiliary_base = packed
        if self.config.baseline == "wiener-malvar":
            auxiliary_base = wiener_packed(packed, variance, self.config.prior_window)
            baseline = malvar(auxiliary_base, colors, wb)
        else:
            baseline = bilinear(packed, colors, fp32=self.config.physical_fp32)
        labels = F.one_hot(colors, 3).to(packed.dtype).reshape(batch, 12, 1, 1)
        inputs = torch.cat(
            (packed, variance.clamp_min(0).sqrt(), labels.expand(-1, -1, height, width)), dim=1
        )
        if self.config.camera_conditioning:
            balance = packed.new_ones(batch, 3) if wb is None else wb.to(packed)
            transform = (
                torch.eye(3, device=packed.device, dtype=packed.dtype)[None].expand(batch, -1, -1)
                if matrix is None
                else matrix.to(packed)
            )
            # Highlight recovery depends on white point and camera primaries.
            metadata = torch.cat((balance.clamp_min(1e-6).log2(), transform.flatten(1)), dim=1)
            inputs = torch.cat(
                (inputs, metadata[:, :, None, None].expand(-1, -1, height, width)), dim=1
            )
        if self.config.standardized_noise:
            inputs = torch.cat((inputs, standardized_noise(packed, variance)), dim=1)
        x = self.stem(
            F.pad(inputs, (0, -width % self.multiple, 0, -height % self.multiple), mode="replicate")
        )
        log_variance = None
        if self.config.noise_modulation:
            log_variance = F.pad(
                (variance.float().clamp_min(1e-8).log() + 12) / 6,
                (0, -width % self.multiple, 0, -height % self.multiple),
                mode="replicate",
            )
        skips = []
        for index, (encoder, down) in enumerate(zip(self.encoders, self.downs)):
            if self.config.noise_modulation:
                x = self.noise_encoder[index](x, log_variance)
            x = encoder(x)
            skips.append(x)
            x = down(x)
        if self.context is not None:
            x = x + self.context(
                render(baseline, wb, matrix, fp32=self.config.physical_fp32), x.shape[-2:]
            )
        if self.noise_middle is not None:
            x = self.noise_middle(x, log_variance)
        x = self.middle(x)
        for index, (up, decoder, skip) in enumerate(zip(self.ups, self.decoders, reversed(skips))):
            x = up(x) + skip
            if self.config.noise_modulation:
                x = self.noise_decoder[index](x, log_variance)
            x = decoder(x)
        x = x[..., :height, :width]
        prediction = baseline + F.pixel_shuffle(self.head(x), 2).float()
        if self.refiner is not None:
            prediction = prediction + self.refiner(prediction, variance, colors, x)
        if self.coarse_refiner is not None:
            prediction = prediction + self.coarse_refiner(prediction, variance, colors, x)
        if auxiliary:
            return prediction, auxiliary_base + self.mosaic_head(x).float()
        return prediction

    def restoration_state_dict(self):
        return {k: v for k, v in self.state_dict().items() if not k.startswith("context.backbone.")}
