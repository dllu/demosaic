"""Verify transport, evidence isolation and invalid donor geometry."""

import numpy as np
import pytest

from demosaic.donor_phase_geometry import transport_donor_geometry
from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate


def scene():
    y, x = np.indices((128, 128), dtype=np.float64) - 63.5
    packed_xy = np.stack((x, y), -1)
    colors = np.array([0, 1, 1, 2])
    frequencies = np.array([[0.122, 0.024], [-0.059, 0.082]])
    hessian = np.array([[6, -3], [-3, 3]]) / 128**2
    curve = 0.5 * ((packed_xy @ hessian) * packed_xy).sum(-1)
    first = packed_xy @ frequencies[0] + curve + 0.37
    second = packed_xy @ frequencies[1] - 0.15
    signal = 0.11 + 0.012 * np.cos(2 * np.pi * first) + 0.01 * np.cos(2 * np.pi * second)
    bayer = np.tile(colors.reshape(2, 2), (64, 64))
    raw = signal * np.array([0.9, 1, 0.8])[bayer]
    packed = raw.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
    return raw, colors, bayer, packed, frequencies, hessian


def test_disjoint_geometry_transport_measures_center_shift_and_rejects_overlap():
    pytest.importorskip("scipy.optimize")
    _, colors, _, packed, frequencies, hessian = scene()
    options = {"shot": 8e-5, "read": 2.56e-8}
    donor = (128, 0, 128, 128)
    query = (0, 0, 128, 128)
    result = transport_donor_geometry(packed, colors, donor, query, frequencies, **options)
    assert result["accepted"] == [True, False]
    np.testing.assert_allclose(
        result["frequencies_xy"][0], frequencies[0] + hessian @ [-128, 0], atol=0.001, rtol=0
    )
    np.testing.assert_allclose(np.asarray(result["hessians_xy"][0]), hessian, atol=1e-5, rtol=0)
    far = transport_donor_geometry(
        packed, colors, donor, (1024, 0, 128, 128), frequencies, **options
    )
    assert far["status"] == "distant donor"
    with pytest.raises(ValueError, match="disjoint"):
        transport_donor_geometry(packed, colors, donor, (64, 0, 128, 128), frequencies, **options)


def test_fixed_quadratic_query_refits_phase_without_the_other_fold():
    raw, _, bayer, _, frequencies, hessian = scene()
    mask = stratified_split(raw.shape, 811)
    options = {
        "shot": 8e-5,
        "read": 2.56e-8,
        "config": LocalWaveConfig(window=128, stride=128),
        "guide_frequencies_xy": frequencies,
        "phase_bins": 8,
    }
    stationary = fit_local_candidate(raw, bayer, mask, **options)
    options["guide_phase_hessians_xy"] = (hessian, np.zeros_like(hessian))
    changed = fit_local_candidate(raw, bayer, mask, **options)
    hidden = fit_local_candidate(np.where(mask, raw, np.nan), bayer, mask, **options)
    np.testing.assert_array_equal(changed.full_cfa, hidden.full_cfa)
    assert np.mean((changed.full_cfa[~mask] - raw[~mask]) ** 2) < 0.05 * np.mean(
        (stationary.full_cfa[~mask] - raw[~mask]) ** 2
    )
