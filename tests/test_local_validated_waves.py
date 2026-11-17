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


def test_phase_recenter_recovers_an_offset_without_the_other_fold():
    raw, colors, _ = scene()
    truth = np.asarray(((5 / 64, 3 / 64), (-4 / 64, 7 / 64)))
    radial = truth / np.linalg.norm(truth, axis=1, keepdims=True)
    shifted = truth + radial / 64
    mask = stratified_split(raw.shape, 81)
    options = {
        "shot": 0,
        "read": 1e-8,
        "config": CONFIG,
        "guide_frequencies_xy": shifted,
        "phase_bins": 8,
        "recenter_phase_guides": True,
    }
    selected = local.fit_local_candidate(raw, colors, mask, **options)
    corrupted = local.fit_local_candidate(np.where(mask, raw, np.nan), colors, mask, **options)
    np.testing.assert_allclose(selected.frequencies_xy, truth, rtol=0, atol=1e-14)
    np.testing.assert_array_equal(selected.frequencies_xy, corrupted.frequencies_xy)
    np.testing.assert_array_equal(selected.full_cfa, corrupted.full_cfa)


def test_phase_recenter_does_not_move_the_guide_on_a_flat():
    raw, colors, _ = scene()
    raw.fill(0.07)
    original = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    fit = local.fit_local_candidate(
        raw,
        colors,
        stratified_split(raw.shape, 81),
        shot=0,
        read=1e-8,
        config=CONFIG,
        phase_bins=8,
        guide_frequencies_xy=original,
        recenter_phase_guides=True,
    )
    assert fit.frequencies_xy == original


def test_edge_guard_subsets_only_the_frequency_search(monkeypatch):
    raw, colors, _ = scene()
    raw[:, 30:] += 0.1
    discovery = stratified_split(raw.shape, 81)
    options = {
        "shot": 0,
        "read": 1e-6,
        "config": CONFIG,
        "guide_frequencies_xy": ((5 / 64, 3 / 64), (-4 / 64, 7 / 64)),
        "phase_bins": 8,
        "recenter_phase_guides": True,
    }
    inspected = []

    def record(_raw, green, _nuisance, _x, _y, guide, *_args):
        inspected.append(green.reshape(raw.shape).copy())
        return guide

    monkeypatch.setattr(local, "_recenter_phase_guides", record)
    plain = local.fit_local_candidate(raw, colors, discovery, **options)
    guarded = local.fit_local_candidate(
        np.where(discovery, raw, np.nan), colors, discovery, **options, phase_guide_edge_guard_px=8
    )
    np.testing.assert_array_equal(inspected[0], (colors == 1) & discovery)
    assert guarded.guide_search_excluded > 100
    assert inspected[0].sum() - inspected[1].sum() == guarded.guide_search_excluded
    assert not (inspected[1] & ~inspected[0]).any()
    np.testing.assert_array_equal(guarded.full_cfa, plain.full_cfa)
    np.testing.assert_array_equal(guarded.conditional_null_cfa, plain.conditional_null_cfa)
    for match, control in zip(guarded.selected_indices, plain.selected_indices, strict=True):
        np.testing.assert_array_equal(match, control)

    flat = local.fit_local_candidate(
        np.full_like(raw, 0.07), colors, discovery, **options, phase_guide_edge_guard_px=8
    )
    assert flat.guide_search_excluded == 0
    np.testing.assert_array_equal(inspected[-1], inspected[0])


