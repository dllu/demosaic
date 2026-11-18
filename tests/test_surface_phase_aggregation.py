from types import SimpleNamespace

import numpy as np

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.phase_aggregation import PhaseAggregateConfig
from demosaic.surface_phase_aggregation import (
    SurfacePhaseOperator,
    bound_phase_average,
    bound_phase_average_locally,
)


def test_tangent_kernel_agrees_with_direct_phase_weights_inside_rail():
    yy, xx = np.indices((64, 64))
    colors = np.tile([[0, 1], [1, 2]], (32, 32))
    raw = 0.1 + 0.006 * np.cos(2 * np.pi * (0.08 * xx + 0.05 * yy))
    mask = stratified_split(raw.shape, 529)
    candidate = SimpleNamespace(
        discovery_mask=mask,
        frequencies_xy=((0.08, 0.05), (-0.04, 0.09)),
        variance_cfa=0.01 + 0.0002 * xx,
        edge_geometry=(0.0, 0.0),
        parallel_edges=(0.0, -0.33, 0.33),
    )
    config = PhaseAggregateConfig(bins=24, window=49, query_stride=8)
    op = SurfacePhaseOperator(candidate, colors, 0, config, tangent=True)
    actual = op.apply(raw)
    np.testing.assert_array_equal(np.unique(op.side), [0, 1, 2])
    changed = raw.copy()
    changed[op.side != 1] += 100
    changed[~mask] = np.nan
    np.testing.assert_array_equal(actual[:, op.side == 1], op.apply(changed)[:, op.side == 1])

    phase = np.mod(xx * 0.08 + yy * 0.05, 1) * config.bins
    floor = np.floor(phase).astype(int)
    part = phase - floor
    qfloor, qpart = floor[32, 32], part[32, 32]
    weight = np.zeros(raw.shape)
    for q in (0, 1):
        for p in (0, 1):
            offset = (qfloor + q - floor - p + config.bins // 2) % config.bins - config.bins // 2
            weight += (
                (qpart if q else 1 - qpart)
                * (part if p else 1 - part)
                * np.maximum(0, 3 - np.abs(offset))
            )
    normal = np.array([0.08, 0.05]) / np.hypot(0.08, 0.05)
    minor = config.window / np.sqrt(2 * np.pi)
    along = (normal[1] * (xx - 32) - normal[0] * (yy - 32)) / (minor * 2)
    across = (normal[0] * (xx - 32) + normal[1] * (yy - 32)) / minor
    region = (op.side == 1) & (along**2 + across**2 <= 1) & mask
    for color in range(3):
        keep = region & (colors == color)
        precision = 1 / candidate.variance_cfa[keep]
        expected = np.average(raw[keep], weights=precision * weight[keep]) - np.average(
            raw[keep], weights=precision
        )
        np.testing.assert_allclose(actual[color, 32, 32], expected, atol=1e-16)


def test_phase_averaging_preserves_the_paired_predictive_refit():
    yy, xx = np.indices((64, 64))
    raw = 0.07 + 0.05 * (xx > 35) + 0.012 * np.cos(2 * np.pi * (0.103 * xx + 0.046 * yy))
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    parent = np.full((3, 64, 64), 0.07)
    colors = np.array([0, 1, 1, 2])
    cfg = LocalWaveConfig(window=64, stride=64, validation_window=33, validation_stride=8)
    settings = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "guide_frequencies_xy": ((0.103, 0.046), (-0.046, 0.103)),
        "phase_bins": 8,
        "shrink_phase_fit": True,
        "config": cfg,
        "compare_pooled_support": True,
        "compare_pooled_refit": True,
        "active_guide_directions": [True, False],
        "phase_edge_side": "validation",
    }
    original, _ = restore_local_waves(parent, packed, colors, **settings)
    actual, _ = restore_local_waves(parent, packed, colors, compare_phase_averages=True, **settings)
    for key, result in original.items():
        np.testing.assert_array_equal(actual[key], result)
    assert np.linalg.norm(actual["tangent-average", 2] - parent) > 0.1


def test_bound_operates_in_each_color_and_keeps_the_smaller_estimate_exact():
    parent = np.full((3, 24, 32), 0.125, dtype=np.float32)
    old = parent + np.array([0, 0.001, -0.003], dtype=np.float32)[:, None, None]
    proposed = parent + np.array([0.001, -0.01, 0.0025], dtype=np.float32)[:, None, None]
    result = bound_phase_average(parent, old, proposed)
    np.testing.assert_array_equal(result[0], parent[0])
    np.testing.assert_allclose(result[1], parent[1] - 0.001, atol=8e-9)
    np.testing.assert_array_equal(result[2], proposed[2])


def test_local_peak_bound_keeps_each_color_in_its_signed_neighborhood():
    parent = np.zeros((3, 8, 8))
    wave = parent.copy()
    wave[0, 3, 3], wave[1, 3, 3], wave[1, 3, 4] = 3, -2, 1
    tangent = np.ones_like(wave) * 10
    tangent[0, 3, 2] = -1
    tangent[1, 3, 3] = -10
    measured = bound_phase_average_locally(parent, wave, tangent, peak_window=3)
    assert measured[0, 3, 2] == 0
    assert measured[0, 3, 3] == 3
    assert measured[0, 3, 5] == 0
    assert measured[1, 3, 3] == -2
    assert measured[1, 3, 4] == 1
    np.testing.assert_array_equal(measured[2], 0)


def test_energy_bound_holds_inside_every_clipped_window():
    rng = np.random.default_rng(779)
    parent = np.full((3, 13, 15), 0.1)
    wave = rng.normal(size=parent.shape) / 100
    wave[:2, 2:7, :5] = 0
    proposed = rng.normal(size=parent.shape) / 80
    result = bound_phase_average_locally(
        parent, parent + wave, parent + proposed, peak_window=3, energy_window=5
    )
    delta = result - parent
    for y in range(13):
        for x in range(15):
            local = np.s_[:, max(0, y - 2) : y + 3, max(0, x - 2) : x + 3]
            assert np.all(
                np.sum(delta[local] ** 2, axis=(1, 2))
                <= np.sum(wave[local] ** 2, axis=(1, 2)) + 1e-16
            )
