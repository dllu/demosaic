"""Independent NumPy float64 reductions for saved precision-pilot outputs."""

import hashlib
import json
import math
from functools import lru_cache

import numpy as np

ROI = (48, 48, 160, 160)


def input_fingerprint(values):
    """Independently reproduce the producer's five-forward-argument byte trace."""
    digest = hashlib.sha256()
    for name in sorted(("packed", "variance", "colors", "wb", "matrix")):
        value = np.asarray(values[name])
        if value.dtype not in (np.dtype("float32"), np.dtype("int64")):
            raise ValueError("Unexpected physical-input dtype")
        header = {"name": name, "dtype": "torch." + value.dtype.name, "shape": list(value.shape)}
        digest.update(json.dumps(header, sort_keys=True).encode() + b"\0")
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def comparison_gates(kind, baseline, current):
    """Fixed per-observation noninferiority gates; no group can hide a failure."""
    if kind == "photo":
        return {
            "PSNR_loss_at_most_0.05dB": current["srgb_psnr"] >= baseline["srgb_psnr"] - 0.05,
            "SSIM_loss_at_most_0.0001": current["srgb_ssim"] >= baseline["srgb_ssim"] - 0.0001,
        }
    if kind in ("adc-carrier", "weak-noisy-carrier"):
        return {
            "signed_gain_loss_at_most_0.05": current["in_phase_gain"]
            >= baseline["in_phase_gain"] - 0.05
        }
    if kind == "flat":
        return {
            "flat_luma_RMS_at_most_1.25x": current["spatial_luma_rms"]
            <= 1.25 * baseline["spatial_luma_rms"]
        }
    raise ValueError("Unknown fixed precision gate kind")


def finite_rgb(value):
    value = np.asarray(value)
    if value.ndim != 4 or value.shape[1] != 3 or not np.isfinite(value).all():
        raise ValueError("Expected finite BCHW RGB")
    return value.astype(np.float64)


def linear_rgb(rgb, wb, matrix):
    rgb = finite_rgb(rgb)
    return np.einsum(
        "bij,bjhw->bihw",
        np.asarray(matrix, np.float64),
        rgb * np.asarray(wb, np.float64)[..., None, None],
    )


def display_rgb(rgb, wb, matrix):
    value = np.clip(linear_rgb(rgb, wb, matrix), 0, 1)
    return np.clip(
        np.where(
            value <= 0.0031308, value * 12.92, 1.055 * np.maximum(value, 1e-10) ** (1 / 2.4) - 0.055
        ),
        0,
        1,
    )


def display_metrics(prediction, target, wb, matrix):
    """Full-image sRGB PSNR/SSIM, Gaussian11/sigma1.5 with valid windows."""
    p, t = display_rgb(prediction, wb, matrix), display_rgb(target, wb, matrix)
    if p.shape != t.shape or min(p.shape[-2:]) < 11:
        raise ValueError("Photo prediction/target shape differs or lacks valid SSIM windows")
    axis = np.arange(-5, 6, dtype=np.float64)
    kernel = np.exp(-(axis * axis) / (2 * 1.5**2))
    kernel /= kernel.sum()

    def smooth(value):
        # Native NumPy valid windows avoid a separate dependency or padded edge pixels.
        horizontal = np.einsum(
            "...k,k->...", np.lib.stride_tricks.sliding_window_view(value, 11, axis=-1), kernel
        )
        return np.einsum(
            "...k,k->...",
            np.lib.stride_tricks.sliding_window_view(horizontal, 11, axis=-2),
            kernel,
        )

    mp, mt = smooth(p), smooth(t)
    vp, vt = np.maximum(smooth(p * p) - mp * mp, 0), np.maximum(smooth(t * t) - mt * mt, 0)
    bound = np.sqrt(vp * vt)
    covariance = np.clip(smooth(p * t) - mp * mt, -bound, bound)
    ssim = ((2 * mp * mt + 0.01**2) * (2 * covariance + 0.03**2)) / (
        (mp * mp + mt * mt + 0.01**2) * (vp + vt + 0.03**2)
    )
    mse = np.mean((p - t) ** 2, axis=(1, 2, 3))
    return {
        "srgb_psnr": -10 * np.log10(np.maximum(mse, 1e-12)),
        "srgb_ssim": ssim.mean(axis=(1, 2, 3)),
    }


