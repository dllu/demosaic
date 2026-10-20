"""Frozen DINOv3 ConvNeXt features fused into three restoration resolutions."""

import torch
from torch import nn
from torch.nn import functional as F


class DinoPyramidContext(nn.Module):
    """A small top-down pyramid around an unchanged pretrained encoder.

    Four native feature maps feed lateral projections and top-down addition.
    The first three pyramid levels provide offsets at half, quarter and eighth
    sensor resolution. Zero gates initially preserve the restoration trunk.
    Padding is removed by cropping, never by squeezing its extent into an ROI.
    """

    def __init__(self, config):
        super().__init__()
        from transformers import AutoModel

        self.backbone = AutoModel.from_pretrained(config.dino_model, revision=config.dino_revision)
        if getattr(self.backbone.config, "model_type", None) != "dinov3_convnext":
            raise ValueError("ConvNeXt pyramid requires a DINOv3 ConvNeXt backbone")
        widths = self.backbone.config.hidden_sizes
        if len(widths) != 4:
            raise ValueError("ConvNeXt pyramid requires four encoder stages")
        config.dino_revision = (
            getattr(self.backbone.config, "_commit_hash", None) or config.dino_revision
        )
        self.backbone.requires_grad_(False).eval()
        width = 64
        self.laterals = nn.ModuleList(nn.Conv2d(c, width, 1) for c in widths)
        self.smooth = nn.ModuleList(nn.Conv2d(width, width, 3, padding=1) for _ in widths[:3])
        self.projections = nn.ModuleList(nn.Conv2d(width, c, 1) for c in (128, 256, 512))
        self.gates = nn.ParameterList(
            nn.Parameter(torch.zeros(1, c, 1, 1)) for c in (128, 256, 512)
        )
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406])[None, :, None, None])
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225])[None, :, None, None])

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self

    def forward(self, preview, size, *, return_features=False):
        h, w = preview.shape[-2:]
        if (size[0] * 8, size[1] * 8) != (h + -h % 8, w + -w % 8):
            raise ValueError("ConvNeXt pyramid expects the native RGB trunk's padded extent")
        preview = F.pad(preview, (0, -w % 32, 0, -h % 32), mode="replicate")
        with torch.no_grad():
            hidden = self.backbone(
                pixel_values=(preview - self.mean) / self.std, output_hidden_states=True
            ).hidden_states
            # HF returns the input followed by four BCHW stage outputs.
            features = hidden[1:]
        pyramid = [lateral(x) for lateral, x in zip(self.laterals, features)]
        for index in range(2, -1, -1):
            pyramid[index] = pyramid[index] + F.interpolate(
                pyramid[index + 1], scale_factor=2, mode="bilinear", align_corners=False
            )
        offsets = []
        for index, (smooth, projection, gate) in enumerate(
            zip(self.smooth, self.projections, self.gates)
        ):
            # Upsample in the padded coordinate system, then remove its tail.
            # Direct resize to the trunk's smaller extent would warp rectangles.
            offset = F.interpolate(
                projection(smooth(pyramid[index])),
                scale_factor=2,
                mode="bilinear",
                align_corners=False,
            )
            factor = 4 // (2**index)
            offsets.append(offset[..., : size[0] * factor, : size[1] * factor] * gate)
        offsets = tuple(offsets)
        return (offsets, tuple(features)) if return_features else offsets


class DinoPackedContext(nn.Module):
    """Frozen ConvNeXt pyramid fused on the native quarter-resolution grid.

    Padding extends the preview; cropping removes its tail after top-down
    fusion. Resizing directly to an unpadded rectangle would move features.
    """

    def __init__(self, config):
        super().__init__()
        from transformers import AutoModel

        self.backbone = AutoModel.from_pretrained(config.dino_model, revision=config.dino_revision)
        if getattr(self.backbone.config, "model_type", None) != "dinov3_convnext":
            raise ValueError("Packed context requires a DINOv3 ConvNeXt backbone")
        widths = self.backbone.config.hidden_sizes
        if len(widths) != 4:
            raise ValueError("Packed context requires four encoder stages")
        config.dino_revision = (
            getattr(self.backbone.config, "_commit_hash", None) or config.dino_revision
        )
        self.backbone.requires_grad_(False).eval()
        self.laterals = nn.ModuleList(nn.Conv2d(c, config.width, 1) for c in widths)
        self.projection = nn.Conv2d(config.width, config.width, 3, padding=1)
        self.gate = nn.Parameter(torch.zeros(1, config.width, 1, 1))
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406])[None, :, None, None])
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225])[None, :, None, None])

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self

    def forward(self, preview, size):
        height, width = preview.shape[-2:]
        if tuple(size) != ((height + 3) // 4, (width + 3) // 4):
            raise ValueError("Packed context expects the native quarter-resolution extent")
        preview = F.pad(preview, (0, -width % 32, 0, -height % 32), mode="replicate")
        with torch.no_grad():
            hidden = self.backbone(
                pixel_values=(preview - self.mean) / self.std, output_hidden_states=True
            ).hidden_states[1:]
        pyramid = [lateral(x) for lateral, x in zip(self.laterals, hidden)]
        for index in range(2, -1, -1):
            pyramid[index] = pyramid[index] + F.interpolate(
                pyramid[index + 1], scale_factor=2, mode="bilinear", align_corners=False
            )
        return self.projection(pyramid[0])[..., : size[0], : size[1]] * self.gate
