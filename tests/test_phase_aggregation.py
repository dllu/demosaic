"""Measurement-kernel parity, actual withholding, edge/color isolation and adoption."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import (
    LocalWaveConfig,
    conditional_scores,
    fit_local_candidate,
    restore_local_waves,
)
from demosaic.phase_aggregation import (
    PhaseAggregateConfig,
    PhaseAggregateOperator,
    aggregate_candidate,
    conditional_null_projection,
    restore_phase_aggregation,
)

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
GEOMETRY = LocalWaveConfig(
    window=32,
    stride=16,
    validation_window=17,
    validation_stride=8,
    edge_refinements=0,
    frequency_refinements=0,
)
CONFIG = PhaseAggregateConfig(bins=16, window=17, query_stride=8)


def scene(layout=LAYOUTS[0], shape=(32, 32)):
    yy, xx = np.indices(shape)
    layout = np.asarray(layout)
    colors = np.tile(layout.reshape(2, 2), (shape[0] // 2, shape[1] // 2))
    signal = 0.03 + 0.003 * np.cos(2 * np.pi * (3 * xx + 2 * yy) / 32)
    signal += 0.0015 * np.cos(2 * np.pi * (-2 * xx + 4 * yy) / 32 + 0.7)
    rgb = np.array([0.8, 1.0, 0.6])[:, None, None] * signal
    raw = rgb[colors, yy, xx]
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    return raw, colors, rgb, packed, layout


def fixed(colors):
    return SimpleNamespace(
        discovery_mask=stratified_split(colors.shape, 71),
        frequencies_xy=((3 / 32, 2 / 32), (-2 / 32, 4 / 32)),
        variance_cfa=np.linspace(1, 2, colors.size).reshape(colors.shape),
        edge_geometry=(0.0, 0.0),
    )


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("direction", [0, 1])
def test_phase_average_matches_direct_measurement_weights(layout, direction):
    raw, colors, _, _, _ = scene(layout)
    candidate = fixed(colors)
    operator = PhaseAggregateOperator(candidate, colors, direction, CONFIG)
    actual = operator.apply(raw)
    y, x = 16, 16  # A spatial query-grid point; no spatial interpolation ambiguity.
    yy, xx = np.indices(raw.shape)
    f = candidate.frequencies_xy[direction]
    phase = np.remainder(xx * f[0] + yy * f[1], 1) * CONFIG.bins
    b, a = np.floor(phase).astype(int), phase % 1
    qb, qa = b[y, x], a[y, x]

    def kernel(delta):
        delta = (delta + CONFIG.bins // 2) % CONFIG.bins - CONFIG.bins // 2
        return np.maximum(0, 3 - np.abs(delta)) / 9

    weight = (1 - qa) * ((1 - a) * kernel(qb - b) + a * kernel(qb - b - 1))
    weight += qa * ((1 - a) * kernel(qb + 1 - b) + a * kernel(qb - b))
    region = (np.abs(yy - y) <= 8) & (np.abs(xx - x) <= 8)
    side = (xx >= 16) == (x >= 16)
    for color in range(3):
        selected = candidate.discovery_mask & region & side & (colors == color)
        precision = 1 / candidate.variance_cfa[selected]
        phase_weights = precision * weight[selected]
        expected = (
            np.dot(raw[selected], phase_weights) / phase_weights.sum()
            - np.dot(raw[selected], precision) / precision.sum()
        )
        np.testing.assert_allclose(actual[color, y, x], expected, atol=4e-17, rtol=1e-12)


def test_constant_per_color_is_annihilated_and_other_colors_cannot_enter():
    raw, colors, _, _, _ = scene()
    operator = PhaseAggregateOperator(fixed(colors), colors, 0, CONFIG)
    constants = np.array([0.1, 0.3, -0.2])[colors]
    np.testing.assert_allclose(operator.apply(constants), 0, atol=3e-15)
    first = operator.apply(raw)
    changed = raw.copy()
    changed[colors == 2] *= 1000
    second = operator.apply(changed)
    np.testing.assert_array_equal(first[:2], second[:2])


def test_operator_is_linear_excludes_withheld_values_and_stops_at_edge():
    raw, colors, _, _, _ = scene()
    candidate = fixed(colors)
    operator = PhaseAggregateOperator(candidate, colors, 0, CONFIG)
    first = operator.apply(raw)
    damaged = raw.copy()
    damaged[~candidate.discovery_mask] = np.nan
    np.testing.assert_array_equal(operator.apply(damaged), first)
    other = raw.copy()
    other[:, :16] += 100
    np.testing.assert_array_equal(operator.apply(other)[..., 16:], first[..., 16:])
    np.testing.assert_allclose(
        operator.apply(2 * raw - 3 * raw**2), 2 * first - 3 * operator.apply(raw**2), atol=1e-16
    )


@pytest.mark.parametrize("layout", LAYOUTS)
def test_projection_matches_validation_null_and_annihilates_its_full_span(layout):
    raw, colors, _, _, _ = scene(layout)
    split = stratified_split(raw.shape, 71)
    candidate = fit_local_candidate(raw, colors, split, shot=0.00008, read=2.56e-8, config=GEOMETRY)
    for direction in (0, 1):
        projected = conditional_null_projection(candidate, raw, colors, direction)
        np.testing.assert_array_equal(projected, candidate.conditional_null_cfa[direction])
        damaged = raw.copy()
        damaged[~split] = np.nan
        np.testing.assert_array_equal(
            conditional_null_projection(candidate, damaged, colors, direction), projected
        )
        start, stop = candidate.wave_slices[direction]
        keep = np.ones(candidate.design.shape[1], bool)
        keep[start:stop] = False
        design = candidate.design[:, keep]
        rng = np.random.default_rng(42)
        nuisance = np.empty(raw.size)
        for color in range(3):
            selected = (colors == color).ravel()
            nuisance[selected] = design[selected] @ rng.normal(size=design.shape[1])
        nuisance = nuisance.reshape(raw.shape)
        residual = nuisance - conditional_null_projection(candidate, nuisance, colors, direction)
        operator = PhaseAggregateOperator(candidate, colors, direction, CONFIG)
        np.testing.assert_allclose(operator.apply(residual), 0, atol=4e-14)
        # The original difference of means does not itself remove affine/step nuisance.
        assert np.max(np.abs(operator.apply(nuisance))) > 1e-4


@pytest.mark.parametrize("layout", LAYOUTS)
def test_all_aggregate_predictors_exclude_actual_withheld_pixels(layout):
    raw, colors, _, _, _ = scene(layout)
    split = stratified_split(raw.shape, 71)
    candidate = fit_local_candidate(raw, colors, split, shot=0.00008, read=2.56e-8, config=GEOMETRY)
    first = aggregate_candidate(candidate, raw, colors, CONFIG)
    damaged = raw.copy()
    damaged[~split] = np.nan
    second = aggregate_candidate(candidate, damaged, colors, CONFIG)
    np.testing.assert_array_equal(first[1], second[1])
    for a, b in zip(first[2], second[2], strict=True):
        np.testing.assert_array_equal(a.full_cfa, b.full_cfa)
    scores = conditional_scores(first[2][0], raw, colors, ~split, window=17, stride=8)
    damaged = raw.copy()
    damaged[split] = np.nan
    repeated = conditional_scores(first[2][0], damaged, colors, ~split, window=17, stride=8)
    for a, b in zip(scores, repeated, strict=True):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_exact_parent_is_not_doubled_and_H1_control_matches_existing_stage(layout):
    _, _, rgb, packed, layout = scene(layout)
    outputs, _ = restore_phase_aggregation(
        rgb,
        packed,
        layout,
        shot=0.00008,
        read=2.56e-8,
        geometry_config=GEOMETRY,
        aggregation_config=CONFIG,
    )
    for mode in ("global", "local"):
        for t in (0.0, 2.0, 4.0):
            np.testing.assert_array_equal(outputs[mode, t], rgb)
    parent = rgb * 0.4
    outputs, _ = restore_phase_aggregation(
        parent,
        packed,
        layout,
        shot=0.00008,
        read=2.56e-8,
        geometry_config=GEOMETRY,
        aggregation_config=CONFIG,
    )
    expected, _ = restore_local_waves(
        parent,
        packed,
        layout,
        shot=0.00008,
        read=2.56e-8,
        config=GEOMETRY,
        thresholds=(0.0, 2.0, 4.0),
    )
    for (mode, t), value in expected.items():
        np.testing.assert_array_equal(outputs["H1-" + mode, t], value)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_even_boundary_axes_and_ADC_identity(layout):
    _, _, rgb, packed, layout = scene(layout, shape=(34, 38))
    outputs, aux = restore_phase_aggregation(
        rgb * 0.7,
        packed,
        layout,
        shot=0.00008,
        read=2.56e-8,
        geometry_config=GEOMETRY,
        aggregation_config=CONFIG,
        thresholds=(2.0,),
    )
    assert aux["patches"] == 4
    assert all(v.shape == rgb.shape and np.isfinite(v).all() for v in outputs.values())
    outputs, aux = restore_phase_aggregation(
        rgb, packed, layout, shot=0.0, read=0.0, geometry_config=GEOMETRY
    )
    assert aux["identity_zero_noise"] and aux["patches"] == 0
    for value in outputs.values():
        np.testing.assert_array_equal(value, rgb)
    # The production256 minimum still applies before a no-noise bypass.
    with pytest.raises(ValueError):
        restore_phase_aggregation(rgb, packed, layout, shot=0.0, read=0.0)


@pytest.mark.parametrize(
    "kwargs", [{"bins": 0}, {"window": 4}, {"query_stride": 0}, {"edge_stopping": 1}]
)
def test_invalid_kernel_geometry_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PhaseAggregateConfig(**kwargs)


def test_invalid_CFA_and_unsupported_harmonics_are_rejected():
    _, _, rgb, packed, layout = scene()
    for colors, geometry in [
        (np.array([0, 0, 0, 0]), GEOMETRY),
        (layout, replace(GEOMETRY, harmonics=3)),
    ]:
        with pytest.raises(ValueError):
            restore_phase_aggregation(
                rgb, packed, colors, shot=0.01, read=0, geometry_config=geometry
            )
