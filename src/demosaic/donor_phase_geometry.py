"""Transport carrier geometry from disjoint donor RAW measurements."""

import numpy as np

from .experiments.evaluation.withheld import fit_candidate, geometry, stratified_split
from .local_validated_waves import _guide_frequencies, phase_gradient_in_annulus


def _phase_basis(coords, parameters):
    x, y = coords.T
    fx, fy, hxx, hxy, hyy = parameters
    turns = fx * x + fy * y + 0.5 * (hxx * x**2 + 2 * hxy * x * y + hyy * y**2)
    return np.column_stack((np.cos(2 * np.pi * turns), np.sin(2 * np.pi * turns)))


def _local_frequency_map(residual, frequencies):
    h, w = residual.shape
    fy, fx = np.meshgrid(np.fft.fftfreq(4 * h), np.fft.fftfreq(4 * w), indexing="ij")
    grid = np.stack((fx, fy), -1)
    radius = np.hypot(fx, fy)
    taper = np.hanning(h)[:, None] * np.hanning(w)
    power = np.abs(np.fft.fft2(residual * taper, (4 * h, 4 * w))) ** 2
    distance = np.linalg.norm(grid[..., None, :] - frequencies, axis=-1)
    other = np.minimum(
        distance[..., ::-1], np.linalg.norm(grid[..., None, :] + frequencies[::-1], axis=-1)
    )
    peaks = []
    for k in (0, 1):
        mask = (
            (radius >= 1 / 64)
            & (radius <= 0.24)
            & (distance[..., k] <= 0.058)
            & (distance[..., k] <= other[..., k])
            & (grid @ frequencies[k] > 0)
        )
        level = np.where(mask, power, -np.inf)
        peaks.append(grid[np.unravel_index(np.argmax(level), level.shape)])
    return np.stack(peaks)


