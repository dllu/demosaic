"""Established camera-RGB and photographic detail reductions, without script imports."""

import numpy as np

from demosaic.archive_metrics import linear_rgb


def band(values):
    """DCT16 annulus 1/8 <= radial frequency < 1/3, native160 pixels."""
    values = np.asarray(values, dtype=np.float64)
    c = np.cos(np.pi * (np.arange(16)[None] + 0.5) * np.arange(16)[:, None] / 16)
    c *= np.sqrt(2 / 16)
    c[0] /= np.sqrt(2)
    f = np.arange(16) / 32
    radius = np.hypot(f[:, None], f[None])
    selected = (radius >= 1 / 8) & (radius < 1 / 3)
    luma = np.einsum("c,bchw->bhw", np.array([0.2126, 0.7152, 0.0722]), values)
    blocks = luma.reshape(len(luma), 10, 16, 10, 16).transpose(0, 1, 3, 2, 4)
    blocks = blocks.reshape(len(luma), 100, 16, 16)
    return (c @ blocks @ c.T)[..., selected], blocks.mean((-1, -2))


def errors(value, target, roi):
    x, y, w, h = roi
    full = value.astype(np.float64) - target.astype(np.float64)
    crop = full[..., y : y + h, x : x + w]
    dc = crop.mean((-2, -1), keepdims=True)
    return {
        "full_error_RMS_DN16": float(np.sqrt(np.mean(full**2)) * 65535),
        "crop_spatial_RMS_DN16": float(np.sqrt(np.mean((crop - dc) ** 2)) * 65535),
        "crop_DC_RMS_DN16": float(np.sqrt(np.mean(dc**2)) * 65535),
    }


def photo_metrics(value, target, arrays, roi):
    x, y, w, h = roi
    a, b = [v[..., y : y + h, x : x + w].astype(np.float64) for v in (value, target)]
    error = a - b
    dc = error.mean((-1, -2), keepdims=True)
    predicted, _ = band(linear_rgb(a, arrays))
    truth, _ = band(linear_rgb(b, arrays))
    energy = float(np.sum(truth * truth))
    if energy <= 0:
        raise ValueError("Photo diagnostic needs nonzero target detail")
    gain = float(np.sum(predicted * truth) / energy)
    return {
        "full_error_RMS_DN16": float(
            np.sqrt(np.mean((value.astype(np.float64) - target) ** 2)) * 65535
        ),
        "crop_error_RMS_DN16": float(np.sqrt(np.mean(error**2)) * 65535),
        "crop_DC_RMS_DN16": float(np.sqrt(np.mean(dc**2)) * 65535),
        "crop_spatial_RMS_DN16": float(np.sqrt(np.mean((error - dc) ** 2)) * 65535),
        "crop_linear_sRGB_luma_band_gain": gain,
        "crop_relative_band_error": float(np.sqrt(np.sum((predicted - truth) ** 2) / energy)),
        "crop_orthogonal_band_RMS_DN16": float(
            np.sqrt(np.sum((predicted - gain * truth) ** 2) / (100 * 256)) * 65535
        ),
    }
