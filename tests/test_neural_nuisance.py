"""Actual withholding, same-phase inputs, nuisance recovery and matched controls."""

from dataclasses import replace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate, restore_local_waves
from demosaic.neural_nuisance import (
    WithheldBackground,
    conditional_components,
    fit_neural_candidate,
    masked_packed_input,
    restore_neural_nuisance,
)

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
CONFIG = LocalWaveConfig(
    window=64,
    stride=32,
    validation_window=33,
    validation_stride=8,
    edge_refinements=1,
    frequency_refinements=1,
)


def scene(layout=LAYOUTS[0], shape=(64, 64)):
    yy, xx = np.indices(shape)
    colors = np.tile(np.asarray(layout).reshape(2, 2), (shape[0] // 2, shape[1] // 2))
    level = 0.03 + 0.02 * (xx > 20) + 0.01 * (yy > 38) + 0.005 * (xx + yy > 75)
    background = np.array([0.8, 1.0, 0.6])[:, None, None] * level
    signal = 0.003 * np.cos(2 * np.pi * (5 * xx + 3 * yy) / 64 + 0.2)
    signal += 0.0015 * np.cos(2 * np.pi * (-4 * xx + 7 * yy) / 64 - 0.5)
    rgb = background + np.array([0.8, 1.0, 0.6])[:, None, None] * signal
    raw = rgb[colors, yy, xx]
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    return raw, colors, rgb, packed, background


@pytest.mark.parametrize("layout", LAYOUTS)
def test_neural_nuisance_excludes_withheld_RAW_and_keeps_shared_proxy(layout):
    raw, colors, _, _, background = scene(layout)
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    field = WithheldBackground(background, mask)
    candidate = fit_neural_candidate(raw, colors, reference, field, config=CONFIG)
    damaged = raw.copy()
    damaged[~mask] = np.nan
    repeated_reference = fit_local_candidate(
        damaged, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    repeated = fit_neural_candidate(damaged, colors, repeated_reference, field, config=CONFIG)
    assert candidate.frequencies_xy == repeated.frequencies_xy
    assert candidate.edge_geometry == reference.edge_geometry
    np.testing.assert_array_equal(candidate.variance_cfa, reference.variance_cfa)
    for name in ["design", "coefficients", "full_cfa", "conditional_null_cfa", "variance_cfa"]:
        np.testing.assert_array_equal(getattr(candidate, name), getattr(repeated, name))
    for a, b in zip(candidate.operators, repeated.operators, strict=True):
        np.testing.assert_array_equal(a, b)


def test_known_independent_background_recovers_two_waves_beyond_one_step():
    raw, colors, _, _, background = scene()
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    candidate = fit_neural_candidate(
        raw, colors, reference, WithheldBackground(background, mask), config=CONFIG
    )
    assert np.mean((candidate.full_cfa[~mask] - raw[~mask]) ** 2) < 0.05 * np.mean(
        (reference.full_cfa[~mask] - raw[~mask]) ** 2
    )
    expected = np.array([[5, 3], [-4, 7]]) / 64
    for frequency in candidate.frequencies_xy:
        assert (
            min(min(np.linalg.norm(frequency - f), np.linalg.norm(frequency + f)) for f in expected)
            < 0.6 / 64
        )


def test_neural_coordinate_uses_own_color_and_known_sensor_white_only():
    raw, colors, _, _, background = scene()
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    first = fit_neural_candidate(
        raw, colors, reference, WithheldBackground(background, mask), config=CONFIG
    )
    changed = background.copy()
    changed[2, 12:22, 10:20] = 2.0
    changed[2, :8, :8] = -0.01
    second = fit_neural_candidate(
        raw, colors, reference, WithheldBackground(changed, mask), config=CONFIG
    )
    assert first.frequencies_xy == second.frequencies_xy
    for color in [0, 1]:
        np.testing.assert_array_equal(first.operators[color], second.operators[color])
        np.testing.assert_array_equal(first.coefficients[color], second.coefficients[color])
    yy, xx = np.indices(raw.shape)
    np.testing.assert_array_equal(
        second.design[:, reference.wave_slices[0][0]],
        np.minimum(changed[colors, yy, xx], 1).ravel(),
    )


def test_mismatched_background_mask_is_rejected_before_fitting():
    raw, colors, _, _, background = scene()
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    with pytest.raises(ValueError, match="background/mask"):
        fit_neural_candidate(
            raw, colors, reference, WithheldBackground(background, ~mask), config=CONFIG
        )


@pytest.mark.parametrize("layout", LAYOUTS)
def test_delivered_conditional_component_is_the_tested_full_minus_null(layout):
    raw, colors, rgb, _, background = scene(layout)
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    field = WithheldBackground(background, mask)
    neural = fit_neural_candidate(raw, colors, reference, field, config=CONFIG)
    yy, xx = np.indices(raw.shape)
    for candidate, used in [(reference, None), (neural, field)]:
        components, fractions, spectra = conditional_components(
            candidate, np.zeros_like(rgb), raw, colors, used
        )
        assert np.all(fractions >= 0) and np.all(fractions <= 1 + 1e-10)
        assert np.all(spectra >= -1e-10) and np.all(spectra <= 1 + 1e-10)
        for direction in range(2):
            actual = components[direction, colors, yy, xx]
            np.testing.assert_allclose(
                actual, candidate.full_cfa - candidate.conditional_null_cfa[direction], atol=2e-13
            )
        damaged = raw.copy()
        damaged[~mask] = np.nan
        repeated = conditional_components(candidate, np.zeros_like(rgb), damaged, colors, used)[0]
        np.testing.assert_array_equal(components, repeated)
        # A half parent leaves half of the unique conditional component.
        half = conditional_components(candidate, rgb * 0.5, raw, colors, used)[0]
        np.testing.assert_allclose(half, components * 0.5, atol=2e-13)


def test_masked_input_preserves_measured_signed_values_excludes_B_and_colors():
    raw = np.random.default_rng(1).normal(0.0, 0.01, (64, 64)).astype(np.float32)
    mask = stratified_split(raw.shape, 71)
    first = masked_packed_input(raw, mask)
    damaged = raw.copy()
    damaged[~mask] = np.nan
    np.testing.assert_array_equal(first, masked_packed_input(damaged, mask))
    for phase in range(4):
        y, x = divmod(phase, 2)
        np.testing.assert_array_equal(
            first[phase][mask[y::2, x::2]], raw[y::2, x::2][mask[y::2, x::2]]
        )
    changed = raw.copy()
    changed[::2, ::2] += 1
    np.testing.assert_array_equal(first[1:], masked_packed_input(changed, mask)[1:])


def test_input_fill_fallback_uses_only_own_phase_A_mean():
    raw = np.full((64, 64), np.nan)
    mask = np.zeros((64, 64), bool)
    for y in range(2):
        for x in range(2):
            mask[y, x] = True
            raw[y, x] = -0.02 + (2 * y + x) * 0.003
    result = masked_packed_input(raw, mask)
    for phase in range(4):
        np.testing.assert_allclose(result[phase], -0.02 + phase * 0.003, atol=1e-16)
    mask[:] = False
    with pytest.raises(ValueError, match="Every CFA phase"):
        masked_packed_input(raw, mask)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_matched_global_mask_H1_and_exact_parent_identity(layout):
    _, _, rgb, packed, background = scene(layout)
    mask = stratified_split(rgb.shape[1:], 71)
    fields = (WithheldBackground(background, mask), WithheldBackground(background, ~mask))
    exact, _ = restore_neural_nuisance(
        rgb, packed, np.array(layout), fields, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    for value in exact.values():
        np.testing.assert_array_equal(value, rgb)
    parent = rgb * 0.5
    values, _ = restore_neural_nuisance(
        parent, packed, np.array(layout), fields, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    expected, _ = restore_local_waves(
        parent,
        packed,
        np.array(layout),
        shot=0.00008,
        read=2.56e-8,
        config=CONFIG,
        thresholds=(0.0, 2.0, 4.0),
        discovery_mask=mask,
    )
    for (mode, t), value in expected.items():
        np.testing.assert_array_equal(values["H1-" + mode, t], value)


def test_ADC_identity_without_neural_fields_and_complement_guard():
    _, _, rgb, packed, background = scene()
    values, aux = restore_neural_nuisance(
        rgb, packed, np.array(LAYOUTS[0]), None, shot=0.0, read=0.0, config=CONFIG
    )
    assert aux["identity_zero_noise"]
    for value in values.values():
        np.testing.assert_array_equal(value, rgb)
    mask = stratified_split(rgb.shape[1:], 71)
    same = WithheldBackground(background, mask)
    with pytest.raises(ValueError, match="complementary"):
        restore_neural_nuisance(
            rgb,
            packed,
            np.array(LAYOUTS[0]),
            (same, same),
            shot=0.00008,
            read=2.56e-8,
            config=CONFIG,
        )


def test_background_owns_immutable_copy_and_rejects_bad_native_axes():
    rgb = np.ones((3, 64, 64), np.float32)
    mask = stratified_split((64, 64), 71)
    field = WithheldBackground(rgb, mask)
    rgb[:] = 0
    mask[:] = False
    assert field.rgb.all() and field.discovery_mask.any()
    assert not field.rgb.flags.writeable and not field.discovery_mask.flags.writeable
    with pytest.raises(ValueError):
        WithheldBackground(np.ones((3, 32, 32)), np.ones((32, 32), np.uint8))
    with pytest.raises(ValueError):
        masked_packed_input(np.ones((31, 32)), np.zeros((31, 32), bool))
    raw, colors, _, _, background = scene()
    mask = stratified_split(raw.shape, 71)
    reference = fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG)
    with pytest.raises(ValueError):
        fit_neural_candidate(
            raw,
            colors,
            reference,
            WithheldBackground(background, mask),
            config=replace(CONFIG, harmonics=3),
        )
