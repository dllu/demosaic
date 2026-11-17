"""Add shared whole-scene semantics while retaining the existing local V120 path."""

from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .scene_context import SceneGrid, sample_scene_features, scene_preview


@dataclass(frozen=True)
class EncodedScene:
    features: tuple[torch.Tensor, ...]
    grid: SceneGrid


class SceneAdapter(nn.Module):
    """Trainable coarse conditioning; no scene RGB is copied into native output."""

    def __init__(self, input_channels, *, width=32, output_channels=512):
        super().__init__()
        if len(input_channels) != 4 or min(input_channels) < 1 or width < 1:
            raise ValueError("Require four spatial feature levels and a positive adapter width")
        self.projections = nn.ModuleList(nn.Conv2d(c, width, 1) for c in input_channels)
        self.output = nn.Conv2d(width, output_channels, 1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, scene, boxes_xywh, output_hw, *, mode):
        if mode not in ("pooled", "spatial") or len(scene.features) != 4:
            raise ValueError("Require pooled or spatial complete-scene features")
        fields = []
        for stride, feature, projection in zip(
            (4, 8, 16, 32), scene.features, self.projections, strict=True
        ):
            if feature.shape[0] != 1 or feature.shape[1] != projection.in_channels:
                raise ValueError("Require a single scene and matching feature widths")
            normalized = F.layer_norm(feature.float().movedim(1, -1), (feature.shape[1],)).movedim(
                -1, 1
            )
            projected = projection(normalized)
            if mode == "spatial":
                value = sample_scene_features(projected, scene.grid, stride, boxes_xywh, output_hw)
            else:
                # Do not average fully padded feature cells into the descriptor.
                h, w = projected.shape[-2:]
                if (h * stride, w * stride) != scene.grid.padded_hw:
                    raise ValueError("Scene feature extent differs from encoder padding")
                ay = (
                    scene.grid.preview_hw[0] - torch.arange(h, device=feature.device) * stride
                ).clamp(0, stride)
                ax = (
                    scene.grid.preview_hw[1] - torch.arange(w, device=feature.device) * stride
                ).clamp(0, stride)
                weights = (ay[:, None] * ax[None]).float()
                pooled = (projected.float() * weights).sum((-2, -1), keepdim=True) / weights.sum()
                value = pooled.expand(len(boxes_xywh), -1, *output_hw).to(projected.dtype)
            fields.append(value)
        return self.output(F.gelu(torch.stack(fields).mean(dim=0)))


class WholeSceneRestorer(nn.Module):
    """An explicit experiment wrapper; existing V120 checkpoints stay unchanged.

    Scene and local features share the frozen DINO backbone weights, but have
    separate forward passes. The original local encoder/trunk remain present.
    Pooled/spatial scene offsets enter only the trunk's eighth-resolution state.
    The zero-initialized output adapter preserves the initial base prediction.
    """

    def __init__(self, base, *, mode, adapter_width=32):
        super().__init__()
        if mode not in ("none", "pooled", "spatial"):
            raise ValueError("Unknown whole-scene experiment mode")
        context = base.context
        if (
            base.config.restoration_backbone != "pretrained-rgb"
            or base.config.rgb_processing_scale != 1
            or base.config.dino_feature_fusion != "convnext-pyramid"
            or context.backbone.config.model_type != "dinov3_convnext"
            or base.pretrained_rgb.rgb_refinement is not None
        ):
            raise ValueError(
                "Whole-scene wrapper requires native V120-style ConvNeXt RGB restoration"
            )
        if any(p.requires_grad for p in context.backbone.parameters()):
            raise ValueError("The shared scene/local DINO encoder must remain frozen")
        self.base = base
        self.adapter = SceneAdapter(context.backbone.config.hidden_sizes, width=adapter_width)
        self.mode = mode

    def train(self, mode=True):
        super().train(mode)
        self.base.context.backbone.eval()
        return self

    def encode_scene(self, packed, colors, wb, matrix, *, long_side=1024, exposure=1.0):
        """Encode one complete noisy observation once, without any clean target."""
        preview, grid = scene_preview(
            packed, colors, wb, matrix, long_side=long_side, exposure=exposure
        )
        # Inference may build the small preview on the CPU. Transfer only that
        # preview; a complete100MP packed observation need not live on CUDA.
        preview = preview.to(self.base.context.mean.device)
        preview = F.pad(
            preview,
            (0, grid.padded_hw[1] - grid.preview_hw[1], 0, grid.padded_hw[0] - grid.preview_hw[0]),
            mode="replicate",
        )
        context = self.base.context
        with torch.no_grad():
            features = context.backbone(
                pixel_values=(preview - context.mean) / context.std, output_hidden_states=True
            ).hidden_states[1:]
        return EncodedScene(tuple(f.detach() for f in features), grid)

    def forward(self, packed, variance, colors, wb, matrix, *, scene=None, boxes_xywh=None):
        if self.mode == "none":
            return self.base(packed, variance, colors, wb, matrix)
        if scene is None or boxes_xywh is None or len(boxes_xywh) != len(packed):
            raise ValueError("Scene-conditioned crops require their encoded scene and native boxes")
        if not isinstance(scene, EncodedScene) and (
            not isinstance(scene, (tuple, list))
            or len(scene) != len(packed)
            or any(not isinstance(s, EncodedScene) for s in scene)
        ):
            raise ValueError("Require one shared scene or one encoded scene per native crop")
        h, w = 2 * packed.shape[-2], 2 * packed.shape[-1]
        if (
            h % 8
            or w % 8
            or any(
                len(b) != 4
                or any(type(v) is not int for v in b)
                or b[0] % 2
                or b[1] % 2
                or tuple(b[2:]) != (w, h)
                for b in boxes_xywh
            )
        ):
            raise ValueError("Require phase-preserving boxes matching native crops divisible by8")

        def conditioned_context(preview, size):
            offsets = self.base.context(preview, size)
            if not isinstance(offsets, tuple) or len(offsets) != 3:
                raise ValueError("Require all three original local context offsets")
            if isinstance(scene, EncodedScene):
                extra = self.adapter(scene, boxes_xywh, size, mode=self.mode)
            else:
                # Keep the original local B4 forward for the primary panel;
                # each photograph still queries only its own scene/coordinates.
                extra = torch.cat(
                    [
                        self.adapter(s, [box], size, mode=self.mode)
                        for s, box in zip(scene, boxes_xywh, strict=True)
                    ]
                )
            return (*offsets[:2], offsets[2] + extra.to(offsets[2].dtype))

        return self.base.pretrained_rgb(
            packed, variance, colors, wb, matrix, context=conditioned_context
        )

    def restoration_state_dict(self):
        return {"base." + k: v for k, v in self.base.restoration_state_dict().items()} | {
            "adapter." + k: v for k, v in self.adapter.state_dict().items()
        }

    def load_restoration_state_dict(self, values):
        if set(values) != set(self.restoration_state_dict()):
            raise ValueError("Scene checkpoint must contain every base/adapter restoration tensor")
        missing, unexpected = self.base.load_state_dict(
            {k.removeprefix("base."): v for k, v in values.items() if k.startswith("base.")},
            strict=False,
        )
        if unexpected or any(not k.startswith("context.backbone.") for k in missing):
            raise ValueError("Scene checkpoint is incompatible with the frozen base backbone")
        self.adapter.load_state_dict(
            {k.removeprefix("adapter."): v for k, v in values.items() if k.startswith("adapter.")},
            strict=True,
        )
