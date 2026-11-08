"""Check phase separation, exact deterministic geometry and noise propagation."""

import numpy as np
import pytest
from green_phase_spectrum import tapered_spectrum
from phase_frequency_holdout import describe_phase_holdout, select_phase_frequencies


def fixture(layout=(0, 1, 1, 2)):
    n = 32
    y, x = np.indices((n, n))
    packed = np.stack(
        [
            0.02
            + 0.001
            * np.cos(2 * np.pi * (5 * (2 * x + i % 2) + 7 * (2 * y + i // 2)) / (2 * n) + 0.3)
            for i in range(4)
        ]
    )
    variance = np.full_like(packed, 1e-6)
    return packed, variance, np.array(layout)


@pytest.mark.parametrize("layout", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_native_phase_compensation(layout):
    packed, variance, colors = fixture(layout)
    outputs = describe_phase_holdout(packed, variance, colors)
    for direction in outputs:
        peak = direction["peaks"][0]
        assert peak["bin_yx"] == [7, 5]
        assert peak["signed_principal_phase_agreement"] == pytest.approx(1, abs=2e-5)


def test_other_phase_cannot_change_selection():
    packed, variance, colors = fixture()
    before = describe_phase_holdout(packed, variance, colors)
    # Change the measured phase and its variance, preserving selection phase1.
    y, x = np.indices((32, 32))
    changed = packed.copy()
    changed[2] = 0.03 + 0.2 * np.cos(2 * np.pi * (11 * x + 3 * y) / 32)
    noise = variance.copy()
    noise[2] *= 123
    after = describe_phase_holdout(changed, noise, colors)
    assert before[0]["selection_phase"] == after[0]["selection_phase"] == 1
    assert [p["bin_yx"] for p in before[0]["peaks"]] == [p["bin_yx"] for p in after[0]["peaks"]]
    assert [p["selection_power"] for p in before[0]["peaks"]] == [
        p["selection_power"] for p in after[0]["peaks"]
    ]
    assert before[0]["peaks"][0]["other_phase_power"] != after[0]["peaks"][0]["other_phase_power"]
    assert before[1]["peaks"][0]["bin_yx"] != after[1]["peaks"][0]["bin_yx"]


def test_affine_background_invariance():
    packed, variance, colors = fixture()
    y, x = np.indices((32, 32))
    before = describe_phase_holdout(packed, variance, colors)
    after = describe_phase_holdout(packed + 0.4 + 0.01 * x - 0.02 * y, variance, colors)
    for a, b in zip(before, after, strict=True):
        assert [p["bin_yx"] for p in a["peaks"]] == [p["bin_yx"] for p in b["peaks"]]
        np.testing.assert_allclose(
            [p["other_phase_power"] for p in a["peaks"]],
            [p["other_phase_power"] for p in b["peaks"]],
            rtol=2e-9,
        )


def test_frequency_order_matches_direct_linear_rows():
    packed, variance, _ = fixture()
    image = packed[1]
    result = tapered_spectrum(image, variance[1])
    for y, x in select_phase_frequencies(result["spectrum"], result["noise_variance"]):
        n = image.shape[0]
        yy, xx = np.indices(image.shape)
        basis = np.stack([np.ones(image.size), xx.ravel(), yy.ravel()], axis=1)
        window = np.outer(np.hanning(n), np.hanning(n)).ravel()
        # Independently form one complete fitted-plane Fourier row.
        fourier = window * np.exp(-2j * np.pi * (x * xx.ravel() + y * yy.ravel()) / n) / n
        plane_operator = np.linalg.solve(
            basis.T @ (window[:, None] ** 2 * basis), basis.T * window**2
        )
        row = fourier - (fourier @ basis) @ plane_operator
        np.testing.assert_allclose(result["spectrum"][y, x], row @ image.ravel(), atol=1e-16)
        assert result["noise_variance"][y, x] == pytest.approx(
            np.sum(abs(row) ** 2 * variance[1].ravel()), rel=1e-12
        )


@pytest.mark.parametrize("case", ["zero-variance", "nan", "bad-layout", "bad-shape"])
def test_invalid_contract(case):
    packed, variance, colors = fixture()
    if case == "zero-variance":
        variance[:] = 0
    elif case == "nan":
        packed[0, 0, 0] = np.nan
        packed[1, 0, 0] = np.nan
    elif case == "bad-layout":
        colors[:] = 1
    else:
        packed = packed[:3]
    with pytest.raises(ValueError):
        describe_phase_holdout(packed, variance, colors)
