"""The shared RAW phase field needs predictive support in both donors."""

import numpy as np
import pytest

from demosaic.bracket_phase_geometry import bracket_donor_geometry
from demosaic.search_donor_geometry import screening_mask


def example(*, mismatched_planar=False):
    nominal = np.array([[0.122, 0.024], [-0.059, 0.082]])
    H = np.array([[6, -3], [-3, 3]]) / 128**2
    colors = np.array([0, 1, 1, 2])
    cfa = np.tile(colors.reshape(2, 2), (64, 64))
    y, x = np.indices((128, 128), dtype=np.float64) - 63.5
    donors = []
    for dx, phase in [(-128, 0.27), (128, 0.65)]:
        xy = np.stack((x + dx, y), -1)
        if mismatched_planar:
            first = (xy @ nominal[0]) * (1.035 if dx < 0 else 1) + phase
        else:
            curvature = 0.5 * ((xy @ H) * xy).sum(-1)
            first = xy @ nominal[0] + curvature + phase
        second = xy @ nominal[1] - 0.15
        signal = 0.11 + 0.012 * np.cos(2 * np.pi * first) + 0.01 * np.cos(2 * np.pi * second)
        raw = signal * np.array([0.9, 1, 0.8])[cfa]
        packed = raw.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
        donors.append((packed, colors, (128 + dx, 0, 128, 128)))
    return nominal, H, donors


def test_bracket_interpolates_geometry_with_different_donor_phases():
    pytest.importorskip("scipy.optimize")
    frequencies, H, donors = example()
    result = bracket_donor_geometry(
        donors, (128, 0, 128, 128), frequencies, shot=8e-5, read=2.56e-8
    )
    assert result["accepted"] == [True, False]
    np.testing.assert_allclose(result["frequencies_xy"][0], frequencies[0], atol=0.001, rtol=0)
    np.testing.assert_allclose(result["hessians_xy"][0], H, atol=1e-5, rtol=0)


def test_bracket_rejects_a_flat_donor_and_unbracketed_query():
    pytest.importorskip("scipy.optimize")
    frequencies, _, donors = example()
    p, colors, box = donors[0]
    donors[0] = (np.full_like(p, 0.1), colors, box)
    noise = {"shot": 8e-5, "read": 2.56e-8}
    result = bracket_donor_geometry(donors, (128, 0, 128, 128), frequencies, **noise)
    assert result["accepted"] == [False, False]
    outside = bracket_donor_geometry(donors, (512, 0, 128, 128), frequencies, **noise)
    assert outside["status"] == "query is outside the bracket"
    with pytest.raises(ValueError, match="disjoint"):
        bracket_donor_geometry(donors, (64, 0, 128, 128), frequencies, **noise)


def test_shared_curvature_must_outpredict_individual_planar_donors():
    pytest.importorskip("scipy.optimize")
    frequencies, _, donors = example(mismatched_planar=True)
    result = bracket_donor_geometry(
        donors, (128, 0, 128, 128), frequencies, shot=8e-5, read=2.56e-8
    )
    assert np.all(np.asarray(result["heldout_error_reduction"])[..., 0] > 8)
    assert np.max(np.asarray(result["local_planar_error_reduction"])[..., 0]) < 0
    assert result["accepted"] == [False, False]


def test_bracket_refit_ignores_raw_sites_reserved_for_screening():
    pytest.importorskip("scipy.optimize")
    frequencies, _, donors = example()
    scope = [~screening_mask(box) for _, _, box in donors]
    modified = []
    for (packed, colors, box), eligible in zip(donors, scope, strict=True):
        h, w = eligible.shape
        packed_scope = eligible.reshape(h // 2, 2, w // 2, 2).transpose(1, 3, 0, 2)
        modified.append((np.where(packed_scope.reshape(packed.shape), packed, 0.4), colors, box))
    kwargs = {"shot": 8e-5, "read": 2.56e-8, "eligible_masks": scope}
    original = bracket_donor_geometry(donors, (128, 0, 128, 128), frequencies, **kwargs)
    changed = bracket_donor_geometry(modified, (128, 0, 128, 128), frequencies, **kwargs)
    assert any(original["accepted"])
    assert original == changed
