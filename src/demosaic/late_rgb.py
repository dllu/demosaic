"""Optional learned RGB refinement with one existing frozen-DINO feature pass."""

import torch
from torch import nn
from torch.nn import functional as F

from .precision import ieee_fp32


class NeighborhoodBlock(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.local3 = nn.Conv2d(width, width, 3, padding=1, groups=width)
        self.local5 = nn.Conv2d(width, width, 5, padding=2, groups=width)
        self.mix = nn.Conv2d(width, width, 1)

    def forward(self, x):
        return x + self.mix(F.gelu(self.local3(x) + self.local5(x)))


class LateRgbRefinement(nn.Module):
    """Refine normalized restored RGB; global/spatial differ only in prompt pooling.

    Four zero-initialized projections generate scale/shift fields. A separate
    zero RGB output preserves the parent, including its common gradients.
    This head learns RGB directly, without forcing noisy CFA agreement or
    using a fixed Malvar innovation. Existing earlier DINO guidance is retained.
    """

    def __init__(self, feature_channels, mode, *, width=32):
        super().__init__()
        if mode not in ("global", "spatial") or len(feature_channels) != 4:
            raise ValueError("Late RGB refinement requires global/spatial and four DINO stages")
        self.mode = mode
        self.feature_channels = tuple(feature_channels)
        self.input = nn.Conv2d(67 + 21, width, 1)
        self.modulations = nn.ModuleList(nn.Conv2d(c, 2 * width, 1) for c in feature_channels)
        self.blocks = nn.Sequential(NeighborhoodBlock(width), NeighborhoodBlock(width))
        self.output = nn.Conv2d(width, 3, 3, padding=1)
        for layer in [*self.modulations, self.output]:
            nn.init.zeros_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, prediction, decoder_features, condition, dino_features):
        batch, channels, height, width = prediction.shape
        if (
            channels != 3
            or decoder_features.shape != (batch, 67, height, width)
            or condition.shape != (batch, 21, height, width)
            or len(dino_features) != 4
        ):
            raise ValueError("Late RGB refinement requires aligned native RGB/decoder/conditioning")
        hidden = F.gelu(self.input(torch.cat((decoder_features, condition), 1)))
        field = None
        for index, (feature, projection, channels) in enumerate(
            zip(dino_features, self.modulations, self.feature_channels, strict=True)
        ):
            stride = 4 * 2**index
            if feature.shape != (
                batch,
                channels,
                (height + -height % 32) // stride,
                (width + -width % 32) // stride,
            ):
                raise ValueError("Late DINO feature grid must retain the padded native coordinates")
            prompt = projection(feature.detach())
            if self.mode == "global":
                prompt = prompt.mean((-2, -1), keepdim=True).expand_as(prompt)
            prompt = F.interpolate(
                prompt, scale_factor=stride, mode="bilinear", align_corners=False
            )
            prompt = prompt[..., :height, :width]
            field = prompt.float() if field is None else field + prompt.float()
        with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
            scale, shift = (field / 4).chunk(2, dim=1)
            hidden = hidden.float() * (1 + scale) + shift
        delta = self.output(self.blocks(hidden))
        with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
            return prediction.float() + delta.float()
