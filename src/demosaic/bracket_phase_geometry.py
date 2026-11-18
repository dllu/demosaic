"""Fit a shared phase derivative field to independent RAW regions on both sides."""

import numpy as np

from .donor_phase_geometry import _curved_starts, _fit_fold, _fold_fields, _hessian, _model_columns
from .experiments.evaluation.withheld import stratified_split
from .local_validated_waves import _guide_frequencies, phase_gradient_in_annulus


def _overlaps(a, b):
    return all(max(a[k], b[k]) < min(a[k] + a[k + 2], b[k] + b[k + 2]) for k in (0, 1))


def _center(box):
    x, y, w, h = box
    return np.array([x + (w - 1) / 2, y + (h - 1) / 2])


def _encode_hessian(H):
    return [H[0, 0], H[0, 1], H[1, 1]]


def _join_starts(models, offsets, span, shapes, reference):
    normalized = np.stack(
        [
            m * np.r_[np.repeat(span / min(s), 2), np.repeat((span / min(s)) ** 2, 3)]
            for m, s in zip(models, shapes, strict=True)
        ]
    )
    hessians = np.stack([_hessian(m) for m in normalized])
    transported = normalized[:, :2] - np.einsum("ijk,ik->ij", hessians, offsets)
    starts = [reference, *[np.r_[f, p[2:]] for f, p in zip(transported, normalized, strict=True)]]
    H = hessians.mean(0)
    axis = offsets[1] - offsets[0]
    distance = np.linalg.norm(axis)
    unit = axis / distance
    drift_error = (normalized[1, :2] - normalized[0, :2] - H @ axis) / distance
    adjust = np.outer(drift_error, unit) + np.outer(unit, drift_error)
    adjust -= (drift_error @ unit) * np.outer(unit, unit)
    H += adjust
    center = (normalized[:, :2] - offsets @ H).mean(0)
    return [*starts, np.r_[center, _encode_hessian(H)]]


def _carrier_problem(donors, other):
    problems = []
    for raw, xy, background, train, _test, inverse_sigma, _center_offset in donors:
        coordinates = xy[train]
        design = _model_columns(background[train], coordinates, [other])
        sigma = inverse_sigma[train]
        u, s, _ = np.linalg.svd(design * sigma[:, None], full_matrices=False)
        basis = u[:, s > 1e-10 * s[0]]
        target = raw.ravel()[train] * sigma
        target -= basis @ (basis.T @ target)
        x, y = coordinates.T
        terms = 2 * np.pi * np.column_stack((x, y, 0.5 * x**2, x * y, 0.5 * y**2))
        problems.append((terms, target, basis, sigma))
    return problems


def _estimate(donors, starts, other, span, query_shape, *, curved):
    from scipy.optimize import minimize

    problems = _carrier_problem(donors, other)
    dimensions = 5 if curved else 2

    def objective(values):
        params = values if curved else np.r_[values, 0, 0, 0]
        H = _hessian(params)
        if np.linalg.norm(H, ord=2) > 16 or not phase_gradient_in_annulus(
            params[:2] / span, H / span**2, query_shape
        ):
            return 1e12, np.zeros_like(values)
        for raw, *_, offset in donors:
            if not phase_gradient_in_annulus(
                (params[:2] + H @ offset) / span, H / span**2, raw.shape
            ):
                return 1e12, np.zeros_like(values)
        error = 0.0
        grad = np.zeros(dimensions)
        for terms, target, basis, sigma in problems:
            design = terms[:, :dimensions]
            angle = design @ values
            cosine, sine = np.cos(angle), np.sin(angle)
            wave = np.column_stack((cosine, sine)) * sigma[:, None]
            wave -= basis @ (basis.T @ wave)
            beta = np.linalg.lstsq(wave, target, rcond=1e-10)[0]
            residual = target - wave @ beta
            response = (-sine * beta[0] + cosine * beta[1]) * sigma
            error += residual @ residual / len(target)
            grad -= 2 * ((residual * response) @ design) / len(target)
        return error, grad

    unique = {tuple(p[:dimensions]) for p in starts}
    options = sorted(map(np.asarray, sorted(unique)), key=lambda p: objective(p)[0])
    best = options[0].copy()
    cost = objective(best)[0]
    # The two best proposals can disagree about the physical origin of the seed.
    for start in options[:2]:
        bounds = [(v - 2, v + 2) for v in start[:2]]
        if curved:
            bounds += [(-16, 16)] * 3
        result = minimize(
            objective,
            start,
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={"ftol": 1e-14, "gtol": 1e-9, "maxiter": 100},
        )
        if result.fun < cost:
            best, cost = result.x, result.fun
    return best if curved else np.r_[best, 0, 0, 0]


def _error_reductions(donors, planar, curved, local_planar):
    improvements = []
    for (raw, xy, background, train, test, precision, _offset), local in zip(
        donors, local_planar, strict=True
    ):
        improvements.append([])
        for index in (0, 1):
            errors = []
            other = curved[1 - index]
            for proposed in (planar[index], local[index], curved[index]):
                design = _model_columns(background, xy, (proposed, other))
                model = design[train] * precision[train, None]
                beta = np.linalg.lstsq(model, raw.ravel()[train] * precision[train], rcond=1e-10)[0]
                residual = (raw.ravel()[test] - design[test] @ beta) * precision[test]
                errors.append(float(residual @ residual))
            improvements[-1].append((errors[0] - errors[2], errors[1] - errors[2]))
    return improvements


