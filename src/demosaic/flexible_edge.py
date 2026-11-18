"""Discovery-only low-order boundaries for a local RAW background."""

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from .full_frame_edge import best_threshold, search_edge, supported_parallel_edges


def coordinates_along_edge(xy, normal):
    a, b = np.cos(normal), np.sin(normal)
    x, y = xy.T
    tangent = -b * x + a * y
    return a * x + b * y, np.column_stack((np.ones_like(tangent), tangent, tangent**2))


def edge_terms(xy, normal, curves, width):
    coordinate, tangent = coordinates_along_edge(xy, normal)
    distance = coordinate[:, None] - tangent @ np.asarray(curves).T
    return expit(distance / width)


def _profile_objective(values, xy, angle, variance):
    affine = np.column_stack((np.ones(len(values)), xy))
    normal, powers = coordinates_along_edge(xy, angle)

    def objective(curves, width):
        q = expit((normal[:, None] - powers @ curves.T) / width)
        design = np.column_stack((affine, q))
        coefficients = np.linalg.lstsq(design, values, rcond=1e-9)[0]
        residual = values - design @ coefficients
        weighted = q * (1 - q) * residual[:, None]
        derivative = (weighted.T @ powers) * coefficients[3:, None]
        return float(residual @ residual / variance), 2 * derivative / (variance * width)

    return objective


def _optimize(objective, result, bounds, native_size):
    # Start with enough blur to capture weakly initialized boundaries before
    # returning to a transition on approximately the native pixel scale.
    for pixel_width in (1.25, 0.42):
        width = 2 * pixel_width / native_size
        fit = minimize(
            objective,
            result,
            args=(width,),
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={"maxiter": 45, "ftol": 1e-9},
        )
        if fit.fun <= objective(result, width)[0]:
            result = fit.x
    return objective(result, width)[0], result, width


def _fit_shapes(values, xy, angle, seed, native_size, variance):
    """Variable projection over linear RGB nuisance coefficients and edge shapes."""
    objective = _profile_objective(values, xy, angle, variance)
    seed = np.asarray(seed, dtype=float)
    bounds = [(-1.415, 1.415), (-0.15, 0.15), (-0.20, 0.20)] * len(seed)

    def flat(parameters, width):
        error, derivative = objective(parameters.reshape(seed.shape), width)
        return error, derivative.ravel()

    error, result, width = _optimize(flat, seed.ravel(), bounds, native_size)
    return error, result.reshape(seed.shape), width


def fit_flexible_edges(values, xy, normal, offsets, native_size, shot, read, *, maximum):
    """Fit a few smooth step boundaries using only discovery green samples.

    Each offset can vary quadratically along one shared axis. Add a boundary
    only if the normalized residual reduction exceeds the fixed complexity
    cost. The returned terms are also used when fitting the conditional null.
    """
    if maximum not in (2, 4) or not 1 <= len(offsets) <= 2:
        raise ValueError("Require one or two initial boundaries and a limit of two or four")
    variance = read + shot * max(1e-6, values.mean())
    position, _ = coordinates_along_edge(xy, normal)
    affine = np.column_stack((np.ones(len(values)), xy))
    hard = np.column_stack((affine, *(position > t for t in offsets)))
    residual = values - hard @ np.linalg.lstsq(hard, values, rcond=1e-10)[0]
    starting_error = residual @ residual / variance
    seed = [[o, 0.0, 0.0] for o in offsets]
    error, curves, width = _fit_shapes(values, xy, normal, seed, native_size, variance)
    cost = 3 * np.log(len(values))
    if starting_error - error <= cost:
        error, curves, width = starting_error, np.asarray(seed), 0.0
    while len(curves) < maximum:
        companion = (
            edge_terms(xy, normal, curves, width) if width else position[:, None] > curves[:, 0]
        )
        if np.linalg.matrix_rank(np.column_stack((affine, companion))) < 3 + len(curves):
            break
        offset, benefit = best_threshold(values, xy, normal, companion=companion)
        if benefit <= variance * cost:
            break
        if np.min(np.abs(curves[:, 0] - offset)) < 4 / native_size:
            break
        seed = np.vstack((curves, [offset, 0, 0]))
        new_error, new_curves, new_width = _fit_shapes(
            values, xy, normal, seed, native_size, variance
        )
        if error - new_error <= cost:
            break
        error, curves, width = new_error, new_curves, new_width
    if width == 0:
        return None
    return float(normal), curves.tolist(), float(width)


