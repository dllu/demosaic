"""Validate companion frequency proposals on the anchor's measured support."""

from itertools import product

import numpy as np

from .donor_frequency_bank import _predict_designs, active_anchor
from .experiments.evaluation.withheld import stratified_split
from .local_validated_waves import (
    _fixed_phase_offset,
    _guide_frequencies,
    _phase_bin_weights,
    fit_local_candidate,
    phase_gradient_in_annulus,
)
from .search_donor_geometry import _native_view, _validate_search, screening_mask

SEARCH_STEPS = (-2, -1, 0, 1, 2)
PROFILE_MARGIN = 1.0


def frequency_neighborhood(center, native_side):
    """Use the same two-bin radial and tangent neighborhood in both selectors."""
    center = np.asarray(center, dtype=float)
    radial = center / np.linalg.norm(center)
    tangent = np.array([-radial[1], radial[0]])
    return [
        center + (a * radial + b * tangent) / native_side
        for a, b in product(SEARCH_STEPS, repeat=2)
        if a * a + b * b <= 4 and (a or b)
    ]


def _eligible(candidates, anchor, config, hessian, shape):
    limit = np.cos(np.deg2rad(config.family_degrees))
    accepted = []
    for f in candidates:
        norm = np.linalg.norm(f)
        if not phase_gradient_in_annulus(f, hessian, shape):
            continue
        if abs(f @ anchor) > limit * np.linalg.norm(anchor) * norm:
            continue
        if any(min(np.linalg.norm(f - g), np.linalg.norm(f + g)) < 1e-9 for g in accepted):
            continue
        accepted.append(f)
    return np.asarray(accepted)


def _carrier_columns(x, y, shape, center, curvature):
    knots = _phase_bin_weights(x, y, center, 8, offset=_fixed_phase_offset(x, y, shape, curvature))
    p = 2 * np.pi * np.arange(8) / 8
    return knots @ np.column_stack((np.cos(p), np.sin(p), np.cos(2 * p), np.sin(2 * p)))


def _contrasts(observed, no_carrier, original, proposals):
    """Standardized gains over the absent and original companion predictions."""
    directions = proposals - np.stack((no_carrier, original))[:, None]
    energy = np.sum(directions**2, axis=-1)
    residual = observed - np.stack((no_carrier, original))
    reduction = 2 * np.einsum("kc,knc->kn", residual, directions) - energy
    gains = np.divide(
        reduction, 2 * np.sqrt(energy), out=np.zeros_like(reduction), where=energy > 0
    )
    return gains, reduction[1]


def reserve_companion_frequencies(
    packed,
    colors,
    query,
    guide,
    candidate_frequencies,
    *,
    shot,
    read,
    config,
    envelope=None,
    hessians=None,
):
    """Choose between the same center-frequency candidates with and without a taper.

    Both crossed held-out screening folds must predict better than the candidate
    with its companion absent and better than the current guide. Reconstruction
    has its own independent delivery gate on the complement of the reserve.
    """
    anchor = active_anchor(guide)
    labels = ("uniform",) if envelope is None else ("uniform", "localized")
    if anchor is None:
        return dict.fromkeys(labels, guide), {"status": "no anchor"}

    _validate_search(query, shot, read)
    raw, cfa = _native_view(packed, colors, query)
    reserve = screening_mask(query)
    if not np.isfinite(raw[reserve]).all():
        raise ValueError("Require finite RAW sites in the frequency reserve")
    y, x = np.nonzero(reserve)
    frequencies = np.asarray(_guide_frequencies(guide["frequencies_xy"], config.family_degrees))
    h = np.zeros((2, 2, 2)) if hessians is None else np.asarray(hessians, np.float64)
    partner = 1 - anchor
    old = frequencies[partner]
    old_active = guide["active"][partner]
    candidates = _eligible(
        [old, *map(np.asarray, candidate_frequencies)],
        frequencies[anchor],
        config,
        h[partner],
        raw.shape,
    )
    if not len(candidates) or not np.array_equal(candidates[0], old):
        raise ValueError("Original companion must be eligible")
    if len(candidates) == 1 and old_active:
        return dict.fromkeys(labels, guide), {"status": "no distinct candidate"}

    columns = [_carrier_columns(x, y, raw.shape, f, h[partner]) for f in candidates]
    if envelope is None:
        weights = {"uniform": 1.0}
    else:
        envelope = np.asarray(envelope, np.float64)
        if (
            envelope.shape != raw.shape
            or not np.isfinite(envelope).all()
            or not np.all((envelope >= 0) & (envelope <= 1))
        ):
            raise ValueError("Require a finite native taper in [0, 1]")
        weights = {"uniform": 1.0, "localized": envelope[reserve, None]}
    anchor_columns = _carrier_columns(x, y, raw.shape, frequencies[anchor], h[anchor])
    split = stratified_split(raw.shape, config.split_seed + 242192)
    folds = reserve & split, reserve & ~split
    masked = np.where(reserve, raw, np.nan)
    traces = {name: [] for name in weights}
    for discover, observe in (folds, folds[::-1]):
        base = fit_local_candidate(
            masked,
            cfa,
            discover,
            shot=shot,
            read=read,
            config=config,
            guide_frequencies_xy=frequencies,
            phase_bins=8,
            phase_harmonics=((1,), (1,)),
        )
        nuisance = base.design[reserve.ravel(), : base.wave_slices[0][0]]
        null = np.column_stack((nuisance, anchor_columns))
        for name, taper in weights.items():
            design = [null, *(np.column_stack((null, profile * taper)) for profile in columns)]
            values, predictions = _predict_designs(
                raw[reserve],
                cfa[reserve],
                discover[reserve],
                observe[reserve],
                base.variance_cfa[reserve],
                design,
            )
            absent, old_prediction = predictions[:2]
            traces[name].append(
                _contrasts(
                    values,
                    absent,
                    old_prediction if old_active else absent,
                    np.asarray(predictions[1:]),
                )
            )
    selected = {}
    details = {}
    for name, trace in traces.items():
        margin = np.stack([t[0] for t in trace])
        improvement = np.stack([t[1] for t in trace])
        eligible = margin.min(axis=(0, 1)) > PROFILE_MARGIN
        pooled = improvement.sum(axis=0)
        best = (
            int(np.argmax(np.where(eligible, pooled, -np.inf)))
            if eligible.any()
            else int(pooled.argmax())
        )
        if eligible[best]:
            next_frequencies = frequencies.copy()
            next_frequencies[partner] = candidates[best]
            selected[name] = guide | {
                "frequencies_xy": next_frequencies.tolist(),
                "active": [True, True],
            }
        else:
            selected[name] = guide
        details[name] = {
            "chosen": best,
            "accepted": bool(eligible[best]),
            "margins": margin.tolist(),
            "squared_error_reduction": improvement.tolist(),
        }
    return selected, {
        "status": "evaluated",
        "anchor": anchor,
        "candidates": candidates.tolist(),
        "screening": details,
    }
