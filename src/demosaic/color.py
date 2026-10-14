"""Explicit scene-linear and display transforms; no hidden 8-bit conversions."""

import numpy as np
import torch


def srgb_to_linear(x):
    if isinstance(x, np.ndarray):
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return torch.where(x <= 0.04045, x / 12.92, ((x.clamp_min(0) + 0.055) / 1.055).pow(2.4))


def linear_to_srgb(x):
    if isinstance(x, np.ndarray):
        return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.maximum(x, 0) ** (1 / 2.4) - 0.055)
    return torch.where(x <= 0.0031308, 12.92 * x, 1.055 * x.clamp_min(1e-10).pow(1 / 2.4) - 0.055)


def render(rgb, white_balance=None, matrix=None):
    """B×3×H×W camera RGB -> clipped sRGB, for previews and display losses."""
    if white_balance is not None:
        rgb = rgb * white_balance[..., None, None]
    if matrix is not None:
        rgb = torch.einsum("bij,bjhw->bihw", matrix, rgb)
    return linear_to_srgb(rgb.clamp(0, 1)).clamp(0, 1)
