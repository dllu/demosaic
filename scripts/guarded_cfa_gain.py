"""Experimental input-only photometry with noise and reference-white guards.

This is a new fixed policy, separate from the rejected unmasked least squares.
No production model, training target or inference default uses it.
"""

import numpy as np
import torch

from demosaic.cfa import mosaic, pack

POLICY = {
    "name": "guarded-CFA-gain-v1",
    "fit_linear_RGB_upper": 0.90,
    "minimum_predicted_signal_sigma": 4.0,
    "minimum_samples_per_channel": 256,
    "gain_limits": [0.95, 1.05],
    "highlight_taper_linear_RGB": [0.90, 0.98],
    "sensor_epsilon": 1 / 65535,
    "denominator_floor": 1e-12,
}


def linear_rgb(prediction, wb, matrix):
    return torch.einsum(
        "bij,bjhw->bihw", matrix.double(), prediction.double() * wb.double()[..., None, None]
    )


def fit_terms(prediction, packed, variance, colors, wb, matrix):
    """Sufficient statistics only; reference/GT and display exposure unavailable.

    The four-sigma exclusion is a heuristic on supplied input noise, not a
    confidence interval for the correlated restored prediction. Negative noisy
    samples are retained; only the upper ADC boundary is excluded from data.
    """
    if packed.ndim != 4 or packed.shape[1] != 4 or packed.shape != variance.shape:
        raise ValueError("Expected four Bayer phases and matching variance")
    b, _, h, w = packed.shape
    if prediction.shape != (b, 3, 2 * h, 2 * w) or wb.shape != (b, 3) or matrix.shape != (b, 3, 3):
        raise ValueError("Prediction or camera metadata shape mismatch")
    if colors.ndim == 1:
        colors = colors[None].expand(b, -1)
    if colors.shape != (b, 4) or colors.dtype != torch.int64:
        raise ValueError("Expected integer Bayer labels")
    if not torch.equal(colors.sort(-1).values, colors.new_tensor([0, 1, 1, 2]).expand(b, -1)):
        raise ValueError("Invalid Bayer color counts")
    if any(not torch.isfinite(v).all() for v in [prediction, packed, variance, wb, matrix]):
        raise ValueError("Nonfinite fit inputs")
    if (variance < 0).any() or (wb <= 0).any():
        raise ValueError("Invalid variance or white balance")
    with torch.autocast(device_type=prediction.device.type, enabled=False):
        rgb = linear_rgb(prediction, wb, matrix).float()
        safe = (rgb.amin(1, keepdim=True) > 0) & (
            rgb.amax(1, keepdim=True) < POLICY["fit_linear_RGB_upper"]
        )
        p = mosaic(prediction.double(), colors)
        margin = (
            POLICY["minimum_predicted_signal_sigma"] * variance.double().sqrt()
            + POLICY["sensor_epsilon"]
        )
        valid = pack(safe) & (p > margin) & (p < 1 - margin)
        valid &= packed.double() < 1 - POLICY["sensor_epsilon"]
        numerators, denominators, counts = [], [], []
        for channel in range(3):
            mask = valid & (colors == channel)[..., None, None]
            numerators.append((p * packed.double() * mask).sum((1, 2, 3)))
            denominators.append((p.square() * mask).sum((1, 2, 3)))
            counts.append(mask.sum((1, 2, 3)))
        return {
            "numerator": torch.stack(numerators, 1),
            "denominator": torch.stack(denominators, 1),
            "count": torch.stack(counts, 1),
        }


def solve(terms):
    numerator, denominator, count = [terms[k] for k in ["numerator", "denominator", "count"]]
    supported = count >= POLICY["minimum_samples_per_channel"]
    supported &= (denominator >= POLICY["denominator_floor"]) & (numerator > 0)
    ratio = numerator / denominator.clamp_min(POLICY["denominator_floor"])
    return torch.where(supported, ratio.clamp(*POLICY["gain_limits"]), torch.ones_like(ratio))


def apply_gain(prediction, gains, wb, matrix):
    """One global fit per image with a continuous, fixed near-white taper.

    Gain magnitude is bounded5%; with an identity camera this keeps the neutral
    taper monotone. Camera mixing/color edges still require actual quality tests.
    No clipping of restored RGB values or independent display adjustment.
    """
    with torch.autocast(device_type=prediction.device.type, enabled=False):
        rgb = linear_rgb(prediction, wb, matrix)
        low, high = POLICY["highlight_taper_linear_RGB"]
        weight = ((high - rgb.amax(1, keepdim=True)) / (high - low)).clamp(0, 1)
        factor = 1 + weight * (gains.double()[..., None, None] - 1)
        return (prediction.double() * factor).float()


def correct(prediction, packed, variance, colors, wb, matrix):
    terms = fit_terms(prediction, packed, variance, colors, wb, matrix)
    gains = solve(terms)
    return apply_gain(prediction, gains, wb, matrix), gains, terms


def numpy_terms(prediction, packed, variance, colors, wb, matrix):
    """Independent camera sums and phase slices, without Torch/mosaic/pack."""
    p = prediction.astype(np.float64)
    b = len(p)
    balanced = p * wb.astype(np.float64)[..., None, None]
    rgb = np.stack(
        [
            sum(matrix[:, c, k, None, None].astype(np.float64) * balanced[:, k] for k in range(3))
            for c in range(3)
        ],
        1,
    ).astype(np.float32)
    safe = (rgb.min(1) > 0) & (rgb.max(1) < np.float32(POLICY["fit_linear_RGB_upper"]))
    out = {
        k: np.zeros((b, 3), dtype=np.int64 if k == "count" else np.float64)
        for k in ["numerator", "denominator", "count"]
    }
    for bi in range(b):
        for phase, c in enumerate(colors[bi]):
            dy, dx = divmod(phase, 2)
            values = p[bi, c, dy::2, dx::2]
            observed = packed[bi, phase].astype(np.float64)
            margin = (
                POLICY["minimum_predicted_signal_sigma"]
                * np.sqrt(variance[bi, phase].astype(np.float64))
                + POLICY["sensor_epsilon"]
            )
            valid = safe[bi, dy::2, dx::2] & (values > margin) & (values < 1 - margin)
            valid &= observed < 1 - POLICY["sensor_epsilon"]
            x, y = values[valid].ravel(), observed[valid].ravel()
            out["numerator"][bi, c] += float(np.dot(x, y))
            out["denominator"][bi, c] += float(np.dot(x, x))
            out["count"][bi, c] += len(x)
    return out


def numpy_solve(terms):
    n, d, c = [terms[k] for k in ["numerator", "denominator", "count"]]
    supported = (
        (c >= POLICY["minimum_samples_per_channel"]) & (d >= POLICY["denominator_floor"]) & (n > 0)
    )
    ratio = n / np.maximum(d, POLICY["denominator_floor"])
    return np.where(supported, np.clip(ratio, *POLICY["gain_limits"]), 1.0)


def numpy_apply(prediction, gains, wb, matrix):
    p = prediction.astype(np.float64)
    balanced = p * wb.astype(np.float64)[..., None, None]
    rgb = np.stack(
        [
            sum(matrix[:, c, k, None, None].astype(np.float64) * balanced[:, k] for k in range(3))
            for c in range(3)
        ],
        1,
    )
    low, high = POLICY["highlight_taper_linear_RGB"]
    weight = np.clip((high - rgb.max(1, keepdims=True)) / (high - low), 0, 1)
    return (p * (1 + weight * (gains[..., None, None] - 1))).astype(np.float32)
