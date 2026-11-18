"""Retain distinct whole-scene donor nominations before reserved query admission."""

from itertools import combinations

import numpy as np

from .bracket_phase_geometry import _overlaps
from .experiments.evaluation.withheld import geometry, stratified_split
from .local_validated_waves import _guide_frequencies, _phase_bin_weights, fit_local_candidate
from .localized_donor_geometry import _confirm_pair
from .reserved_wire_footprint import _standardized_gain
from .search_donor_geometry import (
    _FAMILY_COSINE,
    _bracket_fraction,
    _compatible_peak_pairs,
    _cosine,
    _native_donor,
    _native_view,
    _screen_peaks,
    _validate_search,
    screening_mask,
)

BANK_SIZE = 8
AFFINITY_MARGIN = 0.10
QUERY_GAIN = 1.0


def screened_donor_tiles(donors, query, *, shot, read, localized):
    _validate_search(query, shot, read)
    tiles = []
    for donor in donors:
        box = donor[2]
        raw, cfa = _native_donor(donor, query)
        mask = screening_mask(box)
        peaks = _screen_peaks(
            raw, cfa, mask, shot, read, minimum=8 if localized else 20, refined_edge=localized
        )
        tiles.append((box, raw, cfa, mask, peaks))
    return tiles


def _separate(a, b, family_cosine):
    return b is None or abs(_cosine(a, b)) <= family_cosine


def _distance(a, b, native_width):
    return float(min(np.linalg.norm(a - b), np.linalg.norm(a + b))) * native_width


def donor_frequency_bank(
    tiles, query, affinities, anchor, *, shot, read, localized, family_degrees
):
    """Rank distinct frequencies within a fixed margin of the best scene match.

    Confirmation uses the same crossed donor folds and edge model as the
    corresponding single-bracket search. At most eight candidates reach it.
    """
    weights = np.asarray(affinities, dtype=np.float64)
    if (
        weights.shape != (len(tiles),)
        or not np.isfinite(weights).all()
        or ((weights < 0) | (weights > 1)).any()
    ):
        raise ValueError("Require one finite scene affinity in [0, 1] per donor")
    limit = np.cos(np.deg2rad(family_degrees))
    native_width = min(query[2:])
    choices = []
    for i, j in combinations(range(len(tiles)), 2):
        left, right = tiles[i], tiles[j]
        if not left[-1] or not right[-1] or _overlaps(left[0], right[0]):
            continue
        fraction = _bracket_fraction(left[0], right[0], query)
        if fraction is None:
            continue
        geometric = list(
            _compatible_peak_pairs([p for p in left[-1] if p[1] >= 20], right[-1], fraction)
        ) + list(_compatible_peak_pairs(left[-1], [p for p in right[-1] if p[1] >= 20], fraction))
        if not geometric:
            continue
        strongest = max(geometric, key=lambda m: m[0])
        affinity = min(weights[i], weights[j])
        for entry in geometric:
            if _separate(entry[1], anchor, limit):
                choices.append((affinity, i, j, entry, strongest))
    if not choices:
        return {"compatible_frequencies": [], "shortlist": []}

    best_affinity = max(row[0] for row in choices)
    ranked = sorted(choices, key=lambda row: (row[0] * row[3][0], row[0]), reverse=True)
    shortlist = []
    distinct = []
    for affinity, i, j, candidate, strongest in ranked:
        f = candidate[1]
        if affinity < best_affinity - AFFINITY_MARGIN or any(
            _distance(f, other, native_width) <= 1 for other in distinct
        ):
            continue
        fits = [candidate]
        if _separate(f, strongest[1], _FAMILY_COSINE):
            fits.append(strongest)
        witness = _confirm_pair(
            tiles[i], tiles[j], fits, shot, read, refined_edge=localized, parallel_edge=localized
        )
        shortlist.append(
            {
                "frequency_xy": f.tolist(),
                "affinity": float(affinity),
                "donor_valid": witness["active"][0],
                "witness": witness,
            }
        )
        distinct.append(f)
        if len(shortlist) == BANK_SIZE:
            break
    # Preserve actual candidate coverage before ranking and link it to query diagnostics.
    all_frequencies = np.unique(np.stack([row[3][1] for row in choices]), axis=0)
    return {"compatible_frequencies": all_frequencies.tolist(), "shortlist": shortlist}


