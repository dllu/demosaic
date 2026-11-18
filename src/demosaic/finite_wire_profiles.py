"""Choose a narrow periodic line shape on RAW reserved from delivery."""

from itertools import product

import numpy as np

from .experiments.evaluation.withheld import stratified_split
from .local_validated_waves import fit_local_candidate
from .search_donor_geometry import _native_view, _validate_search, screening_mask

PHASES = tuple(np.arange(16) / 16)
WIDTHS = (0.04, 0.07, 0.11)
MINIMUM_PROFILE_GAIN = 1.0


def _sample_profiles(x, y, frequency, hessian, phases, widths):
    """Integrate shifted, zero-mean Gaussian lines over the native pixel."""
    result = np.zeros((len(x), len(phases)))
    for dx, dy in product((-0.25, 0.25), repeat=2):
        xy = np.column_stack((x + dx, y + dy))
        cycles = xy @ frequency + 0.5 * np.sum((xy @ hessian) * xy, axis=1)
        offset = np.remainder(cycles[:, None] + phases + 0.5, 1) - 0.5
        result += 0.25 * np.exp(-0.5 * (offset / widths) ** 2)
    return result - np.sqrt(2 * np.pi) * widths


def _fold_gains(raw, layout, source, target, variance, nuisance, library, flexible):
    """Predict a common shape with separate signed amplitudes at R, G and B sites."""
    candidate_count = library.shape[1]
    reduction = np.zeros(candidate_count)
    energy = np.zeros(candidate_count)
    flexible_reduction = 0.0
    for c in range(3):
        train, held = source & (layout == c), target & (layout == c)
        inverse_sigma = 1 / np.sqrt(variance)
        design = nuisance * inverse_sigma[:, None]
        values = raw * inverse_sigma
        candidates = library * inverse_sigma[:, None]
        series = np.column_stack((values, candidates, flexible * inverse_sigma[:, None]))
        coefficients = np.linalg.lstsq(design[train], series[train], rcond=1e-10)[0]
        train_residual = series[train] - design[train] @ coefficients
        held_residual = series[held] - design[held] @ coefficients
        y = train_residual[:, 0]
        signals = train_residual[:, 1 : candidate_count + 1]
        power = (signals**2).sum(axis=0)
        amplitude = np.divide(y @ signals, power, out=np.zeros_like(power), where=power > 1e-10)
        prediction = held_residual[:, 1 : candidate_count + 1] * amplitude
        observed = held_residual[:, 0]
        reduction += 2 * (observed @ prediction) - (prediction**2).sum(axis=0)
        energy += (prediction**2).sum(axis=0)
        full = train_residual[:, candidate_count + 1 :]
        terms = np.linalg.lstsq(full, y, rcond=1e-10)[0]
        pred = held_residual[:, candidate_count + 1 :] @ terms
        flexible_reduction += pred @ (2 * observed - pred)
    margin = np.divide(
        reduction, 2 * np.sqrt(energy), out=np.zeros_like(reduction), where=energy > 0
    )
    return reduction, margin, flexible_reduction


def reserve_wire_profiles(
    packed,
    colors,
    query,
    guide,
    *,
    shot,
    read,
    config,
    hessians=None,
    envelopes=None,
    minimum_gain=MINIMUM_PROFILE_GAIN,
):
    """Vary phase and width on crossed halves of the reserve only.

    An absent direction and the other carrier are represented in the comparison.
    The chosen shape must improve on the absent direction in both folds and
    outperform flexible eight-knot prediction in their combined held-out error.
    The result is a basis choice for later independent validation.
    """
    _validate_search(query, shot, read)
    if not np.isfinite(minimum_gain) or minimum_gain < 0:
        raise ValueError("Require a finite nonnegative reserve gain")
    active = np.asarray(guide["active"], dtype=bool)
    if not active.any():
        return (None, None), {"directions": [], "trials": 0}
    raw, cfa = _native_view(packed, colors, query)
    reserve = screening_mask(query)
    screening_raw = np.where(reserve, raw, np.nan)
    if not np.isfinite(screening_raw[reserve]).all():
        raise ValueError("Require finite RAW in the profile reserve")
    frequencies = np.asarray(guide["frequencies_xy"], dtype=float)
    hessians = np.zeros((2, 2, 2)) if hessians is None else np.asarray(hessians, dtype=float)
    y, x = np.indices(raw.shape) - (np.asarray(raw.shape)[:, None, None] - 1) / 2
    widths, phases = map(np.asarray, zip(*product(WIDTHS, PHASES), strict=True))
    split = stratified_split(raw.shape, config.split_seed + 181969)
    folds = reserve & split, reserve & ~split
    models = [
        fit_local_candidate(
            screening_raw,
            cfa,
            selection,
            shot=shot,
            read=read,
            config=config,
            guide_frequencies_xy=frequencies,
            phase_bins=8,
            guide_phase_hessians_xy=hessians,
            guide_envelopes=envelopes,
        )
        for selection in folds
    ]
    profiles = [None, None]
    records = []
    for d in np.flatnonzero(active):
        taper = np.ones(raw.shape) if envelopes is None else np.asarray(envelopes[d])
        candidates = (
            _sample_profiles(x[reserve], y[reserve], frequencies[d], hessians[d], phases, widths)
            * taper[reserve, None]
        )
        scores = []
        for i, fit in enumerate(models):
            design = fit.design[reserve.ravel()]
            start, end = fit.wave_slices[d]
            lo, hi = fit.wave_slices[1 - d]
            nuisance = design[:, : fit.wave_slices[0][0]]
            if active[1 - d]:
                nuisance = np.column_stack((nuisance, design[:, lo:hi]))
            scores.append(
                _fold_gains(
                    raw[reserve],
                    cfa[reserve],
                    folds[i][reserve],
                    folds[1 - i][reserve],
                    fit.variance_cfa[reserve],
                    nuisance,
                    candidates,
                    design[:, start:end],
                )
            )
        reduction, margin, flexible = zip(*scores, strict=True)
        pooled = np.sum(reduction, axis=0)
        qualified = (np.minimum(*margin) > minimum_gain) & (pooled > sum(flexible))
        winner = int(
            np.where(qualified, pooled, -np.inf).argmax() if qualified.any() else pooled.argmax()
        )
        accepted = bool(qualified[winner])
        if accepted:
            sampled = _sample_profiles(
                x.ravel(),
                y.ravel(),
                frequencies[d],
                hessians[d],
                phases[[winner]],
                widths[[winner]],
            ).reshape(raw.shape)
            profiles[d] = sampled * taper
        records.append(
            {
                "direction": int(d),
                "width_cycles": widths[winner],
                "phase_cycles": phases[winner],
                "accepted": accepted,
                "margins": [float(m[winner]) for m in margin],
                "squared_error_reduction": [float(r[winner]) for r in reduction],
                "flexible_squared_error_reduction": list(flexible),
            }
        )
    return tuple(profiles), {"directions": records, "trials": len(phases)}
