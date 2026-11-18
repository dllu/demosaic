"""Fit shared second-order perspective on reserved RAW, then validate delivery independently."""

from itertools import product

import numpy as np

from .donor_frequency_bank import _predict_designs
from .experiments.evaluation.withheld import geometry, stratified_split
from .local_validated_waves import (
    _fixed_phase_offset,
    _guide_frequencies,
    _phase_bin_weights,
    fit_local_candidate,
    phase_gradient_in_annulus,
)
from .reserved_wire_footprint import _standardized_gain
from .search_donor_geometry import _native_view, _validate_search, screening_mask

GRADIENT_STEPS = (-0.18, -0.09, 0.0, 0.09, 0.18)
MINIMUM_GEOMETRY_GAIN = 1.0


def projective_hessians(frequencies, gradient):
    """Quadratic term of (f · x) / (1 + g · x) at the query center."""
    f = np.asarray(frequencies, dtype=np.float64)
    g = np.asarray(gradient, dtype=np.float64)
    return -(f[..., :, None] * g[None, None, :] + g[None, :, None] * f[..., None, :])


def _phase_columns(xx, yy, shape, frequency, hessian):
    offset = _fixed_phase_offset(xx, yy, shape, hessian)
    phase = 2 * np.pi * np.arange(8) / 8
    knots = np.column_stack((np.cos(phase), np.sin(phase), np.cos(2 * phase), np.sin(2 * phase)))
    return _phase_bin_weights(xx, yy, frequency, 8, offset=offset) @ knots


def _fold_scores(raw, cfa, fold, test, frequencies, hessians, measured, config, shot, read):
    fit = fit_local_candidate(
        raw,
        cfa,
        fold,
        shot=shot,
        read=read,
        config=config,
        guide_frequencies_xy=frequencies,
        phase_bins=8,
        phase_harmonics=((1, 2), (1, 2)),
    )
    start = fit.wave_slices[0][0]
    reserve = fold | test
    design = fit.design[reserve.ravel()]
    nuisance = design[:, :start]
    x, y, _, _ = geometry(raw.shape)
    xx, yy = x[reserve], y[reserve]
    planar = tuple(design[:, a:b] for a, b in fit.wave_slices)
    measured_raw, layout = raw[reserve], cfa[reserve]
    discover, validate = fold[reserve], test[reserve]
    variance = fit.variance_cfa[reserve]
    scores = np.zeros((2, len(hessians), 3), dtype=np.float64)
    for d in measured:
        competitor = planar[1 - d] if 1 - d in measured else np.empty((len(xx), 0))
        null = np.column_stack((nuisance, competitor))
        alternatives = [
            np.column_stack((null, _phase_columns(xx, yy, raw.shape, frequencies[d], h[d])))
            for h in hessians
        ]
        v, predictions = _predict_designs(
            measured_raw, layout, discover, validate, variance, [null, *alternatives]
        )
        no_wave, unwarped, *rest = predictions
        for k, p in enumerate((unwarped, *rest)):
            scores[d, k, :2] = _standardized_gain(v, unwarped, p), _standardized_gain(v, no_wave, p)
            innovation = p - unwarped
            scores[d, k, 2] = innovation @ (2 * (v - unwarped) - innovation)
    return scores


def reserve_projective_phase(
    packed, colors, query, guide, *, shot, read, config, ranking="predictive"
):
    """Test two-dimensional perspective gradients on crossed screening samples.

    Each tested direction competes with its planar prediction and a null
    that keeps the other direction. Accepted geometry is only a guide for
    the subsequent independent per-color RAW delivery check.
    """
    if ranking not in ("standardized", "predictive"):
        raise ValueError("Choose standardized or predictive perspective ranking")
    measured = tuple(i for i, active in enumerate(guide["active"]) if active)
    if not measured:
        return None, {"status": "no guide"}
    _validate_search(query, shot, read)
    raw, cfa = _native_view(packed, colors, query)
    reserve = screening_mask(query)
    raw = np.where(reserve, raw, np.nan)
    if not np.isfinite(raw[reserve]).all():
        raise ValueError("Require finite RAW in the geometry reserve")
    frequencies = _guide_frequencies(guide["frequencies_xy"], config.family_degrees)
    gradients = [(0.0, 0.0)]
    hessians = [np.zeros((2, 2, 2))]
    for uv in product(GRADIENT_STEPS, repeat=2):
        if uv == (0.0, 0.0):
            continue
        hp = projective_hessians(frequencies, np.asarray(uv) / min(raw.shape))
        if all(
            phase_gradient_in_annulus(f, h, raw.shape) for f, h in zip(frequencies, hp, strict=True)
        ):
            gradients.append(uv)
            hessians.append(hp)

    split = stratified_split(raw.shape, config.split_seed + 219141)
    folds = reserve & split, reserve & ~split
    scores = np.stack(
        [
            _fold_scores(raw, cfa, a, b, frequencies, hessians, measured, config, shot, read)
            for a, b in (folds, folds[::-1])
        ]
    )
    minimum = scores[..., :2].min(axis=(0, 3))
    ids = minimum.argmax(axis=1)
    confirmed = minimum > MINIMUM_GEOMETRY_GAIN
    if ranking == "predictive":
        gains = scores[..., 2].sum(axis=0)
        alternatives = np.where(confirmed, gains, -np.inf).argmax(axis=1)
        ids = np.where(confirmed.any(axis=1), alternatives, ids)
    winning = [i if confirmed[d, i] else 0 for d, i in enumerate(ids)]
    plans = np.zeros((2, 2, 2, 2))
    for d, index in enumerate(winning):
        plans[d] = hessians[index]
    return plans, {
        "status": "geometry evaluated",
        "anchor": measured[0],
        "trials": len(hessians),
        "directions": [
            {
                "direction": d,
                "proposed": gradients[i],
                "gains": scores[:, d, i, :2].tolist(),
                "squared_error_reductions": scores[:, d, i, 2].tolist(),
                "accepted": bool(winning[d]),
            }
            for d, i in enumerate(ids)
        ],
    }
