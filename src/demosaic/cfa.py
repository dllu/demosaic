"""Spatial-phase Bayer packing. Phases always mean TL, TR, BL, BR, not RGGB."""

import torch
from torch import Tensor
from torch.nn import functional as F

PATTERNS = {"RGGB": (0, 1, 1, 2), "BGGR": (2, 1, 1, 0), "GRBG": (1, 0, 2, 1), "GBRG": (1, 2, 0, 1)}


def color_indices(pattern: str, *, device=None) -> Tensor:
    try:
        return torch.tensor(PATTERNS[pattern.upper()], device=device, dtype=torch.long)
    except KeyError:
        raise ValueError(
            f"Unsupported CFA {pattern!r}; expected one of {tuple(PATTERNS)}"
        ) from None


def pack(mosaic: Tensor) -> Tensor:
    """B×1×H×W -> B×4×H/2×W/2. Input dimensions must be even."""
    if mosaic.ndim != 4 or mosaic.shape[1] != 1:
        raise ValueError("Expected B×1×H×W mosaic")
    if mosaic.shape[-2] % 2 or mosaic.shape[-1] % 2:
        raise ValueError("Bayer packing requires even dimensions")
    return F.pixel_unshuffle(mosaic, 2)


def unpack(packed: Tensor) -> Tensor:
    if packed.ndim != 4 or packed.shape[1] != 4:
        raise ValueError("Expected B×4×H×W packed Bayer")
    return F.pixel_shuffle(packed, 2)


def mosaic(rgb: Tensor, colors: Tensor) -> Tensor:
    """Sample linear camera RGB at the specified per-batch CFA phases."""
    if colors.ndim == 1:
        colors = colors.unsqueeze(0).expand(rgb.shape[0], -1)
    # unshuffle groups all four spatial phases for each RGB channel.
    phases = F.pixel_unshuffle(rgb, 2).reshape(
        rgb.shape[0], 3, 4, rgb.shape[-2] // 2, rgb.shape[-1] // 2
    )
    return phases.gather(
        1, colors[:, None, :, None, None].expand(-1, 1, -1, phases.shape[-2], phases.shape[-1])
    ).squeeze(1)


def bilinear(packed: Tensor, colors: Tensor) -> Tensor:
    """Normalized convolution with exact preservation of observed samples."""
    batch, _, height, width = packed.shape
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    masks = F.one_hot(colors, 3).to(packed.dtype).permute(0, 2, 1)[..., None, None]
    sparse = F.pixel_shuffle((packed[:, None] * masks).reshape(batch, 12, height, width), 2)
    mask = F.pixel_shuffle(
        masks.expand(-1, -1, -1, height, width).reshape(batch, 12, height, width), 2
    )
    kernel = packed.new_tensor([[1, 2, 1], [2, 4, 2], [1, 2, 1]])[None, None]
    kernel = kernel.expand(3, 1, 3, 3)
    numerator = F.conv2d(F.pad(sparse, (1, 1, 1, 1), mode="replicate"), kernel, groups=3)
    denominator = F.conv2d(F.pad(mask, (1, 1, 1, 1), mode="replicate"), kernel, groups=3)
    result = numerator / denominator.clamp_min(1e-8)
    return torch.where(mask.bool(), sparse, result)
