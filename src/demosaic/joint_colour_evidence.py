"""Joint held-out CFA evidence for a separately fitted RGB carrier vector."""

import numpy as np

from .local_validated_waves import _box_sums


def joint_conditional_scores(
    candidate, raw, colors, validation_mask, *, window=65, stride=16, reliability=None
):
    """Pool actual CFA full/null gains before normalization, then share one gain.

    RGB coefficients remain independent. A scalar score sums variance-normalized
    prediction gains and energies over all observed colours; it is not a green
    score copied into missing colours, a sum of three Z scores or calibrated
    confidence. All predictors/variance/geometry must exclude validation values.
    """
    raw, colors, mask = np.asarray(raw, np.float64), np.asarray(colors), np.asarray(validation_mask)
    if (
        raw.shape != candidate.full_cfa.shape
        or colors.shape != raw.shape
        or mask.shape != raw.shape
        or mask.dtype != bool
        or (mask & candidate.discovery_mask).any()
        or not np.isfinite(raw[mask]).all()
        or not np.isin(colors, (0, 1, 2)).all()
        or not np.isfinite(candidate.variance_cfa).all()
        or np.any(candidate.variance_cfa <= 0)
    ):
        raise ValueError("Require matching CFA, positive A-only variance and disjoint validation")
    units = len(candidate.unit_keys)
    if reliability is not None and (
        reliability.shape != (units, 3)
        or not np.isfinite(reliability).all()
        or np.any((reliability < 0) | (reliability > 1))
    ):
        raise ValueError("Require finite per-direction and color reliability in [0, 1]")
    h, w = raw.shape
    ay, ax = [np.unique(np.r_[np.arange(0, n, stride), n - 1]) for n in raw.shape]
    selected_colors = colors[mask].astype(np.intp, copy=False) if reliability is not None else None
    local = np.empty((units, h, w))
    glob = np.empty(units)
    for unit in range(units):
        base, full, value, variance = [
            a[mask]
            for a in [
                candidate.conditional_null_cfa[unit],
                candidate.full_cfa,
                raw,
                candidate.variance_cfa,
            ]
        ]
        if reliability is not None:
            full = base + reliability[unit, selected_colors] * (full - base)
        improvement, energy = np.zeros(raw.shape), np.zeros(raw.shape)
        improvement[mask] = ((value - base) ** 2 - (value - full) ** 2) / variance
        energy[mask] = (full - base) ** 2 / variance
        numerator = _box_sums(improvement, ay, ax, window)
        denominator = 2 * np.sqrt(np.maximum(_box_sums(energy, ay, ax, window), 0))
        scores = np.divide(
            numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0
        )
        horizontal = np.stack([np.interp(np.arange(w), ax, row) for row in scores])
        local[unit] = np.stack(
            [np.interp(np.arange(h), ay, horizontal[:, x]) for x in range(w)], axis=1
        )
        norm = 2 * np.sqrt(energy.sum())
        glob[unit] = improvement.sum() / norm if norm else 0
    return np.repeat(local[:, None], 3, axis=1), np.repeat(glob[:, None], 3, axis=1)
