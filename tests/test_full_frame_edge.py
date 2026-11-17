"""Full offset support, independent least squares and actual CFA withholding."""

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import fit_candidate, stratified_split
from demosaic.full_frame_edge import best_threshold, search_edge
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate


@pytest.mark.parametrize("angle", [0.0, 0.37, np.pi / 2, 2.1])
def test_offset_sweep_matches_brute_force_affine_plus_step(angle):
    y, x = np.mgrid[:6, :8]
    coordinates = np.column_stack((x.ravel() / 4 - 1, y.ravel() / 3 - 1))
    values = np.random.default_rng(12).normal(size=len(coordinates))
    offset, benefit = best_threshold(values, coordinates, angle)
    basis = np.column_stack((np.ones(len(values)), coordinates))
    baseline = np.linalg.lstsq(basis, values, rcond=None)[0]
    baseline_error = np.sum((values - basis @ baseline) ** 2)
    positions = coordinates[:, 0] * np.cos(angle) + coordinates[:, 1] * np.sin(angle)
    unique = np.unique(positions)
    gains = []
    for left in unique[:-1]:
        # Use the left endpoint: exactly the partition to the right, even for
        # adjacent floating values with no representable strict midpoint.
        design = np.column_stack((basis, positions > left))
        coefficient = np.linalg.lstsq(design, values, rcond=None)[0]
        gains.append(baseline_error - np.sum((values - design @ coefficient) ** 2))
    design = np.column_stack((basis, positions > offset))
    actual = baseline_error - np.sum(
        (values - design @ np.linalg.lstsq(design, values, rcond=None)[0]) ** 2
    )
    assert abs(benefit - max(gains)) < 1e-11
    assert abs(actual - benefit) < 1e-11


@pytest.mark.parametrize("layout", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
@pytest.mark.parametrize("offset", [0.83, -0.83])
def test_far_edge_outside_old_grid_recovered_without_withheld_values(layout, offset):
    y, x = np.mgrid[:64, :64]
    nx, ny = 2 * (x + 0.5) / 64 - 1, 2 * (y + 0.5) / 64 - 1
    truth = 0.02 + 0.15 * (nx * np.cos(0.37) + ny * np.sin(0.37) > offset)
    raw = truth + np.random.default_rng(7).normal(0, 1e-4, truth.shape)
    colors = np.tile(np.asarray(layout).reshape(2, 2), (32, 32))
    mask = stratified_split(raw.shape, 71)
    args = {"shot": 8e-5, "read": 2.56e-8, "nuisance": "step", "peaks": 1, "edge_refinements": 3}
    bounded = fit_candidate(raw, colors, mask, **args)
    full = fit_candidate(raw, colors, mask, edge_search="full-frame", **args)
    assert np.mean((full.background - truth) ** 2) < 0.2 * np.mean(
        (bounded.background - truth) ** 2
    )
    damaged = raw.copy()
    damaged[~mask] = np.nan
    repeat = fit_candidate(damaged, colors, mask, edge_search="full-frame", **args)
    assert repeat.edge_geometry == full.edge_geometry
    for key in ["background", "prediction", "noise_variance"]:
        np.testing.assert_array_equal(getattr(full, key), getattr(repeat, key))
    local = fit_local_candidate(
        raw,
        colors,
        mask,
        shot=8e-5,
        read=2.56e-8,
        config=LocalWaveConfig(
            window=64, stride=32, validation_window=33, edge_search="full-frame"
        ),
    )
    assert local.edge_geometry == full.edge_geometry


def test_search_uses_no_values_outside_supplied_discovery_and_rejects_bad_support():
    y, x = np.mgrid[:8, :8]
    coords = np.column_stack((x.ravel() / 4 - 1, y.ravel() / 4 - 1))
    values = (coords[:, 0] + coords[:, 1] > 0.8).astype(float)
    a = search_edge(values, coords, 2)
    assert all(np.isfinite(a))
    with pytest.raises(ValueError):
        best_threshold(values[:8], coords[:8], 0)
    with pytest.raises(ValueError):
        best_threshold(np.ones(16), np.zeros((16, 2)), 0)
    with pytest.raises(ValueError):
        search_edge(values, coords, 4)
