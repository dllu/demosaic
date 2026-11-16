"""Verify the diagnostic synthesis and small GT-oracle optimization independently."""

import numpy as np
import pytest
import torch
from diagnose_measured_wave_fit import fit_constant_gains, native_basis

from demosaic.late_scale_supported_cfa_wave import ScaleSupportedCFAReadout

lsq_linear = pytest.importorskip(
    "scipy.optimize", reason="Requires the optional eval extra"
).lsq_linear


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_native_basis_matches_actual_readout_with_spatial_gates(dtype):
    gen = torch.Generator().manual_seed(12301)
    model = ScaleSupportedCFAReadout().to(dtype=dtype)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=gen, dtype=dtype) * 0.2)
        context = torch.randn((2, 4, 36, 8, 10), generator=gen, dtype=dtype)
        waves = torch.randn((2, 4, 3, 2, 8, 10), generator=gen, dtype=dtype)
        bins = torch.tensor([[[[0, 1], [4, 5]], [[7, 9], [1, 8]]]]).expand(2, -1, -1, -1)
        actual = model(context, waves, bins).numpy()
        gates = model.gates(torch.nn.functional.silu(model.context(context.flatten(0, 1))))
        gates = gates.tanh().reshape(2, 4, 3, 8, 10).numpy()
    result = np.empty_like(actual)
    for item in range(2):
        for color in range(3):
            basis = native_basis(waves[item, :, color].numpy(), bins[item].reshape(4, 2).numpy())
            lifted_gates = gates[item, :, color].repeat(2, -2).repeat(2, -1)
            result[item, color] = (basis * lifted_gates).sum(0)
    tolerance = 2e-6 if dtype == torch.float32 else 1e-13
    np.testing.assert_allclose(result, actual, atol=tolerance, rtol=tolerance)


@pytest.mark.parametrize("bin_yx", [[1, 2], [7, 9], [4, 5]])
def test_basis_recovers_native_carrier_and_quadrature_at_actual_offsets(bin_yx):
    h, w = 8, 10
    signed = np.where(
        np.array(bin_yx) <= (np.array([h, w]) - 1) // 2, bin_yx, np.array(bin_yx) - [h, w]
    )
    yy, xx = np.mgrid[:h, :w]
    phase = 2 * np.pi * (signed[0] * yy / h + signed[1] * xx / w)
    waves = np.stack([np.cos(phase), np.sin(phase)])[None]
    actual = native_basis(waves, np.array([bin_yx]), quadrature=True)
    yy, xx = np.mgrid[: 2 * h, : 2 * w]
    native_phase = np.pi * (signed[0] * yy / h + signed[1] * xx / w)
    np.testing.assert_allclose(actual[0], np.cos(native_phase), atol=3e-14)
    np.testing.assert_allclose(actual[1], -np.sin(native_phase), atol=3e-14)


@pytest.mark.parametrize("bounded", [True, False])
def test_global_gram_solver_matches_independent_full_design_solver(bounded):
    rng = np.random.default_rng(12302)
    basis = rng.normal(size=(8, 12, 13))
    target = rng.normal(size=(12, 13)) + 2.5 * basis[0]
    correction, receipt = fit_constant_gains(basis, target, bounded=bounded)
    design = basis.reshape(8, -1).T
    if bounded:
        expected = lsq_linear(design, target.ravel(), bounds=(-1, 1), method="bvls", tol=1e-13).x
        assert receipt["box_duality_gap_half_MSE"] <= 1e-12
        assert receipt["gains_at_bounds"] >= 1
    else:
        expected = np.linalg.lstsq(design, target.ravel(), rcond=1e-12)[0]
    np.testing.assert_allclose(receipt["coefficients"], expected, atol=1e-12)
    np.testing.assert_allclose(correction.ravel(), design @ expected, atol=1e-12)
    assert receipt["fitted_MSE"] <= receipt["zero_MSE"]


def test_bounded_solver_keeps_actual_amplitude_limits():
    basis = np.eye(4)[:2].reshape(2, 2, 2)
    target = np.array([[2, -3], [0, 0]])
    correction, bounded = fit_constant_gains(basis, target, bounded=True)
    _, free = fit_constant_gains(basis, target, bounded=False)
    np.testing.assert_allclose(bounded["coefficients"], [1, -1])
    np.testing.assert_allclose(correction, [[1, -1], [0, 0]])
    np.testing.assert_allclose(free["coefficients"], [2, -3])
    assert bounded["box_duality_gap_half_MSE"] == 0


@pytest.mark.parametrize("bounded", [True, False])
def test_rank_deficient_and_invalid_carriers_remain_explicit(bounded):
    basis = np.stack([np.ones((3, 4)), np.ones((3, 4)), np.zeros((3, 4))])
    correction, receipt = fit_constant_gains(basis, np.full((3, 4), 0.5), bounded=bounded)
    assert receipt["numerical_rank"] == 1 and receipt["slots"] == 3
    np.testing.assert_allclose(correction, 0.5, atol=1e-14)
    assert receipt["coefficients"][2] == 0


@pytest.mark.parametrize("bounded", [True, False])
def test_zero_wave_basis_cannot_fit_a_target(bounded):
    correction, receipt = fit_constant_gains(np.zeros((8, 5, 6)), np.ones((5, 6)), bounded=bounded)
    assert not correction.any() and receipt["numerical_rank"] == 0
    assert receipt["fitted_MSE"] == receipt["zero_MSE"] == 1


def test_phase_relaxation_is_distinct_from_real_measured_wave():
    yy, xx = np.mgrid[:8, :10]
    phase = 2 * np.pi * (yy / 8 + xx / 10)
    waves = np.stack([np.cos(phase), np.sin(phase)])[None]
    bins = np.array([[1, 1]])
    real = native_basis(waves, bins)
    relaxed = native_basis(waves, bins, quadrature=True)
    target = relaxed[1]
    _, fixed = fit_constant_gains(real, target, bounded=False)
    _, rotated = fit_constant_gains(relaxed, target, bounded=False)
    assert fixed["fitted_MSE"] > 0.49
    assert rotated["fitted_MSE"] < 1e-28


@pytest.mark.parametrize("invalid", ["nonfinite", "shape", "float_bins", "outside"])
def test_invalid_native_synthesis_inputs_reject(invalid):
    waves, bins = np.ones((2, 2, 8, 10)), np.array([[1, 2], [7, 9]])
    if invalid == "nonfinite":
        waves[0, 0, 0, 0] = np.nan
    elif invalid == "shape":
        waves = waves[:, 0]
    elif invalid == "float_bins":
        bins = bins.astype(float)
    else:
        bins[0, 0] = 8
    with pytest.raises(ValueError):
        native_basis(waves, bins)
