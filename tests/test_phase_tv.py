"""Independent TV objective/bounds, physical operators and compact native detail."""

import numpy as np
import pytest

from demosaic.phase_envelope import correct_complex_patch
from demosaic.phase_tv import (
    _divergence,
    _gradient,
    _poisson_neumann,
    correct_edge_phase_patch,
    denoise_complex_tv,
)


def test_neumann_solver_matches_dense_graph_laplacian_and_adjoint():
    rng = np.random.default_rng(2026110300)
    height, width = 5, 7
    rhs = rng.normal(size=(2, height, width))
    dual = rng.normal(size=(2, 2, height, width))
    dual[0, :, -1], dual[1, :, :, -1] = 0, 0
    assert np.sum(_gradient(rhs) * dual) == pytest.approx(
        -np.sum(rhs * _divergence(dual)), abs=1e-12
    )
    laplacian = np.zeros((height * width, height * width))
    for y in range(height):
        for x in range(width):
            for yy, xx in [(y + 1, x), (y, x + 1)]:
                if yy < height and xx < width:
                    a, b = y * width + x, yy * width + xx
                    laplacian[a, a] += 1
                    laplacian[b, b] += 1
                    laplacian[a, b] -= 1
                    laplacian[b, a] -= 1
    expected = np.linalg.solve(
        np.eye(height * width) + 16 * laplacian, rhs.reshape(2, -1).T
    ).T.reshape(rhs.shape)
    np.testing.assert_allclose(_poisson_neumann(rhs, 16), expected, rtol=3e-13, atol=1e-13)


@pytest.mark.parametrize("weight", [0.1, 2.0])
def test_vectorial_two_pixel_solution_and_reported_error_bound(weight):
    values = np.array([[[0.0, 1.0]], [[0.2, 0.6]]]) * 0.001
    result, info = denoise_complex_tv(values, weight * 0.001, iterations=2048)
    difference = values[:, 0, 1] - values[:, 0, 0]
    distance = np.linalg.norm(difference)
    change = min(weight * 0.001, distance / 2) * difference / distance
    exact = values.copy()
    exact[:, 0, 0] += change
    exact[:, 0, 1] -= change
    error = 0.5 * np.sum((result - exact) ** 2)
    assert error <= info["absolute_primal_dual_gap"] + 1e-20
    assert info["relative_primal_dual_gap"] < 1e-5


def test_constant_zero_weight_rotation_and_iteration_cap():
    constant = np.ones((2, 9, 11)) * 0.002
    np.testing.assert_array_equal(denoise_complex_tv(constant, 0.1)[0], constant)
    rng = np.random.default_rng(2026110301)
    values = rng.normal(size=(2, 9, 11)) * 0.001
    np.testing.assert_array_equal(denoise_complex_tv(values, 0)[0], values)
    _, info = denoise_complex_tv(values, 0.001, iterations=1)
    assert info["iterations"] == 1 and np.isfinite(info["relative_primal_dual_gap"])
    angle = 0.73
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    rotated = np.einsum("ij,jhw->ihw", rotation, values)
    original, _ = denoise_complex_tv(values, 0.001)
    actual, _ = denoise_complex_tv(rotated, 0.001)
    np.testing.assert_allclose(
        actual, np.einsum("ij,jhw->ihw", rotation, original), rtol=1e-9, atol=1e-12
    )


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_compact_wave_recovers_native_detail_with_less_blank_spill(colors):
    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    mask = np.clip((80 - np.hypot(xx - 128, yy - 128)) / 8, 0, 1)
    wave = mask * np.cos(2 * np.pi * (0.0625 * xx + 0.09375 * yy))
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    variance = np.full_like(packed, 1e-7)
    old, _ = correct_complex_patch(packed, variance, colors, base)
    actual, _ = correct_edge_phase_patch(packed, variance, colors, base)
    blank = mask == 0
    assert np.mean((actual[:, blank] - base[:, blank]) ** 2) < np.mean(
        (old[:, blank] - base[:, blank]) ** 2
    )
    assert np.mean((actual - target) ** 2) < 0.2 * np.mean((base - target) ** 2)
    unchanged, _ = correct_edge_phase_patch(packed, np.zeros_like(packed), colors, base)
    np.testing.assert_array_equal(unchanged, base)


@pytest.mark.parametrize(
    "values,weight,iterations",
    [
        (np.zeros((3, 3, 3)), 1, 8),
        (np.zeros((2, 3, 3)), -1, 8),
        (np.full((2, 3, 3), np.nan), 1, 8),
        (np.zeros((2, 3, 3)), 1, 0),
    ],
)
def test_invalid_TV_inputs_reject(values, weight, iterations):
    with pytest.raises(ValueError):
        denoise_complex_tv(values, weight, iterations)