def crop(rgb, roi=ROI):
    value = finite_rgb(rgb)
    x, y, w, h = roi
    if x < 0 or y < 0 or min(w, h) < 1 or x + w > value.shape[-1] or y + h > value.shape[-2]:
        raise ValueError("ROI is outside the saved native prediction")
    return value[..., y : y + h, x : x + w]


@lru_cache(maxsize=3)
def carrier_basis(period, roi=ROI):
    x, _y, w, h = roi
    angle = np.arange(x, x + w, dtype=np.float64) * (2 * math.pi / period)
    basis = np.stack(
        (
            np.ones((h, w)),
            np.broadcast_to(np.cos(angle), (h, w)),
            np.broadcast_to(np.sin(angle), (h, w)),
        ),
        axis=-1,
    ).reshape(-1, 3)
    return basis, np.linalg.pinv(basis)


def carrier_metrics(prediction, target, period, roi=ROI):
    p, t = (
        crop(prediction, roi).reshape(len(prediction), 3, -1),
        crop(target, roi).reshape(len(target), 3, -1),
    )
    if p.shape != t.shape:
        raise ValueError("Carrier prediction/target shape differs")
    basis, inverse = carrier_basis(period, roi)
    bp, bt = p @ inverse.T, t @ inverse.T
    a, b = bp[..., 1:], bt[..., 1:]
    power = np.maximum((b * b).sum(-1), 1e-24)
    gain = (a * b).sum(-1) / power
    quadrature = (b[..., 0] * a[..., 1] - b[..., 1] * a[..., 0]) / power
    residual = p - bp @ basis.T
    return {
        "in_phase_gain": gain.mean(1),
        "gain_channel_std": gain.std(1),
        "quadrature_gain": quadrature.mean(1),
        "amplitude_ratio": np.sqrt((a * a).sum(-1) / power).mean(1),
        "dc_bias_abs": np.abs(bp[..., 0] - bt[..., 0]).mean(1),
        "noncarrier_rms": np.sqrt((residual * residual).mean((1, 2))),
        "linear_srgb_rmse": np.sqrt(((p - t) ** 2).mean((1, 2))),
    }


def flat_metrics(prediction, target, roi=ROI):
    p, t = crop(prediction, roi), crop(target, roi)
    if p.shape != t.shape:
        raise ValueError("Flat prediction/target shape differs")
    weights = np.array([0.2126, 0.7152, 0.0722])[None, :, None, None]
    luma, truth = (p * weights).sum(1), (t * weights).sum(1)
    centered = luma - luma.mean((-2, -1), keepdims=True)
    h, w = luma.shape[-2:]
    radius = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :])
    band = (radius >= 1 / 48) & (radius <= 0.22)
    spectrum = np.abs(np.fft.fft2(centered))
    level = np.maximum(np.abs(truth.mean((-2, -1))), 1e-12)
    return {
        "dc_bias_abs_rgb": np.abs(p.mean((-2, -1)) - t.mean((-2, -1))).mean(1),
        "linear_srgb_rmse": np.sqrt(((p - t) ** 2).mean((1, 2, 3))),
        "spatial_luma_rms": np.sqrt((centered * centered).mean((-2, -1))),
        "relative_band_rms": np.sqrt(((spectrum * spectrum) * band).sum((-2, -1)))
        / (h * w)
        / level,
        "relative_peak_band_contrast": 2 * np.max(spectrum * band, axis=(-2, -1)) / (h * w) / level,
    }


def physical_difference(prediction, baseline):
    p, b = finite_rgb(prediction), finite_rgb(baseline)
    if p.shape != b.shape:
        raise ValueError("Precision predictions have different shapes")
    delta = p - b
    return {
        "RGB_values": delta.size,
        "max_abs_DN16": float(np.abs(delta).max() * 65535),
        "RMS_DN16": float(np.sqrt(np.mean(delta * delta)) * 65535),
    }
