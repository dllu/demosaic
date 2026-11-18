"""Rank native donor windows with optional A-only scene affinities."""

from itertools import combinations

import numpy as np

from .bracket_phase_geometry import _overlaps
from .localized_donor_geometry import _confirm_pair
from .screened_scene_donors import donor_affinities
from .search_donor_geometry import (
    _bracket_fraction,
    _matching_peaks,
    _native_donor,
    _screen_peaks,
    _validate_search,
    screening_mask,
)


def corridor_affinities(features, grid, boxes, query, endpoint):
    """Combine endpoint appearance with support along its route from the query."""
    boxes = np.asarray(boxes, dtype=np.float64).reshape(-1, 4)
    if not len(boxes):
        return np.empty(0)
    qx, qy, qw, qh = query
    anchor = np.array([qx + qw / 2, qy + qh / 2])
    centers = boxes[:, :2] + boxes[:, 2:] / 2
    fractions = np.array([0.30, 0.48, 0.66, 0.84])
    points = anchor + (centers[:, None] - anchor) * fractions[None, :, None]
    widths = np.minimum(boxes[:, 2:], [qw, qh])[:, None] / 2
    widths = np.broadcast_to(widths, points.shape)
    windows = np.concatenate((points - widths / 2, widths), axis=-1)
    support = donor_affinities(features, grid, windows.reshape(-1, 4), query)
    return np.sqrt(endpoint * np.quantile(support.reshape(-1, len(fractions)), 0.25, axis=1))


def rank_scene_windows(donors, query, *, shot, read, affinities):
    """Find one bracket per ranking, then confirm it on independent donor folds."""
    _validate_search(query, shot, read)
    n = len(donors)
    ranks = {key: np.asarray(values, dtype=np.float64) for key, values in affinities.items()}
    for values in ranks.values():
        if (
            values.shape != (n,)
            or not np.isfinite(values).all()
            or np.any((values < 0) | (values > 1))
        ):
            raise ValueError("Require one screening affinity in [0, 1] per donor")
    tiles = []
    for donor in donors:
        box = donor[2]
        raw, layout = _native_donor(donor, query)
        screening = screening_mask(box)
        peaks = _screen_peaks(raw, layout, screening, shot, read, minimum=8, refined_edge=True)
        tiles.append((box, raw, layout, screening, peaks))
    selected = dict.fromkeys(ranks)
    scores = dict.fromkeys(ranks, (-1.0, 0.0))
    matching = 0
    for (i, left), (j, right) in combinations(enumerate(tiles), 2):
        if not left[-1] or not right[-1] or _overlaps(left[0], right[0]):
            continue
        fraction = _bracket_fraction(left[0], right[0], query)
        if fraction is None:
            continue
        first, second = left[-1], right[-1]
        options = (
            _matching_peaks([p for p in first if p[1] >= 20], second, fraction),
            _matching_peaks(first, [p for p in second if p[1] >= 20], fraction),
        )
        matches = max(options, key=lambda values: sum(m[0] for m in values))
        if not matches:
            continue
        matching += 1
        score = sum(m[0] for m in matches)
        for key, prior in ranks.items():
            rank = (min(prior[i], prior[j]), score)
            if rank > scores[key]:
                scores[key] = rank
                selected[key] = (i, j, matches)

    out, confirmations = {}, {}
    common = {
        "candidate_count": n,
        "with_peaks": sum(bool(tile[-1]) for tile in tiles),
        "compatible_brackets": matching,
        "status": "no matching bracket",
        "active": [False, False],
    }
    for key, pair in selected.items():
        if pair is None:
            out[key] = common.copy()
            continue
        i, j, matches = pair
        if (i, j) not in confirmations:
            confirmations[i, j] = _confirm_pair(
                tiles[i], tiles[j], matches, shot, read, refined_edge=True, parallel_edge=True
            )
        out[key] = (
            common
            | confirmations[i, j]
            | {
                "status": "evaluated",
                "candidate_indices": [i, j],
                "selected_affinity": ranks[key][[i, j]].tolist(),
            }
        )
    return out
