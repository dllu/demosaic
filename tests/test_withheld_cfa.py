"""No held-out pixels, parent output or hidden template may enter discovery."""

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import (
    fit_candidate,
    stratified_split,
    validate_candidate,
)


def scene(size=64):
    y, x = np.mgrid[:size, :size]
    colors = np.array([[0, 1], [1, 2]])[y % 2, x % 2]
    signal = 0.002 * np.cos(2 * np.pi * (x * 5 / size + y * 3 / size) + 0.7)
    return 0.02 + signal, colors


@pytest.mark.parametrize("nuisance,refinements", [("affine", 0), ("step", 0), ("step", 3)])
def test_discovery_is_invariant_to_arbitrary_withheld_values(nuisance, refinements):
    raw, colors = scene()
    mask = stratified_split(raw.shape, 17)
    first = fit_candidate(
        raw,
        colors,
        mask,
        shot=0.00128,
        read=6.5536e-6,
        nuisance=nuisance,
        edge_refinements=refinements,
    )
    damaged = raw.copy()
    damaged[~mask] = np.nan
    second = fit_candidate(
        damaged,
        colors,
        mask,
        shot=0.00128,
        read=6.5536e-6,
        nuisance=nuisance,
        edge_refinements=refinements,
    )
    assert first.frequencies_xy == second.frequencies_xy
    assert first.edge_index == second.edge_index
    assert first.edge_geometry == second.edge_geometry
    for key in ("background", "prediction", "noise_variance"):
        np.testing.assert_array_equal(getattr(first, key), getattr(second, key))


def test_native_phase_split_is_balanced_and_exhaustive():
    mask = stratified_split((64, 96), 22)
    for y in range(2):
        for x in range(2):
            assert mask[y::2, x::2].sum() == 64 * 96 // 8
    np.testing.assert_array_equal(mask, stratified_split((64, 96), 22))
    assert not np.array_equal(mask, stratified_split((64, 96), 23))


def test_fixed_prediction_is_validated_without_reselection():
    raw, colors = scene()
    mask = stratified_split(raw.shape, 17)
    candidate = fit_candidate(raw, colors, mask, shot=0.00128, read=6.5536e-6)
    np.testing.assert_allclose(candidate.prediction, raw, atol=2e-15)
    result = validate_candidate(candidate, raw, ~mask)
    assert result["weighted_SSE_improvement"] > 0 and result["validation_z"] > 0
    modified = raw.copy()
    modified[~mask] = candidate.background[~mask]
    other = validate_candidate(candidate, modified, ~mask)
    assert other["weighted_SSE_improvement"] < 0
    with pytest.raises(ValueError, match="disjoint"):
        validate_candidate(candidate, raw, mask)


def test_correctly_represented_step_has_no_periodic_residual():
    raw, colors = scene()
    x = np.mgrid[:64, :64][1]
    raw = 0.02 + 0.08 * (x >= 32)
    candidate = fit_candidate(
        raw, colors, stratified_split(raw.shape, 5), shot=0.00128, read=6.5536e-6, nuisance="step"
    )
    np.testing.assert_allclose(candidate.background, raw, atol=2e-15)
    np.testing.assert_allclose(candidate.prediction, raw, atol=2e-15)
