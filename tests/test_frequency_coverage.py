import numpy as np
import pytest
from frequency_coverage import (
    eligible_bins,
    footprint,
    power_fraction,
    sample_camera_rgb,
    select_bins,
)
from phase_frequency_holdout import select_phase_frequencies


def independent_sorted_selection(spectrum, variance, allowed, count):
    h, w = spectrum.shape
    result = []
    candidates = sorted(
        [(float(abs(spectrum[y, x]) ** 2 / variance[y, x]), y, x) for y, x in np.argwhere(allowed)],
        key=lambda r: (-r[0], r[1], r[2]),
    )
    for _, y, x in candidates:
        if any(
            min(abs(y - a), h - abs(y - a)) <= 1 and min(abs(x - b), w - abs(x - b)) <= 1
            for a, b in [v for q in result for v in [q, ((-q[0]) % h, (-q[1]) % w)]]
        ):
            continue
        result.append((y, x))
        if len(result) == count:
            break
    return [list(q) for q in result]


@pytest.mark.parametrize("shape", [(16, 24), (31, 32), (32, 32)])
@pytest.mark.parametrize(
    "band", [(1 / 16, 1 / 3, True), (1 / 32, 1 / 16, False), (1 / 32, 1 / 3, True)]
)
def test_selection_matches_independent_sorted_search_and_legacy(shape, band):
    rng = np.random.default_rng(18601)
    z = rng.normal(size=shape) + 1j * rng.normal(size=shape)
    v = rng.uniform(0.1, 2, shape)
    allowed = eligible_bins(shape, *band[:2], upper_inclusive=band[2])
    actual = select_bins(z, v, allowed)
    assert actual == independent_sorted_selection(z, v, allowed, 4)
    if band[0] == 1 / 16:
        assert actual == [list(q) for q in select_phase_frequencies(z, v)]


def test_dyadic_lower_band_retains_excluded_24pixel_fundamental():
    h, w = 96, 96
    y, x = np.indices((h, w))
    signal = np.cos(2 * np.pi * (2 * x) / 24) + 0.2 * np.cos(2 * np.pi * (2 * y) / 8)
    z = np.fft.fft2(signal, norm="ortho")
    v = np.ones_like(signal)
    high = eligible_bins((h, w), 1 / 16, 1 / 3)
    low = eligible_bins((h, w), 1 / 32, 1 / 16, upper_inclusive=False)
    assert not (high & low).any()
    assert [0, 8] not in select_bins(z, v, high) and [0, 8] in select_bins(z, v, low)
    power = abs(z) ** 2
    assert power_fraction(power, footprint((h, w), select_bins(z, v, high), 0)) < 0.05
    assert power_fraction(power, footprint((h, w), select_bins(z, v, low), 0)) > 0.95


def test_ties_are_lexicographic_input_mask_unmodified_and_scale_invariant():
    z = np.ones((16, 16), complex)
    v = np.ones((16, 16))
    mask = eligible_bins(z.shape, 1 / 32, 1 / 3)
    saved = mask.copy()
    actual = select_bins(z, v, mask)
    assert actual == independent_sorted_selection(z, v, mask, 4)
    assert actual == select_bins(z * 8, v * 64, mask) and np.array_equal(mask, saved)


def test_footprint_wrap_conjugate_union_and_nested_radius():
    mask = footprint((16, 20), [[0, 19]], 1)
    assert mask[0, 0] and mask[15, 18] and mask[0, 1] and mask[1, 2]
    assert np.all(mask <= footprint((16, 20), [[0, 19]], 4))
    assert power_fraction(np.zeros((16, 20)), mask) is None
    assert power_fraction(np.ones((16, 20)), mask) == np.count_nonzero(mask) / 320


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_cfa_sampling_matches_explicit_native_samples(colors):
    image = np.arange(3 * 16 * 20).reshape(1, 3, 16, 20).astype(float)
    actual = sample_camera_rgb(image, np.array([colors]))
    for p, c in enumerate(colors):
        np.testing.assert_array_equal(actual[0, p], image[0, c, p // 2 :: 2, p % 2 :: 2])


@pytest.mark.parametrize("damage", ["variance", "mask", "count", "nonfinite", "bins", "band"])
def test_bad_contracts_reject(damage):
    z = np.ones((16, 16), complex)
    v = np.ones((16, 16))
    mask = np.ones((16, 16), bool)
    if damage == "variance":
        v[0, 0] = 0
    if damage == "mask":
        mask = mask.astype(int)
    if damage == "nonfinite":
        z[0, 0] = np.nan
    with pytest.raises(ValueError):
        if damage == "bins":
            footprint(z.shape, [[0, 16]], 1)
        elif damage == "band":
            eligible_bins(z.shape, 1 / 16, 1 / 32)
        else:
            select_bins(z, v, mask, count=0 if damage == "count" else 4)


def test_counterfactual_selection_is_independent_of_other_phase_and_targets():
    from report_frequency_coverage import measure_input

    rng = np.random.default_rng(18602)
    arrays = {
        "packed": rng.normal(0.02, 0.002, (1, 4, 64, 64)).astype("f4"),
        "variance": np.full((1, 4, 64, 64), 2e-6, dtype="f4"),
        "colors": np.array([[0, 1, 1, 2]], dtype="i8"),
    }
    actual = [[[3, 7], [6, 10], [9, 13], [12, 16]], [[4, 8], [7, 11], [10, 14], [13, 17]]]
    first, stats = measure_input(arrays, actual)

    class ForbiddenTarget:
        def __array__(self, *args, **kwargs):
            raise AssertionError("Target must not enter selection")

    arrays["target"] = ForbiddenTarget()
    arrays["packed"][:, 2] = rng.normal(0.1, 0.02, (1, 64, 64))
    arrays["variance"][:, 2] *= 8
    changed, newstats = measure_input(arrays, actual)
    for key in ["FP64_high4", "lower4", "broad4"]:
        assert first[key][0] == changed[key][0]
    assert first["actual_high4"] == changed["actual_high4"] == actual
    assert first["balanced8"][0] == actual[0] + first["lower4"][0]
    assert all(
        a["selection_power"] == b["selection_power"]
        for a, b in zip(stats["broad4"][:4], newstats["broad4"][:4], strict=True)
    )


def test_numeric_group_identity_survives_metric_reduction():
    from report_frequency_coverage import summarize

    rows = [
        {"present": True, "nominal_fundamentals_below_high": 1, "fraction": 0.1},
        {"present": True, "nominal_fundamentals_below_high": 1, "fraction": 0.3},
        {"present": True, "nominal_fundamentals_below_high": 2, "fraction": 0.7},
    ]
    groups = summarize(rows, ["present", "nominal_fundamentals_below_high"])
    assert [r["nominal_fundamentals_below_high"] for r in groups] == [1, 2]
    assert [r["cases"] for r in groups] == [2, 1]
    assert groups[0]["fraction"]["mean"] == 0.2 and groups[1]["fraction"]["mean"] == 0.7
