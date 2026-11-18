"""Find shared carrier geometry in disjoint regions of a larger RAW field."""

from itertools import combinations, product

import numpy as np

from .bracket_phase_geometry import _center, _overlaps, bracket_donor_geometry
from .carrier_spectrum import discovery_weights, weighted_spectrum
from .donor_phase_geometry import _fold_fields, _model_columns
from .experiments.evaluation.withheld import stratified_split
from .local_validated_waves import _guide_frequencies

_MIN_RADIUS = 0.035
_MAX_RADIUS = 0.23
_MIN_SEARCH_BENEFIT = 20
_MIN_HELDOUT_BENEFIT = 8
_MATCH_COSINE = np.cos(np.deg2rad(25))
_FAMILY_COSINE = np.cos(np.deg2rad(20))


def screening_mask(box):
    """Choose one site per CFA parity in each absolute 4 by 4 block."""
    x, y, w, h = box
    xx, yy = np.arange(x, x + w), np.arange(y, y + h)[:, None]
    bx = (xx // 4).astype(np.uint64)
    by = (yy // 4).astype(np.uint64)
    key = (bx * np.uint64(0x9E3779B97F4A7C15)) ^ (by * np.uint64(0xD6E8FEB86659FD93))
    key ^= (((xx % 2) + 2 * (yy % 2)).astype(np.uint64) + 1) * np.uint64(0xBF58476D1CE4E5B9)
    key = (key ^ (key >> 30)) * np.uint64(0xBF58476D1CE4E5B9)
    key = (key ^ (key >> 27)) * np.uint64(0x94D049BB133111EB)
    slot = (xx % 4) // 2 + 2 * ((yy % 4) // 2)
    return ((key ^ (key >> 31)) >> 62) == slot


def candidate_boxes(frame, query, size=128, stride=64):
    """Cover the retained native context with query-disjoint Bayer-aligned boxes."""
    x, y, w, h = frame
    qx, qy, qw, qh = query
    axes = []
    for origin, extent, start, end in ((x, w, qx, qx + qw), (y, h, qy, qy + qh)):
        last = origin + extent - size
        starts = {last, start - size, end, *range(origin, last + 1, stride)}
        axes.append(sorted(v for v in starts if origin <= v <= last and (v - origin) % 2 == 0))
    boxes = [(a, b, size, size) for a, b in product(*axes)]
    return [box for box in boxes if not _overlaps(box, query)]


def _native(packed, colors, box):
    w, h = box[2:]
    raw = packed.reshape(2, 2, h // 2, w // 2).transpose(2, 0, 3, 1).reshape(h, w)
    return raw, np.tile(colors.reshape(2, 2), (h // 2, w // 2))


def _native_view(packed, colors, box):
    w, h = box[2:]
    packed, colors = np.asarray(packed), np.asarray(colors)
    if (
        min(w, h) < 64
        or w % 4
        or h % 4
        or packed.shape != (4, h // 2, w // 2)
        or sorted(colors.tolist()) != [0, 1, 1, 2]
    ):
        raise ValueError("Require native Bayer samples with matching dimensions")
    return _native(packed, colors, box)


def _native_donor(donor, query):
    if _overlaps(donor[2], query):
        raise ValueError("Require native Bayer donors disjoint from the query")
    return _native_view(*donor)


def _validate_search(query, shot, read):
    if not np.isfinite([shot, read]).all() or min(shot, read) < 0 or shot + read <= 0:
        raise ValueError("Require a positive sensor noise profile")
    if len(query) != 4 or min(query[2:]) <= 0:
        raise ValueError("Require positive query dimensions")


def _screen_power(raw, layout, mask, shot, read, *, refined_edge=False):
    _, nuisance, selected, _, _, _ = _fold_fields(
        raw, layout, mask, shot, read, refined_edge=refined_edge
    )
    weights = discovery_weights(raw, selected, nuisance, shot=shot, read=read, hann=True)
    return weighted_spectrum(raw, selected, nuisance, weights) * weights.mean()


def _screen_peaks(
    raw, layout, mask, shot, read, *, minimum=_MIN_SEARCH_BENEFIT, refined_edge=False
):
    grid = np.stack(
        np.meshgrid(np.fft.fftfreq(raw.shape[1]), np.fft.fftfreq(raw.shape[0])), axis=-1
    )
    radius = np.linalg.norm(grid, axis=-1)
    valid = (
        (radius >= _MIN_RADIUS)
        & (radius <= _MAX_RADIUS)
        & ((grid[..., 1] > 0) | ((grid[..., 1] == 0) & (grid[..., 0] > 0)))
    )
    power = _screen_power(raw, layout, mask, shot, read, refined_edge=refined_edge)
    remaining = np.where(valid, power, 0)
    peaks = []
    for _ in range(6):
        iy, ix = np.unravel_index(remaining.argmax(), remaining.shape)
        if remaining[iy, ix] < minimum:
            break
        coarse = grid[iy, ix]
        point = coarse.copy()
        for axis, n in enumerate(raw.shape[::-1]):
            yy = (iy + (np.arange(-1, 2) if axis else 0)) % raw.shape[0]
            xx = (ix + (0 if axis else np.arange(-1, 2))) % raw.shape[1]
            low, middle, high = np.log(np.maximum(power[yy, xx], 1e-6))
            curvature = low + high - 2 * middle
            if curvature < -1e-8:
                point[axis] += np.clip(0.5 * (low - high) / curvature, -0.5, 0.5) / n
        if _MIN_RADIUS <= np.linalg.norm(point) <= _MAX_RADIUS:
            peaks.append((point, float(remaining[iy, ix])))
        delta = np.minimum(
            np.linalg.norm((grid - coarse) * raw.shape[::-1], axis=-1),
            np.linalg.norm((grid + coarse) * raw.shape[::-1], axis=-1),
        )
        remaining[delta <= 2] = 0
    return peaks


def _cosine(a, b):
    return (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))


def _bracket_fraction(first, second, query):
    span = min(query[2:])
    a, b = (_center(first) - _center(query)) / span, (_center(second) - _center(query)) / span
    line = b - a
    fraction = -(a @ line) / (line @ line)
    if (
        not 0.25 <= fraction <= 0.75
        or np.linalg.norm(a + fraction * line) > 0.25
        or max(np.linalg.norm(a), np.linalg.norm(b)) > 2
    ):
        return None
    return fraction


def _compatible_peak_pairs(left, right, fraction, *, widened=False):
    minimum_cosine = np.sqrt(0.5) if widened else _MATCH_COSINE
    max_difference = 0.06 if widened else 0.045
    for (a, score_a), (b, score_b) in product(left, right):
        angle = _cosine(a, b)
        b = b if angle >= 0 else -b
        difference = np.linalg.norm(a - b)
        if abs(angle) >= minimum_cosine and difference <= max_difference:
            center = (1 - fraction) * a + fraction * b
            score = min(score_a, score_b) / (1 + (difference / 0.025) ** 2)
            yield score, center, a, b


def _matching_peaks(left, right, fraction, *, first=None):
    options = _compatible_peak_pairs(left, right, fraction, widened=first is not None)
    selected = [] if first is None else [first]
    for entry in sorted(options, key=lambda p: p[0], reverse=True):
        if not selected or abs(_cosine(entry[1], selected[0][1])) <= _FAMILY_COSINE:
            selected.append(entry)
        if len(selected) == 2:
            break
    return selected


def _verify_planes(
    raw, layout, eligible, seeds, seed, shot, read, *, refined_edge=False, parallel_edge=False
):
    split = stratified_split(raw.shape, seed)
    gains = []
    models = np.pad(seeds * min(raw.shape), ((0, 0), (0, 3)))
    for fold in (split, ~split):
        xy, nuisance, train, test, precision, _ = _fold_fields(
            raw,
            layout,
            fold & eligible,
            shot,
            read,
            eligible,
            refined_edge=refined_edge,
            parallel_edge=parallel_edge,
        )
        full = _model_columns(nuisance, xy, models)
        errors = []
        for design in (
            full,
            *(
                np.delete(full, np.s_[nuisance.shape[1] + 2 * k : nuisance.shape[1] + 2 * k + 2], 1)
                for k in range(len(seeds))
            ),
        ):
            beta = np.linalg.lstsq(
                design[train] * precision[train, None],
                raw.ravel()[train] * precision[train],
                rcond=1e-10,
            )[0]
            residual = (raw.ravel()[test] - design[test] @ beta) * precision[test]
            errors.append(float(residual @ residual))
        gains.append(np.subtract(errors[1:], errors[0]))
    return np.stack(gains)


def search_donor_geometry(
    donors, query, *, shot, read, fit_curvature=False, donor_affinity=None, affinity_first=False
):
    """Rank brackets with optional screening-only affinity, then validate independently."""
    _validate_search(query, shot, read)
    if affinity_first and donor_affinity is None:
        raise ValueError("Affinity ranking requires screening affinities")
    affinity = np.ones(len(donors)) if donor_affinity is None else np.asarray(donor_affinity)
    if (
        affinity.shape != (len(donors),)
        or not np.isfinite(affinity).all()
        or np.any((affinity < 0) | (affinity > 1))
    ):
        raise ValueError("Require one screening affinity in [0, 1] per donor")
    tiles = []
    for donor in donors:
        box = donor[2]
        raw, layout = _native_donor(donor, query)
        screen = screening_mask(box)
        peaks = _screen_peaks(raw, layout, screen, shot, read)
        tiles.append((raw, layout, screen, peaks))
    best_score = 0.0
    best = None
    for i, j in combinations(range(len(donors)), 2):
        a, b = donors[i][2], donors[j][2]
        if _overlaps(a, b) or not tiles[i][3] or not tiles[j][3]:
            continue
        fraction = _bracket_fraction(a, b, query)
        if fraction is None:
            continue
        matches = _matching_peaks(tiles[i][3], tiles[j][3], fraction)
        if not matches:
            continue
        prior = min(affinity[i], affinity[j])
        score = prior if affinity_first else sum(row[0] for row in matches) * prior
        if score > best_score:
            best_score, best = score, (i, j, matches)
    result = {
        "candidate_count": len(donors),
        "with_peaks": sum(bool(tile[3]) for tile in tiles),
        "active": [False, False],
    }
    if best is None:
        return result | {"status": "no matching bracket"}
    i, j, matches = best
    gains = []
    for donor_index, column, seed in ((i, 2, 202611170720), (j, 3, 202611170721)):
        raw, layout, screen, _ = tiles[donor_index]
        if not np.isfinite(raw).all():
            raise ValueError("Require finite samples in selected donors")
        seeds = np.stack([row[column] for row in matches])
        gains.append(_verify_planes(raw, layout, ~screen, seeds, seed, shot, read))
    gains = np.stack(gains)
    measured = len(matches)
    active = np.pad(np.min(gains, axis=(0, 1)) > _MIN_HELDOUT_BENEFIT, (0, 2 - measured))
    frequencies = [row[1] for row in matches]
    if measured == 1:
        fx, fy = frequencies[0]
        frequencies.append(np.array([-fy, fx]))
    hessians = np.zeros((2, 2, 2)).tolist()
    bracket = None
    if fit_curvature:
        bracket = bracket_donor_geometry(
            [donors[i], donors[j]],
            query,
            frequencies,
            shot=shot,
            read=read,
            eligible_masks=[~tiles[k][2] for k in (i, j)],
        )
        for k in range(measured):
            if bracket["accepted"][k]:
                active[k] = True
                frequencies[k] = np.asarray(bracket["frequencies_xy"][k])
                hessians[k] = bracket["hessians_xy"][k]
    return result | {
        "status": "evaluated",
        "donor_boxes": [list(donors[k][2]) for k in (i, j)],
        "score": float(best_score),
        **({"selected_affinity": affinity[[i, j]].tolist()} if donor_affinity is not None else {}),
        "screened_frequencies_xy": [row[1].tolist() for row in matches],
        "donor_frequencies_xy": [[row[k].tolist() for row in matches] for k in (2, 3)],
        "heldout_planar_reduction": gains.tolist(),
        "active": active.tolist(),
        "frequencies_xy": np.stack(frequencies).tolist(),
        "hessians_xy": hessians,
        "bracket": bracket,
    }


def recover_curved_direction(donors, query, fit, *, shot, read):
    """Try one extra swept direction on an already selected, validated bracket."""
    result = fit | {"curved_direction_added": False}
    if fit["active"] != [True, False] or len(fit["screened_frequencies_xy"]) != 1:
        return result
    pair = [next(d for d in donors if tuple(d[2]) == tuple(box)) for box in fit["donor_boxes"]]
    fraction = _bracket_fraction(pair[0][2], pair[1][2], query)
    spectra, eligible = [], []
    for packed, colors, box in pair:
        raw, layout = _native(packed, colors, box)
        screen = screening_mask(box)
        spectra.append(_screen_peaks(raw, layout, screen, shot, read))
        eligible.append(~screen)
    first = np.asarray(fit["frequencies_xy"][0])
    candidates = _matching_peaks(*spectra, fraction, first=(0, first, None, None))
    if len(candidates) < 2:
        return result
    reference = [first, candidates[1][1]]
    check = bracket_donor_geometry(
        pair, query, reference, shot=shot, read=read, eligible_masks=eligible
    )
    result["curved_direction_check"] = check
    if not check["accepted"][1]:
        return result
    frequencies = [first.tolist(), check["frequencies_xy"][1]]
    try:
        _guide_frequencies(frequencies, 20)
    except ValueError:
        return result
    result["curved_direction_added"] = True
    result["active"] = [True, True]
    result["frequencies_xy"] = frequencies
    result["hessians_xy"] = [fit["hessians_xy"][0], check["hessians_xy"][1]]
    return result
