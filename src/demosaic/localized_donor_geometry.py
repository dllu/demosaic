"""Find a common local carrier in two regions selected from the RAW scene."""

from itertools import product

import numpy as np

from .bracket_phase_geometry import _overlaps
from .search_donor_geometry import (
    _bracket_fraction,
    _matching_peaks,
    _native_donor,
    _native_view,
    _screen_peaks,
    _screen_power,
    _validate_search,
    _verify_planes,
    screening_mask,
)


def _support_windows(raw, layout, box, shot, read, minimum, refined_edge):
    x, y, w, h = box
    windows = []
    for n in (min(w, h) * 3 // 4, min(w, h) // 2):
        if n < 64 or n % 4:
            continue
        step = n // 2
        xs = sorted({w - n, *range(0, w - n + 1, step)})
        ys = sorted({h - n, *range(0, h - n + 1, step)})
        for a, b in product(xs, ys):
            if a % 2 or b % 2:
                continue
            box = (x + a, y + b, n, n)
            scope = np.s_[b : b + n, a : a + n]
            observed, cfa = raw[scope], layout[scope]
            discovery = screening_mask(box)
            peaks = _screen_peaks(
                observed, cfa, discovery, shot, read, minimum=minimum, refined_edge=refined_edge
            )
            if peaks:
                windows.append((box, observed, cfa, discovery, peaks))
    return windows


def _query_benefit(power, frequency):
    h, w = power.shape
    x, y = frequency * (w, h)
    ix, iy = int(np.floor(x)), int(np.floor(y))
    wx, wy = x - ix, y - iy
    return sum(
        power[(iy + b) % h, (ix + a) % w] * u * v
        for (a, u), (b, v) in product(enumerate((1 - wx, wx)), enumerate((1 - wy, wy)))
    )


def localize_donor_geometry(
    donors,
    query,
    *,
    shot,
    read,
    unequal=False,
    query_measurements=None,
    refined_edge=False,
    parallel_edge=False,
):
    """Select one local pair on screening sites, then confirm each family on B and C.

    In unequal mode the quieter side may contribute a weaker spectral proposal.
    Both sides still have the same reserved RAW validation requirement.
    Query measurements, when supplied, rank viable pairs on screening sites only.
    """
    _validate_search(query, shot, read)
    if parallel_edge and not refined_edge:
        raise ValueError("Parallel-edge validation requires the refined edge search")
    if not donors:
        return {"status": "no donor bracket", "active": [False, False]}
    if len(donors) != 2:
        raise ValueError("Require two fixed donor regions")
    arrays = [_native_donor(d, query) for d in donors]
    first, second = [d[2] for d in donors]
    if _overlaps(first, second) or _bracket_fraction(first, second, query) is None:
        return {"status": "invalid donor bracket", "active": [False, False]}
    windows = [
        _support_windows(*values, item[2], shot, read, 8 if unequal else 20, refined_edge)
        for item, values in zip(donors, arrays, strict=True)
    ]
    baseline = {
        "status": "no compatible local windows",
        "active": [False, False],
        "donor_boxes": [list(d[2]) for d in donors],
        "screen_windows": [len(w) for w in windows],
    }
    query_power = None
    if query_measurements is not None:
        raw, cfa = _native_view(*query_measurements, query)
        query_power = _screen_power(
            raw, cfa, screening_mask(query), shot, read, refined_edge=refined_edge
        )
    best_rank, best = (-1.0, -1.0), None
    for left, right in product(*windows):
        fraction = _bracket_fraction(left[0], right[0], query)
        if fraction is None:
            continue
        if unequal:
            # Check each direction with one donor above the original screen
            # strength, while permitting a quieter match in the opposite field.
            # Process these alternatives using screening samples only.
            first, second = left[-1], right[-1]
            directed = [
                _matching_peaks([p for p in first if p[1] >= 20], second, fraction),
                _matching_peaks(first, [p for p in second if p[1] >= 20], fraction),
            ]
            matches = max(directed, key=lambda p: sum(v[0] for v in p))
        else:
            matches = _matching_peaks(left[-1], right[-1], fraction)
        if not matches:
            continue
        score = sum(m[0] for m in matches)
        screened_query = 0.0
        if query_power is not None:
            screened_query = sum(
                np.log1p(max(0, _query_benefit(query_power, m[1]) - 2)) for m in matches
            )
        rank = (screened_query, score)
        if rank > best_rank:
            best_rank, best = rank, (left, right, matches)
    if best is None:
        return baseline

    left, right, matches = best
    return (
        baseline
        | _confirm_pair(
            left, right, matches, shot, read, refined_edge=refined_edge, parallel_edge=parallel_edge
        )
        | ({"screened_query_score": float(best_rank[0])} if query_power is not None else {})
    )


def _confirm_pair(left, right, matches, shot, read, *, refined_edge, parallel_edge):
    gains = []
    for (_, raw, cfa, discovery, _), column, seed in zip(
        (left, right), (2, 3), (202611170720, 202611170721), strict=True
    ):
        f = np.stack([m[column] for m in matches])
        gains.append(
            _verify_planes(
                raw,
                cfa,
                ~discovery,
                f,
                seed,
                shot,
                read,
                refined_edge=refined_edge,
                parallel_edge=parallel_edge,
            )
        )
    active = np.pad(np.min(gains, axis=(0, 1)) > 8, (0, 2 - len(matches)))
    frequencies = [m[1] for m in matches]
    if len(frequencies) == 1:
        fx, fy = frequencies[0]
        frequencies.append(np.array([-fy, fx]))
    return {
        "status": "evaluated",
        "windows": [left[0], right[0]],
        "active": active.tolist(),
        "frequencies_xy": np.stack(frequencies).tolist(),
        "heldout_planar_reduction": np.asarray(gains).tolist(),
        "screened_frequencies_xy": [m[1].tolist() for m in matches],
        "donor_frequencies_xy": [[m[k].tolist() for m in matches] for k in (2, 3)],
        "score": float(sum(m[0] for m in matches)),
    }
