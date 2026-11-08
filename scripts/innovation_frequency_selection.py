"""Input-only RAW/parent-innovation selection; nominal RAW units, not confidence."""

import numpy as np
from frequency_coverage import eligible_bins, sample_camera_rgb
from green_phase_spectrum import tapered_spectrum

VIEWS = {
    "RAW_current": ("RAW", 1 / 16),
    "innovation_current": ("innovation", 1 / 16),
    "RAW_wide": ("RAW", 1 / 64),
    "innovation_wide": ("innovation", 1 / 64),
}


def measurement_fields(packed, restored, colors):
    packed, restored = np.asarray(packed), np.asarray(restored)
    predicted = sample_camera_rgb(restored, colors)
    if packed.shape != predicted.shape or not np.isfinite(packed).all():
        raise ValueError("Expected matching finite native RGB and packed observations")
    # Deliberate FP64 diagnostic subtraction, not a claim of FP32 runtime parity.
    raw = packed.astype(np.float64)
    return {"RAW": raw, "innovation": raw - predicted.astype(np.float64)}


def pooled_score(field, variance, colors):
    field, variance, colors = map(np.asarray, (field, variance, colors))
    if (
        field.ndim != 4
        or field.shape[:2] != (1, 4)
        or variance.shape != field.shape
        or colors.shape != (1, 4)
        or not np.isfinite(variance).all()
        or (variance < 0).any()
    ):
        raise ValueError("Expected one four-phase field and nonnegative RAW variance")
    # This denominator remains RAW's propagated variance, including for the
    # correlated innovation. It is a shared unit convention, NOT residual noise.
    planes = []
    for phase in np.flatnonzero(colors[0] == 1):
        value = field[0, phase] - field[0, phase, 0, 0]
        record = tapered_spectrum(value, variance[0, phase])
        planes.append(
            abs(record["spectrum"]) ** 2 / np.maximum(record["noise_variance"], (1 / 65535) ** 2)
        )
    if len(planes) != 2:
        raise ValueError("Expected two green CFA phases")
    mean = np.mean(planes, axis=0)
    return sum(np.roll(mean, (dy, dx), (0, 1)) for dy in [-1, 0, 1] for dx in [-1, 0, 1]) / 9


def select_pooled(score, lower, *, count=8):
    score = np.asarray(score)
    if score.ndim != 2 or not np.isfinite(score).all() or (score < 0).any():
        raise ValueError("Expected a finite nonnegative pooled score")
    if type(count) is not int or not 1 <= count <= 16:
        raise ValueError("Expected count1..16")
    available = eligible_bins(score.shape, lower, 1 / 3)
    bins, values = [], []
    h, w = score.shape
    for _ in range(count):
        chosen = np.where(available, score, -np.inf)
        flat = int(chosen.argmax())
        if not np.isfinite(chosen.flat[flat]):
            raise ValueError("Too few eligible unsuppressed bins")
        y, x = divmod(flat, w)
        bins.append([y, x])
        values.append(float(score[y, x]))
        for cy, cx in [(y, x), ((-y) % h, (-x) % w)]:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    available[(cy + dy) % h, (cx + dx) % w] = False
    return {"bins_yx_rank_order": bins, "nominal_scores": values}


def fundamental_distances(shape, bins, angles, periods):
    """Nearest principal carrier to recipe fundamentals, measured in native bins."""
    bins = np.asarray(bins)
    centers = np.where(bins <= (np.asarray(shape) - 1) // 2, bins, bins - shape)
    native = 2 * np.asarray(shape)
    records = []
    for angle, period in zip(angles, periods, strict=True):
        target = native * np.asarray([np.sin(angle), np.cos(angle)]) / period
        delta = (
            centers[:, None, :] - np.asarray([target, -target])[None] + native / 2
        ) % native - native / 2
        distance = np.sqrt(np.sum(delta**2, axis=-1))
        rank, _ = np.unravel_index(distance.argmin(), distance.shape)
        records.append(
            {
                "minimum_distance_native_bins": float(distance.min()),
                "nearest_rank": int(rank),
                "fundamental_native_fy_fx": (target / native).tolist(),
            }
        )
    return records
