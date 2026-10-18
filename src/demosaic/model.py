"""Sensor-conditioned local restoration with optional frozen DINOv3 context."""

import math
from dataclasses import asdict, dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import bilinear, malvar, mosaic
from .color import render
from .precision import REFINEMENT_DTYPES, amp_context, ieee_fp32
from .prior import box_mean, standardized_noise, wiener_packed


@dataclass
class ModelConfig:
    restoration_backbone: str = "local"
    width: int = 32
    encoder_blocks: tuple[int, ...] = (2, 2, 4)
    middle_blocks: int = 6
    decoder_blocks: tuple[int, ...] = (2, 2, 2)
    attention: bool = True
    dino: bool = False
    dino_model: str = "facebook/dinov3-vits16-pretrain-lvd1689m"
    dino_revision: str = "main"
    dino_lora_rank: int = 0
    dino_input_adapter: bool = False
    dino_feature_fusion: str = "bottleneck"
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
    pyramid_refinement: bool = False
    pyramid_measurements: bool = True
    pyramid_width: int = 24
    pyramid_blocks: int = 2
    variance_stabilization: bool = False
    physical_anchors: bool = False
    rgb_processing_scale: int = 1
    packed_detail_prior: bool = False
    rgb_hidden_autocast: bool = False
    rgb_center_camera_matrix: bool = False
    rgb_middle_skip_fp32: bool = False
    adc_cfa_projection: bool = False
    raw_kernel_reconstruction: bool = False
    raw_kernel_windows: tuple[int, ...] = (1, 5, 17)
    raw_kernel_phase_conditioning: bool = False
    raw_directional_residual: bool = False
    isotropic_groups: int = 6
    isotropic_blocks: int = 8
    isotropic_local_width: int = 32
    isotropic_raw_gain: float = 1.0
    isotropic_residual_scale: float = 1.0

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
    makes the correction exactly zero. Physical operations keep IEEE FP32 math;
    neural operations default to FP32 with an optional FP16 inference mode.
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
        self.compute_precision = "float32"
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
            residual = F.pixel_unshuffle(residual.clamp(-8, 8), 2)
            noise = F.pixel_unshuffle(noise, 2)
            with amp_context(rgb.device, dtype=self.compute_precision):
                inputs = torch.cat((residual, noise, self.context(features.float())), dim=1)
                correction = F.pixel_shuffle(self.head(self.blocks(self.stem(inputs))), 2)
            return correction.float() * scale


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


