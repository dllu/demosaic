"""Conservative isolated bright-defect correction in normalized Bayer data."""

import hashlib
import math

import numpy as np


def repair_hot_pixels(raw, *, shot, read, sigma=6.0, ratio=2.0, min_delta=0.005, rows=128):
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
    """
    raw = np.asarray(raw)
    if raw.ndim != 2 or min(raw.shape) < 7 or raw.dtype not in (np.float32, np.float64):
        raise ValueError("Expected a normalized floating-point Bayer image at least 7×7")
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
    for y in range(3, height - 3, rows):
        stop = min(height - 3, y + rows)
        center = raw[y:stop, 3 : width - 3]
        neighbors = [
            raw[y + dy : stop + dy, 3 + dx : width - 3 + dx]
            for dy, dx in ((-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2))
        ]
        maximum = np.maximum.reduce(neighbors)
        positive = np.maximum(maximum, 0)
        margin = np.maximum(min_delta, sigma * np.sqrt(shot * positive + read))
        mask = (center > ratio * positive) & (center - maximum > margin)
        yy, xx = np.nonzero(mask)
        if not len(yy):
            continue
        coherent = np.zeros(len(yy), dtype=bool)
        for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
            near_y, near_x = y + yy + dy, 3 + xx + dx
            near = raw[near_y, near_x]
            background = np.median(
                np.stack(
                    [
                        raw[near_y + oy, near_x + ox]
                        for oy, ox in (
                            (-2, -2),
                            (-2, 0),
                            (-2, 2),
                            (0, -2),
                            (0, 2),
                            (2, -2),
                            (2, 0),
                            (2, 2),
                        )
                    ]
                ),
                axis=0,
            )
            support_margin = np.maximum(
                min_delta, 3 * np.sqrt(shot * np.maximum(background, 0) + read)
            )
            coherent |= near - background > support_margin
        supported += int(coherent.sum())
        yy, xx = yy[~coherent], xx[~coherent]
        if not len(yy):
            continue
        replacement = np.median(np.stack([neighbor[yy, xx] for neighbor in neighbors]), axis=0)
        result[y + yy, 3 + xx] = replacement
        coordinates = np.column_stack((y + yy, 3 + xx)).astype("<i8")
        coordinates_digest.update(coordinates.tobytes())
        phases += np.bincount(2 * ((y + yy) % 2) + (3 + xx) % 2, minlength=4)
        for index in np.argsort(center[yy, xx])[-32:]:
            examples.append(
                {
                    "xy": [int(xx[index] + 3), int(yy[index] + y)],
                    "before": float(center[yy[index], xx[index]]),
                    "after": float(replacement[index]),
                }
            )
        count += len(yy)
    return result, {
        "method": "same-CFA-eight-neighbor-isolated-bright-v1",
        "shot": shot,
        "read": read,
        "sigma": sigma,
        "ratio": ratio,
        "min_delta": min_delta,
        "corrected_pixels": count,
        "phase_counts_row_major": phases.tolist(),
        "coherent_candidates_preserved": supported,
        "support_sigma": 3.0,
        "untouched_border_pixels": 3,
        "coordinates_yx_int64_sha256": coordinates_digest.hexdigest(),
        "examples": sorted(examples, key=lambda item: item["before"], reverse=True)[:32],
    }
