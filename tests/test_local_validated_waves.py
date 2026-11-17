"""Actual held-out invariance, color/direction validation and parent replacement."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import demosaic.local_validated_waves as local
from demosaic.donor_phase_support import ALL_HARMONICS, donor_harmonic_scores
from demosaic.experiments.evaluation.withheld import stratified_split

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
CONFIG = local.LocalWaveConfig(window=64, stride=32, edge_refinements=1, frequency_refinements=1)


def scene(layout=LAYOUTS[0], size=64):
    y, x = np.mgrid[:size, :size]
    signal = 0.03 + 0.003 * np.cos(2 * np.pi * (5 * x + 3 * y) / size + 0.2)
    signal += 0.0015 * np.cos(2 * np.pi * (-4 * x + 7 * y) / size - 0.5)
    rgb = np.array([0.8, 1.0, 0.6])[:, None, None] * signal
    colors = np.tile(np.array(layout).reshape(2, 2), (size // 2, size // 2))
    raw = rgb[colors, y, x]
    return raw, colors, rgb


def test_guided_query_refits_phase_from_only_its_discovery_samples():
    raw, colors, _ = scene()
    frequencies = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    mask = stratified_split(raw.shape, 81)
    options = {
        "shot": 0.00008,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": frequencies,
    }
    original = local.fit_local_candidate(raw, colors, mask, **options)
    corrupted = local.fit_local_candidate(np.where(mask, raw, np.nan), colors, mask, **options)
    assert original.frequencies_xy == frequencies
    np.testing.assert_array_equal(original.coefficients, corrupted.coefficients)
    np.testing.assert_array_equal(original.conditional_null_cfa, corrupted.conditional_null_cfa)
    # Donor phase is absent from the API. A translated query must fit changed
    # sine/cosine amplitudes without changing either supplied direction.
    translated = np.roll(raw, 2, axis=1)
    changed = local.fit_local_candidate(translated, colors, mask, **options)
    assert changed.frequencies_xy == frequencies
    np.testing.assert_allclose(changed.full_cfa, translated, rtol=0, atol=1e-12)
    assert not np.allclose(original.coefficients[:, -4:], changed.coefficients[:, -4:])


def test_all_knot_harmonics_span_the_existing_discovery_model():
    raw, colors, _ = scene()
    split = stratified_split(raw.shape, 81)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": ((5 / 64, 3 / 64), (-4 / 64, 7 / 64)),
        "phase_bins": 8,
    }
    knot = local.fit_local_candidate(raw, colors, split, **options)
    modes = local.fit_local_candidate(raw, colors, split, phase_harmonics=ALL_HARMONICS, **options)
    np.testing.assert_allclose(modes.full_cfa, knot.full_cfa, rtol=0, atol=1e-13)
    np.testing.assert_allclose(
        modes.conditional_null_cfa, knot.conditional_null_cfa, rtol=0, atol=1e-13
    )
    np.testing.assert_allclose(
        local.phase_fit_reliability(modes, colors),
        local.phase_fit_reliability(knot, colors),
        rtol=0,
        atol=1e-13,
    )


def test_donor_support_requires_the_actual_higher_harmonic():
    _, colors, _ = scene()
    yy, xx = np.indices(colors.shape)
    frequencies = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    first = local._phase_harmonic_columns(xx, yy, frequencies[0], 8, (1, 2))
    second = local._phase_harmonic_columns(xx, yy, frequencies[1], 8, (1,))
    baseline = 0.06 + second @ np.array([0.001, -0.002])
    data = baseline + first @ np.array([0.001, 0.002, 0.004, -0.001])
    noisy = data.reshape(colors.shape) + np.random.default_rng(120).normal(0, 0.001, colors.shape)
    scores = donor_harmonic_scores(noisy, colors, frequencies, shot=0, read=1e-6, config=CONFIG)
    np.testing.assert_array_equal((scores >= 3).all(axis=0), [[True, False, False], [False] * 3])


def test_refit_uses_measured_color_and_preserves_the_gate():
    raw, layout, rgb = scene()
    raw += np.random.default_rng(5).normal(0, 0.001, raw.shape)
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    parent = np.broadcast_to(rgb.mean(axis=(-2, -1), keepdims=True), rgb.shape).copy()
    config = replace(CONFIG, window=64, stride=64, validation_window=33, validation_stride=8)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": config,
        "guide_frequencies_xy": ((5 / 64, 3 / 64), (-4 / 64, 7 / 64)),
        "phase_bins": 8,
    }
    for compare in (False, True):
        values, stats = local.restore_local_waves(
            parent,
            packed,
            LAYOUTS[0],
            **options,
            shrink_phase_fit=True,
            compare_pooled_support=True,
            compare_pooled_refit=compare,
            thresholds=(0, 1e3),
        )
        if not compare:
            control, original_stats = values, stats["records"]
    assert original_stats == stats["records"]
    for method, output in control.items():
        np.testing.assert_array_equal(values[method], output)
    for mode in ("all-site-refit", "weighted-refit"):
        np.testing.assert_array_equal(values[mode, 1e3], parent)
    assert np.max(abs(values["all-site-refit", 0] - parent)) > 1e-4
    assert np.max(abs(values["all-site-refit", 0] - values["weighted-refit", 0])) > 1e-6

    fold = stratified_split(raw.shape, config.split_seed)
    fit = local.fit_local_candidate(raw, layout, fold, **options)
    altered = raw.copy()
    altered[(layout == 1) & ~fold] += 0.002 * fit.unit_fields[0][(layout == 1) & ~fold, 0]
    scores = {0: np.zeros((3, *raw.shape))}
    first, _ = local._refit_phase_components(fit, raw, layout, parent, scores)
    second, focused = local._refit_phase_components(fit, altered, layout, parent, scores)
    assert np.max(abs(second[0, 1] - first[0, 1])) > 1e-4
    np.testing.assert_array_equal(second[:, [0, 2]], first[:, [0, 2]])
    np.testing.assert_allclose(second, focused, atol=1e-13, rtol=0)


def test_discovery_reliability_subtracts_fit_noise_and_shrinks_the_validated_prediction():
    raw, colors, _ = scene()
    split = stratified_split(raw.shape, 81)
    frequencies = ((0.078, 0.045), (-0.064, 0.108))
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": frequencies,
        "phase_bins": 8,
    }
    fit = local.fit_local_candidate(raw, colors, split, **options)
    damaged = local.fit_local_candidate(np.where(split, raw, np.nan), colors, split, **options)
    reliability = local.phase_fit_reliability(fit, colors)
    np.testing.assert_array_equal(reliability, local.phase_fit_reliability(damaged, colors))
    for direction in range(2):
        for color in range(3):
            samples = split & (colors == color)
            difference = fit.full_cfa[samples] - fit.conditional_null_cfa[direction, samples]
            energy = np.linalg.norm(difference / np.sqrt(fit.variance_cfa[samples])) ** 2
            expected = max(0, 1 - 7 / energy) if energy else 0
            assert reliability[direction, color] == pytest.approx(expected, abs=1e-14)
    _, observed = local.conditional_scores(fit, raw, colors, ~split, reliability=reliability)
    for direction in range(2):
        for color in range(3):
            samples = ~split & (colors == color)
            base = fit.conditional_null_cfa[direction, samples]
            delta = reliability[direction, color] * (fit.full_cfa[samples] - base)
            noise = np.sqrt(fit.variance_cfa[samples])
            norm = np.linalg.norm(delta / noise)
            if norm:
                similarity = np.dot((raw[samples] - base) / noise, delta / noise) / norm
                assert observed[direction, color] == pytest.approx(similarity - norm / 2)
            else:
                assert observed[direction, color] == 0
    zero = np.zeros_like(reliability)
    field, global_scores = local.conditional_scores(fit, raw, colors, ~split, reliability=zero)
    assert not field.any() and not global_scores.any()


def test_pooled_support_preserves_veto_and_can_admit_unequal_positive_scores():
    first = np.array([3.0, -1.0, 0.0, 1.5, 2.0, 1.0])
    second = np.array([3.0, 4.0, 3.0, 2.8, 1.0, -2.0])
    score = local.pooled_support_score(first, second)
    np.testing.assert_array_equal(score, local.pooled_support_score(second, first))
    np.testing.assert_allclose(score, [3, -1, 0, 2.15, 1.5, -2], rtol=0, atol=1e-14)
    np.testing.assert_array_equal(
        local.support_weight(score, 0), local.support_weight(np.minimum(first, second), 0)
    )
    assert local.support_weight(score, 2)[3] > 0
    assert local.support_weight(np.minimum(first, second), 2)[3] == 0


def test_phase_agreement_measures_interpolated_shape_and_preserves_phase_sign():
    a = np.array([[0.2, 0.3, -0.8, 0.4], [0.0, 0.2, 0.1, -0.1], [0.0, 0.0, 0.0, 0.0]])
    b = np.array([[0.1, -0.2, -0.3, 0.7], [0.0, -0.6, -0.3, 0.3], [1.0, 0.0, 0.0, 0.0]])
    x = np.linspace(0, 1, 10000, endpoint=False)
    phases = np.arange(5) / 5
    first, second = [np.interp(x, phases, np.r_[v, -v.sum()], period=1) for v in (a[0], b[0])]
    expected = first @ second / (np.linalg.norm(first) * np.linalg.norm(second))
    observed = local.phase_profile_agreement(a, b)
    np.testing.assert_allclose(observed, [expected, -1.0, 0.0], rtol=0, atol=2e-7)
    np.testing.assert_allclose(local.phase_profile_agreement(3 * b, a / 2), observed, atol=1e-14)


def test_joint_delivery_preserves_an_individual_color_veto(monkeypatch):
    import demosaic.joint_colour_evidence as joint

    raw, _, rgb = scene()
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    parent = np.broadcast_to(rgb.mean(axis=(-2, -1), keepdims=True), rgb.shape)

    def positive_joint(candidate, raw, *_args, **_kwargs):
        return np.full((len(candidate.unit_keys), *raw.shape), 4.0), None

    def green_only(candidate, raw, *_args, **_kwargs):
        field = np.zeros((len(candidate.unit_keys), 3, *raw.shape))
        field[:, 1] = 4.0
        return field, np.zeros((len(candidate.unit_keys), 3))

    monkeypatch.setattr(joint, "joint_conditional_scores", positive_joint)
    monkeypatch.setattr(local, "conditional_scores", green_only)
    result, _ = local.restore_local_waves(
        parent,
        packed,
        LAYOUTS[0],
        shot=8e-5,
        read=2.56e-8,
        config=CONFIG,
        guide_frequencies_xy=((5 / 64, 3 / 64), (-4 / 64, 7 / 64)),
        compare_pooled_support=True,
        compare_joint_colour_support=True,
    )
    full, guarded = result["joint", 2.0], result["joint-veto", 2.0]
    assert np.max(abs(full[[0, 2]] - parent[[0, 2]])) > 1e-4
    np.testing.assert_array_equal(guarded[[0, 2]], parent[[0, 2]])
    np.testing.assert_array_equal(guarded[1], full[1])


@pytest.mark.parametrize("orientation", ["along", "across"])
def test_oriented_validation_matches_direct_native_pixel_sums(orientation):
    raw, colors, _ = scene()
    split = stratified_split(raw.shape, 87)
    fit = local.fit_local_candidate(
        raw,
        colors,
        split,
        shot=8e-5,
        read=2.56e-8,
        config=CONFIG,
        guide_frequencies_xy=((0.078, 0.045), (-0.064, 0.108)),
    )
    window = 19
    local_scores, global_scores = local.conditional_scores(
        fit,
        raw,
        colors,
        ~split,
        window=window,
        stride=8,
        orientation=orientation,
    )
    _, square_global = local.conditional_scores(fit, raw, colors, ~split, window=window, stride=8)
    np.testing.assert_array_equal(global_scores, square_global)
    for direction, (fx, fy) in enumerate(fit.frequencies_xy):
        norm = np.hypot(fx, fy)
        for cy, cx in [(0, 0), (32, 24), (63, 63)]:
            y, x = np.mgrid[:64, :64]
            parallel = ((y - cy) * fx - (x - cx) * fy) / norm
            perpendicular = ((x - cx) * fx + (y - cy) * fy) / norm
            if orientation == "across":
                parallel, perpendicular = perpendicular, parallel
            region = (abs(parallel) <= window / np.sqrt(2)) & (
                abs(perpendicular) <= window / (2 * np.sqrt(2))
            )
            for color in range(3):
                good = region & ~split & (colors == color)
                full, base = fit.full_cfa[good], fit.conditional_null_cfa[direction, good]
                variance, value = fit.variance_cfa[good], raw[good]
                energy = np.sum((full - base) ** 2 / variance)
                numerator = np.sum(((value - base) ** 2 - (value - full) ** 2) / variance)
                expected = numerator / (2 * np.sqrt(energy)) if energy else 0.0
                assert local_scores[direction, color, cy, cx] == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_donor_half_frequency_requires_measured_long_repeat(layout):
    y, x = np.mgrid[:64, :64]
    colors = np.tile(np.asarray(layout).reshape(2, 2), (32, 32))
    guides = np.array([[10 / 64, 4 / 64], [-4 / 64, 10 / 64]])

    def signal(f):
        return np.cos(2 * np.pi * (x * f[0] + y * f[1]) + 0.4)

    raw = 0.12 + 0.01 * signal(guides[0]) + 0.008 * signal(guides[1])
    raw += np.random.default_rng(93).normal(0, 0.001, raw.shape)
    options = {"shot": 0.0, "read": 1e-6, "config": CONFIG}
    original = local.donor_subharmonic_scores(raw, colors, guides, **options)
    longer = local.donor_subharmonic_scores(
        raw + 0.003 * signal(guides[1] / 2), colors, guides, **options
    )
    assert np.max(original) < 3.0
    assert np.min(longer[:, 1]) > 10.0
    assert np.max(longer[:, 0]) < 3.0


@pytest.mark.parametrize("layout", LAYOUTS)
def test_phase_bins_recover_periodic_profile_and_ignore_withheld_measurements(layout):
    height = width = 64
    y, x = np.mgrid[:height, :width]
    directions = ((0.078, 0.045), (-0.064, 0.108))
    positions = np.arange(8) / 8
    profiles = (
        ([0, 0, -3, 2, 1, 0, 0, 0], [0, 1, 0, 0, 0, 0, -1, 0]),
        ([0, 1, -5, 3, 0, 1, 0, 0], [-1, 0, 0, 2, 0, -1, 0, 0]),
        ([0, 0, -1, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, -2, 1]),
    )
    rgb = np.stack(
        [
            0.04
            + 0.001
            * sum(
                np.interp(fx * x + fy * y, positions, profile, period=1)
                for (fx, fy), profile in zip(directions, channel, strict=True)
            )
            for channel in profiles
        ]
    )
    colors = np.tile(np.asarray(layout).reshape(2, 2), (height // 2, width // 2))
    raw = rgb[colors, y, x]
    split = stratified_split(raw.shape, 81)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": directions,
        "phase_bins": 8,
    }
    first = local.fit_local_candidate(raw, colors, split, **options)
    destroyed = local.fit_local_candidate(np.where(split, raw, np.nan), colors, split, **options)
    np.testing.assert_allclose(first.full_cfa, raw, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(first.full_cfa, destroyed.full_cfa)
    np.testing.assert_array_equal(first.conditional_null_cfa, destroyed.conditional_null_cfa)
    assert np.max(np.abs(first.full_cfa - first.conditional_null_cfa[0])) > 0.001
    assert np.max(np.abs(first.full_cfa - first.conditional_null_cfa[1])) > 0.001
    options.pop("guide_frequencies_xy")
    with pytest.raises(ValueError, match="fixed guides"):
        local.fit_local_candidate(raw, colors, split, **options)


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("harmonics", [1, 3])
@pytest.mark.parametrize(
    "support_unit,background",
    [("direction", "step"), ("harmonic", "step"), ("harmonic", "piecewise_affine")],
)
def test_every_discovery_quantity_excludes_withheld_pixels(
    layout, harmonics, support_unit, background
):
    raw, colors, _ = scene(layout)
    mask = stratified_split(raw.shape, 71)
    config = replace(CONFIG, harmonics=harmonics, support_unit=support_unit, background=background)
    first = local.fit_local_candidate(raw, colors, mask, shot=0.00008, read=2.56e-8, config=config)
    destroyed = raw.copy()
    destroyed[~mask] = np.nan
    second = local.fit_local_candidate(
        destroyed, colors, mask, shot=0.00008, read=2.56e-8, config=config
    )
    assert first.frequencies_xy == second.frequencies_xy
    assert first.edge_geometry == second.edge_geometry
    for key in [
        "design",
        "coefficients",
        "full_cfa",
        "conditional_null_cfa",
        "variance_cfa",
    ]:
        np.testing.assert_array_equal(getattr(first, key), getattr(second, key))
    assert first.wave_slices == second.wave_slices
    assert first.unit_slices == second.unit_slices and first.unit_keys == second.unit_keys
    for a, b in zip(
        (*first.operators, *first.wave_fields, *first.unit_fields),
        (*second.operators, *second.wave_fields, *second.unit_fields),
        strict=True,
    ):
        np.testing.assert_array_equal(a, b)


def test_conditional_validation_cannot_borrow_the_stronger_direction():
    raw, colors, _ = scene()
    mask = stratified_split(raw.shape, 71)
    candidate = local.fit_local_candidate(
        raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    _, score = local.conditional_scores(candidate, raw, colors, ~mask)
    assert np.all(score > 0)
    changed = raw.copy()
    changed[~mask] = candidate.conditional_null_cfa[1, ~mask]
    _, reduced = local.conditional_scores(candidate, changed, colors, ~mask)
    assert np.all(reduced[1] < 0)
    assert reduced[0, 1] > 0
    with pytest.raises(ValueError, match="disjoint"):
        local.conditional_scores(candidate, raw, colors, mask)


def test_each_color_has_its_own_validation_evidence():
    raw, colors, _ = scene()
    mask = stratified_split(raw.shape, 71)
    candidate = local.fit_local_candidate(
        raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    maps, score = local.conditional_scores(candidate, raw, colors, ~mask)
    changed = raw.copy()
    blue = (~mask) & (colors == 2)
    changed[blue] = candidate.conditional_null_cfa[1, blue]
    new_maps, new_score = local.conditional_scores(candidate, changed, colors, ~mask)
    assert new_score[1, 2] < 0
    np.testing.assert_array_equal(new_score[:, :2], score[:, :2])
    np.testing.assert_array_equal(new_maps[:, :2], maps[:, :2])


def test_validation_does_not_read_discovery_values_again():
    raw, colors, _ = scene()
    mask = stratified_split(raw.shape, 71)
    candidate = local.fit_local_candidate(
        raw, colors, mask, shot=0.00008, read=2.56e-8, config=CONFIG
    )
    first = local.conditional_scores(candidate, raw, colors, ~mask)
    damaged = raw.copy()
    damaged[mask] = np.nan
    second = local.conditional_scores(candidate, damaged, colors, ~mask)
    for a, b in zip(first, second, strict=True):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_existing_exact_parent_component_is_replaced_without_doubling(layout):
    raw, colors, rgb = scene(layout)
    candidate = local.fit_local_candidate(
        raw, colors, stratified_split(raw.shape, 71), shot=0.00008, read=2.56e-8, config=CONFIG
    )
    np.testing.assert_array_equal(local.replacement_components(candidate, rgb), 0)
    zero = local.replacement_components(candidate, np.zeros_like(rgb))
    partial = local.replacement_components(candidate, 0.4 * rgb)
    np.testing.assert_allclose(partial, 0.6 * zero, atol=2e-15)


def test_parent_values_do_not_change_raw_discovery_validation_or_matching():
    raw, _, rgb = scene()
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    values, first = local.restore_local_waves(
        rgb,
        packed,
        np.array(LAYOUTS[0]),
        shot=0.00008,
        read=2.56e-8,
        thresholds=(0, 2),
        config=CONFIG,
    )
    _, second = local.restore_local_waves(
        np.zeros_like(rgb),
        packed,
        np.array(LAYOUTS[0]),
        shot=0.00008,
        read=2.56e-8,
        thresholds=(0, 2),
        config=CONFIG,
    )
    assert first["records"] == second["records"]
    assert first["parent_used_for_discovery_or_validation"] is False
    for output in values.values():
        np.testing.assert_array_equal(output, rgb)


def test_local_boxes_equal_direct_truncated_native_windows():
    rng = np.random.default_rng(72)
    field = rng.normal(size=(31, 24))
    ay, ax = np.array([0, 7, 30]), np.array([0, 8, 23])
    actual = local._box_sums(field, ay, ax, 9)
    expected = np.array(
        [[field[max(0, y - 4) : y + 5, max(0, x - 4) : x + 5].sum() for x in ax] for y in ay]
    )
    np.testing.assert_allclose(actual, expected, atol=2e-14)


def test_direction_matching_handles_swaps_conjugates_and_rejects_other_frequencies():
    first = ((0.1, 0.04), (-0.05, 0.1))
    second = ((0.05, -0.1), (0.1, 0.041))
    matched = local.match_directions(first, second, (64, 96), 1.5)
    assert [(a, b) for a, b, _ in matched] == [(0, 1), (1, 0)]
    assert not local.match_directions(first, ((0.2, 0.1), (-0.2, 0.15)), (64, 96), 1.5)


def test_unrelated_direction_cannot_discard_a_valid_partial_match():
    first = np.array([[3, 0], [-3, 2]]) / 128
    second = np.array([[3.1, 0], [3, 2]]) / 128
    assert local.match_directions(first, second, (128, 128), 1.5, matching="legacy") == []
    matched = local.match_directions(first, second, (128, 128), 1.5)
    assert [(a, b) for a, b, _ in matched] == [(0, 0)]
    assert matched[0][2] == pytest.approx(0.1)
    swapped = local.match_directions(first, -second[::-1], (128, 128), 1.5)
    assert [(a, b) for a, b, _ in swapped] == [(0, 1)]


def test_harmonic_group_is_fitted_and_validated_as_a_whole():
    size = 64
    y, x = np.mgrid[:size, :size]
    phase = 2 * np.pi * (3 * x + y) / size
    signal = 0.03 + 0.003 * np.cos(phase) + 0.001 * np.sin(2 * phase) + 0.0005 * np.cos(3 * phase)
    signal += 0.001 * np.cos(2 * np.pi * (-2 * x + 4 * y) / size)
    rgb = np.array([0.8, 1, 0.6])[:, None, None] * signal
    colors = np.tile(np.array(LAYOUTS[0]).reshape(2, 2), (size // 2, size // 2))
    raw = rgb[colors, y, x]
    mask = stratified_split(raw.shape, 71)
    candidate = local.fit_local_candidate(
        raw,
        colors,
        mask,
        shot=0.00008,
        read=2.56e-8,
        config=replace(CONFIG, harmonics=3, frequency_refinements=0),
    )
    assert [stop - start for start, stop in candidate.wave_slices] == [6, 6]
    np.testing.assert_allclose(candidate.full_cfa, raw, atol=2e-15)
    np.testing.assert_array_equal(local.replacement_components(candidate, rgb), 0)
    for direction in range(2):
        start, stop = candidate.wave_slices[direction]
        assert 3 * np.linalg.norm(candidate.frequencies_xy[direction]) <= 0.24
        assert candidate.wave_fields[direction].shape == (size, size, stop - start)
        # A null retains the entire other family, but none of this family's harmonics.
        changed = raw.copy()
        changed[~mask] = candidate.conditional_null_cfa[direction, ~mask]
        _, score = local.conditional_scores(candidate, changed, colors, ~mask)
        assert np.all(score[direction] < 0)
    assert local._harmonic_count((0.13, 0), 3) == 1
    assert local._harmonic_count((0.09, 0), 3) == 2


def test_harmonic_unit_cannot_borrow_fundamental_validation():
    size = 64
    y, x = np.mgrid[:size, :size]
    phase = 2 * np.pi * (3 * x + y) / size
    signal = 0.03 + 0.003 * np.cos(phase) + 0.001 * np.sin(2 * phase)
    signal += 0.0007 * np.cos(2 * np.pi * (-2 * x + 4 * y) / size)
    rgb = np.array([0.8, 1, 0.6])[:, None, None] * signal
    colors = np.tile(np.array(LAYOUTS[0]).reshape(2, 2), (size // 2, size // 2))
    raw, mask = rgb[colors, y, x], stratified_split((size, size), 71)
    config = replace(CONFIG, harmonics=3, frequency_refinements=0, support_unit="harmonic")
    candidate = local.fit_local_candidate(
        raw, colors, mask, shot=0.00008, read=2.56e-8, config=config
    )
    group = local.fit_local_candidate(
        raw,
        colors,
        mask,
        shot=0.00008,
        read=2.56e-8,
        config=replace(config, support_unit="direction"),
    )
    assert candidate.frequencies_xy == group.frequencies_xy
    np.testing.assert_array_equal(candidate.coefficients, group.coefficients)
    np.testing.assert_array_equal(candidate.full_cfa, group.full_cfa)
    np.testing.assert_array_equal(local.replacement_components(candidate, rgb), 0)
    unit, fundamental = [candidate.unit_keys.index(key) for key in [(0, 2), (0, 1)]]
    _, original = local.conditional_scores(candidate, raw, colors, ~mask)
    assert np.all(original[[unit, fundamental]] > 0)
    changed = raw.copy()
    changed[~mask] = candidate.conditional_null_cfa[unit, ~mask]
    _, score = local.conditional_scores(candidate, changed, colors, ~mask)
    assert np.all(score[unit] < 0)
    assert np.all(score[fundamental] > 0)


def test_harmonic_matching_uses_its_actual_native_frequency_distance():
    first = SimpleNamespace(unit_keys=((0, 1), (0, 2), (0, 3), (1, 1)))
    second = SimpleNamespace(unit_keys=((1, 1), (1, 2), (1, 3), (0, 1)))
    units = local._match_units(first, second, [(0, 1, 0.6), (1, 0, 0.9)], 1.5)
    assert [(a, b) for a, b, _ in units] == [(0, 0), (1, 1), (3, 3)]
    np.testing.assert_allclose([d for _, _, d in units], [0.6, 1.2, 0.9])


def test_piecewise_affine_background_explains_different_slopes_across_the_edge():
    size = 64
    y, x = np.mgrid[:size, :size]
    xx, yy = 2 * (x + 0.5) / size - 1, 2 * (y + 0.5) / size - 1
    signal = 0.03 + 0.006 * xx + 0.005 * yy + (xx > 0) * (0.02 + 0.01 * xx - 0.008 * yy)
    signal += 0.0005 * np.cos(2 * np.pi * (5 * x + 3 * y) / size)
    rgb = np.array([0.8, 1, 0.6])[:, None, None] * signal
    colors = np.tile(np.array(LAYOUTS[0]).reshape(2, 2), (size // 2, size // 2))
    raw = rgb[colors, y, x]
    candidate = local.fit_local_candidate(
        raw,
        colors,
        stratified_split(raw.shape, 71),
        shot=0.00008,
        read=2.56e-8,
        config=replace(CONFIG, background="piecewise_affine", frequency_refinements=0),
    )
    assert candidate.wave_slices[0][0] == 6
    np.testing.assert_allclose(candidate.full_cfa, raw, atol=2e-14)


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize(
    "support_unit,background", [("direction", "step"), ("harmonic", "piecewise_affine")]
)
def test_even_nonmultiple_four_axes_fit_boundary_tiles_without_cfa_shift(
    layout, support_unit, background
):
    h, w = 66, 70
    y, x = np.mgrid[:h, :w]
    signal = 0.03 + 0.003 * np.cos(2 * np.pi * (5 * x + 3 * y) / 64)
    rgb = np.array([0.8, 1, 0.6])[:, None, None] * signal
    colors = np.tile(np.array(layout).reshape(2, 2), (h // 2, w // 2))
    raw = rgb[colors, y, x]
    packed = np.stack([raw[a::2, b::2] for a in range(2) for b in range(2)])
    outputs, aux = local.restore_local_waves(
        rgb,
        packed,
        np.array(layout),
        shot=0.00008,
        read=2.56e-8,
        config=replace(CONFIG, harmonics=3, support_unit=support_unit, background=background),
    )
    assert aux["patches"] == 4
    assert [r["xy"] for r in aux["records"]] == [[0, 0], [6, 0], [0, 2], [6, 2]]
    for output in outputs.values():
        np.testing.assert_array_equal(output, rgb)


def test_soft_support_is_zero_below_threshold_and_monotone():
    values = local.support_weight(np.array([-4, 0, 1, 2, 3, 10, 1e8]), 2)
    np.testing.assert_array_equal(values[:4], 0)
    assert np.all(np.diff(values) >= 0)
    assert values[-1] <= 1
    np.testing.assert_array_equal(local.support_weight([-1, 0, 1], 0), [0, 0, 1])
    with pytest.raises(ValueError):
        local.support_weight([np.nan], 2)


def test_zero_noise_is_bit_identity_without_fitting(monkeypatch):
    raw, _, rgb = scene()
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])

    def forbidden(*a, **k):
        raise AssertionError("No zero-noise fit permitted")

    monkeypatch.setattr(local, "fit_local_candidate", forbidden)
    values, aux = local.restore_local_waves(
        rgb.astype(np.float32),
        packed,
        np.array(LAYOUTS[0]),
        shot=0,
        read=0,
        thresholds=(0, 2, 4),
        config=CONFIG,
    )
    assert aux["patches"] == 0 and aux["identity_zero_noise"]
    for value in values.values():
        np.testing.assert_array_equal(value, rgb.astype(np.float32))


@pytest.mark.parametrize(
    "key,value",
    [
        ("window", 31),
        ("stride", 3),
        ("family_degrees", np.nan),
        ("edge_refinements", 4),
        ("window", 64.0),
        ("validation_window", 64),
        ("harmonics", 0),
        ("harmonics", 5),
        ("harmonics", 3.0),
        ("matching", "greedy"),
        ("support_unit", "channel"),
        ("background", "polynomial"),
    ],
)
def test_invalid_geometry_rejects(key, value):
    with pytest.raises(ValueError):
        replace(CONFIG, **{key: value})


@pytest.mark.parametrize("changed", [None, "parent", "packed", "colors", "prediction"])
def test_completed_pilot_adoption_requires_exact_inputs_and_native_prediction(tmp_path, changed):
    from pilot_local_validated_waves import checked_adoption

    from demosaic.experiments.artifacts import reference, write_json
    from demosaic.prediction_archive import fingerprint

    parent = np.full((3, 32, 32), 0.02, np.float32)
    packed = np.full((4, 16, 16), 0.02, np.float32)
    colors = np.array(LAYOUTS[0])
    path = tmp_path / "prediction.npy"
    np.save(path, parent)
    record = {
        "parent_values": fingerprint(parent),
        "packed_values": fingerprint(packed),
        "colors_values": fingerprint(colors),
        "predictions": {"local-t2": reference(path)},
        "aux": {"patches": 1},
    }
    receipt = tmp_path / "receipt.json"
    write_json(receipt, record)
    binding = reference(receipt)
    if changed == "parent":
        parent[0, 0, 0] += 0.001
    elif changed == "packed":
        packed[0, 0, 0] += 0.001
    elif changed == "colors":
        colors[:] = LAYOUTS[1]
    elif changed == "prediction":
        np.save(path, parent + 0.001)
    if changed:
        with pytest.raises(ValueError):
            checked_adoption(binding, parent, packed, colors, ["local-t2"])
    else:
        predictions, aux = checked_adoption(binding, parent, packed, colors, ["local-t2"])
        assert predictions == record["predictions"] and aux == {"patches": 1}


@pytest.mark.parametrize("correct", [True, False])
def test_procedural_parent_name_is_bound_to_actual_cache_checkpoint(tmp_path, correct):
    from pilot_local_validated_waves import verified_wire_parent

    from demosaic.experiments.artifacts import write_json

    sha = (
        "96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4"
        if correct
        else "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb"
    )
    path = tmp_path / "plan.json"
    write_json(path, {"parent": {"path": "/unused/weights.pt", "sha256": sha, "step": 5000}})
    if correct:
        assert verified_wire_parent(path)["label"] == "V143"
    else:
        with pytest.raises(ValueError, match="V143"):
            verified_wire_parent(path)
