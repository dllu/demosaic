"""Independent gradients, flat penalties and isolation of the changed term."""

import numpy as np
import pytest
import torch
from nonlocal_residual_objective import objective as previous_objective
from weak_gradient_objective import objective, weak_gradient_loss


@pytest.mark.parametrize("shape", [(2, 3, 7, 11), (1, 3, 16, 8)])
def test_value_and_gradient_match_independent_numpy(shape):
    rng = np.random.default_rng(17301)
    target = rng.normal(0.005, 5 / 65535, shape)
    output = target + rng.normal(0, 1 / 65535, shape)
    expected_gradient = np.zeros(shape)
    expected_loss = 0.0
    for axis in [-1, -2]:
        clean_difference = np.diff(target, axis=axis)
        units = np.sqrt(np.mean(clean_difference**2, axis=1, keepdims=True) + (2 / 65535) ** 2)
        residual = np.diff(output - target, axis=axis) / units
        expected_loss += np.mean(np.sqrt(1 + residual**2) - 1) / 2
        derivative = residual / np.sqrt(1 + residual**2) / units / residual.size / 2
        first = [slice(None)] * 4
        second = first.copy()
        first[axis], second[axis] = slice(None, -1), slice(1, None)
        expected_gradient[tuple(first)] -= derivative
        expected_gradient[tuple(second)] += derivative
    clean = torch.tensor(target, requires_grad=True)
    value = torch.tensor(output, requires_grad=True)
    loss = weak_gradient_loss(value, clean)
    actual = torch.autograd.grad(loss, (value, clean), allow_unused=True)
    assert float(loss.detach()) == pytest.approx(expected_loss, rel=1e-12, abs=1e-15)
    np.testing.assert_allclose(actual[0].numpy(), expected_gradient, rtol=1e-12, atol=1e-12)
    assert actual[1] is None


@pytest.mark.parametrize("flat_target", [False, True])
def test_descent_recovers_weak_signal_and_removes_false_flat_texture(flat_target):
    flat = torch.full((1, 3, 8, 16), 0.005, dtype=torch.float64)
    wave = torch.sin(torch.arange(16, dtype=torch.float64) * (2 * torch.pi / 8)) * (0.2 / 65535)
    target = flat if flat_target else flat + wave
    value = (flat + wave if flat_target else flat).clone().requires_grad_()
    loss = weak_gradient_loss(value, target)
    gradient = torch.autograd.grad(loss, value)[0]
    error = value.detach() - target
    assert float((gradient * error).sum()) > 0
    assert weak_gradient_loss(value.detach() - gradient * 1e-8, target) < loss
    assert weak_gradient_loss(target, target) == 0


def test_rgb_constant_error_has_zero_gradient_penalty_under_changing_units():
    target = torch.zeros((1, 3, 8, 16), dtype=torch.float64)
    target[..., 8:] = 0.125
    offsets = torch.tensor([0.25, -0.125, 0.0625], dtype=torch.float64)[None, :, None, None]
    assert weak_gradient_loss(target + offsets, target) == 0


def test_equal_residuals_receive_more_pressure_at_weak_and_zero_target_edges():
    flat = torch.zeros((1, 3, 8, 16), dtype=torch.float64)
    ramp = torch.arange(16, dtype=torch.float64)[None, None, None] * (100 / 65535)
    residual = torch.sin(torch.arange(16, dtype=torch.float64) * (torch.pi / 4)) / 65535
    assert weak_gradient_loss(flat + residual, flat) > 100 * weak_gradient_loss(
        flat + ramp + residual, flat + ramp
    )


@pytest.mark.parametrize("pairs", [False, True])
def test_only_gradient_term_changes_and_target_mask_is_exact(pairs):
    rng = np.random.default_rng(17302)
    target = torch.from_numpy(rng.normal(0.005, 1e-5, (2, 3, 32, 32)).astype(np.float32))
    frozen = target + 0.00001
    output = frozen + torch.from_numpy(rng.normal(0, 1e-5, target.shape).astype(np.float32))
    batch = {
        "target": target,
        "variance": torch.full((2, 4, 16, 16), 6e-6),
        "pair_indices": torch.tensor([[0, 1]], dtype=torch.int64)
        if pairs
        else torch.empty((0, 2), dtype=torch.int64),
    }
    units = torch.full((int(pairs), 1, 1, 1), 2 / 65535)
    before, old_terms, old_mask = previous_objective(output, frozen, batch, units, 4)
    after, new_terms, new_mask = objective(output, frozen, batch, units, 4)
    assert torch.equal(old_mask, new_mask)
    assert all(torch.equal(old_terms[k], new_terms[k]) for k in old_terms if k != "gradient")
    assert not torch.equal(old_terms["gradient"], new_terms["gradient"])
    torch.testing.assert_close(
        after - before, new_terms["gradient"] - old_terms["gradient"], rtol=1e-4, atol=1e-6
    )


@pytest.mark.parametrize("floor", [0, -1, True, float("nan"), float("inf")])
def test_invalid_floor_rejected(floor):
    value = torch.zeros((1, 3, 4, 4))
    with pytest.raises(ValueError, match="floor"):
        weak_gradient_loss(value, value, floor_DN16=floor)
