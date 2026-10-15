"""Explicit scene-linear and display transforms; no hidden 8-bit conversions."""

import numpy as np
import torch

from .precision import ieee_fp32


def srgb_to_linear(x):
    if isinstance(x, np.ndarray):
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return torch.where(x <= 0.04045, x / 12.92, ((x.clamp_min(0) + 0.055) / 1.055).pow(2.4))


def linear_to_srgb(x):
    if isinstance(x, np.ndarray):
        return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.maximum(x, 0) ** (1 / 2.4) - 0.055)
    return torch.where(x <= 0.0031308, 12.92 * x, 1.055 * x.clamp_min(1e-10).pow(1 / 2.4) - 0.055)


def render(rgb, white_balance=None, matrix=None, *, fp32=True):
    """B×3×H×W camera RGB -> clipped sRGB, for previews and display losses."""
    if fp32:
        with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
            return _render(
                rgb.float(),
                None if white_balance is None else white_balance.float(),
                None if matrix is None else matrix.float(),
            )
    return _render(rgb, white_balance, matrix)


def _render(rgb, white_balance, matrix):
    if white_balance is not None:
        rgb = rgb * white_balance[..., None, None]
    if matrix is not None:
        rgb = torch.einsum("bij,bjhw->bihw", matrix, rgb)
    return linear_to_srgb(rgb.clamp(0, 1)).clamp(0, 1)
