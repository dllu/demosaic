import numpy as np

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate, restore_local_waves
from demosaic.matched_query_evidence import matched_contrast


def test_contrast_rejects_nuisance_with_a_fixed_validation_design():
    x = np.linspace(-1, 1, 64)
    nuisance = np.column_stack((np.ones_like(x), x, x > 0))
    signal = np.cos(18 * x) + nuisance @ np.array([3, -6, 2])
    y = np.sin(x * 8) + 0.5 * signal
    shifted = y + nuisance @ np.array([12, -10, 5])
    observed = matched_contrast(shifted, signal, nuisance)
    np.testing.assert_allclose(observed, matched_contrast(y, signal, nuisance), atol=1e-12)
    assert observed > 0
    assert matched_contrast(y, nuisance[:, 1], nuisance) == 0


def test_optional_contrasts_preserve_existing_refit_inputs_and_output():
    yy, xx = np.indices((64, 64))
    values = 0.11 + 0.014 * np.cos(2 * np.pi * (xx * 0.11 + yy * 0.045))
    packed = values.reshape(32, 2, 32, 2).transpose(1, 3, 0, 2).reshape(4, 32, 32)
    parent = np.full((3, 64, 64), 0.11, np.float64)
    colors = np.array([0, 1, 1, 2])
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": LocalWaveConfig(window=64, stride=64, validation_window=33, validation_stride=8),
        "guide_frequencies_xy": ((0.11, 0.045), (0.045, -0.11)),
        "active_guide_directions": [True, False],
        "phase_bins": 8,
        "shrink_phase_fit": True,
        "compare_pooled_support": True,
        "compare_pooled_refit": True,
    }
    baseline, details = restore_local_waves(parent, packed, colors, **options)
    tested, records = restore_local_waves(
        parent, packed, colors, compare_matched_refit=True, **options
    )
    assert details["records"] == records["records"]
    for key, old in baseline.items():
        np.testing.assert_array_equal(tested[key], old)
    assert np.linalg.norm(tested["orthogonal-refit", 2] - parent) > 0.1


def test_query_parallel_boundaries_are_fit_on_discovery_measurements_only():
    yy, xx = np.indices((96, 96))
    axis = 0.75 * (xx - 47.5) + 0.66 * (yy - 47.5)
    raw = 0.08 + 0.12 * ((axis > -5) & (axis < 7))
    colors = np.tile(np.array([[0, 1], [1, 2]]), (48, 48))
    discovery = stratified_split(raw.shape, 578)
    config = LocalWaveConfig(
        window=96, stride=96, edge_search="full-frame", background="parallel_step"
    )
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": config,
        "phase_bins": 8,
        "guide_frequencies_xy": ((0.083, 0.047), (-0.047, 0.083)),
    }
    actual = fit_local_candidate(raw, colors, discovery, **options)
    edited = np.where(discovery, raw, np.nan)
    control = fit_local_candidate(edited, colors, discovery, **options)
    assert actual.parallel_edges is not None
    assert actual.parallel_edges == control.parallel_edges
    np.testing.assert_array_equal(actual.full_cfa, control.full_cfa)
    assert actual.wave_slices[0][0] == 5
    rail_mask = (axis > -3) & (axis < 5)
    assert np.max(np.abs(actual.full_cfa[rail_mask] - raw[rail_mask])) < 0.01
