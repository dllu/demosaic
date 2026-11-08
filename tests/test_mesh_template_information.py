"""Direct augmented-design covariance checks and affine invariants."""

import numpy as np
import pytest
from mesh_template_information import tiled_template_fit


@pytest.mark.parametrize("phases", [1, 2, 4])
@pytest.mark.parametrize("block", [4, 8])
def test_matches_independent_augmented_weighted_design_and_covariance(phases, block):
    rng = np.random.default_rng(17601 + phases + block)
    height, width = 8, 16
    template = rng.normal(size=(phases, height, width))
    residual = rng.normal(size=template.shape)
    weight_variance = rng.uniform(0.5, 2, template.shape)
    actual_variance = rng.uniform(0.1, 3, template.shape)
    actual = tiled_template_fit(
        template, {"raw": residual}, weight_variance, {"raw": actual_variance}, block
    )
    yy, xx = np.meshgrid(np.linspace(-1, 1, block), np.linspace(-1, 1, block), indexing="ij")
    plane = np.stack((np.ones_like(xx), xx, yy), -1).reshape(-1, 3)
    for ty in range(height // block):
        for tx in range(width // block):
            ys, xs = slice(ty * block, (ty + 1) * block), slice(tx * block, (tx + 1) * block)
            signal = template[:, ys, xs].reshape(-1)
            design = np.zeros((len(signal), phases * 3 + 1))
            for phase in range(phases):
                design[phase * block**2 : (phase + 1) * block**2, phase * 3 : (phase + 1) * 3] = (
                    plane
                )
            design[:, -1] = signal
            weight = 1 / weight_variance[:, ys, xs].reshape(-1)
            matrix = np.linalg.pinv(design * np.sqrt(weight[:, None])) * np.sqrt(weight[None])
            fit = matrix @ residual[:, ys, xs].reshape(-1)
            variance = (matrix[-1] ** 2) @ actual_variance[:, ys, xs].reshape(-1)
            np.testing.assert_allclose(
                actual["amplitudes"]["raw"][ty, tx], fit[-1], rtol=1e-11, atol=1e-12
            )
            np.testing.assert_allclose(
                actual["amplitude_variances"]["raw"][ty, tx], variance, rtol=1e-11, atol=1e-12
            )


def test_exact_amplitude_is_invariant_to_separate_phase_affine_backgrounds():
    yy, xx = np.mgrid[:16, :16]
    signal = np.stack([np.sin(xx * 0.7 + p) * np.cos(yy * 0.5) for p in range(4)])
    background = np.stack([p + 0.1 * p * xx - 0.2 * yy for p in range(4)])
    weights = 1 + (xx + yy)[None] / 32 + np.zeros_like(signal)
    result = tiled_template_fit(
        signal,
        {"raw": 0.75 * signal + background, "parent": signal},
        weights,
        {"raw": weights, "parent": None},
        8,
    )
    np.testing.assert_allclose(result["amplitudes"]["raw"], 0.75, atol=1e-13)
    np.testing.assert_allclose(result["amplitudes"]["parent"], 1, atol=1e-13)
    assert result["amplitude_variances"]["parent"] is None
    np.testing.assert_allclose(
        result["amplitude_variances"]["raw"], 1 / result["weighted_template_energy"], rtol=1e-12
    )


def test_zero_template_is_unidentifiable():
    value = np.zeros((2, 8, 8))
    result = tiled_template_fit(
        value, {"raw": value}, np.ones_like(value), {"raw": np.ones_like(value)}, 4
    )
    assert not np.any(result["weighted_template_energy"])
    assert np.isnan(result["amplitudes"]["raw"]).all()
    assert np.isnan(result["amplitude_variances"]["raw"]).all()


def test_pure_affine_template_is_unidentifiable():
    yy, xx = np.mgrid[:8, :8]
    value = np.stack([2 + 0.3 * xx - 0.1 * yy, 5 - 0.2 * xx + yy])
    result = tiled_template_fit(
        value, {"raw": value}, np.ones_like(value), {"raw": np.ones_like(value)}, 4
    )
    assert not np.any(result["weighted_template_energy"])
    assert np.isnan(result["amplitudes"]["raw"]).all()


@pytest.mark.parametrize(
    "bad", ["shape", "nan", "zero_weight", "negative_variance", "variance_shape", "block", "keys"]
)
def test_invalid_contracts_reject(bad):
    value = np.ones((2, 8, 8))
    residual, weights, variance, block = value.copy(), value.copy(), value.copy(), 4
    if bad == "shape":
        residual = residual[..., :7]
    if bad == "nan":
        value[0, 0, 0] = np.nan
    if bad == "zero_weight":
        weights[0, 0, 0] = 0
    if bad == "negative_variance":
        variance[0, 0, 0] = -1
    if bad == "variance_shape":
        variance = variance[..., :7]
    if bad == "block":
        block = 3
    variances = {"other" if bad == "keys" else "raw": variance}
    with pytest.raises(ValueError):
        tiled_template_fit(value, {"raw": residual}, weights, variances, block)
