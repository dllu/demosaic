"""Model-independent integer registration and sensor-unit reference calibration."""

from dataclasses import asdict, dataclass

import numpy as np

from .cfa import PATTERNS


@dataclass(frozen=True)
class Alignment:
    # Observation[y,x] corresponds to gain * reference[y-dy,x-dx].
    dy: int
    dx: int
    gain: float
    green_l1: float
    samples: int
    coarse_shift: tuple[int, int]

    def to_dict(self):
        return asdict(self)


def green_plane(raw, pattern):
    """Preserve measured greens and interpolate only missing green positions."""
    raw = np.asarray(raw, dtype=np.float32)
    if raw.ndim != 2 or min(raw.shape) < 8 or not np.isfinite(raw).all():
        raise ValueError("Expected finite 2D Bayer measurements")
    colors = PATTERNS[pattern]
    h, w = raw.shape
    green = raw.copy()
    for phase, color in enumerate(colors):
        if color == 1:
            continue
        y, x = divmod(phase, 2)
        ys, xs = slice(2 + y, h - 2, 2), slice(2 + x, w - 2, 2)
        green[ys, xs] = (
            raw[1 + y : h - 3 : 2, xs]
            + raw[3 + y : h - 1 : 2, xs]
            + raw[ys, 1 + x : w - 3 : 2]
            + raw[ys, 3 + x : w - 1 : 2]
        ) * 0.25
    return green


def align_raw(reference, observed, reference_pattern, observed_pattern, *, max_shift=128):
    """Coarse phase correlation, then bounded integer green-L1 refinement.

    Registration/gain use only the two sensor captures, never a model output.
    Color primaries/WB are irrelevant to matching the same camera's greens.
    A reference-only signal mask avoids selecting positive noisy shadow tails.
    """
    if reference.shape != observed.shape or max_shift < 0:
        raise ValueError("Pair geometry must match and max_shift must be nonnegative")
    a, b = green_plane(reference, reference_pattern), green_plane(observed, observed_pattern)
    h, w = a.shape
    margin = max_shift + 8
    if min(h, w) <= 2 * margin + 32:
        raise ValueError("Pair is too small for the requested registration range")
    down = 8

    def coarse(image):
        height, width = h // down * down, w // down * down
        small = (
            image[:height, :width].reshape(height // down, down, width // down, down).mean((1, 3))
        )
        small = np.sqrt(small.clip(0, 1))
        small -= small.mean()
        if small.std() < 0.003:
            raise ValueError("Insufficient scene contrast for registration")
        return small * np.hanning(small.shape[0])[:, None] * np.hanning(small.shape[1])[None]

    fa, fb = np.fft.rfft2(coarse(a)), np.fft.rfft2(coarse(b))
    cross = fb * fa.conj()
    cross /= np.maximum(np.abs(cross), 1e-12)
    corr = np.fft.fftshift(np.fft.irfft2(cross, s=(h // down, w // down)))
    cy, cx = np.array(corr.shape) // 2
    radius = int(np.ceil(max_shift / down))
    local = corr[cy - radius : cy + radius + 1, cx - radius : cx + radius + 1]
    py, px = np.unravel_index(np.argmax(local), local.shape)
    initial = ((int(py) - radius) * down, (int(px) - radius) * down)
    stride = max(3, int(np.sqrt(h * w / 200_000)) | 1)
    sample = b[margin : h - margin : stride, margin : w - margin : stride]

    def score(dy, dx):
        target = a[margin - dy : h - margin - dy : stride, margin - dx : w - margin - dx : stride]
        valid = (target > 0.005) & (target < 0.9)
        if valid.sum() < 256:
            return float("inf"), 1.0, 0
        x, y = target[valid], sample[valid]
        gain = float(np.sum(x * y, dtype=np.float64) / np.sum(x * x, dtype=np.float64))
        if not 0.01 < gain < 100:
            return float("inf"), gain, 0
        valid &= (target * gain > 0.005) & (target * gain < 0.9)
        x, y = target[valid], sample[valid]
        if len(x) < 256:
            return float("inf"), gain, len(x)
        gain = float(np.sum(x * y, dtype=np.float64) / np.sum(x * x, dtype=np.float64))
        return float(np.mean(np.abs(y - gain * x))), gain, len(x)

    candidates = []
    for dy in range(
        max(-max_shift, initial[0] - down - 1), min(max_shift, initial[0] + down + 1) + 1
    ):
        for dx in range(
            max(-max_shift, initial[1] - down - 1), min(max_shift, initial[1] + down + 1) + 1
        ):
            error, gain, count = score(dy, dx)
            candidates.append((error, dy, dx, gain, count))
    error, dy, dx, gain, count = min(candidates)
    if not np.isfinite(error) or error > 0.035:
        raise ValueError(f"Unreliable registration: green L1={error:.6f}")
    return Alignment(dy, dx, gain, error, count, initial)


def calibrate_rgb(rgb, raw, pattern):
    """Calibrate an independently demosaiced reference against its own CFA.

    LibRaw's RGB scaling can differ from camera_white_level_per_channel used
    by read_raw. Gains are derived from clean data only, shared by all methods.
    RGB input is linear H×W×3 float; raw is normalized H×W sensor measurements.
    """
    rgb, raw = np.asarray(rgb, dtype=np.float32), np.asarray(raw, dtype=np.float32)
    if rgb.shape != (*raw.shape, 3) or not np.isfinite(rgb).all():
        raise ValueError("Reference RGB and sensor dimensions must match")
    xx, xy = np.zeros(3), np.zeros(3)
    counts = np.zeros(3, dtype=np.int64)
    for phase, color in enumerate(PATTERNS[pattern]):
        y, x = divmod(phase, 2)
        target = raw[16 + y : -16 : 8, 16 + x : -16 : 8]
        source = rgb[16 + y : -16 : 8, 16 + x : -16 : 8, color]
        valid = (target > 0.005) & (target < 0.8) & (source > 0) & (source < 0.98)
        xx[color] += np.sum(source[valid] ** 2, dtype=np.float64)
        xy[color] += np.sum(source[valid] * target[valid], dtype=np.float64)
        counts[color] += valid.sum()
    if np.any(counts < 64) or np.any(xx <= 0):
        raise ValueError("Insufficient clean sensor samples to calibrate RGB reference")
    gains = xy / xx
    if not np.isfinite(gains).all() or np.any(gains <= 0):
        raise ValueError("Invalid reference-unit calibration")
    return rgb * gains.astype(np.float32), {
        "rgb_to_sensor_gains": gains.tolist(),
        "samples": counts.tolist(),
    }


def measured_reference(raw, pattern, alignment, y, x, size):
    """Sparse RGB truth from actual clean CFA samples, including odd shifts."""
    dy, dx = alignment.dy, alignment.dx
    if min(y - dy, x - dx) < 0 or y - dy + size > raw.shape[0] or x - dx + size > raw.shape[1]:
        raise ValueError("Aligned reference crop is outside its sensor")
    crop = raw[y - dy : y - dy + size, x - dx : x - dx + size] * alignment.gain
    values = np.zeros((3, size, size), dtype=np.float32)
    weights = np.zeros((3, size, size), dtype=np.uint8)
    for py in range(2):
        for px in range(2):
            phase = ((y - dy + py) % 2) * 2 + (x - dx + px) % 2
            color = PATTERNS[pattern][phase]
            values[color, py::2, px::2] = crop[py::2, px::2]
            weights[color, py::2, px::2] = 1
    return values, weights