def active_anchor(guide):
    return next((i for i, accepted in enumerate(guide["active"]) if accepted), None)


def _companion_predictions(raw, cfa, fold, test, anchor, candidates, config, shot, read):
    fixed = fit_local_candidate(
        raw,
        cfa,
        fold,
        shot=shot,
        read=read,
        config=config,
        guide_frequencies_xy=(anchor, (-anchor[1], anchor[0])),
        phase_bins=8,
    )
    _, end = fixed.wave_slices[0]
    null = fixed.design[:, :end]
    x, y, _, _ = geometry(raw.shape)
    basis = []
    for f in candidates:
        weights = _phase_bin_weights(x, y, f, 8)
        basis.append(np.column_stack((null, weights[:, :-1] - weights[:, -1:])))
    predictions = [np.empty(np.count_nonzero(test)) for _ in range(len(basis) + 1)]
    observed = np.empty_like(predictions[0])
    sigma = np.sqrt(fixed.variance_cfa)
    for color in range(3):
        source = fold & (cfa == color)
        target = test & (cfa == color)
        placement = (cfa == color)[test]
        observed[placement] = raw[target] / sigma[target]
        values = raw[source] / sigma[source]
        for dst, design in zip(predictions, [null, *basis], strict=True):
            coefficients = np.linalg.lstsq(
                design[source.ravel()] / sigma[source, None], values, rcond=1e-10
            )[0]
            dst[placement] = (design[target.ravel()] @ coefficients) / sigma[target]
    return observed, predictions


def select_bank_companion(packed, colors, query, guide, bank, *, shot, read, config):
    """Keep the measured anchor and condition the new frequency on reserved CFA.

    The query selector sees screening sites only. Its nominated partner must
    subsequently pass the independent delivery fit and its crossed RAW tests.
    """
    index = active_anchor(guide)
    if index is None:
        return guide, {"status": "no baseline anchor"}
    _validate_search(query, shot, read)
    frequencies = _guide_frequencies(guide["frequencies_xy"], config.family_degrees)
    anchor, old = frequencies[index], frequencies[1 - index]
    candidates = [entry["frequency_xy"] for entry in bank["shortlist"] if entry["donor_valid"]]
    if not candidates:
        return guide, {"status": "no confirmed donor candidate"}
    previous = int(guide["active"][1 - index])
    proposed = [old, *candidates] if previous else candidates
    raw, cfa = _native_view(packed, colors, query)
    reserved = screening_mask(query)
    raw = np.where(reserved, raw, np.nan)
    if not np.isfinite(raw[reserved]).all():
        raise ValueError("Require finite RAW in the companion reserve")
    half = stratified_split(cfa.shape, config.split_seed + 346284)
    folds = reserved & half, reserved & ~half
    gains = []
    for fold, test in (folds, folds[::-1]):
        observed, preds = _companion_predictions(
            raw, cfa, fold, test, anchor, proposed, config, shot, read
        )
        compare = preds[previous]
        gains.append(
            [
                (
                    _standardized_gain(observed, preds[0], p),
                    _standardized_gain(observed, compare, p),
                )
                for p in preds[1 + previous :]
            ]
        )
    gains = np.asarray(gains)
    conservative = np.min(gains, axis=(0, 2))
    pick = int(conservative.argmax())
    receipt = {
        "gains": gains.tolist(),
        "candidate_frequencies_xy": candidates,
        "best": pick,
        "status": "uniform fallback",
    }
    if conservative[pick] <= QUERY_GAIN:
        return guide, receipt
    next_freq = list(frequencies)
    next_freq[1 - index] = candidates[pick]
    changed = guide | {"frequencies_xy": [list(f) for f in next_freq], "active": [True, True]}
    return changed, receipt | {"status": "selected", "anchor_index": index}
