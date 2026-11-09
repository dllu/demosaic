"""Independent native-phase transport, source-head agreement and gate controls."""

import numpy as np
import pytest
import torch
from readout_gate_interventions import (
    POLICIES,
    amplitude_match,
    correction_stats,
    crop_gates,
    local_intervention,
    native_basis,
    policy_gate,
    rms,
    synthesize,
)

from demosaic.late_cfa_innovation_wave import CFAInnovationWaveReadout


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_native_analytic_wave_on_non_square_grid(dtype):
    n, count, h, w = 2, 4, 9, 14
    bins = np.array([[[[1, 2], [2, 12]], [[3, 1], [1, 11]]]] * n, dtype=np.int64)
    yy, xx = np.mgrid[:h, :w]
    fy, fx = np.moveaxis(bins.reshape(n, count, 2), -1, 0)
    ky, kx = np.where(fy <= 4, fy, fy - h), np.where(fx <= 6, fx, fx - w)
    angle = 2 * np.pi * (ky[..., None, None] * yy / h + kx[..., None, None] * xx / w)
    amplitude = np.array([0.003 + 0.001j, -0.001 + 0.002j, 0.0005 - 0.001j])[
        None, None, :, None, None
    ]
    complex_wave = amplitude * np.exp(1j * angle[:, :, None])
    waves = np.stack((complex_wave.real, complex_wave.imag), 3).astype(dtype)
    gate = np.array([0.2, -0.3, 0.4], dtype=dtype)[None, None, :, None, None]
    gate = np.broadcast_to(gate, (n, count, 3, h, w)).copy()
    actual = synthesize(native_basis(waves, bins), gate)
    yy, xx = np.mgrid[: 2 * h, : 2 * w]
    phase = np.pi * (ky[..., None, None] * yy / h + kx[..., None, None] * xx / w)
    expected = ((amplitude * np.exp(1j * phase[:, :, None])).real * gate[..., :1, :1]).sum(1)
    np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=1e-9)


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_independent_synthesis_matches_original_head(dtype):
    rng = np.random.default_rng(19901)
    context = torch.tensor(rng.normal(size=(2, 4, 24, 9, 14)), dtype=dtype)
    waves = torch.tensor(rng.normal(scale=0.003, size=(2, 4, 3, 2, 9, 14)), dtype=dtype)
    bins = torch.tensor([[[[1, 2], [2, 12]], [[3, 1], [1, 11]]]] * 2)
    head = CFAInnovationWaveReadout().to(dtype)
    with torch.no_grad():
        head.gates.weight.copy_(
            torch.tensor(rng.normal(scale=0.1, size=head.gates.weight.shape), dtype=dtype)
        )
        head.gates.bias.copy_(torch.tensor([0.2, -0.1, 0.3], dtype=dtype))
        gates = (
            head.gates(torch.nn.functional.silu(head.context(context.flatten(0, 1))))
            .tanh()
            .reshape(2, 4, 3, 9, 14)
        )
        expected = head(context, waves, bins).numpy()
    basis = native_basis(waves.numpy(), bins.numpy())
    actual = synthesize(basis, gates.numpy())
    np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=3e-9)


@pytest.mark.parametrize("policy", POLICIES)
def test_gate_control_shapes_bounds_and_identities(policy):
    rng = np.random.default_rng(19902)
    gates = rng.uniform(-1, 1, (2, 4, 3, 9, 14)).astype(np.float32)
    value = policy_gate(gates, policy)
    assert np.isfinite(value).all() and (abs(value) <= 1).all()
    if policy == "actual":
        np.testing.assert_array_equal(value, gates)
    elif policy.startswith("shared-spatial"):
        np.testing.assert_array_equal(value, gates.mean(2, keepdims=True))
    elif policy == "color-constant":
        np.testing.assert_array_equal(value, gates.mean((-2, -1), keepdims=True))
    elif policy.startswith("shared-constant"):
        np.testing.assert_array_equal(value, gates.mean((2, 3, 4), keepdims=True))
    else:
        assert (value >= 0).all()


def test_amplitude_match_and_zero_exception_are_explicit():
    a = np.arange(20, dtype=np.float32).reshape(1, 1, 4, 5)
    value, record = amplitude_match(a, a * 3)
    assert record["possible"] and not record["bounded_gate_architecture"]
    assert abs(rms(value) - rms(a * 3)) < 1e-6
    value, record = amplitude_match(a * 0, a)
    assert not record["possible"] and not value.any()
    value, record = amplitude_match(a * 0, a * 0)
    assert record["possible"] and record["scale"] == 1


def test_odd_roi_gates_mask_and_positive_negative_decomposition():
    rng = np.random.default_rng(19903)
    gates = rng.uniform(-1, 1, (1, 4, 3, 9, 14)).astype(np.float32)
    basis = rng.normal(scale=0.003, size=(1, 4, 3, 18, 28)).astype(np.float32)
    roi = [3, 5, 10, 8]
    np.testing.assert_array_equal(
        crop_gates(gates, roi), gates.repeat(2, -2).repeat(2, -1)[..., 5:13, 3:13]
    )
    mask = np.ones((1, 1, 18, 28), dtype=bool)
    mask[..., :4, :3] = False
    actual = synthesize(basis, gates, mask)
    assert not actual[..., :4, :3].any()
    positive = synthesize(basis, gates.clip(0, 1), mask)
    negative = synthesize(basis, gates.clip(-1, 0), mask)
    np.testing.assert_allclose(actual, positive + negative, atol=2e-9, rtol=2e-5)
    stats = correction_stats(actual)
    assert stats["equal_RGB_orthogonal_RMS_DN16"] <= stats["RMS_DN16"]


def test_invalid_shapes_bins_and_nonfinite_values():
    waves = np.zeros((1, 2, 3, 2, 8, 10), dtype=np.float32)
    bins = np.array([[[[1, 1]], [[2, 2]]]])
    with pytest.raises(ValueError):
        native_basis(waves, bins.astype(np.float32))
    bins[0, 0, 0] = [20, 20]
    with pytest.raises(ValueError):
        native_basis(waves, bins)
    with pytest.raises(ValueError):
        policy_gate(np.full((1, 2, 3, 8, 10), np.nan), "actual")
    with pytest.raises(ValueError):
        policy_gate(np.zeros((1, 2, 3, 8, 10)), "unknown")


@pytest.mark.parametrize("policy", POLICIES)
def test_saved_odd_crop_matches_full_context_and_uses_global_constants(policy):
    rng = np.random.default_rng(19904)
    gate = rng.uniform(-1, 1, (1, 4, 3, 9, 14)).astype(np.float32)
    basis = rng.normal(scale=0.003, size=(1, 4, 3, 18, 28)).astype(np.float32)
    mask = np.ones((1, 1, 18, 28), dtype=bool)
    mask[..., :5, :5] = False
    roi = [3, 3, 10, 8]
    full = synthesize(basis, policy_gate(gate, policy), mask) * 0.7
    bundle = {
        "basis": basis[..., 3:11, 3:13],
        "gate_EMA": crop_gates(gate, roi),
        "mask": mask[..., 3:11, 3:13],
    }
    constants = {
        "color": gate.mean((-2, -1), keepdims=True).tolist(),
        "shared": gate.mean((2, 3, 4), keepdims=True).tolist(),
    }
    actual = local_intervention(bundle, "EMA", policy, constants, 0.7)
    np.testing.assert_array_equal(actual, full[..., 3:11, 3:13])
