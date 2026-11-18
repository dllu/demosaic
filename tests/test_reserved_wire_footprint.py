"""Isolation of the coarse support search from the query restoration sites."""

import numpy as np
import pytest

from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.reserved_wire_footprint import select_wire_footprint, wire_footprint
from demosaic.search_donor_geometry import screening_mask


@pytest.mark.parametrize("second_active", [False, True])
def test_wire_location_uses_only_the_reserved_samples(second_active):
    shape = (128, 128)
    query = (44, 56, *shape[::-1])
    center = (87.5, 55.5)
    yy, xx = np.indices(shape)
    envelope = wire_footprint(shape, center)
    guide = ((0.078, 0.034), (-0.041, 0.073))
    phase = 2 * np.pi * (guide[0][0] * xx + guide[0][1] * yy)
    rng = np.random.default_rng(124)
    raw = 0.08 + 0.06 * (xx > 64) + 0.009 * envelope * np.cos(phase + 0.3)
    raw += rng.normal(0, 0.0008, size=shape)
    reserved = screening_mask(query)
    damaged = np.where(reserved, raw, np.nan)
    colors = np.array([0, 1, 1, 2])
    config = LocalWaveConfig(window=128, stride=64)
    results = []
    for samples in (raw, damaged):
        packed = samples.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
        results.append(
            select_wire_footprint(
                packed,
                colors,
                query,
                guide,
                [True, second_active],
                shot=0,
                read=0.0008**2,
                config=config,
                record_partner=True,
            )
        )
    (m, a), (n, b) = results
    assert a == b
    assert a["confirmed"]
    assert a["winner"]["direction"] == 0
    if second_active:
        assert sorted(a["partner"]) == ["localization_scores", "wave_scores"]
        assert all(len(v) == 2 and np.isfinite(v).all() for v in a["partner"].values())
    else:
        assert "partner" not in a
    assert np.linalg.norm(np.asarray(a["winner"]["center_xy"]) - center) < 12
    np.testing.assert_array_equal(m["confirmed"], n["confirmed"])
    assert not m["confirmed"][0, 0]