def _fit_bracket(tiles, splits, offsets, frequencies, span, query_shape, shot, read):
    proposals, donors = [], []
    for (raw, colors), discovery, offset in zip(tiles, splits, offsets, strict=True):
        fields = _fold_fields(raw, colors, discovery, shot, read)
        xy, background, train, test, inverse_sigma, _ = fields
        normalized = xy * (min(raw.shape) / span) + offset
        donors.append((raw, normalized, background, train, test, inverse_sigma, offset))
        guess, _ = _fit_fold(
            raw, colors, discovery, frequencies, -offset * span, shot, read, fields
        )
        proposals.append(guess)
    reference = np.pad(frequencies * span, ((0, 0), (0, 3)))
    planar, curved = reference.copy(), reference.copy()
    for k in (0, 1):
        starts = _join_starts(
            [p[k] for p in proposals], offsets, span, [raw.shape for raw, _ in tiles], reference[k]
        )
        planar[k] = _estimate(donors, starts, planar[1 - k], span, query_shape, curved=False)
    curved[:] = planar
    for k in (0, 1):
        starts = _join_starts(
            [p[k] for p in proposals], offsets, span, [raw.shape for raw, _ in tiles], reference[k]
        )
        starts.extend(_curved_starts(reference[k], offsets[0]))
        starts.extend(_curved_starts(reference[k], offsets[1]))
        curved[k] = _estimate(
            donors, [planar[k], *starts], curved[1 - k], span, query_shape, curved=True
        )
    local_planar = []
    for donor, proposal, offset in zip(donors, proposals, offsets, strict=True):
        estimates = []
        for k in (0, 1):
            derivative = curved[k, :2] + _hessian(curved[k]) @ offset
            measured = proposal[k, :2] * span / min(donor[0].shape)
            starts = [planar[k], reference[k], np.r_[derivative, 0, 0, 0], np.r_[measured, 0, 0, 0]]
            estimates.append(
                _estimate([donor], starts, curved[1 - k], span, query_shape, curved=False)
            )
        local_planar.append(estimates)
    return curved, _error_reductions(donors, planar, curved, local_planar)


def bracket_donor_geometry(donors, query_box, seed_frequencies, *, shot, read):
    """Estimate shared geometry from two disjoint RAW donors that bracket a native query."""
    if (
        len(donors) != 2
        or min(query_box[2:]) < 1
        or not np.isfinite([shot, read]).all()
        or min(shot, read) < 0
        or shot + read <= 0
    ):
        raise ValueError(
            "Two donor observations, positive query geometry and sensor noise are required"
        )
    frequencies = np.asarray(_guide_frequencies(seed_frequencies, 20))
    boxes = [b for _, _, b in donors]
    if _overlaps(*boxes) or any(_overlaps(b, query_box) for b in boxes):
        raise ValueError("Donor and query RAW boxes must be mutually disjoint")
    width, height = query_box[2:]
    span = min(height, width)
    offsets = np.asarray([_center(b) - _center(query_box) for b in boxes]) / span
    H = np.zeros((2, 2, 2), np.float64)
    result = {
        "frequencies_xy": frequencies.tolist(),
        "hessians_xy": H.tolist(),
        "accepted": [False, False],
        "donor_offsets_xy": (offsets * span).tolist(),
    }
    direction = offsets[1] - offsets[0]
    fraction = -(offsets[0] @ direction) / (direction @ direction)
    cross_distance = np.linalg.norm(offsets[0] + fraction * direction)
    if (
        not 0.25 <= fraction <= 0.75
        or cross_distance > 0.25
        or np.max(np.linalg.norm(offsets, axis=1)) > 2
    ):
        return result | {"status": "query is outside the bracket"}
    tiles = []
    for packed, colors, (_, _, w, h) in donors:
        packed, colors = np.asarray(packed), np.asarray(colors)
        if (
            min(h, w) < 64
            or h % 2
            or w % 2
            or packed.shape != (4, h // 2, w // 2)
            or colors.shape != (4,)
            or not np.isfinite(packed).all()
        ):
            raise ValueError("Require native finite Bayer donor samples and matching geometry")
        raw = packed.reshape(2, 2, h // 2, w // 2).transpose(2, 0, 3, 1).reshape(h, w)
        tiles.append((raw, np.tile(colors.reshape(2, 2), (h // 2, w // 2))))
    splits = [stratified_split(raw.shape, 202611170720 + i) for i, (raw, _) in enumerate(tiles)]
    fits = [
        _fit_bracket(tiles, masks, offsets, frequencies, span, (height, width), shot, read)
        for masks in (splits, [~v for v in splits])
    ]
    params = np.stack([p for p, _ in fits])
    gains, local_gains = np.moveaxis(np.asarray([g for _, g in fits]), -1, 0)
    for k in (0, 1):
        f = params[:, k, :2]
        h = np.stack([_hessian(p[k]) for p in params])
        disagreement = np.linalg.norm(f[0] - f[1])
        h_difference = np.linalg.norm(h[0] - h[1])
        proposed = f.mean(0) / span
        average = h.mean(0) / span**2
        if (
            np.min(gains[..., k]) > 0
            and np.min(gains[..., k].sum(1)) > 16
            and np.min(local_gains[..., k]) > 0
            and np.min(local_gains[..., k].sum(1)) > 16
            and disagreement <= 1.25
            and h_difference <= 3
            and phase_gradient_in_annulus(proposed, average, (height, width))
        ):
            trial = frequencies.copy()
            trial[k] = proposed
            try:
                _guide_frequencies(trial, 20)
            except ValueError:
                continue
            frequencies = trial
            H[k] = average
            result["accepted"][k] = True
    return result | {
        "status": "evaluated",
        "frequencies_xy": frequencies.tolist(),
        "hessians_xy": H.tolist(),
        "fold_models": params.tolist(),
        "heldout_error_reduction": gains.tolist(),
        "local_planar_error_reduction": local_gains.tolist(),
    }
