"""Independent convex objectives, physical waves and clipped-window fallback."""

import numpy as np
import pytest

from demosaic.phase_sparse import coefficient_tv, connected_support
from demosaic.phase_tv import correct_edge_phase_patch


@pytest.mark.parametrize("weight", [0.001, 0.004])
@pytest.mark.parametrize("alpha", [0.0005, 0.01])
def test_two_pixel_group_TV_matches_analytic_solution_and_gap(weight, alpha):
    direction = np.array([0.6, 0.8])
    values = direction[:, None, None] * np.array([[[0.003, 0.008]]])
    if 0.005 <= 2 * weight:
        amplitudes = np.array([0.0055, 0.0055])
    else:
        amplitudes = np.array([0.003 + weight, 0.008 - weight])
    exact = direction[:, None, None] * np.maximum(0, amplitudes - alpha)[None, None, :]
    actual, info = coefficient_tv(values, weight, alpha, iterations=2048)
    assert 0.5 * np.sum((actual - exact) ** 2) <= info["absolute_primal_dual_gap"] + 1e-20
    assert info["converged"]


def test_masked_single_free_pixel_has_analytic_soft_threshold_and_exact_support():
    direction = np.array([0.6, 0.8])
    values = direction[:, None, None] * np.array([[[0.001, 0.005, 0.002]]])
    mask = np.array([[False, True, False]])
    exact = np.zeros_like(values)
    exact[:, 0, 1] = direction * 0.003
    actual, info = coefficient_tv(values, 0.001, mask, mode="mask", iterations=2048)
    assert 0.5 * np.sum((actual - exact) ** 2) <= info["absolute_primal_dual_gap"] + 1e-20
    np.testing.assert_array_equal(actual[:, ~mask], 0)


@pytest.mark.parametrize("mode", ["group", "mask"])
def test_rotation_equivariance_and_nonmultiple_iteration_cap(mode):
    rng = np.random.default_rng(2026110800)
    values = rng.normal(0, 0.001, (2, 9, 11))
    extra = 0.0003 if mode == "group" else np.indices((9, 11)).sum(axis=0) % 3 != 0
    angle = 0.73
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    actual, _ = coefficient_tv(values, 0.001, extra, mode=mode)
    rotated, _ = coefficient_tv(np.einsum("ij,jhw->ihw", rotation, values), 0.001, extra, mode=mode)
    np.testing.assert_allclose(rotated, np.einsum("ij,jhw->ihw", rotation, actual), atol=1e-12)
    _, info = coefficient_tv(values, 0.001, extra, mode=mode, iterations=1)
    assert info["iterations"] == 1 and np.isfinite(info["relative_primal_dual_gap"])


def test_zero_TV_weight_is_exact_group_prox_or_mask_projection():
    values = np.array([[[0.003, 0.0]], [[0.004, 0.0]]])
    actual, info = coefficient_tv(values, 0, 0.001)
    np.testing.assert_allclose(actual, values * 0.8, rtol=0, atol=1e-18)
    assert info["iterations"] == 0 and info["converged"]
    mask = np.array([[False, True]])
    actual, _ = coefficient_tv(values, 0, mask, mode="mask")
    np.testing.assert_array_equal(actual, values * mask)


def test_connected_support_keeps_large_regions_and_removes_diagonal_islands():
    mask = np.zeros((6, 9), bool)
    mask[1:3, 1:4] = True
    mask[4, 7:9] = True
    mask[5, 8] = True
    mask[0, 8] = mask[3, 4] = mask[4, 5] = True
    before = mask.copy()
    expected = np.zeros_like(mask)
    expected[1:3, 1:4] = True
    actual, info = connected_support(mask, 4)
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(mask, before)
    assert sorted(info["component_areas"]) == [1, 1, 1, 3, 6]
    assert info["kept_component_areas"] == [6] and info["removed_pixels"] == 6


@pytest.mark.parametrize(
    "mask,minimum",
    [
        (np.ones((2, 2)), 1),
        (np.ones((2, 2), bool), 0),
        (np.ones((2, 2), bool), True),
        (np.ones((2, 2), bool), 1.5),
    ],
)
def test_invalid_connected_support_inputs_reject(mask, minimum):
    with pytest.raises(ValueError):
        connected_support(mask, minimum)


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_sparse_pipeline_recovers_a_physical_wave_and_preserves_clipped_grid_TV(colors):
    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    wave = np.cos(2 * np.pi * (-0.0713 * xx + 0.0532 * yy) + 0.7)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    variance = np.full_like(packed, 1e-7)
    actual, info = correct_edge_phase_patch(packed, variance, colors, base, sparse_support=True)
    roi = (..., slice(48, 208), slice(48, 208))
    assert np.mean((actual[roi] - target[roi]) ** 2) < 0.1 * np.mean((base[roi] - target[roi]) ** 2)
    assert info["sparse_support"]["enabled"]
    assert info["TV_noise_multiplier"] == 4
    assert any("support" in d.get("solver", {}) for d in info["local"])
    unchanged, _ = correct_edge_phase_patch(
        packed, np.zeros_like(packed), colors, base, sparse_support=True
    )
    np.testing.assert_array_equal(unchanged, base)
    packed[0, 40, 50] = 1.0
    fixed, _ = correct_edge_phase_patch(packed, variance, colors, base)
    guarded, info = correct_edge_phase_patch(packed, variance, colors, base, sparse_support=True)
    np.testing.assert_array_equal(guarded, fixed)
    assert info["sparse_support"]["clipped_window_grid_TV_fallback"]
    assert info["TV_noise_multiplier"] == 16


@pytest.mark.parametrize(
    "kwargs",
    [
        {"values": np.zeros((3, 3, 3))},
        {"values": np.full((2, 3, 3), np.nan)},
        {"weight": -1},
        {"extra": -1},
        {"extra": np.nan},
        {"mode": "unknown"},
        {"mode": "mask", "extra": np.ones((3, 3))},
        {"iterations": 0},
        {"iterations": True},
    ],
)
def test_invalid_coefficient_inputs_reject(kwargs):
    arguments = {"values": np.zeros((2, 3, 3)), "weight": 0.001, "extra": 0.0003, **kwargs}
    with pytest.raises(ValueError):
        coefficient_tv(**arguments)
