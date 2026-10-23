"""Conservative isolated bright-defect correction in normalized Bayer data."""

import hashlib
import math

import numpy as np

NEIGHBORS = ((-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2))


def _second_largest(values):
    largest = values[0].copy()
    second = np.full_like(largest, -np.inf)
    for value in values[1:]:
        second = np.maximum(second, np.minimum(largest, value))
        largest = np.maximum(largest, value)
    return second


def _bright_outlier(value, reference, shot, read, sigma, ratio, min_delta):
    positive = np.maximum(reference, 0)
    margin = np.maximum(min_delta, sigma * np.sqrt(shot * positive + read))
    return (value > ratio * positive) & (value - reference > margin)


def repair_hot_pixels(
    raw,
    *,
    shot,
    read,
    sigma=6.0,
    ratio=2.0,
    min_delta=0.005,
    rows=128,
    clusters=False,
    pattern="RGGB",
):
    """Replace isolated bright sites before demosaicing, using unchanged input.

    All eight neighbors at offsets {-2,0,2} share the center's Bayer phase.
    A candidate must exceed their maximum by both a noise-aware margin and a
    multiplicative contrast. An immediately neighboring photosite that is also
    bright relative to its own CFA surroundings protects coherent light detail.
    Replace remaining candidates with their same-phase median. Multi-site lines
    and highlights therefore block correction; three-pixel borders and hot clusters
    are deliberately left alone. A genuine unresolved single-color light can
    still be ambiguous in one exposure, so correction is an explicit option.

    The original array is never changed. Strip processing bounds scratch memory
    and gives the same result for every strip size; corrections do not cascade.
    Noise coefficients use Var(y|x)=shot*x+read in black-normalized sensor units.

    Optional cluster mode tolerates one contaminated same-phase neighbor and
    only accepts light corroboration from another CFA color. This handles both
    same-phase pairs and the two diagonal green phases. Multi-color point
    lights and continuing lines remain protected; unresolved pure-color pairs
    remain ambiguous. Cluster mode leaves a four-pixel border unchanged.
    """
    raw = np.asarray(raw)
    if pattern not in ("RGGB", "BGGR", "GRBG", "GBRG"):
        raise ValueError("Expected an ordinary Bayer pattern")
    phase_colors = np.array(list(pattern))
    border = 4 if clusters else 3
    minimum = border * 2 + 1
    if raw.ndim != 2 or min(raw.shape) < minimum or raw.dtype not in (np.float32, np.float64):
        raise ValueError(
            f"Expected a normalized floating-point Bayer image at least {minimum}×{minimum}"
        )
    if (
        not all(math.isfinite(x) for x in (shot, read, sigma, ratio, min_delta))
        or min(shot, read, min_delta) < 0
        or sigma <= 0
        or ratio <= 1
        or not isinstance(rows, int)
        or rows < 1
    ):
        raise ValueError("Invalid hot-pixel noise, threshold or strip parameters")
    for y in range(0, raw.shape[0], rows):
        if not np.isfinite(raw[y : y + rows]).all():
            raise ValueError("Bayer image must be finite")
    result = raw.copy()
    height, width = raw.shape
    count = 0
    phases = np.zeros(4, dtype=np.int64)
    coordinates_digest = hashlib.sha256()
    examples = []
    supported = 0
    for y in range(border, height - border, rows):
        stop = min(height - border, y + rows)
        center = raw[y:stop, border : width - border]
        neighbors = [
            raw[y + dy : stop + dy, border + dx : width - border + dx] for dy, dx in NEIGHBORS
        ]
        if clusters:
            maximum = _second_largest(neighbors)
        else:
            maximum = np.maximum.reduce(neighbors)
        mask = _bright_outlier(center, maximum, shot, read, sigma, ratio, min_delta)
        yy, xx = np.nonzero(mask)
        if not len(yy):
            continue
        coherent = np.zeros(len(yy), dtype=bool)
        if clusters:
            # A real line end has one bright neighbor, but that neighbor has
            # further support. A pair of defects only supports itself.
            for dy, dx in NEIGHBORS:
                near_y, near_x = y + yy + dy, border + xx + dx
                near = raw[near_y, near_x]
                reference = _second_largest([raw[near_y + oy, near_x + ox] for oy, ox in NEIGHBORS])
                near_is_spike = _bright_outlier(
                    near, reference, shot, read, sigma, ratio, min_delta
                )
                bright_neighbor = _bright_outlier(
                    near, maximum[yy, xx], shot, read, 3, ratio, min_delta
                )
                coherent |= bright_neighbor & ~near_is_spike
        for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
            near_y, near_x = y + yy + dy, border + xx + dx
            near = raw[near_y, near_x]
            background = np.median(
                np.stack([raw[near_y + oy, near_x + ox] for oy, ox in NEIGHBORS]),
                axis=0,
            )
            support_margin = np.maximum(
                min_delta, 3 * np.sqrt(shot * np.maximum(background, 0) + read)
            )
            support = near - background > support_margin
            if clusters:
                center_color = phase_colors[2 * ((y + yy) % 2) + (border + xx) % 2]
                support &= phase_colors[2 * (near_y % 2) + near_x % 2] != center_color
            coherent |= support
        supported += int(coherent.sum())
        yy, xx = yy[~coherent], xx[~coherent]
        if not len(yy):
            continue
        replacement = np.median(np.stack([neighbor[yy, xx] for neighbor in neighbors]), axis=0)
        result[y + yy, border + xx] = replacement
        coordinates = np.column_stack((y + yy, border + xx)).astype("<i8")
        coordinates_digest.update(coordinates.tobytes())
        phases += np.bincount(2 * ((y + yy) % 2) + (border + xx) % 2, minlength=4)
        for index in np.argsort(center[yy, xx])[-32:]:
            examples.append(
                {
                    "xy": [int(xx[index] + border), int(yy[index] + y)],
                    "before": float(center[yy[index], xx[index]]),
                    "after": float(replacement[index]),
                }
            )
        count += len(yy)
    return result, {
        "method": (
            "same-CFA-seven-of-eight-clusters-v2"
            if clusters
            else "same-CFA-eight-neighbor-isolated-bright-v1"
        ),
        "cluster_mode": bool(clusters),
        "pattern": pattern,
        "shot": shot,
        "read": read,
        "sigma": sigma,
        "ratio": ratio,
        "min_delta": min_delta,
        "corrected_pixels": count,
        "phase_counts_row_major": phases.tolist(),
        "coherent_candidates_preserved": supported,
        "support_sigma": 3.0,
        "untouched_border_pixels": border,
        "coordinates_yx_int64_sha256": coordinates_digest.hexdigest(),
        "examples": sorted(examples, key=lambda item: item["before"], reverse=True)[:32],
    }
