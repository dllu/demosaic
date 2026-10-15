"""Spatial-phase Bayer packing. Phases always mean TL, TR, BL, BR, not RGGB."""

import torch
from torch import Tensor
from torch.nn import functional as F

from .precision import ieee_fp32

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


def bilinear(packed: Tensor, colors: Tensor, *, fp32=True) -> Tensor:
    """Normalized interpolation, kept in FP32 even inside network autocast."""
    if fp32:
        with (
            torch.autocast(device_type=packed.device.type, enabled=False),
            ieee_fp32(),
        ):
            return _bilinear(packed.float(), colors)
    return _bilinear(packed, colors)


def _bilinear(packed, colors):
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


def malvar(packed: Tensor, colors: Tensor, wb=None) -> Tensor:
    """FP32 Malvar-He-Cutler 5×5 linear demosaicing (ICASSP 2004, Fig. 2).

    Independently implemented from the published filters, with phase-preserving
    reflected borders. A classical comparator, not a trained denoiser.
    """
    with (
        torch.autocast(device_type=packed.device.type, enabled=False),
        ieee_fp32(),
    ):
        packed = packed.float()
        batch, _, height, width = packed.shape
        if min(height, width) < 2:
            raise ValueError("Malvar interpolation requires at least a 4×4 mosaic")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if wb is not None:
            wb = torch.as_tensor(wb, device=packed.device, dtype=torch.float32).reshape(-1, 3)
            wb = wb.expand(batch, -1).clamp_min(1e-6)
            packed = packed * wb.gather(1, colors)[..., None, None]
        raw = unpack(packed)
        green = (
            packed.new_tensor(
                [
                    [0, 0, -1, 0, 0],
                    [0, 0, 2, 0, 0],
                    [-1, 2, 4, 2, -1],
                    [0, 0, 2, 0, 0],
                    [0, 0, -1, 0, 0],
                ]
            )
            / 8
        )
        horizontal = (
            packed.new_tensor(
                [
                    [0, 0, 0.5, 0, 0],
                    [0, -1, 0, -1, 0],
                    [-1, 4, 5, 4, -1],
                    [0, -1, 0, -1, 0],
                    [0, 0, 0.5, 0, 0],
                ]
            )
            / 8
        )
        diagonal = (
            packed.new_tensor(
                [
                    [0, 0, -1.5, 0, 0],
                    [0, 2, 0, 2, 0],
                    [-1.5, 0, 6, 0, -1.5],
                    [0, 2, 0, 2, 0],
                    [0, 0, -1.5, 0, 0],
                ]
            )
            / 8
        )
        kernels = torch.stack((green, horizontal, horizontal.T, diagonal))[:, None]
        g, horizontal, vertical, diagonal = F.conv2d(
            F.pad(raw, (2, 2, 2, 2), mode="reflect"), kernels
        ).split(1, dim=1)
        labels = F.one_hot(colors, 3).permute(0, 2, 1)[..., None, None]
        masks = F.pixel_shuffle(
            labels.expand(-1, -1, -1, height, width).reshape(batch, 12, height, width).float(), 2
        ).bool()
        parity = torch.arange(height * 2, device=packed.device)[None, :, None] % 2
        red_row = ((colors == 0).long().argmax(1) // 2)[:, None, None]
        blue_row = ((colors == 2).long().argmax(1) // 2)[:, None, None]
        red = torch.where((parity == red_row)[:, None], horizontal, vertical)
        blue = torch.where((parity == blue_row)[:, None], horizontal, vertical)
        red = torch.where(masks[:, 0:1], raw, torch.where(masks[:, 2:3], diagonal, red))
        blue = torch.where(masks[:, 2:3], raw, torch.where(masks[:, 0:1], diagonal, blue))
        result = torch.cat((red, torch.where(masks[:, 1:2], raw, g), blue), dim=1)
        return result if wb is None else result / wb[..., None, None]