@pytest.mark.parametrize("layout", LAYOUTS)
def test_donor_template_refits_query_phase_and_signed_amplitudes(layout):
    _, colors, _ = scene(layout)
    guide = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    x, y, _, _ = local.geometry(colors.shape)
    templates = (
        np.array([0.6, -0.1, -0.4, -0.4, -0.1, 0.0, 0.1, 0.3]),
        np.array([-0.4, -0.4, 0.1, 0.4, 0.5, 0.2, -0.2, -0.2]),
    )
    translation = (1 / 8, 1 / 3)
    fields = [
        (local._phase_bin_weights(x, y, f, 8) @ local.shifted_donor_knots(shape, [turns])).reshape(
            colors.shape
        )
        for f, shape, turns in zip(guide, templates, translation, strict=True)
    ]
    rgb = 0.06 + np.array([0.02, 0.03, 0.01])[:, None, None] * fields[0]
    rgb += np.array([0.015, -0.005, 0.01])[:, None, None] * fields[1]
    raw = np.take_along_axis(rgb, colors[None], axis=0)[0]
    mask = stratified_split(raw.shape, 81)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": guide,
        "phase_bins": 8,
        "donor_phase_templates": templates,
    }
    fitted = local.fit_local_candidate(raw, colors, mask, **options)
    withheld = local.fit_local_candidate(np.where(mask, raw, np.nan), colors, mask, **options)
    assert translation == fitted.donor_phase_shifts == withheld.donor_phase_shifts
    np.testing.assert_array_equal(fitted.full_cfa, withheld.full_cfa)
    np.testing.assert_allclose(fitted.full_cfa, raw, rtol=0, atol=1e-13)
    start, _ = fitted.unit_slices[1]
    amp = fitted.coefficients[:, start]
    np.testing.assert_allclose(amp / amp[0], [1, -1 / 3, 2 / 3], rtol=0, atol=1e-13)


def test_same_side_validation_and_profiles_do_not_cross_a_strong_step():
    raw, colors, _ = scene()
    frequencies = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    x, y, _, _ = local.geometry(raw.shape)
    side = x >= 32
    basis = local._phase_bin_weights(x, y, frequencies[0], 8)
    dark = (basis @ np.array([1, -0.1, -0.4, -0.6, -0.6, -0.4, 0.2, 0.9])).reshape(raw.shape)
    bright = (basis @ np.array([-0.6, -0.4, 0.1, 0.8, 0.7, 0.1, -0.3, -0.4])).reshape(raw.shape)
    raw = 0.04 + 0.2 * side + np.where(side, 0.003 * bright, 0.008 * dark)
    fold = stratified_split(raw.shape, 19)
    options = {
        "shot": 0.00008,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": frequencies,
        "phase_bins": 8,
    }
    plain = local.fit_local_candidate(raw, colors, fold, **options)
    check = local.fit_local_candidate(raw, colors, fold, phase_edge_side="validation", **options)
    split = local.fit_local_candidate(raw, colors, fold, phase_edge_side="profiles", **options)
    damage = local.fit_local_candidate(
        np.where(fold, raw, np.nan), colors, fold, phase_edge_side="profiles", **options
    )
    np.testing.assert_array_equal(check.full_cfa, plain.full_cfa)
    np.testing.assert_array_equal(split.design, damage.design)
    np.testing.assert_array_equal(split.full_cfa, damage.full_cfa)
    np.testing.assert_array_equal(split.phase_bright_side, side)
    np.testing.assert_allclose(split.full_cfa, raw, rtol=0, atol=1e-13)
    assert np.linalg.norm(plain.full_cfa - raw) > 0.05
    assert split.unit_keys == ((0, 0), (0, 1), (1, 0), (1, 1))
    assert not split.unit_fields[0][side].any()
    clean = local.conditional_scores(check, raw, colors, ~fold, window=33, stride=8)[0]
    damaged = local.conditional_scores(
        check, raw + 0.08 * (side & ~fold), colors, ~fold, window=33, stride=8
    )[0]
    np.testing.assert_array_equal(clean[..., ~side], damaged[..., ~side])
    assert np.max(abs(clean[..., side] - damaged[..., side])) > 0.1

    cross = local.conditional_scores(
        check, raw, colors, ~fold, window=33, stride=8, bright_cross_edge_weight=1
    )[0]
    original = local.conditional_scores(plain, raw, colors, ~fold, window=33, stride=8)[0]
    np.testing.assert_array_equal(cross[..., ~side], clean[..., ~side])
    np.testing.assert_array_equal(cross[..., side], original[..., side])

    half = local.conditional_scores(
        check, raw, colors, ~fold, window=33, stride=1, bright_cross_edge_weight=0.5
    )[0]
    scope = (~fold) & (colors == 1) & (abs(y - 30) <= 16) & (abs(x - 37) <= 16)
    null, full = check.conditional_null_cfa[0][scope], check.full_cfa[scope]
    scale = np.where(side[scope], 1, 0.5)
    variance = check.variance_cfa[scope]
    expected = np.sum(scale * ((raw[scope] - null) ** 2 - (raw[scope] - full) ** 2) / variance)
    expected /= 2 * np.sqrt(np.sum((scale * (full - null)) ** 2 / variance))
    np.testing.assert_allclose(half[0, 1, 30, 37], expected, rtol=0, atol=1e-12)