def _initial_models(residual, frequencies, span):
    h, w = residual.shape
    guesses, gradient_rows = [], []
    for a, b in ((0, h // 2), (h // 2, h)):
        for c, d in ((0, w // 2), (w // 2, w)):
            patch = residual[a:b, c:d]
            guesses.append(_local_frequency_map(patch, frequencies) * span)
            x, y = (c + d - w) / (2 * span), (a + b - h) / (2 * span)
            gradient_rows.extend(((1, 0, x, y, 0), (0, 1, 0, x, y)))
    response = np.asarray(guesses).transpose(0, 2, 1).reshape(8, 2)
    return np.linalg.lstsq(gradient_rows, response, rcond=1e-10)[0].T


def _hessian(parameters):
    return np.array([[parameters[2], parameters[3]], [parameters[3], parameters[4]]])


def _curved_starts(reference, center_delta):
    normal = reference[:2] / np.linalg.norm(reference[:2])
    tangent = np.array([-normal[1], normal[0]])
    for axis in (normal, tangent):
        for q in (-12, -8, -4, 4, 8, 12):
            H = q * np.outer(axis, axis)
            powers = [H[0, 0], H[0, 1], H[1, 1]]
            yield np.r_[reference[:2], powers]
            # A scene guide can already approximate the target center.
            yield np.r_[reference[:2] - H @ center_delta, powers]


def _fit_carrier(coords, target, inverse_sigma, competitor, starts, span, shape, *, curved):
    from scipy.optimize import minimize

    matrix = competitor * inverse_sigma[:, None]
    u, s, _ = np.linalg.svd(matrix, full_matrices=False)
    basis = u[:, s > 1e-10 * s[0]]
    target = target - basis @ (basis.T @ target)

    def admissible(p):
        hessian = _hessian(p)
        return np.linalg.norm(hessian, ord=2) <= 16 and phase_gradient_in_annulus(
            p[:2] / span, hessian / span**2, shape
        )

    def score(p):
        if not admissible(p):
            return -np.inf
        wave = _phase_basis(coords, p) * inverse_sigma[:, None]
        wave -= basis @ (basis.T @ wave)
        fitted = wave @ np.linalg.lstsq(wave, target, rcond=1e-10)[0]
        return float(fitted @ fitted)

    chosen = max(starts, key=score).copy()
    greatest = score(chosen)
    for frequency_step, curvature_step in ((0.8, 4), (0.32, 1.6), (0.12, 0.6), (0.04, 0.2)):
        for k in range(5 if curved else 2):
            step = frequency_step if k < 2 else curvature_step
            for sign in (-1, 1):
                trial = chosen.copy()
                trial[k] += sign * step
                value = score(trial)
                if value > greatest:
                    greatest, chosen = value, trial
    x, y = coords.T
    terms = 2 * np.pi * np.column_stack((x, y, 0.5 * x**2, x * y, 0.5 * y**2))
    if not curved:
        terms = terms[:, :2]
    dimension = terms.shape[1]

    def objective(v):
        p = v if curved else np.r_[v, 0, 0, 0]
        if not admissible(p):
            return 1e12, np.zeros_like(v)
        angle = terms @ v
        sine, cosine = np.sin(angle), np.cos(angle)
        wave = np.column_stack((cosine, sine)) * inverse_sigma[:, None]
        wave -= basis @ (basis.T @ wave)
        coefficient = np.linalg.lstsq(wave, target, rcond=1e-10)[0]
        residual = target - wave @ coefficient
        response = (-sine * coefficient[0] + cosine * coefficient[1]) * inverse_sigma
        size = len(residual)
        return residual @ residual / size, -2 * ((residual * response) @ terms) / size

    bounds = [(z - 1.5, z + 1.5) for z in chosen[:2]] + ([(-16, 16)] * 3 if curved else [])
    result = minimize(
        objective,
        chosen[:dimension],
        method="L-BFGS-B",
        jac=True,
        bounds=bounds,
        options={"ftol": 1e-14, "gtol": 1e-9, "maxiter": 80},
    )
    candidate = result.x if curved else np.r_[result.x, 0, 0, 0]
    if score(candidate) > greatest:
        return candidate
    return chosen


def _model_columns(background, coords, models):
    return np.column_stack((background, *[_phase_basis(coords, value) for value in models]))


def _fold_fields(raw, cfa, discovery, shot, read):
    xx, yy, affine, _ = geometry(raw.shape)
    span = min(raw.shape)
    coords = np.column_stack(
        ((xx.ravel() - (raw.shape[1] - 1) / 2) / span, (yy.ravel() - (raw.shape[0] - 1) / 2) / span)
    )
    initial = fit_candidate(raw, cfa, discovery, shot=shot, read=read, nuisance="step", peaks=1)
    angle, offset = initial.edge_geometry
    x = 2 * (xx.ravel() + 0.5) / raw.shape[1] - 1
    y = 2 * (yy.ravel() + 0.5) / raw.shape[0] - 1
    background = np.column_stack((affine, x * np.cos(angle) + y * np.sin(angle) > offset))
    green = cfa.ravel() == 1
    selected = discovery.ravel() & green
    y_train = raw.ravel()[selected]
    fitted = np.linalg.lstsq(background[selected], y_train, rcond=1e-10)[0]
    inverse_sigma = 1 / np.sqrt(read + shot * np.maximum(background @ fitted, 1e-6))
    return coords, background, selected, green & ~discovery.ravel(), inverse_sigma, fitted


def _fit_fold(raw, cfa, discovery, frequencies, center_delta, shot, read, fields=None):
    if fields is None:
        fields = _fold_fields(raw, cfa, discovery, shot, read)
    coords, background, selected, testing, inverse_sigma, fitted = fields
    span = min(raw.shape)
    y_train = raw.ravel()[selected]
    residual = np.zeros(raw.size)
    residual[selected] = (y_train - background[selected] @ fitted) * inverse_sigma[selected]
    guesses = _initial_models(residual.reshape(raw.shape), frequencies, span)
    reference = np.pad(frequencies * span, ((0, 0), (0, 3)))
    planar, curved = reference.copy(), reference.copy()
    for models, use_hessian in ((planar, False), (curved, True)):
        for k in (0, 1):
            start = guesses[k].copy()
            if not use_hessian:
                start[2:] = 0
            competitor = _model_columns(background[selected], coords[selected], [models[1 - k]])
            starts = [reference[k], planar[k], start]
            if use_hessian:
                starts.extend(_curved_starts(reference[k], center_delta / span))
            models[k] = _fit_carrier(
                coords[selected],
                y_train * inverse_sigma[selected],
                inverse_sigma[selected],
                competitor,
                starts,
                span,
                raw.shape,
                curved=use_hessian,
            )
    gains = []
    for k in (0, 1):
        errors = []
        for candidate in (planar[k], curved[k]):
            design = _model_columns(background, coords, (candidate, curved[1 - k]))
            sys = design[selected] * inverse_sigma[selected, None]
            beta = np.linalg.lstsq(sys, y_train * inverse_sigma[selected], rcond=1e-10)[0]
            held = (raw.ravel()[testing] - design[testing] @ beta) * inverse_sigma[testing]
            errors.append(float(held @ held))
        gains.append(errors[0] - errors[1])
    return curved, gains


def transport_donor_geometry(packed, colors, donor_box, query_box, seed_frequencies, *, shot, read):
    """Give the query only donor gradients and their Hessians in native coordinates."""
    packed, colors = np.asarray(packed), np.asarray(colors)
    dx, dy, dw, dh = donor_box
    qx, qy, qw, qh = query_box
    if (
        min(dw, dh) < 64
        or dw % 2
        or dh % 2
        or packed.shape != (4, dh // 2, dw // 2)
        or colors.shape != (4,)
        or not np.isfinite(packed).all()
        or not np.isfinite([shot, read]).all()
        or min(shot, read) < 0
        or shot + read <= 0
    ):
        raise ValueError("Require finite donor Bayer samples and a positive noise profile")
    if max(dx, qx) < min(dx + dw, qx + qw) and max(dy, qy) < min(dy + dh, qy + qh):
        raise ValueError("Donor and query RAW coordinates must be disjoint")
    frequencies = np.asarray(_guide_frequencies(seed_frequencies, 20))
    center_delta = np.array([qx - dx + (qw - dw) / 2, qy - dy + (qh - dh) / 2])
    hessians = np.zeros((2, 2, 2), np.float64)
    result = {
        "frequencies_xy": frequencies.tolist(),
        "hessians_xy": hessians.tolist(),
        "center_delta_xy": center_delta.tolist(),
        "accepted": [False, False],
    }
    span = min(dh, dw)
    if np.linalg.norm(center_delta) > 2 * span:
        return result | {"status": "distant donor"}
    raw = packed.reshape(2, 2, dh // 2, dw // 2).transpose(2, 0, 3, 1).reshape(dh, dw)
    cfa = np.tile(colors.reshape(2, 2), (dh // 2, dw // 2))
    split = stratified_split(raw.shape, 202611170715)
    folds = [
        _fit_fold(raw, cfa, keep, frequencies, center_delta, shot, read) for keep in (split, ~split)
    ]
    models = np.stack([p for p, _ in folds])
    gains = np.asarray([g for _, g in folds])
    h, w = qh, qw
    for k in (0, 1):
        fold_hessians = np.stack([_hessian(p[k]) for p in models]) / span**2
        at_query = models[:, k, :2] / span + fold_hessians @ center_delta
        proposed = at_query.mean(0)
        averaged = fold_hessians.mean(0)
        disagreement = np.linalg.norm(at_query[0] - at_query[1]) * min(h, w)
        h_difference = np.linalg.norm(fold_hessians[0] - fold_hessians[1]) * min(h, w) ** 2
        if (
            gains[:, k].min() > 16
            and disagreement <= 1.25
            and h_difference <= 3
            and phase_gradient_in_annulus(proposed, averaged, (h, w))
        ):
            trial = frequencies.copy()
            trial[k] = proposed
            try:
                _guide_frequencies(trial, 20)
            except ValueError:
                continue
            frequencies = trial
            hessians[k] = averaged
            result["accepted"][k] = True
    return result | {
        "status": "evaluated",
        "frequencies_xy": frequencies.tolist(),
        "hessians_xy": hessians.tolist(),
        "donor_fold_models": models.tolist(),
        "heldout_error_reduction": gains.tolist(),
        "donor_coordinate_span": span,
    }
