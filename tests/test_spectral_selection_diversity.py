import math

import numpy as np
import pytest
from frequency_coverage import eligible_bins, footprint
from spectral_selection_diversity import (
    pooled_score,
    sector_map,
    select_pooled,
    selection_geometry,
    template_proximity,
)


def independent_sorted(score, radius, quota=None):
    h, w = score.shape
    fy, fx = [np.fft.fftfreq(n) / 2 for n in [h, w]]
    pool = []
    for y in range(h):
        for x in range(w):
            if 1 / 16 <= math.hypot(fy[y], fx[x]) <= 1 / 3 and (
                fy[y] > 0 or (fy[y] == 0 and fx[x] > 0)
            ):
                pool.append((-float(score[y, x]), y, x))
    result = []
    counts = [0] * 4
    for _, y, x in sorted(pool):
        angle = math.atan2(fy[y], fx[x]) % math.pi
        s = min(int(angle / (math.pi / 4)), 3)
        if quota and counts[s] >= quota:
            continue
        if any(
            min(abs(y - a), h - abs(y - a)) <= radius and min(abs(x - b), w - abs(x - b)) <= radius
            for sy, sx in result
            for a, b in [(sy, sx), ((-sy) % h, (-sx) % w)]
        ):
            continue
        result.append([y, x])
        counts[s] += 1
        if len(result) == 8:
            break
    return result


@pytest.mark.parametrize("shape", [(32, 40), (64, 64)])
@pytest.mark.parametrize("radius", [1, 3])
@pytest.mark.parametrize("quota", [None, 2])
def test_ranked_selection_matches_independent_sorted_coordinates(shape, radius, quota):
    score = np.random.default_rng(18801).exponential(size=shape)
    actual = select_pooled(score, radius=radius, quota=quota)
    assert actual["bins"] == independent_sorted(score, radius, quota)
    if quota:
        assert actual["sector_counts"] == [2] * 4


def test_ties_are_row_major_and_all_zero_is_finite():
    score = np.zeros((32, 40))
    assert select_pooled(score)["bins"] == independent_sorted(score, 1)
    assert select_pooled(score)["scores"] == [0] * 8


def test_larger_radius_spreads_a_dominant_lobe_and_preserves_budget():
    score = np.ones((64, 64))
    score[7:20, 7:20] = 100
    a, b = [select_pooled(score, radius=r) for r in [1, 4]]
    assert len(a["bins"]) == len(b["bins"]) == 8
    assert (
        selection_geometry(score.shape, b["bins"], 4)["footprint_cells"]
        > selection_geometry(score.shape, a["bins"], 4)["footprint_cells"]
    )


@pytest.mark.parametrize("pattern", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
def test_pooling_uses_both_green_phases_and_ignores_red_blue(pattern):
    rng = np.random.default_rng(18802)
    raw = rng.normal(0, 0.001, (4, 32, 40))
    var = np.full_like(raw, 1e-6)
    a = pooled_score(raw, var, pattern)[0]
    green = np.flatnonzero(np.asarray(pattern) == 1)
    edited = raw.copy()
    edited[np.asarray(pattern) != 1] += 100
    np.testing.assert_array_equal(a, pooled_score(edited, var, pattern)[0])
    edited = raw.copy()
    edited[green[0]] = 0
    assert not np.array_equal(a, pooled_score(edited, var, pattern)[0])
    edited = raw.copy()
    edited[green] = edited[green[::-1]]
    np.testing.assert_array_equal(a, pooled_score(edited, var, pattern)[0])


def test_template_proximity_matches_explicit_toroidal_distances():
    shape = (32, 40)
    bins = [[5, 7], [7, 16]]
    power = np.random.default_rng(18803).uniform(size=shape)
    r = 3
    y, x = np.indices(shape)
    mask = np.zeros(shape, bool)
    for by, bx in bins:
        for a, b in [(by, bx), ((-by) % shape[0], (-bx) % shape[1])]:
            mask |= (np.minimum(abs(y - a), shape[0] - abs(y - a)) <= r) & (
                np.minimum(abs(x - b), shape[1] - abs(x - b)) <= r
            )
    np.testing.assert_array_equal(mask, footprint(shape, bins, r))
    result = template_proximity(power, bins, r)
    assert result["all_template_fraction"] == pytest.approx(power[mask].sum() / power.sum())
    half = eligible_bins(shape, 1e-12, math.sqrt(2) / 4)
    for degrees, fields in result["sectors"].items():
        labels = sector_map(shape, offset=math.radians(float(degrees)))
        for s in range(4):
            cells = half & (labels == s)
            assert fields["within_sector_proximity"][s] == pytest.approx(
                power[cells & mask].sum() / power[cells].sum()
            )


@pytest.mark.parametrize("damage", ["nan", "negative", "count", "radius", "quota"])
def test_invalid_inputs_reject(damage):
    score = np.ones((32, 40))
    kw = {}
    if damage == "nan":
        score[0, 0] = np.nan
    if damage == "negative":
        score[0, 0] = -1
    if damage == "count":
        kw["count"] = 0
    if damage == "radius":
        kw["radius"] = 0
    if damage == "quota":
        kw["quota"] = 3
    with pytest.raises(ValueError):
        select_pooled(score, **kw)


def test_qr_reference_reproduces_pooling_and_sorted_allocations():
    from selection_diversity_reference import qr_pooled, sorted_pooled

    rng = np.random.default_rng(18804)
    raw = rng.normal(0.01, 0.002, (4, 32, 40))
    variance = rng.uniform(1e-6, 5e-6, raw.shape)
    actual, powers, greens = pooled_score(raw, variance, [0, 1, 1, 2])
    expected, other = qr_pooled(raw, variance, greens)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(powers, other, rtol=1e-11, atol=1e-12)
    for radius, quota in [(1, None), (3, None), (1, 2)]:
        assert select_pooled(actual, radius=radius, quota=quota)["bins"] == sorted_pooled(
            expected, radius, quota
        )


def test_independent_sector_proximity_handles_boundary_frequencies():
    from selection_diversity_reference import reference_proximity

    power = np.random.default_rng(18805).uniform(size=(32, 40))
    bins = [[4, 5], [7, 19]]
    a = template_proximity(power, bins, 3)
    fraction, details = reference_proximity(power, bins, 3)
    assert a["all_template_fraction"] == pytest.approx(fraction)
    for angle, fields in details.items():
        for name, values in fields.items():
            np.testing.assert_allclose(a["sectors"][angle][name], values, atol=1e-14)
