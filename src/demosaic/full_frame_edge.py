"""Discovery-only affine-plus-half-plane search over the entire native frame."""

import numpy as np


def best_threshold(values, coordinates, angle):
    """Exact least-squares step benefit over all distinct offsets at one angle.

    Suffix sums evaluate every sensor-coordinate partition after residualizing
    its step against the same affine basis. No predefined central offset range.
    """
    values, coordinates = np.asarray(values, np.float64), np.asarray(coordinates, np.float64)
    if (
        values.ndim != 1
        or coordinates.shape != (len(values), 2)
        or len(values) < 16
        or not np.isfinite(values).all()
        or not np.isfinite(coordinates).all()
        or not np.isfinite(angle)
    ):
        raise ValueError("Require finite discovery values and native normalized coordinates")
    basis = np.column_stack((np.ones(len(values)), coordinates))
    if np.linalg.matrix_rank(basis) != 3:
        raise ValueError("Require two-dimensional discovery support")
    q, _ = np.linalg.qr(basis, mode="reduced")
    residual = values - q @ (q.T @ values)
    projected = coordinates[:, 0] * np.cos(angle) + coordinates[:, 1] * np.sin(angle)
    order = np.argsort(projected, kind="stable")
    position = projected[order]
    sums = np.cumsum(residual[order][::-1])[::-1][1:]
    q_sums = np.cumsum(q[order][::-1], axis=0)[::-1][1:]
    count = np.arange(len(values) - 1, 0, -1)
    energy = count - np.sum(q_sums * q_sums, axis=1)
    valid = (position[:-1] < position[1:]) & (energy > 32 * np.finfo(float).eps * len(values))
    benefit = np.full(len(values) - 1, -np.inf)
    benefit[valid] = sums[valid] ** 2 / energy[valid]
    index = int(np.argmax(benefit))
    if not np.isfinite(benefit[index]):
        raise ValueError("No identifiable affine-plus-step partition")
    left, right = position[index : index + 2]
    offset = (left + right) * 0.5
    if offset >= right:
        offset = left
    return float(offset), float(benefit[index])


def search_edge(values, coordinates, refinements=3):
    """Coarse-to-fine normal search, optimizing the complete offset axis each time."""
    if type(refinements) is not int or not 0 <= refinements <= 3:
        raise ValueError("Require zero to three angular refinement levels")
    angles = np.linspace(0, np.pi, 12, endpoint=False)
    results = [(float(angle), *best_threshold(values, coordinates, angle)) for angle in angles]
    chosen = max(results, key=lambda row: row[2])
    radius = np.pi / 12
    for _ in range(refinements):
        results = [
            (float(angle), *best_threshold(values, coordinates, angle))
            for angle in chosen[0] + np.linspace(-radius, radius, 9)
        ]
        chosen = max(results, key=lambda row: row[2])
        radius /= 4
    return chosen[:2]