def _fit_smooth_parallel(values, xy, normal, offsets, native_size, variance):
    """Subpixel parallel counterfactual with one jointly fitted angular change."""
    objective = _profile_objective(values, xy, normal, variance)

    def shared(parameters):
        slopes = np.full(len(offsets), parameters[-1])
        return np.column_stack((parameters[:-1], slopes, np.zeros_like(slopes)))

    def loss(parameters, width):
        error, jac = objective(shared(parameters), width)
        return error, np.r_[jac[:, 0], jac[:, 1].sum()]

    bounds = [(-1.415, 1.415)] * len(offsets) + [(-0.15, 0.15)]
    _, fitted, width = _optimize(loss, np.r_[offsets, 0.0], bounds, native_size)
    return normal, shared(fitted), width


def paired_background_score(values, reference, candidate, variance):
    """Standardized benefit for two frozen background predictions."""
    diff = candidate - reference
    energy = np.sum(diff**2 / variance)
    if energy <= 1e-15:
        return 0.0
    return float(np.sum(diff * (values - (reference + candidate) / 2) / variance) / np.sqrt(energy))


def screen_flexible_edges(values, xy, discovery, native_size, shot, read, *, refinements):
    """Choose a nuisance family on two nested splits of the outer discovery data.

    The caller sends only discovery RAW values. One split sets the geometry and
    amplitudes for all three candidates. The other checks their fixed predictions.
    """
    if discovery.shape != values.shape or discovery.dtype != bool:
        raise ValueError("Require a nested discovery mask for the supplied green samples")
    if min(discovery.sum(), (~discovery).sum()) < 16:
        return {"accepted": False, "vs_hard": None, "vs_smooth": None}
    learn, reserved = values[discovery], values[~discovery]
    train, test = xy[discovery], xy[~discovery]
    normal, offset = search_edge(learn, train, refinements)
    train_affine = np.column_stack((np.ones(len(train)), train))
    test_affine = np.column_stack((np.ones(len(test)), test))
    position, _ = coordinates_along_edge(train, normal)
    step = np.column_stack((train_affine, position > offset))
    error = learn - step @ np.linalg.lstsq(step, learn, rcond=1e-10)[0]
    parallel = supported_parallel_edges(learn, train, normal, offset, error @ error, shot, read)
    normal, *offsets = parallel if parallel is not None else (normal, offset)
    curved = fit_flexible_edges(learn, train, normal, offsets, native_size, shot, read, maximum=4)
    if curved is None:
        return {"accepted": False, "vs_hard": None, "vs_smooth": None}
    variance = read + shot * max(1e-6, learn.mean())
    smooth = _fit_smooth_parallel(learn, train, normal, offsets, native_size, variance)
    start, _ = coordinates_along_edge(train, normal)
    stop, _ = coordinates_along_edge(test, normal)
    predictions = []
    for a, b in (
        (start[:, None] > offsets, stop[:, None] > offsets),
        (edge_terms(train, *smooth), edge_terms(test, *smooth)),
        (edge_terms(train, *curved), edge_terms(test, *curved)),
    ):
        design = np.column_stack((train_affine, a))
        coefficients = np.linalg.lstsq(design, learn, rcond=1e-9)[0]
        predictions.append(np.column_stack((test_affine, b)) @ coefficients)
    hard, smooth, curved = predictions
    prediction_variance = read + shot * np.maximum(1e-6, smooth)
    gains = [
        paired_background_score(reserved, ref, curved, prediction_variance)
        for ref in (hard, smooth)
    ]
    return {"accepted": min(gains) > 3, "vs_hard": gains[0], "vs_smooth": gains[1]}
