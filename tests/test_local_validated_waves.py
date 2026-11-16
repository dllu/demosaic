"""Actual held-out invariance, color/direction validation and parent replacement."""

from dataclasses import replace

import numpy as np
import pytest

import demosaic.local_validated_waves as local
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


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("harmonics", [1, 3])
def test_every_discovery_quantity_excludes_withheld_pixels(layout, harmonics):
    raw, colors, _ = scene(layout)
    mask = stratified_split(raw.shape, 71)
    config = replace(CONFIG, harmonics=harmonics)
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
    for a, b in zip(
        (*first.operators, *first.wave_fields),
        (*second.operators, *second.wave_fields),
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


@pytest.mark.parametrize("layout", LAYOUTS)
def test_even_nonmultiple_four_axes_fit_boundary_tiles_without_cfa_shift(layout):
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
        config=replace(CONFIG, harmonics=3),
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
