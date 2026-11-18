"""Test local support and held-out confirmation for RAW donor brackets."""

import numpy as np

import demosaic.localized_donor_geometry as local
from demosaic.search_donor_geometry import screening_mask

COLORS = np.array([0, 1, 1, 2])
NOISE = {"shot": 8e-5, "read": 2.56e-8}
QUERY = (0, 0, 128, 128)


def _patch(x, phase, *, flat=False):
    y, xx = np.indices((128, 128))
    raw = np.full((128, 128), 0.13)
    if not flat:
        angle = 2 * np.pi * (0.106 * xx + 0.044 * y + phase)
        raw += np.where((xx >= 32) & (xx < 96) & (y >= 32) & (y < 96), 0.023 * np.cos(angle), 0)
    return raw, (x, 0, 128, 128)


def _pack(raw, box):
    packed = raw.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
    return packed, COLORS, box


def test_partial_carrier_is_verified_from_a_fixed_window_pair():
    a, ax = _patch(-128, 0.27)
    b, bx = _patch(128, 0.59)
    result = local.localize_donor_geometry([_pack(a, ax), _pack(b, bx)], QUERY, **NOISE)
    assert result["active"] == [True, False]
    np.testing.assert_allclose(result["frequencies_xy"][0], [0.106, 0.044], atol=0.002)
    assert all(box[2] in (64, 96) for box in result["windows"])
    assert np.min(np.asarray(result["heldout_planar_reduction"])[..., 0]) > 8


def test_validation_failure_does_not_try_a_second_screening_pair(monkeypatch):
    # Both donors contain a strong A-only impostor backed by held-out flats.
    a, ax = _patch(-128, 0.27)
    b, bx = _patch(128, 0.59)
    views = [
        _pack(np.where(screening_mask(box), raw, 0.13), box) for raw, box in ((a, ax), (b, bx))
    ]
    true_validate = local._verify_planes
    checks = []

    def observed(*args, **kwargs):
        checks.append(args[0].shape)
        return true_validate(*args, **kwargs)

    monkeypatch.setattr(local, "_verify_planes", observed)
    result = local.localize_donor_geometry(views, QUERY, unequal=True, **NOISE)
    assert result["status"] == "evaluated"
    assert result["active"] == [False, False]
    assert len(checks) == 2
    np.testing.assert_allclose(result["heldout_planar_reduction"], 0, atol=1e-18)


def test_query_ranking_uses_only_screening_pixels():
    a, ax = _patch(-128, 0.27)
    b, bx = _patch(128, 0.59)
    q, _ = _patch(0, 0.4)
    donors = [_pack(a, ax), _pack(b, bx)]
    kwargs = {"unequal": True, "refined_edge": True, **NOISE}
    original = local.localize_donor_geometry(
        donors, QUERY, query_measurements=_pack(q, QUERY)[:2], **kwargs
    )
    screened = np.where(screening_mask(QUERY), q, np.nan)
    check = local.localize_donor_geometry(
        donors, QUERY, query_measurements=_pack(screened, QUERY)[:2], **kwargs
    )
    assert original == check
    assert "screened_query_score" in check


def test_parallel_edge_null_rejects_a_screened_rail_without_reselecting():
    yy, xx = np.indices((128, 128)) - 63.5
    coordinate = np.cos(0.92) * xx + np.sin(0.92) * yy
    donors = []
    for start, shift in ((-128, 0.0), (128, 3.25)):
        projection = coordinate + shift
        raw = 0.08 + 0.14 * ((projection > -3.5) & (projection < 7.0))
        donors.append(_pack(raw, (start, 0, 128, 128)))
    options = {"unequal": True, "refined_edge": True, **NOISE}
    single = local.localize_donor_geometry(donors, QUERY, **options)
    parallel = local.localize_donor_geometry(donors, QUERY, parallel_edge=True, **options)
    assert any(single["active"])
    assert parallel["active"] == [False, False]
    assert parallel["windows"] == single["windows"]
    assert parallel["frequencies_xy"] == single["frequencies_xy"]
