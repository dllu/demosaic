import numpy as np
import pytest

from native_alias_geometry import carrier_footprints, native_regions, power_summary, signed_bins


@pytest.mark.parametrize("shape", [(16, 16), (16, 24), (17, 19)])
def test_masks_against_direct_distance(shape):
    bins = np.array([[3, 2], [shape[0] // 2, shape[1] - 2]])
    for radius in [0, 1, 3]:
        first, union = carrier_footprints(shape, bins, radius)
        yy, xx = np.indices(tuple(2 * n for n in shape))
        expected = []
        for ay, ax in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            mask = np.zeros_like(yy, dtype=bool)
            for y, x in bins:
                y = y if y < (shape[0] + 1) // 2 else y - shape[0]
                x = x if x < (shape[1] + 1) // 2 else x - shape[1]
                y, x = y + ay * shape[0], x + ax * shape[1]
                for sign in [-1, 1]:
                    dy = (yy - sign * y) % (2 * shape[0])
                    dx = (xx - sign * x) % (2 * shape[1])
                    mask |= (np.minimum(dy, 2 * shape[0] - dy) <= radius) & (
                        np.minimum(dx, 2 * shape[1] - dx) <= radius
                    )
            expected.append(mask)
        np.testing.assert_array_equal(first, expected[0])
        np.testing.assert_array_equal(union, np.logical_or.reduce(expected))
        np.testing.assert_array_equal(first, first[(-yy) % len(yy), (-xx) % xx.shape[1]])


@pytest.mark.parametrize("layout", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_four_aliases_and_two_green_ambiguity(layout):
    h, w = 16, 24
    y, x = np.indices((2 * h, 2 * w))
    principal = np.exp(2j * np.pi * (3 * y / (2 * h) - 4 * x / (2 * w)))
    signatures = []
    greens = np.flatnonzero(np.asarray(layout) == 1)
    for ay, ax in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        wave = np.exp(2j * np.pi * ((3 + ay * h) * y / (2 * h) + (-4 + ax * w) * x / (2 * w)))
        phase = []
        for p in greens:
            py, px = divmod(int(p), 2)
            ratio = wave[py::2, px::2] / principal[py::2, px::2]
            np.testing.assert_allclose(ratio, (-1) ** (ay * py + ax * px), atol=8e-14)
            phase.append((-1) ** (ay * py + ax * px))
        signatures.append(phase[1] * phase[0])
    assert sorted(signatures) == [-1, -1, 1, 1]


@pytest.mark.parametrize("alias", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_native_carrier_power_placement(alias):
    shape = (16, 24)
    y, x = np.indices((32, 48))
    ky, kx = 3 + alias[0] * 16, 4 + alias[1] * 24
    wave = np.cos(2 * np.pi * (ky * y / 32 + kx * x / 48) + 0.31)
    power = abs(np.fft.fft2(wave)) ** 2
    summary = power_summary(power, shape, np.array([[3, 4]]), 0)
    assert summary["four_lift_carrier_proximity"] == pytest.approx(1)
    assert summary["principal_carrier_proximity"] == pytest.approx(int(alias == (0, 0)), abs=1e-25)


def test_nyquist_center_lifts_before_expansion_and_partition():
    first, union = carrier_footprints((16, 24), np.array([[8, 0]]), 1)
    assert first[7, 0] and first[9, 0] and first[-7, 0] and first[-9, 0]
    assert np.all(union >= first)
    r = native_regions((32, 48))
    np.testing.assert_array_equal(
        sum(
            r[k].astype(int)
            for k in [
                "strict_principal_square",
                "quarter_cycle_boundary",
                "outside_closed_principal_square",
            ]
        ),
        np.ones((32, 48)),
    )
    assert r["quarter_cycle_boundary"][8, 0] and r["quarter_cycle_boundary"][-8, 0]


@pytest.mark.parametrize(
    "shape,bins,radius",
    [
        ((8, 8), [[8, 0]], 0),
        ((8, 8), [[1.0, 0]], 0),
        ((8, 8), [[1, 0]], -1),
        ((8, 8), [[1, 0]], 4),
        ((7, 8), [[1, 0]], 0),
    ],
)
def test_invalid_geometry(shape, bins, radius):
    with pytest.raises(ValueError):
        carrier_footprints(shape, np.asarray(bins), radius)


def test_invalid_power_and_signed_axes():
    np.testing.assert_array_equal(signed_bins((8, 9), [[4, 4], [7, 8]]), [[-4, 4], [-1, -1]])
    for power in [
        np.zeros((16, 16)),
        np.full((16, 16), np.nan),
        -np.ones((16, 16)),
        np.ones((8, 8)),
    ]:
        with pytest.raises(ValueError):
            power_summary(power, (8, 8), np.array([[1, 0]]), 1)


def test_qr_native_and_independent_summary():
    from audit_native_alias_geometry import qr_native_power, reference_summary
    from green_phase_spectrum import tapered_spectrum

    rng = np.random.default_rng(19001)
    signal = rng.normal(size=(1, 3, 32, 48))
    power = sum(abs(tapered_spectrum(v)["spectrum"]) ** 2 for v in signal[0])
    np.testing.assert_allclose(qr_native_power(signal), power, rtol=2e-13, atol=2e-14)
    for radius in [0, 1, 3]:
        bins = np.array([[8, 0], [2, 9]])
        expected = reference_summary(power, (16, 24), bins, radius)
        actual = power_summary(power, (16, 24), bins, radius)
        assert actual.keys() == expected.keys()
        for key in actual:
            assert actual[key] == pytest.approx(expected[key], abs=1e-14)


def test_qr_removes_affine_native_template():
    from audit_native_alias_geometry import qr_native_power

    y, x = np.indices((32, 48))
    planes = np.stack([3 + 0.3 * x - 0.2 * y, -2 + 0.6 * x + 0.1 * y, np.ones_like(x)])
    assert qr_native_power(planes[None]).max() < 1e-24
