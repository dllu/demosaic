"""Score a fixed RAW carrier shape without reusing its fitted amplitude."""

import numpy as np


def matched_contrast(values, profile, null_design):
    """Return the unit-variance contrast after projecting a whitened profile."""
    if null_design is not None:
        coefficients = np.linalg.lstsq(null_design, profile, rcond=1e-10)[0]
        orthogonal = profile - null_design @ coefficients
    else:
        orthogonal = profile
    norm = np.linalg.norm(orthogonal)
    if norm <= 1e-10 * np.linalg.norm(profile):
        return 0.0
    return float(values @ orthogonal / norm)


def matched_query_scores(candidate, raw, colors, validation, reliability, *, window, stride):
    """Use discovery-fold shapes and variance with validation-only measurements.

    The optional projection uses the weighted validation *design*, without
    fitting any carrier/nuisance shape to the validation RAW. It removes
    sensitivity to held-out nuisance coefficients in the supplied design span.
    """
    if (
        raw.shape != candidate.full_cfa.shape
        or colors.shape != raw.shape
        or validation.shape != raw.shape
        or validation.dtype != bool
        or (validation & candidate.discovery_mask).any()
        or not np.isfinite(raw[validation]).all()
    ):
        raise ValueError("Require finite disjoint validation samples")
    yy, xx = np.indices(raw.shape)
    ay, ax = [np.unique(np.r_[np.arange(0, n, stride), n - 1]) for n in raw.shape]
    scope = validation.ravel()
    y, x, color = yy.ravel()[scope], xx.ravel()[scope], colors.ravel()[scope]
    variance = candidate.variance_cfa.ravel()[scope]
    inverse_sigma = 1 / np.sqrt(variance)
    design = candidate.design[scope] * inverse_sigma[:, None]
    side = (
        candidate.phase_bright_side.ravel()[scope]
        if candidate.phase_bright_side is not None
        else None
    )
    scores = np.zeros((2, len(candidate.unit_slices), 3, *raw.shape))
    radius = window // 2
    for unit, (start, stop) in enumerate(candidate.unit_slices):
        null = candidate.conditional_null_cfa[unit].ravel()[scope]
        values = (raw.ravel()[scope] - null) * inverse_sigma
        profile = (candidate.full_cfa.ravel()[scope] - null) * inverse_sigma
        null_model = np.delete(design, np.s_[start:stop], 1)
        side_ids = (None,) if side is None else (False, True)
        for channel, support in enumerate(reliability[unit]):
            if support == 0:
                continue
            for side_id in side_ids:
                select = color == channel
                if side is not None:
                    select &= side == side_id
                if not select.any():
                    continue
                y_c, x_c, v_c, p_c, n_c = [a[select] for a in (y, x, values, profile, null_model)]
                grid = np.zeros((2, len(ay), len(ax)))
                for i, center_y in enumerate(ay):
                    rows = np.abs(y_c - center_y) <= radius
                    x_row = x_c[rows]
                    v_row, p_row, n_row = v_c[rows], p_c[rows], n_c[rows]
                    for j, center_x in enumerate(ax):
                        use = np.abs(x_row - center_x) <= radius
                        if use.sum() <= n_row.shape[1] + 1:
                            continue
                        v, p = v_row[use], p_row[use]
                        grid[0, i, j] = matched_contrast(v, p, None)
                        grid[1, i, j] = matched_contrast(v, p, n_row[use])
                for mode, coarse in enumerate(grid):
                    rows = np.stack([np.interp(np.arange(raw.shape[1]), ax, r) for r in coarse])
                    value = np.stack(
                        [np.interp(np.arange(raw.shape[0]), ay, col) for col in rows.T], axis=1
                    )
                    if side is None:
                        scores[mode, unit, channel] = value
                    else:
                        pixels = candidate.phase_bright_side == side_id
                        scores[mode, unit, channel, pixels] = value[pixels]
    return scores
