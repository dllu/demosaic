"""Independent query SVDs, CFA withholding and compact signal reconstruction."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import (
    LocalWaveConfig,
    restore_conditional_waves,
    restore_local_waves,
)
from demosaic.neural_nuisance import WithheldBackground, restore_neural_nuisance
from demosaic.spatial_carrier_amplitudes import SpatialCarrierOperator


def fixture(layout=(0, 1, 1, 2)):
    y, x = np.mgrid[:64, :64]
    colors = np.tile(np.array(layout).reshape(2, 2), (32, 32))
    mask = stratified_split(x.shape, 71)
    step = x + 0.4 * y > 51
    basis = np.stack([np.ones(x.shape), x / 64, y / 64, step], axis=-1)
    waves = [
        v
        for f in [(0.11, 0.04), (-0.04, 0.13)]
        for v in [
            np.cos(2 * np.pi * (f[0] * x + f[1] * y)),
            np.sin(2 * np.pi * (f[0] * x + f[1] * y)),
        ]
    ]
    design = np.column_stack([basis.reshape(-1, 4), *[v.ravel() for v in waves]])
    variance = 0.00001 * (1 + step)
    candidate = SimpleNamespace(
        design=design,
        discovery_mask=mask,
        variance_cfa=variance,
        unit_slices=((4, 6), (6, 8)),
        wave_slices=((4, 6), (6, 8)),
        unit_keys=((0, 0), (1, 0)),
    )
    rgb = np.array([0.8, 1, 0.6])[:, None, None] * (
        0.03 + 0.2 * step + 0.005 * waves[0] + 0.003 * waves[2]
    )
    raw = rgb[colors, y, x] + np.random.default_rng(8).normal(0, 0.0002, x.shape)
    attach_global_operators(candidate, colors)
    return candidate, colors, raw, rgb


def attach_global_operators(candidate, colors):
    operators = []
    for color in range(3):
        selected = (candidate.discovery_mask & (colors == color)).ravel()
        precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
        operators.append(
            np.linalg.pinv(candidate.design[selected] * precision[:, None], rcond=1e-10)
            * precision[None]
        )
    candidate.operators = tuple(operators)


@pytest.mark.parametrize("neural", [False, True])
@pytest.mark.parametrize("nuisance_mode", ["local", "global"])
def test_query_predictions_match_independent_column_scaled_svd(neural, nuisance_mode):
    candidate, colors, raw, rgb = fixture()
    field = None
    if neural:
        field = WithheldBackground(
            rgb + 0.001 * np.sin(np.indices(raw.shape)[1])[None], candidate.discovery_mask
        )
        yy, xx = np.indices(raw.shape)
        feature = field.rgb[colors, yy, xx]
        candidate.design = np.insert(candidate.design, 4, feature.ravel(), axis=1)
        candidate.unit_slices = candidate.wave_slices = ((5, 7), (7, 9))
        attach_global_operators(candidate, colors)
    operator = SpatialCarrierOperator(
        candidate, colors, window=33, stride=16, background=field, nuisance_mode=nuisance_mode
    )
    for group in operator.groups:
        coefficient, nulls = operator.coefficients(raw, group)
        for iy, ix in [(0, 0), (2, 2), (4, 4), (1, 3)]:
            y, x = operator.ay[iy], operator.ax[ix]
            selected = group["selected"].copy()
            yy, xx = np.indices(raw.shape)
            selected &= (abs(yy - y) <= 16) & (abs(xx - x) <= 16)
            sigma = np.sqrt(group["weights"][selected])
            for keep, actual in [
                (np.ones(operator.design.shape[1], bool), coefficient),
                *zip(operator.keep, nulls, strict=True),
            ]:
                matrix = operator.design[selected.ravel()][:, keep] * sigma[:, None]
                norm = np.linalg.norm(matrix, axis=0)
                scale = np.divide(1, norm, out=np.zeros_like(norm), where=norm > 0)
                values = raw[selected]
                if nuisance_mode == "global":
                    global_selected = group["selected"].ravel()
                    precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[global_selected])
                    global_fit = np.linalg.lstsq(
                        candidate.design[global_selected] * precision[:, None],
                        raw.ravel()[global_selected] * precision,
                        rcond=1e-10,
                    )[0]
                    values = (
                        values
                        - candidate.design[selected.ravel(), : operator.nuisance_columns]
                        @ global_fit[: operator.nuisance_columns]
                    )
                expected = scale * (np.linalg.pinv(matrix * scale, rcond=1e-4) @ (values * sigma))
                native = group["native"][y * 64 + x, keep]
                assert abs(native @ expected - native @ actual[iy, ix]) < 2e-8


@pytest.mark.parametrize("layout", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
@pytest.mark.parametrize("nuisance_mode", ["local", "global"])
def test_local_operator_withholding_linearity_and_constant_null(layout, nuisance_mode):
    candidate, colors, raw, rgb = fixture(layout)
    operator = SpatialCarrierOperator(
        candidate, colors, window=33, stride=16, nuisance_mode=nuisance_mode
    )
    original = operator.predict(raw)
    damaged = raw.copy()
    damaged[~candidate.discovery_mask] = np.nan
    repeat = operator.predict(damaged)
    for key in ["full_cfa", "conditional_null_cfa"]:
        np.testing.assert_array_equal(getattr(original, key), getattr(repeat, key))
    a, _ = operator.components(raw, rgb)
    b, _ = operator.components(damaged, rgb)
    np.testing.assert_array_equal(a[0], b[0])
    zero = np.zeros_like(rgb)
    first = operator.components(raw, zero)[0][0]
    second = operator.components(raw * 2, zero)[0][0]
    np.testing.assert_allclose(second, 2 * first, atol=1e-10)
    constant = np.full_like(raw, 0.12)
    flat = operator.predict(constant)
    np.testing.assert_allclose(flat.full_cfa, 0.12, atol=1e-8)
    np.testing.assert_allclose(flat.conditional_null_cfa, 0.12, atol=1e-8)
    np.testing.assert_allclose(operator.components(constant, zero)[0][0], 0, atol=1e-8)
    assert np.isfinite(operator.fractions).all() and np.isfinite(operator.spectra).all()


@pytest.mark.parametrize("nuisance_mode", ["local", "global"])
def test_compact_carrier_local_fit_reduces_global_amplitude_dilution(nuisance_mode):
    candidate, colors, _, _ = fixture()
    y, x = np.indices(colors.shape)
    envelope = np.exp(-((x - 32) ** 2 + (y - 32) ** 2) / (2 * 8**2))
    truth = 0.003 * envelope * candidate.design[:, 6].reshape(colors.shape)
    rgb_truth = np.broadcast_to(truth, (3, *truth.shape))
    operator = SpatialCarrierOperator(
        candidate, colors, window=17, stride=8, nuisance_mode=nuisance_mode
    )
    local = operator.components(truth, np.zeros_like(rgb_truth))[0][0][1]
    global_value = []
    for color in range(3):
        selected = (candidate.discovery_mask & (colors == color)).ravel()
        coefficient = np.linalg.lstsq(
            candidate.design[selected], truth.ravel()[selected], rcond=1e-10
        )[0]
        global_value.append((candidate.design[:, 6:8] @ coefficient[6:8]).reshape(truth.shape))
    assert np.mean((local - rgb_truth) ** 2) < 0.6 * np.mean(
        (np.asarray(global_value) - rgb_truth) ** 2
    )


@pytest.mark.parametrize("amplitude_window", [0, 33])
@pytest.mark.parametrize("nuisance_mode", ["local", "global"])
def test_spatial_raw_wave_controls_match_standalone_shared_partition(
    amplitude_window, nuisance_mode
):
    candidate, _colors, raw, rgb = fixture()
    packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])
    layout = np.array([0, 1, 1, 2])
    config = LocalWaveConfig(
        window=64,
        stride=32,
        validation_window=33,
        edge_refinements=1,
        amplitude_window=amplitude_window,
        amplitude_stride=16,
        amplitude_nuisance=nuisance_mode,
    )
    backgrounds = [
        WithheldBackground(rgb, mask)
        for mask in [candidate.discovery_mask, ~candidate.discovery_mask]
    ]
    outputs, aux = restore_neural_nuisance(
        rgb,
        packed,
        layout,
        backgrounds,
        shot=8e-5,
        read=2.56e-8,
        thresholds=(0, 2),
        config=config,
        reselect_frequencies=False,
    )
    standalone, _ = restore_local_waves(
        rgb,
        packed,
        layout,
        shot=8e-5,
        read=2.56e-8,
        thresholds=(0, 2),
        config=config,
        discovery_mask=candidate.discovery_mask,
    )
    for (mode, threshold), value in standalone.items():
        np.testing.assert_array_equal(outputs["H1-" + mode, threshold], value)
    conditional, _ = restore_conditional_waves(
        rgb,
        packed,
        layout,
        shot=8e-5,
        read=2.56e-8,
        thresholds=(0, 2),
        config=config,
        discovery_mask=candidate.discovery_mask,
    )
    for (mode, threshold), value in conditional.items():
        np.testing.assert_array_equal(outputs["conditional-" + mode, threshold], value)
    assert aux["parent_used_for_discovery_or_validation"] is False


def test_fixed_global_background_span_and_parent_projection_share_one_operator():
    candidate, colors, raw, rgb = fixture()
    operator = SpatialCarrierOperator(
        candidate, colors, window=33, stride=16, nuisance_mode="global"
    )
    zero = np.zeros_like(rgb)
    base = operator.components(raw, zero)[0][0]
    delta = np.zeros_like(raw)
    for group in operator.groups:
        delta[group["selected"]] = (
            group["sensor_background"] @ np.arange(1, operator.nuisance_columns + 1) * 0.01
        )
    np.testing.assert_allclose(operator.components(raw + delta, zero)[0][0], base, atol=1e-9)
    y, x = np.indices(raw.shape)
    parent_cfa = rgb[colors, y, x]
    projected = operator.components(parent_cfa, zero)[0][0]
    np.testing.assert_allclose(operator.components(raw, rgb)[0][0], base - projected, atol=1e-9)
    predicted = operator.predict(raw)
    for unit in range(2):
        np.testing.assert_allclose(
            predicted.full_cfa - predicted.conditional_null_cfa[unit],
            base[unit, colors, y, x],
            atol=1e-10,
        )


def test_invalid_local_geometry_rejected():
    candidate, colors, _, _ = fixture()
    with pytest.raises(ValueError):
        SpatialCarrierOperator(candidate, colors, window=16)
    with pytest.raises(ValueError):
        LocalWaveConfig(amplitude_window=16)
