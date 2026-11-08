"""Selected-bin proximity to hidden CFA template power, never a recovery bound.

Counterfactual selection reads one RAW green phase at a time. Exact templates
are diagnostic-only inputs. Local interpolation/mixing can create frequencies
outside a Fourier footprint, and principal CFA aliases remain unresolved.
"""

import math

import numpy as np


def eligible_bins(shape, lower, upper, *, upper_inclusive=True):
    if (
        len(shape) != 2
        or any(type(n) is not int or n < 8 for n in shape)
        or not math.isfinite(lower)
        or not math.isfinite(upper)
        or not 0 < lower < upper <= math.sqrt(2) / 4
    ):
        raise ValueError("Expected axes>=8 and finite ordered principal radial band")
    fy, fx = [np.fft.fftfreq(n) / 2 for n in shape]
    radius = np.hypot(fy[:, None], fx[None, :])
    upper_mask = radius <= upper if upper_inclusive else radius < upper
    return (
        (radius >= lower)
        & upper_mask
        & ((fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0)))
    )


def select_bins(spectrum, variance, eligible, *, count=4):
    spectrum, variance, available = [np.asarray(v) for v in [spectrum, variance, eligible]]
    if (
        spectrum.ndim != 2
        or variance.shape != spectrum.shape
        or available.shape != spectrum.shape
        or available.dtype != np.bool_
        or not np.isfinite(spectrum).all()
        or not np.isfinite(variance).all()
        or (variance <= 0).any()
        or type(count) is not int
        or not 1 <= count <= 16
    ):
        raise ValueError("Expected finite spectrum/positive variance/boolean mask and count1..16")
    available = available.copy()
    power = np.abs(spectrum) ** 2 / variance
    bins = []
    for _ in range(count):
        score = np.where(available, power, -np.inf)
        flat = int(np.argmax(score))
        if not np.isfinite(score.flat[flat]):
            break
        y, x = divmod(flat, spectrum.shape[1])
        bins.append([y, x])
        for cy, cx in [(y, x), ((-y) % len(spectrum), (-x) % spectrum.shape[1])]:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    available[(cy + dy) % len(spectrum), (cx + dx) % spectrum.shape[1]] = False
    return bins


def footprint(shape, bins, radius):
    if len(shape) != 2 or type(radius) is not int or radius < 0:
        raise ValueError("Expected two axes and nonnegative integer bin radius")
    result = np.zeros(shape, dtype=bool)
    bins = np.asarray(bins)
    if bins.size == 0:
        return result
    if (
        bins.ndim != 2
        or bins.shape[1] != 2
        or not np.issubdtype(bins.dtype, np.integer)
        or not ((bins >= 0) & (bins < shape)).all()
    ):
        raise ValueError("Expected in-range integer Nx2 frequency bins")
    for y, x in bins:
        for cy, cx in [(y, x), ((-y) % shape[0], (-x) % shape[1])]:
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    result[(cy + dy) % shape[0], (cx + dx) % shape[1]] = True
    return result


def power_fraction(power, mask):
    power, mask = np.asarray(power), np.asarray(mask)
    if (
        power.ndim != 2
        or mask.shape != power.shape
        or mask.dtype != np.bool_
        or not np.isfinite(power).all()
        or (power < 0).any()
    ):
        raise ValueError("Expected finite nonnegative power and matching mask")
    total = float(power.sum(dtype=np.float64))
    return None if total == 0 else float(power[mask].sum(dtype=np.float64) / total)


def sample_camera_rgb(value, colors):
    value, colors = np.asarray(value), np.asarray(colors)
    if (
        value.ndim != 4
        or value.shape[1] != 3
        or colors.shape != (len(value), 4)
        or not np.isfinite(value).all()
    ):
        raise ValueError("Expected finite Nx3 RGB and Nx4 CFA layout")
    allowed = {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
    if any(tuple(c) not in allowed for c in colors):
        raise ValueError("Expected standard CFA layout")
    return np.stack(
        [
            np.stack([rgb[int(c), p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(layout)])
            for rgb, layout in zip(value, colors, strict=True)
        ]
    )
