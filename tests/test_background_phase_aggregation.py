"""Independent null-fit checks, withholding and identical parent replacement."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.background_phase_aggregation import BackgroundPhaseOperator
from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.neural_nuisance import WithheldBackground, restore_neural_nuisance
from demosaic.phase_aggregation import PhaseAggregateConfig

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
CONFIG = PhaseAggregateConfig(bins=32, window=49, query_stride=8)


def fixture(layout, neural=True):
    yy, xx = np.indices((64, 64))
    colors = np.tile(np.asarray(layout).reshape(2, 2), (32, 32))
    mask = stratified_split(colors.shape, 71)
    frequencies = ((5 / 64, 3 / 64), (-3 / 64, 7 / 64))
    columns = [np.ones(colors.shape), xx / 64, yy / 64, xx >= 32]
    if neural:
        columns.append(np.exp(-((xx - 23) ** 2 + (yy - 43) ** 2) / 600) * (colors + 1))
    n = len(columns)
    for fx, fy in frequencies:
        phase = 2 * np.pi * (fx * xx + fy * yy)
        columns.extend((np.sin(phase), np.cos(phase)))
    design = np.stack(columns, axis=-1).reshape(-1, n + 4)
    variance = 1 + (xx + 2 * yy) / 64
    selected = tuple(np.flatnonzero((mask & (colors == c)).ravel()) for c in range(3))
    operators = []
    for indices in selected:
        precision = 1 / np.sqrt(variance.ravel()[indices])
        operators.append(np.linalg.pinv(design[indices] * precision[:, None]) * precision[None])
    candidate = SimpleNamespace(
        discovery_mask=mask,
        frequencies_xy=frequencies,
        variance_cfa=variance,
        edge_geometry=(0.0, 0.0),
        design=design,
        selected_indices=selected,
        operators=operators,
        wave_slices=((n, n + 2), (n + 2, n + 4)),
        unit_keys=((0, 0), (1, 0)),
    )
    return candidate, colors


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("neural", [False, True])
def test_global_null_matches_independent_two_stage_wls_and_annihilates_nuisance(layout, neural):
    candidate, colors = fixture(layout, neural)
    operator = BackgroundPhaseOperator(candidate, colors, CONFIG)
    rng = np.random.default_rng(42)
    raw = rng.normal(size=colors.shape)
    n = candidate.wave_slices[0][0]
    for direction in (0, 1):
        residual, null = operator.residualize(raw, direction)
        a, b = candidate.wave_slices[1 - direction]
        competitor = candidate.design[:, a:b]
        nuisance_signal = np.empty(raw.size)
        for color, selected in enumerate(candidate.selected_indices):
            precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
            full_coefficient = np.linalg.lstsq(
                candidate.design[selected] * precision[:, None],
                raw.ravel()[selected] * precision,
                rcond=1e-10,
            )[0]
            background = candidate.design[:, :n] @ full_coefficient[:n]
            coefficient = np.linalg.lstsq(
                competitor[selected] * precision[:, None],
                (raw.ravel()[selected] - background[selected]) * precision,
                rcond=1e-10,
            )[0]
            destination = (colors == color).ravel()
            expected = background + competitor @ coefficient
            np.testing.assert_allclose(null.ravel()[destination], expected[destination], atol=4e-14)
            np.testing.assert_allclose(
                residual.ravel()[selected], raw.ravel()[selected] - expected[selected], atol=4e-14
            )
            full_null = np.column_stack((candidate.design[:, :n], competitor))
            nuisance_signal[destination] = (full_null @ rng.normal(size=n + 2))[destination]
        np.testing.assert_allclose(
            operator.apply(nuisance_signal.reshape(raw.shape))[direction], 0, atol=5e-13
        )


@pytest.mark.parametrize("layout", LAYOUTS)
def test_fixed_map_excludes_B_and_parent_difference_matches_actual_prediction(layout):
    candidate, colors = fixture(layout)
    operator = BackgroundPhaseOperator(candidate, colors, CONFIG)
    rng = np.random.default_rng(73)
    raw, other = rng.normal(size=(2, *colors.shape))
    parent = rng.normal(size=(3, *colors.shape))
    actual = operator.apply(raw)
    damaged = raw.copy()
    damaged[~candidate.discovery_mask] = np.nan
    np.testing.assert_array_equal(operator.apply(damaged), actual)
    np.testing.assert_allclose(
        operator.apply(2 * raw - other), 2 * actual - operator.apply(other), atol=4e-14
    )
    yy, xx = np.indices(colors.shape)
    expected = actual - operator.apply(parent[colors, yy, xx])
    np.testing.assert_allclose(operator.components(raw, parent), expected, atol=4e-14)
    np.testing.assert_array_equal(operator.components(raw, np.stack([raw] * 3)), 0)
    for direction, predictive in enumerate(operator.predict(damaged)):
        np.testing.assert_allclose(
            predictive.full_cfa - predictive.conditional_null_cfa[0],
            actual[direction, colors, yy, xx],
            atol=4e-14,
        )


def test_phase_kernel_recovers_narrow_periodic_profile_beyond_H1():
    candidate, colors = fixture(LAYOUTS[0], neural=False)
    # Known geometry in a noiseless operator unit test, never a measured quality claim.
    yy, xx = np.indices(colors.shape)
    phase = np.remainder((5 * xx + 3 * yy) / 64 + 0.5, 1) - 0.5
    target = np.exp(-((phase / 0.065) ** 2))
    target -= target.mean()
    operator = BackgroundPhaseOperator(candidate, colors, CONFIG)
    prediction = operator.apply(target)[0]
    h1 = np.empty_like(prediction)
    for color, selected in enumerate(candidate.selected_indices):
        coefficient = candidate.operators[color] @ target.ravel()[selected]
        h1[color] = (candidate.design[:, -4:-2] @ coefficient[-4:-2]).reshape(colors.shape)
    assert np.mean((prediction - target) ** 2) < 0.6 * np.mean((h1 - target) ** 2)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_integrated_H1_control_identity_and_ADC_bypass(layout):
    candidate, colors = fixture(layout)
    yy, xx = np.indices(colors.shape)
    rgb = np.stack([0.03 + 0.004 * np.cos(2 * np.pi * (5 * xx + 3 * yy) / 64)] * 3)
    raw = rgb[colors, yy, xx]
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    fields = tuple(
        WithheldBackground(rgb * 0.9, mask)
        for mask in (candidate.discovery_mask, ~candidate.discovery_mask)
    )
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
    }
    phase, aux = restore_neural_nuisance(
        rgb, packed, np.asarray(layout), fields, aggregation_config=CONFIG, **kwargs
    )
    baseline, _ = restore_neural_nuisance(rgb, packed, np.asarray(layout), fields, **kwargs)
    assert aux["aggregation_config"] == CONFIG.to_dict()
    for key, value in phase.items():
        if key[0].startswith("H1-"):
            np.testing.assert_array_equal(value, baseline[key])
        else:
            np.testing.assert_array_equal(value, rgb)
    # An attenuated parent makes the control comparison nontrivial: wrong
    # phase-derived support scores for H1 would change these actual corrections.
    attenuated, _ = restore_neural_nuisance(
        rgb * 0.4, packed, np.asarray(layout), fields, aggregation_config=CONFIG, **kwargs
    )
    control, _ = restore_neural_nuisance(rgb * 0.4, packed, np.asarray(layout), fields, **kwargs)
    for key, value in control.items():
        if key[0].startswith("H1-"):
            np.testing.assert_array_equal(attenuated[key], value)
    assert np.max(np.abs(control["H1-global", 0.0] - rgb * 0.4)) > 1e-5
    kwargs.update(shot=0.0, read=0.0)
    identity, _ = restore_neural_nuisance(
        rgb, packed, np.asarray(layout), None, aggregation_config=CONFIG, **kwargs
    )
    for value in identity.values():
        np.testing.assert_array_equal(value, rgb)
