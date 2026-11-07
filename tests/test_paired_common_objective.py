"""Independent values, complete pixel adjoints and pair-mode identifiability."""

import numpy as np
import pytest
import torch

from paired_common_objective import paired_common_error_loss
from paired_response_objective import paired_response_loss


@pytest.mark.parametrize("unit", [2, 16, 128])
def test_numpy_value_and_full_output_adjoint(unit):
    rng = np.random.default_rng(16501)
    output = rng.normal(size=(5, 3, 5, 7)) * 1e-3
    target = rng.normal(size=output.shape) * 1e-3
    pairs = np.array([[3, 1], [4, 0]])
    value = torch.tensor(output, requires_grad=True)
    clean = torch.tensor(target, requires_grad=True)
    actual = paired_common_error_loss(value, clean, pairs, unit_DN16=unit)
    actual.backward()
    error = output - target
    z = (error[pairs[:, 0]] + error[pairs[:, 1]]) / (2 * unit / 65535)
    expected = np.mean(z**2 / (np.sqrt(1 + z**2) + 1))
    derivative = z / np.sqrt(1 + z**2) / (2 * unit / 65535) / z.size
    adjoint = np.zeros_like(output)
    for p, (a, b) in enumerate(pairs):
        adjoint[a] = derivative[p]
        adjoint[b] = derivative[p]
    assert actual.item() == pytest.approx(expected, rel=4e-15)
    np.testing.assert_allclose(value.grad.numpy(), adjoint, rtol=3e-14, atol=3e-14)
    assert clean.grad is None and np.count_nonzero(value.grad.numpy()[2]) == 0


def test_common_error_invisible_to_difference_receives_equal_correcting_gradients():
    output = torch.full((2, 3, 2, 3), 8 / 65535, dtype=torch.float64, requires_grad=True)
    target = torch.zeros_like(output)
    units = output.new_full((1, 1, 1, 1), 2 / 65535)
    assert paired_response_loss(output, target, units, [[0, 1]]) == 0
    loss = paired_common_error_loss(output, target, [[0, 1]])
    loss.backward()
    assert loss > 0 and output.grad.min() > 0
    assert torch.equal(output.grad[0], output.grad[1])


def test_opposite_error_invisible_to_common_still_receives_difference_supervision():
    output = torch.full((2, 3, 2, 3), 1 / 1024, dtype=torch.float64)
    output[1].neg_()
    output.requires_grad_()
    target = torch.zeros_like(output)
    loss = paired_common_error_loss(output, target, [[0, 1]])
    loss.backward()
    assert loss == 0 and output.grad.count_nonzero() == 0
    units = output.new_full((1, 1, 1, 1), 2 / 65535)
    assert paired_response_loss(output, target, units, [[0, 1]]) > 0


def test_correct_different_targets_are_not_averaged_into_one_target_image():
    target = torch.arange(72, dtype=torch.float64).reshape(2, 3, 3, 4) / 128
    value = target.clone().requires_grad_()
    loss = paired_common_error_loss(value, target, [[0, 1]])
    loss.backward()
    assert loss == 0 and value.grad.count_nonzero() == 0


def test_squared_error_pair_decomposition_and_orthogonal_output_gradients():
    gen = torch.Generator().manual_seed(16502)
    error = torch.randn(4, 3, 5, 7, generator=gen, dtype=torch.float64) * 0.001
    common = (error[::2] + error[1::2]) / 2
    difference = error[::2] - error[1::2]
    torch.testing.assert_close(error.square().mean(), common.square().mean() + difference.square().mean() / 4)
    error.requires_grad_()
    a = paired_common_error_loss(error, torch.zeros_like(error), [[0, 1], [2, 3]])
    b = paired_response_loss(error, torch.zeros_like(error), error.new_full((2, 1, 1, 1), 2 / 65535), [[0, 1], [2, 3]])
    ga = torch.autograd.grad(a, error, retain_graph=True)[0]
    gb = torch.autograd.grad(b, error)[0]
    assert torch.equal(ga[::2], ga[1::2]) and torch.equal(gb[::2], -gb[1::2])
    assert (ga * gb).sum().abs() < 1e-10


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64, torch.bfloat16])
def test_tiny_common_error_is_nonzero_and_ADC_zero_weight_is_exact(dtype):
    output = torch.full((2, 3, 2, 3), 1e-10, dtype=dtype, requires_grad=True)
    target = torch.zeros_like(output)
    loss = paired_common_error_loss(output, target, [[0, 1]])
    assert torch.isfinite(loss) and loss > 0
    (loss * 0).backward()
    assert output.grad.count_nonzero() == 0


def test_pair_permutation_and_member_swap_preserve_loss_and_RNG():
    value = torch.arange(120, dtype=torch.float64).reshape(4, 3, 2, 5) / 65535
    rng = torch.get_rng_state().clone()
    a = paired_common_error_loss(value, torch.zeros_like(value), [[0, 1], [2, 3]])
    b = paired_common_error_loss(value, torch.zeros_like(value), [[3, 2], [1, 0]])
    assert a == b and torch.equal(rng, torch.get_rng_state())


@pytest.mark.parametrize("pairs", [[], [[0, 0]], [[0, 1], [1, 2]], [[-1, 0]], [[0, 4]], [[0.0, 1.0]], [0, 1]])
def test_invalid_pairs(pairs):
    x = torch.zeros(4, 3, 2, 2)
    with pytest.raises(ValueError):
        paired_common_error_loss(x, x, pairs)


@pytest.mark.parametrize("unit", [0, -1, float("inf"), float("nan")])
def test_invalid_units(unit):
    x = torch.zeros(2, 3, 2, 2)
    with pytest.raises(ValueError):
        paired_common_error_loss(x, x, [[0, 1]], unit_DN16=unit)
