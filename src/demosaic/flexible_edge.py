"""Discovery-only low-order boundaries for a local RAW background."""

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from .full_frame_edge import best_threshold


def coordinates_along_edge(xy, normal):
    a, b = np.cos(normal), np.sin(normal)
    x, y = xy.T
    tangent = -b * x + a * y
    return a * x + b * y, np.column_stack((np.ones_like(tangent), tangent, tangent**2))


def edge_terms(xy, normal, curves, width):
    coordinate, tangent = coordinates_along_edge(xy, normal)
    distance = coordinate[:, None] - tangent @ np.asarray(curves).T
    return expit(distance / width)


def _fit_shapes(values, xy, angle, seed, native_size, variance):
    """Variable projection over linear RGB nuisance coefficients and edge shapes."""
    affine = np.column_stack((np.ones(len(values)), xy))
    normal, powers = coordinates_along_edge(xy, angle)
    shape = np.asarray(seed, dtype=float).shape
    result = np.asarray(seed, dtype=float).ravel()
    bounds = [(-1.415, 1.415), (-0.15, 0.15), (-0.20, 0.20)] * shape[0]

    def objective(parameters, width):
        q = expit((normal[:, None] - powers @ parameters.reshape(shape).T) / width)
        design = np.column_stack((affine, q))
        coefficients = np.linalg.lstsq(design, values, rcond=1e-9)[0]
        residual = values - design @ coefficients
        weighted = q * (1 - q) * residual[:, None]
        derivative = (weighted.T @ powers) * coefficients[3:, None]
        return float(residual @ residual / variance), (2 * derivative / (variance * width)).ravel()

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
    error = objective(result, width)[0]
    return error, result.reshape(shape), width


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