def test_guide_crosscheck_uses_discovery_only_and_retains_a_coherent_move():
    y, x = np.indices((64, 64))
    freq = (5 / 64, 2 / 64)
    displaced = (6 / 64, 2 / 64)
    raw = 0.08 + 0.006 * np.cos(2 * np.pi * (freq[0] * x + freq[1] * y))
    raw += 0.004 * np.sin(2 * np.pi * (3 / 64 * x - 7 / 64 * y))
    raw += (x > 32) * 0.03
    colors = np.tile([[0, 1], [1, 2]], (32, 32))
    outer = stratified_split(raw.shape, 121)
    radius = np.asarray(freq) / np.linalg.norm(freq)
    seed = tuple(np.asarray(freq) + radius / 64)
    options = {
        "guide_frequencies_xy": (seed, (3 / 64, -7 / 64)),
        "phase_bins": 8,
        "recenter_phase_guides": True,
        "phase_guide_crosscheck": True,
        "shot": 8e-5,
        "read": 1e-8,
        "config": CONFIG,
    }
    expected = local.fit_local_candidate(raw, colors, outer, **options)
    damaged = local.fit_local_candidate(np.where(outer, raw, np.nan), colors, outer, **options)
    np.testing.assert_allclose(expected.frequencies_xy[0], freq, atol=1e-15, rtol=0)
    assert expected.guide_crosschecks == damaged.guide_crosschecks
    assert expected.guide_crosschecks[0]["accepted"]
    np.testing.assert_array_equal(expected.full_cfa, damaged.full_cfa)

    green = (colors == 1) & outer
    a, b = x[green], y[green]
    split = stratified_split(raw.shape, 202611170713)[green]
    affine = np.column_stack((np.ones(len(a)), a, b))
    proposal = 0.08 + 0.012 * np.cos(2 * np.pi * (displaced[0] * a + displaced[1] * b))
    original = 0.08 + 0.006 * np.cos(2 * np.pi * (freq[0] * a + freq[1] * b))
    signal = np.where(split, proposal, original)
    held = local._crosscheck_guide_move(
        a, b, signal, affine, affine, freq, displaced, split, 8e-5, 1e-8
    )
    assert min(held) < 0


@pytest.mark.parametrize("layout", LAYOUTS)
def test_shared_phase_shape_keeps_signed_color_and_withheld_independence(layout):
    _, colors, _ = scene(layout)
    frequencies = ((5 / 64, 3 / 64), (-4 / 64, 7 / 64))
    x, y, _, _ = local.geometry(colors.shape)
    shapes = (
        np.array([0.6, -0.1, -0.4, -0.4, -0.1, 0.0, 0.1, 0.3]),
        np.array([-0.4, -0.4, 0.1, 0.4, 0.5, 0.2, -0.2, -0.2]),
    )
    strong, weak = [
        (local._phase_bin_weights(x, y, f, 8) @ shape).reshape(colors.shape)
        for f, shape in zip(frequencies, shapes, strict=True)
    ]
    rgb = 0.06 + np.array([0.02, 0.03, 0.01])[:, None, None] * strong
    rgb += np.array([0.015, -0.005, 0.01])[:, None, None] * weak
    raw = np.take_along_axis(rgb, colors[None], axis=0)[0]
    mask = stratified_split(raw.shape, 81)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": CONFIG,
        "guide_frequencies_xy": frequencies,
        "phase_bins": 8,
        "shared_phase_shape": True,
    }
    candidate = local.fit_local_candidate(raw, colors, mask, **options)
    damaged = local.fit_local_candidate(np.where(mask, raw, np.nan), colors, mask, **options)
    np.testing.assert_array_equal(candidate.design, damaged.design)
    np.testing.assert_array_equal(candidate.conditional_null_cfa, damaged.conditional_null_cfa)
    np.testing.assert_allclose(candidate.full_cfa, raw, rtol=0, atol=1e-13)
    assert candidate.phase_reliability_degrees == 7
    assert [v.shape[-1] for v in candidate.unit_fields] == [1, 1]
    stop, _ = candidate.unit_slices[1]
    np.testing.assert_allclose(
        candidate.coefficients[:, stop] / candidate.coefficients[0, stop],
        [1, -1 / 3, 2 / 3],
        rtol=0,
        atol=1e-13,
    )


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
