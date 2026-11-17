"""Independent weighted least squares, native CFA withholding and legacy paths."""

from dataclasses import replace

import numpy as np
import pytest

from demosaic.carrier_spectrum import discovery_weights, weighted_spectrum
from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate


@pytest.mark.parametrize("competitor", [False, True])
@pytest.mark.parametrize("taper", [False, True])
def test_fft_benefit_matches_independent_explicit_weighted_least_squares(competitor, taper):
    y, x = np.mgrid[:16, :20]
    mask = np.random.default_rng(62).random(x.shape) < 0.5
    selected = (mask & ((x + y) % 2 == 1)).ravel()
    raw = np.random.default_rng(8).normal(size=x.shape)
    nuisance = np.column_stack((np.ones(x.size), x.ravel(), y.ravel(), (x > 11).ravel()))
    if competitor:
        nuisance = np.column_stack((nuisance, np.cos(2 * np.pi * x.ravel() / 5)))
    weights = np.exp(np.linspace(-2, 2, selected.sum()))
    if taper:
        weights *= np.outer(np.hanning(18)[1:-1], np.hanning(22)[1:-1]).ravel()[selected]
    spectrum = weighted_spectrum(raw, selected, nuisance, weights)
    sigma = np.sqrt(weights / weights.mean())
    basis = nuisance[selected] * sigma[:, None]
    values = raw.ravel()[selected] * sigma
    coefficient = np.linalg.lstsq(basis, values, rcond=1e-10)[0]
    baseline = np.sum((values - basis @ coefficient) ** 2)
    for iy, ix in [(1, 2), (3, 4), (4, 1), (2, 7), (6, 3), (1, 9)]:
        phase = 2 * np.pi * (x * np.fft.fftfreq(20)[ix] + y * np.fft.fftfreq(16)[iy])
        waves = np.column_stack((np.cos(phase).ravel(), np.sin(phase).ravel()))
        design = np.column_stack((basis, waves[selected] * sigma[:, None]))
        coefficient = np.linalg.lstsq(design, values, rcond=1e-10)[0]
        benefit = baseline - np.sum((values - design @ coefficient) ** 2)
        assert abs(benefit - spectrum[iy, ix]) < 1e-11
    np.testing.assert_allclose(
        spectrum, weighted_spectrum(raw, selected, nuisance, 17 * weights), atol=1e-11
    )
    raw.ravel()[~selected] = np.nan
    np.testing.assert_array_equal(spectrum, weighted_spectrum(raw, selected, nuisance, weights))


@pytest.mark.parametrize("layout", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
@pytest.mark.parametrize("mode", ["inverse-variance", "hann-inverse-variance"])
def test_weighted_local_discovery_has_no_withheld_value_dependence(layout, mode):
    y, x = np.mgrid[:64, :64]
    truth = 0.03 + 0.2 * (x + y > 96) + 0.003 * np.cos(2 * np.pi * (0.09 * x + 0.04 * y))
    raw = truth + np.random.default_rng(9).normal(size=x.shape) * np.sqrt(8e-5 * truth + 2.56e-8)
    colors = np.tile(np.array(layout).reshape(2, 2), (32, 32))
    mask = stratified_split(raw.shape, 69)
    config = LocalWaveConfig(
        window=64,
        stride=32,
        validation_window=33,
        edge_search="full-frame",
        frequency_weighting=mode,
    )
    args = {"shot": 8e-5, "read": 2.56e-8, "config": config}
    original = fit_local_candidate(raw, colors, mask, **args)
    damaged = raw.copy()
    damaged[~mask] = np.nan
    repeated = fit_local_candidate(damaged, colors, mask, **args)
    assert original.frequencies_xy == repeated.frequencies_xy
    assert original.edge_geometry == repeated.edge_geometry
    for field in ["full_cfa", "conditional_null_cfa", "variance_cfa", "coefficients"]:
        np.testing.assert_array_equal(getattr(original, field), getattr(repeated, field))
    for a, b in zip(original.operators, repeated.operators, strict=True):
        np.testing.assert_array_equal(a, b)


def test_hann_variance_proxy_is_fixed_a_only_and_invalid_weights_reject():
    y, x = np.mgrid[:16, :20]
    mask = (np.random.default_rng(66).random(x.shape) < 0.5).ravel()
    basis = np.column_stack((np.ones(x.size), x.ravel(), y.ravel()))
    raw = 0.02 + 0.001 * x + 0.0005 * y
    expected = 1 / (2.56e-8 + 8e-5 * raw.ravel()[mask])
    axes = [0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(n) + 0.5) / n) for n in raw.shape]
    expected *= np.outer(*axes).ravel()[mask]
    weights = discovery_weights(raw, mask, basis, shot=8e-5, read=2.56e-8, hann=True)
    np.testing.assert_allclose(weights, expected, rtol=1e-14)
    damaged = raw.copy()
    damaged.ravel()[~mask] = np.nan
    np.testing.assert_array_equal(
        weights, discovery_weights(damaged, mask, basis, shot=8e-5, read=2.56e-8, hann=True)
    )
    with pytest.raises(ValueError):
        weighted_spectrum(raw, mask, basis, np.zeros(mask.sum()))
    with pytest.raises(ValueError):
        weighted_spectrum(raw, mask, basis, np.ones(mask.sum() - 1))
    with pytest.raises(ValueError):
        weighted_spectrum(raw, mask, np.ones((raw.size, 2)), np.ones(mask.sum()))
    with pytest.raises(ValueError):
        replace(LocalWaveConfig(), frequency_weighting="unknown")
