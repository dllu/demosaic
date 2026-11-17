"""Recover distinct fine families, preserve broad context and withhold actual B values."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.background_phase_aggregation import BackgroundPhaseOperator
from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.fine_carrier_proposals import admissible_fine, fit_fine_candidate
from demosaic.local_validated_waves import LocalWaveConfig, _wave_columns, match_directions
from demosaic.neural_nuisance import WithheldBackground, restore_neural_nuisance
from demosaic.phase_aggregation import PhaseAggregateConfig
from demosaic.spatial_carrier_amplitudes import SpatialCarrierOperator

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
TRUE_FINE = ((30 / 256, 19 / 256), (-23 / 256, 19 / 256))
CONFIG = LocalWaveConfig(window=256, stride=128, frequency_weighting="hann-inverse-variance")


def fixture(layout):
    yy, xx = np.indices((256, 256))
    colors = np.tile(np.asarray(layout).reshape(2, 2), (128, 128))
    mask = stratified_split(colors.shape, 71)
    coarse = ((4 / 256, 0), (0, 5 / 256))
    columns = [np.ones(colors.shape), xx / 256, yy / 256, xx >= 128]
    for f in coarse:
        columns.extend(_wave_columns(xx, yy, f).T.reshape(2, *colors.shape))
    design = np.stack(columns, axis=-1).reshape(-1, 8)
    signal = 0.04 + 0.001 * xx / 256 + 0.0005 * yy / 256 + 0.015 * (xx >= 128)
    for amplitude, f in zip([0.01, 0.006, 0.002, 0.0018], (*coarse, *TRUE_FINE), strict=True):
        signal += amplitude * np.cos(2 * np.pi * (f[0] * xx + f[1] * yy) + 0.3)
    rgb = np.array([0.7, 1.2, 0.9])[:, None, None] * signal
    raw = rgb[colors, yy, xx]
    selected = tuple(np.flatnonzero((mask & (colors == c)).ravel()) for c in range(3))
    candidate = SimpleNamespace(
        discovery_mask=mask,
        frequencies_xy=coarse,
        edge_geometry=(0.0, 0.0),
        design=design,
        wave_slices=((4, 6), (6, 8)),
        unit_keys=((0, 0), (1, 0)),
        selected_indices=selected,
        variance_cfa=np.full(colors.shape, 2e-6),
    )
    return candidate, colors, raw, rgb


@pytest.mark.parametrize("layout", LAYOUTS)
def test_two_new_fine_families_are_found_without_changing_broad_design(layout):
    reference, colors, raw, _ = fixture(layout)
    original = reference.design.copy()
    candidate = fit_fine_candidate(raw, colors, reference, shot=8e-5, read=2.56e-8, config=CONFIG)
    matched = match_directions(
        candidate.frequencies_xy, TRUE_FINE, raw.shape, 0.5, matching="cardinality"
    )
    assert len(matched) == 2
    np.testing.assert_array_equal(candidate.design[:, :8], original)
    np.testing.assert_array_equal(reference.design, original)
    np.testing.assert_array_equal(candidate.discovery_mask, reference.discovery_mask)
    damaged = raw.copy()
    damaged[~reference.discovery_mask] = np.nan
    repeated = fit_fine_candidate(
        damaged, colors, reference, shot=8e-5, read=2.56e-8, config=CONFIG
    )
    for key in ["frequencies_xy", "coefficients", "full_cfa", "conditional_null_cfa"]:
        np.testing.assert_array_equal(getattr(candidate, key), getattr(repeated, key))
    for color, selected in enumerate(candidate.selected_indices):
        precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
        expected = np.linalg.lstsq(
            candidate.design[selected] * precision[:, None],
            raw.ravel()[selected] * precision,
            rcond=1e-10,
        )[0]
        np.testing.assert_allclose(candidate.coefficients[color], expected, atol=1e-13)


def test_existing_27p7_pixel_carrier_is_retained_and_its_harmonics_are_not_new_families():
    # The added band never replaces the original broad search. Its duplicate
    # exclusions grow with harmonic order and do not assert confidence bounds.
    f = np.array([1 / 27.69, 0.0])
    samples = np.array([f, 2 * f, 3 * f, 3 * f + [0.003, 0], [-0.09, 0.074], [0.117, 0.074]])
    result = admissible_fine(samples, [f], (512, 512))
    np.testing.assert_array_equal(result, [False, False, False, False, True, True])
    represented = np.array([0.1, 0.08])
    assert not admissible_fine(represented * 1.1, [represented], (512, 512))


def test_fine_parent_operator_annihilates_original_coarse_nuisance_span():
    reference, colors, raw, _ = fixture(LAYOUTS[0])
    candidate = fit_fine_candidate(raw, colors, reference, shot=8e-5, read=2.56e-8, config=CONFIG)
    operator = BackgroundPhaseOperator(
        candidate, colors, PhaseAggregateConfig(bins=16, window=33, query_stride=32)
    )
    rng = np.random.default_rng(45)
    nuisance = np.empty(raw.size)
    for color in range(3):
        selected = (colors == color).ravel()
        nuisance[selected] = reference.design[selected] @ rng.normal(size=8)
    np.testing.assert_allclose(operator.apply(nuisance.reshape(raw.shape)), 0, atol=1e-12)
    yy, xx = np.indices(raw.shape)
    parent = rng.normal(size=(3, *raw.shape))
    np.testing.assert_allclose(
        operator.components(raw, parent),
        operator.apply(raw) - operator.apply(parent[colors, yy, xx]),
        atol=1e-12,
    )


def test_no_distinct_fine_pair_falls_back_to_broad_and_keeps_exact_parent_identity():
    yy, xx = np.indices((32, 32))
    layout = np.array(LAYOUTS[0])
    colors = np.tile(layout.reshape(2, 2), (16, 16))
    signal = 0.03 + 0.003 * np.cos(2 * np.pi * (3 * xx + 2 * yy) / 32)
    rgb = np.stack([signal] * 3)
    raw = rgb[colors, yy, xx]
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    mask = stratified_split(raw.shape, 71)
    fields = tuple(WithheldBackground(rgb * 0.9, m) for m in [mask, ~mask])
    config = LocalWaveConfig(
        window=32,
        stride=16,
        validation_window=17,
        validation_stride=8,
        edge_refinements=0,
        frequency_refinements=0,
    )
    kwargs = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": config,
        "thresholds": (0.0, 2.0),
        "reselect_frequencies": False,
        "aggregation_config": PhaseAggregateConfig(bins=16, window=17, query_stride=8),
        "phase_guide": True,
    }
    control, _ = restore_neural_nuisance(rgb * 0.4, packed, layout, fields, **kwargs)
    added, aux = restore_neural_nuisance(
        rgb * 0.4, packed, layout, fields, add_fine_carriers=True, **kwargs
    )
    assert aux["add_fine_carriers"] and all(
        r["fine_proposal_unavailable_folds"] for r in aux["records"]
    )
    for key, value in control.items():
        np.testing.assert_array_equal(added[key], value)
    assert np.max(np.abs(control["H1-global", 0.0] - rgb * 0.4)) > 1e-5
    identity, _ = restore_neural_nuisance(
        rgb, packed, layout, fields, add_fine_carriers=True, **kwargs
    )
    for value in identity.values():
        np.testing.assert_array_equal(value, rgb)


@pytest.mark.parametrize(
    ("fine_reconstruction", "fine_support"),
    [("phase", "independent"), ("sinusoidal", "independent"), ("sinusoidal", "joint")],
)
def test_distinct_fine_pair_adds_actual_analytic_detail_without_changing_H1(
    fine_reconstruction, fine_support
):
    _, _, raw, rgb = fixture(LAYOUTS[0])
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    mask = stratified_split(raw.shape, 71)
    fields = tuple(WithheldBackground(rgb * 0.9, m) for m in [mask, ~mask])
    config = LocalWaveConfig(
        window=256,
        stride=128,
        validation_window=33,
        validation_stride=32,
        edge_refinements=0,
        frequency_refinements=0,
        frequency_weighting="hann-inverse-variance",
    )
    kwargs = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": config,
        "thresholds": (0.0, 2.0),
        "reselect_frequencies": False,
        "aggregation_config": PhaseAggregateConfig(bins=16, window=33, query_stride=32),
        "phase_guide": True,
    }
    parent = rgb * 0.4
    control, control_aux = restore_neural_nuisance(
        parent, packed, np.array(LAYOUTS[0]), fields, **kwargs
    )
    added, aux = restore_neural_nuisance(
        parent,
        packed,
        np.array(LAYOUTS[0]),
        fields,
        add_fine_carriers=True,
        fine_reconstruction=fine_reconstruction,
        fine_support=fine_support,
        **kwargs,
    )
    assert all("fine-H1-" in r["arms"] for r in aux["records"])
    for key, value in control.items():
        if key[0].startswith("H1-"):
            np.testing.assert_array_equal(added[key], value)
    assert (
        np.max(np.abs(added["conditional-local", 0.0] - control["conditional-local", 0.0])) > 1e-4
    )
    if fine_reconstruction == "sinusoidal":
        for record in aux["records"]:
            assert record["arms"]["fine-H1-"]["amplitude_nuisance"] == "global"
            assert record["arms"]["fine-H1-"]["amplitude_window"] == 33
            assert "H1_diagnostics_scope" not in record["arms"]["fine-H1-"]
            assert record["arms"]["fine-H1-"]["carrier_delivery"].startswith("Sinusoidal full-fit")
            assert record["arms"]["fine-H1-"]["colour_support"] == fine_support
    for a, b in zip(aux["records"], control_aux["records"], strict=True):
        for name in ["H1-", "neural"]:
            assert a["arms"][name] == b["arms"][name]


@pytest.mark.parametrize("layout", LAYOUTS)
def test_fine_sinusoidal_operator_preserves_independent_colour_amplitudes_and_A_only_map(layout):
    reference, colors, _, _ = fixture(layout)
    yy, xx = np.indices(colors.shape)
    waves = np.column_stack([_wave_columns(xx, yy, f) for f in TRUE_FINE])
    design = np.column_stack([reference.design, waves])
    operators = []
    for selected in reference.selected_indices:
        operators.append(np.linalg.pinv(design[selected], rcond=1e-10))
    candidate = SimpleNamespace(
        design=design,
        discovery_mask=reference.discovery_mask,
        variance_cfa=reference.variance_cfa,
        operators=operators,
        wave_slices=((8, 10), (10, 12)),
        unit_slices=((8, 10), (10, 12)),
        unit_keys=((0, 0), (1, 0)),
    )
    # Deliberately different RGB amplitudes and phases in the two directions.
    # Geometry is fixed here: discovery accuracy is tested separately above.
    amplitude = np.array(
        [
            [0.003, 0.0004, 0.0002, -0.0001],
            [0.0018, -0.0003, 0.0016, 0.0002],
            [0.0003, 0.0001, 0.0028, -0.0005],
        ]
    )
    truth = (amplitude @ waves.T).reshape(3, *colors.shape)
    rng = np.random.default_rng(122)
    broad = (rng.normal(0, 0.01, (3, 8)) @ reference.design.T).reshape(truth.shape)
    raw = (broad + truth)[colors, yy, xx]
    operator = SpatialCarrierOperator(
        candidate, colors, window=129, stride=32, nuisance_mode="global"
    )
    recovered = operator.components(raw, broad)[1].sum(axis=0)
    assert np.mean((recovered - truth) ** 2) < 1e-16 * np.mean(truth**2)
    # Recover each colour's actual signed sine/cosine coefficients, rather than
    # approving a neutralized image that merely shows more green geometry.
    for color in range(3):
        fitted = np.linalg.lstsq(waves, recovered[color].ravel(), rcond=1e-10)[0]
        np.testing.assert_allclose(fitted, amplitude[color], atol=1e-10)
    damaged = raw.copy()
    damaged[~candidate.discovery_mask] = np.nan
    a, b = operator.predict(raw), operator.predict(damaged)
    np.testing.assert_array_equal(a.full_cfa, b.full_cfa)
    np.testing.assert_array_equal(a.conditional_null_cfa, b.conditional_null_cfa)
    actual = operator.components(damaged, broad)[1]
    np.testing.assert_array_equal(actual, operator.components(raw, broad)[1])
    np.testing.assert_allclose(operator.components(raw, broad + truth)[1], 0, atol=1e-12)
    np.testing.assert_allclose(
        operator.components(broad[colors, yy, xx], np.zeros_like(broad))[1], 0, atol=1e-12
    )
