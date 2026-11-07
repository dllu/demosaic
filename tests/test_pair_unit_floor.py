"""Independent unit rounding,loss scaling and pixel-adjoint checks."""

import math

import numpy as np
import pytest
import torch
from pair_unit_floor import pair_units_from_increment_variance
from paired_response_objective import paired_response_loss


@pytest.mark.parametrize("floor", [2, 16])
def test_exact_fp32_units_against_independent_numpy_sqrt_and_clamp(floor):
    values = np.array([0, 1e-12, 3e-10, 2e-9, 2e-8, 1e-7, 1e-5], dtype=np.float32)
    expected = np.maximum(np.sqrt(values), np.float32(floor / 65535)).reshape(-1, 1, 1, 1)
    actual = pair_units_from_increment_variance(values.tolist(), floor_DN16=floor)
    assert actual.dtype == torch.float32 and actual.device.type == "cpu"
    assert actual.numpy().tobytes() == expected.tobytes()


def test_floor16_to2_changes_only_old_floor_limited_pairs_and_is_bounded_by8():
    values = np.array([0, 1e-12, 3e-9, 2e-8, 1e-7], dtype=np.float32)
    old = pair_units_from_increment_variance(values, floor_DN16=16)
    new = pair_units_from_increment_variance(values, floor_DN16=2)
    unchanged = old > 16 / 65535
    assert torch.equal(old[unchanged], new[unchanged])
    assert torch.all((old / new >= 1) & (old / new <= 8))
    assert old.flatten()[0] / new.flatten()[0] == 8


def test_units_are_detached_and_do_not_advance_rng():
    state = torch.get_rng_state().clone()
    values = torch.tensor([0.0, 1e-8], requires_grad=True)
    result = pair_units_from_increment_variance(values, floor_DN16=2)
    assert not result.requires_grad and torch.equal(state, torch.get_rng_state())


def test_empty_units_keep_the_original_pair_axis_geometry():
    assert pair_units_from_increment_variance([], floor_DN16=2).shape == (0, 1, 1, 1)


@pytest.mark.parametrize("floor", [0, -1, float("nan"), float("inf")])
def test_invalid_floors(floor):
    with pytest.raises(ValueError):
        pair_units_from_increment_variance([1e-8], floor_DN16=floor)


@pytest.mark.parametrize("values", [[-1e-8], [float("nan")], [float("inf")], [[1e-8]], 1e-8])
def test_invalid_variances(values):
    with pytest.raises(ValueError):
        pair_units_from_increment_variance(values, floor_DN16=2)


@pytest.mark.parametrize("floor", [2, 16])
def test_pair_loss_and_full_output_adjoints_against_numpy(floor):
    rng = np.random.default_rng(16401)
    output = rng.normal(size=(4, 3, 5, 7)) * 1e-4
    target = rng.normal(size=output.shape) * 1e-4
    pairs = np.array([[2, 0], [3, 1]])
    units = pair_units_from_increment_variance([1e-10, 1e-7], floor_DN16=floor).double()
    value = torch.tensor(output, requires_grad=True)
    actual = paired_response_loss(value, torch.tensor(target), units, pairs)
    actual.backward()
    u = units.numpy()
    error = (
        (output[pairs[:, 0]] - output[pairs[:, 1]]) - (target[pairs[:, 0]] - target[pairs[:, 1]])
    ) / u
    expected = np.mean(error**2 / (np.sqrt(error**2 + 0.003**2) + 0.003))
    derivative = error / np.sqrt(error**2 + 0.003**2) / u / error.size
    adjoint = np.zeros_like(output)
    adjoint[pairs[:, 0]] = derivative
    adjoint[pairs[:, 1]] = -derivative
    assert float(actual.detach()) == pytest.approx(expected, rel=3e-15)
    np.testing.assert_allclose(value.grad.numpy(), adjoint, rtol=3e-14, atol=3e-14)


def test_small_error_pair_gradient_increases_toward64_and_large_toward8():
    norms = []
    for error in [1e-14, 1e-2]:
        values = []
        for floor in [16, 2]:
            x = torch.zeros(2, 3, 2, 2, dtype=torch.float64)
            x[0] = error
            x.requires_grad_()
            unit = pair_units_from_increment_variance([0], floor_DN16=floor).double()
            loss = paired_response_loss(x, torch.zeros_like(x), unit, [[0, 1]])
            loss.backward()
            values.append(float(x.grad[0, 0, 0, 0]))
        norms.append(values[1] / values[0])
    assert math.isclose(norms[0], 64, rel_tol=1e-12)
    assert math.isclose(norms[1], 8, rel_tol=1e-8)


def test_zero_target_difference_regions_still_penalize_differential_false_detail():
    x = torch.zeros(2, 3, 5, 7, dtype=torch.float64)
    x[0, :, 2, 3] = 1e-5
    x.requires_grad_()
    unit = pair_units_from_increment_variance([0], floor_DN16=2).double()
    loss = paired_response_loss(x, torch.zeros_like(x), unit, [[0, 1]])
    loss.backward()
    assert loss > 0 and x.grad[0, :, 2, 3].min() > 0 and x.grad[1, :, 2, 3].max() < 0


def test_common_error_stays_invisible_and_zero_ADC_weight_stays_exact():
    unit = pair_units_from_increment_variance([0], floor_DN16=2).double()
    common = torch.full((2, 3, 5, 7), 0.01, dtype=torch.float64)
    assert paired_response_loss(common, torch.zeros_like(common), unit, [[0, 1]]) == 0
    x = common.clone()
    x[0] += 0.001
    x.requires_grad_()
    loss = paired_response_loss(x, torch.zeros_like(x), unit, [[0, 1]]) * 0
    loss.backward()
    assert loss == 0 and x.grad.count_nonzero() == 0