class PyramidNoiseRefiner(nn.Module):
    """Multiscale noise-unit correction with explicit measured-CFA innovation.

    Innovation is the observation minus the current RGB estimate sampled at
    the actual CFA phases. Disabling it supplies zeros to the same channels,
    preserving initialization and capacity for a matched ablation. Physical
    feature construction/scaling stays IEEE FP32. No reference or target
    image is available to this module.
    """

    def __init__(self, context_channels, width=24, blocks=2, *, measurements=True):
        super().__init__()
        if width < 12 or blocks < 1:
            raise ValueError("Invalid pyramid refinement configuration")
        self.measurements = measurements
        self.compute_precision = "float32"
        self.context = nn.Conv2d(context_channels, 12, 1)
        self.stem = nn.Conv2d(52, width, 3, padding=1)
        self.encoders, self.downs = nn.ModuleList(), nn.ModuleList()
        channels = width
        for _ in range(2):
            self.encoders.append(nn.Sequential(*(GatedBlock(channels) for _ in range(blocks))))
            self.downs.append(nn.Conv2d(channels, channels * 2, 2, stride=2))
            channels *= 2
        self.middle = nn.Sequential(*(GatedBlock(channels) for _ in range(blocks)))
        self.ups, self.decoders = nn.ModuleList(), nn.ModuleList()
        for _ in range(2):
            self.ups.append(nn.Sequential(nn.Conv2d(channels, channels * 2, 1), nn.PixelShuffle(2)))
            channels //= 2
            self.decoders.append(nn.Sequential(*(GatedBlock(channels) for _ in range(blocks))))
        self.head = nn.Conv2d(width, 12, 3, padding=1)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, rgb, packed, variance, colors, features):
        with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
            rgb, packed = rgb.float(), packed.float()
            phase_variance = box_mean(variance.float().clamp_min(0), 7)
            rgb_variance = bilinear(phase_variance, colors)
            scale = rgb_variance.clamp_min(0).sqrt()
            residual = (rgb - box_mean(rgb, 63)) / scale.clamp_min(1e-4)
            noise = (rgb_variance.clamp_min(1e-8).log() + 12) / 6
            innovation = (
                (packed - mosaic(rgb, colors)) / phase_variance.clamp_min(1e-8).sqrt()
                if self.measurements
                else torch.zeros_like(packed)
            )
            if colors.ndim == 1:
                colors = colors[None].expand(rgb.shape[0], -1)
            h, w = packed.shape[-2:]
            labels = F.one_hot(colors, 3).float().flatten(1)[:, :, None, None].expand(-1, -1, h, w)
            with amp_context(rgb.device, dtype=self.compute_precision):
                inputs = torch.cat(
                    (
                        F.pixel_unshuffle(residual.clamp(-8, 8), 2),
                        F.pixel_unshuffle(noise, 2),
                        innovation.clamp(-8, 8),
                        labels,
                        self.context(features.float()),
                    ),
                    dim=1,
                )
                x = self.stem(F.pad(inputs, (0, -w % 4, 0, -h % 4), mode="replicate"))
                skips = []
                for encoder, down in zip(self.encoders, self.downs):
                    x = encoder(x)
                    skips.append(x)
                    x = down(x)
                x = self.middle(x)
                for up, decoder, skip in zip(self.ups, self.decoders, reversed(skips)):
                    x = decoder(up(x) + skip)
                correction = F.pixel_shuffle(self.head(x[..., :h, :w]), 2)
            return correction.float() * scale


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
        if getattr(self.backbone.config, "model_type", None) == "dinov3_convnext":
            raise ValueError("DINOv3 ConvNeXt requires dino_feature_fusion: convnext-pyramid")
        # Frozen weights are loaded separately; pin the exact upstream revision.
        config.dino_revision = (
            getattr(self.backbone.config, "_commit_hash", None) or config.dino_revision
        )
        self.backbone.requires_grad_(False).eval()
        if config.dino_lora_rank:
            from .dino_adaptation import install_qv_adapters

            self.lora = install_qv_adapters(self.backbone, config.dino_lora_rank)
        else:
            self.lora = nn.ModuleDict()
        self.adapter = nn.Conv2d(self.backbone.config.hidden_size * 3, channels, 1)
        self.gate = nn.Parameter(torch.zeros(1, channels, 1, 1))
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406])[None, :, None, None])
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225])[None, :, None, None])
        self.input_adapter = None
        if config.dino_input_adapter:
            from .dino_adaptation import DinoInputAdapter

            # Keep subsequent common layers' initialization and global RNG
            # identical when adding an initially identity feature-input path.
            with torch.random.fork_rng(devices=[]):
                self.input_adapter = DinoInputAdapter()

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self

    def forward(self, preview, size):
        if self.input_adapter is not None:
            preview = self.input_adapter(preview)
        # Keep native token geometry and pad to 16, without a classification crop.
        h, w = preview.shape[-2:]
        preview = F.pad(preview, (0, -w % 16, 0, -h % 16), mode="replicate")
        adapt_encoder_input = self.input_adapter is not None or bool(self.lora)
        with torch.set_grad_enabled(adapt_encoder_input and torch.is_grad_enabled()):
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
        self.refinement_precision = "float32"
        cfg = self.config
        units = (cfg.isotropic_raw_gain, cfg.isotropic_residual_scale)
        if any(
            type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            for value in units
        ):
            raise ValueError("Isotropic RAW gain and residual scale must be finite and positive")
        if units != (1, 1) and cfg.restoration_backbone != "packed-isotropic":
            raise ValueError("Isotropic RAW/residual units require the packed-isotropic backbone")
        if type(cfg.raw_kernel_reconstruction) is not bool:
            raise ValueError("RAW kernel reconstruction must be a boolean")
        if cfg.raw_kernel_reconstruction and cfg.restoration_backbone != "pretrained-rgb":
            raise ValueError("RAW kernel reconstruction requires the pretrained RGB backbone")
        if type(cfg.raw_directional_residual) is not bool:
            raise ValueError("RAW directional residual must be a boolean")
        if cfg.raw_directional_residual and (
            cfg.restoration_backbone != "pretrained-rgb"
            or not cfg.variance_stabilization
            or not cfg.physical_anchors
            or cfg.rgb_processing_scale != 1
            or cfg.raw_kernel_reconstruction
            or cfg.adc_cfa_projection
        ):
            raise ValueError(
                "RAW directional residual requires native stabilized anchored RGB without other RAW heads"
            )
        if cfg.adc_cfa_projection and (
            cfg.restoration_backbone != "pretrained-rgb" or not cfg.variance_stabilization
        ):
            raise ValueError(
                "ADC CFA projection requires explicit stabilized RGB noise conditioning"
            )
        if cfg.rgb_center_camera_matrix and cfg.restoration_backbone != "pretrained-rgb":
            raise ValueError("Centered camera matrices require the pretrained RGB backbone")
        if cfg.rgb_middle_skip_fp32 and cfg.restoration_backbone != "pretrained-rgb":
            raise ValueError("FP32 middle skips require the pretrained RGB backbone")
        if type(cfg.dino_lora_rank) is not int or cfg.dino_lora_rank < 0:
            raise ValueError("DINO adapter rank must be a nonnegative integer")
        if cfg.dino_lora_rank and not cfg.dino:
            raise ValueError("DINO adapters require DINO context")
        if type(cfg.dino_input_adapter) is not bool:
            raise ValueError("DINO input adapter must be a boolean")
        if cfg.dino_input_adapter and not cfg.dino:
            raise ValueError("DINO input adapter requires DINO context")
        if cfg.dino_feature_fusion not in ("bottleneck", "convnext-pyramid", "packed-convnext"):
            raise ValueError("Unknown DINO feature fusion")
        if cfg.dino_feature_fusion == "packed-convnext" and (
            not cfg.dino
            or cfg.restoration_backbone != "packed-isotropic"
            or cfg.dino_lora_rank
            or cfg.dino_input_adapter
        ):
            raise ValueError("Packed ConvNeXt fusion requires packed-isotropic and frozen DINO")
        if cfg.dino_feature_fusion == "convnext-pyramid" and (
            not cfg.dino
            or cfg.restoration_backbone != "pretrained-rgb"
            or cfg.rgb_processing_scale != 1
            or cfg.dino_lora_rank
            or cfg.dino_input_adapter
        ):
            raise ValueError(
                "ConvNeXt pyramid requires native pretrained RGB, DINO, and no input/LoRA adapter"
            )
        if cfg.rgb_processing_scale not in (1, 2):
            raise ValueError("RGB processing scale must be 1 or 2")
        if type(cfg.raw_kernel_phase_conditioning) is not bool:
            raise ValueError("RAW kernel phase conditioning must be a boolean")
        if cfg.raw_kernel_phase_conditioning and not cfg.raw_kernel_reconstruction:
            raise ValueError("RAW kernel phase conditioning requires RAW kernel reconstruction")
        if cfg.packed_detail_prior and cfg.rgb_processing_scale != 2:
            raise ValueError("The packed detail prior requires RGB processing scale 2")
        if cfg.rgb_processing_scale == 2 and (
            cfg.restoration_backbone != "pretrained-rgb" or not cfg.variance_stabilization
        ):
            raise ValueError("Packed RGB processing requires the stabilized pretrained backbone")
        if cfg.physical_anchors and not cfg.variance_stabilization:
            raise ValueError("Physical anchors require variance stabilization")
        if cfg.restoration_backbone not in ("local", "pretrained-rgb", "packed-isotropic"):
            raise ValueError("Unknown restoration backbone")
        if cfg.rgb_hidden_autocast and cfg.restoration_backbone != "pretrained-rgb":
            raise ValueError("RGB hidden autocast requires the pretrained RGB backbone")
        if cfg.variance_stabilization and cfg.restoration_backbone != "pretrained-rgb":
            raise ValueError("Variance stabilization requires the pretrained RGB backbone")
        if cfg.restoration_backbone == "packed-isotropic":
            if (
                not cfg.physical_fp32
                or not cfg.camera_conditioning
                or cfg.baseline != "bilinear"
                or cfg.noise_modulation
                or cfg.standardized_noise
                or cfg.noise_refinement
                or cfg.coarse_refinement_factor
                or cfg.pyramid_refinement
                or (cfg.dino and cfg.dino_feature_fusion != "packed-convnext")
            ):
                raise ValueError(
                    "Packed isotropic requires FP32 camera features, bilinear baseline, "
                    "no legacy refiners, and packed-convnext fusion when DINO is enabled"
                )
            from .packed_isotropic import PackedIsotropic

            self.packed_isotropic = PackedIsotropic(
                cfg.width,
                cfg.isotropic_groups,
                cfg.isotropic_blocks,
                cfg.isotropic_local_width,
                raw_gain=cfg.isotropic_raw_gain,
                residual_scale=cfg.isotropic_residual_scale,
            )
            self.context = None
            if cfg.dino:
                from .dino_pyramid import DinoPackedContext

                with torch.random.fork_rng(devices=[]):
                    self.context = DinoPackedContext(cfg)
            self.refiner = self.coarse_refiner = self.pyramid_refiner = None
            return
        if cfg.restoration_backbone == "pretrained-rgb":
            from .pretrained_rgb import PretrainedRgbDemosaic

            if (
                cfg.width != 64
                or not cfg.camera_conditioning
                or not cfg.physical_fp32
                or cfg.noise_modulation
                or cfg.standardized_noise
                or cfg.noise_refinement
                or cfg.coarse_refinement_factor
                or cfg.pyramid_refinement
            ):
                raise ValueError(
                    "Pretrained RGB requires width64, FP32 physical camera features "
                    "and no legacy noise/refiner branches"
                )
            self.pretrained_rgb = PretrainedRgbDemosaic(
                stabilized=cfg.variance_stabilization,
                physical_anchors=cfg.physical_anchors,
                processing_scale=cfg.rgb_processing_scale,
                detail_prior=cfg.packed_detail_prior,
                hidden_autocast=cfg.rgb_hidden_autocast,
                center_camera_matrix=cfg.rgb_center_camera_matrix,
                middle_skip_fp32=cfg.rgb_middle_skip_fp32,
                adc_projection=cfg.adc_cfa_projection,
                raw_kernel=cfg.raw_kernel_reconstruction,
                raw_kernel_windows=cfg.raw_kernel_windows,
                raw_kernel_phase_conditioning=cfg.raw_kernel_phase_conditioning,
                raw_directional_residual=cfg.raw_directional_residual,
            )
            if cfg.dino and cfg.dino_feature_fusion == "convnext-pyramid":
                from .dino_pyramid import DinoPyramidContext

                # Preserve common initialization/global RNG when adding this
                # independent, initially zero feature branch.
                with torch.random.fork_rng(devices=[]):
                    self.context = DinoPyramidContext(cfg)
            else:
                self.context = DinoContext(cfg, 512) if cfg.dino else None
            self.refiner = self.coarse_refiner = self.pyramid_refiner = None
            return
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

        self.pyramid_refiner = (
            PyramidNoiseRefiner(
                cfg.width,
                cfg.pyramid_width,
                cfg.pyramid_blocks,
                measurements=cfg.pyramid_measurements,
            )
            if cfg.pyramid_refinement
            else None
        )

    def set_noise(self, shot, read):
        if self.config.variance_stabilization:
            self.pretrained_rgb.set_noise(shot, read)
        return self

    def set_refinement_precision(self, precision):
        """Set inference arithmetic without changing weights or physical maps."""
        if precision not in REFINEMENT_DTYPES:
            raise ValueError(f"Unknown refinement precision {precision!r}")
        for module in self.modules():
            if isinstance(module, (RgbNoiseRefiner, PyramidNoiseRefiner)):
                module.compute_precision = precision
        self.refinement_precision = precision
        return self

    def forward(
        self,
        packed,
        variance,
        colors,
        wb=None,
        matrix=None,
        *,
        auxiliary=False,
        normalization_mask=None,
    ):
        batch, phases, height, width = packed.shape
        if phases != 4 or variance.shape != packed.shape:
            raise ValueError("Expected four packed phases and matching variance maps")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if self.config.restoration_backbone == "packed-isotropic":
            if normalization_mask is not None:
                raise ValueError("Normalization augmentation requires the pretrained RGB backbone")
            prediction = self.packed_isotropic(packed, variance, colors, wb, matrix, self.context)
            return (prediction, mosaic(prediction, colors)) if auxiliary else prediction
        if self.config.restoration_backbone == "pretrained-rgb":
            prediction = self.pretrained_rgb(
                packed,
                variance,
                colors,
                wb,
                matrix,
                self.context,
                normalization_mask=normalization_mask,
            )
            return (prediction, mosaic(prediction, colors)) if auxiliary else prediction
        if normalization_mask is not None:
            raise ValueError("Normalization augmentation requires the pretrained RGB backbone")
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
        if self.pyramid_refiner is not None:
            prediction = prediction + self.pyramid_refiner(prediction, packed, variance, colors, x)
        if auxiliary:
            return prediction, auxiliary_base + self.mosaic_head(x).float()
        return prediction

    def restoration_state_dict(self):
        return {k: v for k, v in self.state_dict().items() if not k.startswith("context.backbone.")}
