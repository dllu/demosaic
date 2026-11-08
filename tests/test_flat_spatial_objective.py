"""Independent window enumeration/derivatives and clean-mask scope checks."""

import numpy as np
import pytest
import torch
from flat_spatial_objective import flat_spatial_error_loss, objective
from flat_target_anchor import flat_target_mask
from nonlocal_residual_objective import objective as previous_objective


def independent(output, target, mask, window, unit):
    error = (output - target) / (unit / 65535)
    gradient = np.zeros_like(error)
    loss = 0.0
    n, channels, height, width = error.shape
    for b in range(n):
        for y in range(height):
            for x in range(width):
                if not mask[b, 0, y, x]:
                    continue
                ys = slice(max(0, y - window // 2), min(height, y + window // 2 + 1))
                xs = slice(max(0, x - window // 2), min(width, x + window // 2 + 1))
                for c in range(channels):
                    patch = error[b, c, ys, xs]
                    residual = patch - patch.mean()
                    variance = np.mean(residual**2)
                    loss += (np.sqrt(1 + variance) - 1) / error.size
                    gradient[b, c, ys, xs] += residual / (
                        np.sqrt(1 + variance) * patch.size * (unit / 65535) * error.size
                    )
    return loss, gradient


@pytest.mark.parametrize("shape,window", [((2, 3, 7, 11), 5), ((1, 3, 4, 6), 17)])
def test_values_and_gradients_match_independent_truncated_windows(shape, window):
    rng = np.random.default_rng(18101)
    target = rng.normal(0.01, 3 / 65535, shape)
    output = target + rng.normal(0, 2 / 65535, shape)
    mask = rng.random((shape[0], 1, *shape[-2:])) > 0.3
    expected, derivative = independent(output, target, mask, window, 4)
    clean = torch.tensor(target, requires_grad=True)
    value = torch.tensor(output, requires_grad=True)
    loss = flat_spatial_error_loss(value, clean, torch.tensor(mask), window=window)
    gradients = torch.autograd.grad(loss, (value, clean), allow_unused=True)
    assert loss.item() == pytest.approx(expected, rel=1e-12, abs=1e-14)
    np.testing.assert_allclose(gradients[0].numpy(), derivative, rtol=1e-11, atol=1e-10)
    assert gradients[1] is None


@pytest.mark.parametrize("weak_signal", [False, True])
def test_descent_removes_false_texture_or_recovers_actual_sub_dn_signal(weak_signal):
    flat = torch.full((1, 3, 8, 16), 0.005, dtype=torch.float64)
    wave = torch.sin(torch.arange(16, dtype=torch.float64) * (2 * torch.pi / 8)) / 65535
    target = flat + 0.25 * wave if weak_signal else flat
    value = (flat if weak_signal else flat + wave).clone().requires_grad_()
    mask = flat_target_mask(target)
    assert mask.all()
    loss = flat_spatial_error_loss(value, target, mask)
    derivative = torch.autograd.grad(loss, value)[0]
    assert float((derivative * (value.detach() - target)).sum()) > 0
    assert flat_spatial_error_loss(value.detach() - derivative * 1e-8, target, mask) < loss
    assert flat_spatial_error_loss(target, target, mask) == 0


def test_spatially_constant_rgb_errors_remain_free_of_spatial_penalty():
    target = torch.zeros((1, 3, 7, 11), dtype=torch.float64)
    output = target + torch.tensor([0.125, -0.25, 0.0625])[None, :, None, None]
    output.requires_grad_()
    loss = flat_spatial_error_loss(output, target, flat_target_mask(target))
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, output)[0]) == 0


def test_large_constant_error_does_not_change_spatial_value_or_derivative():
    rng = np.random.default_rng(18102)
    error = torch.tensor(rng.normal(0, 2 / 65535, (1, 3, 7, 11)))
    target = torch.zeros_like(error)
    mask = flat_target_mask(target)
    a, b = error.clone().requires_grad_(), (error + 0.125).requires_grad_()
    values = [flat_spatial_error_loss(x, target, mask) for x in [a, b]]
    torch.testing.assert_close(values[0], values[1], rtol=1e-10, atol=1e-12)
    gradients = [torch.autograd.grad(loss, x)[0] for loss, x in zip(values, [a, b], strict=True)]
    torch.testing.assert_close(gradients[0], gradients[1], rtol=1e-9, atol=1e-8)


def test_zero_coverage_has_zero_loss_and_gradient_and_mean_keeps_coverage_weight():
    rng = np.random.default_rng(18103)
    value = torch.tensor(rng.normal(0, 2 / 65535, (1, 3, 7, 11)), requires_grad=True)
    target = torch.zeros_like(value)
    empty = torch.zeros((1, 1, 7, 11), dtype=torch.bool)
    loss = flat_spatial_error_loss(value, target, empty)
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0
    full = ~empty
    reference = flat_spatial_error_loss(value, target, full)
    observed = flat_spatial_error_loss(
        value.repeat(2, 1, 1, 1), target.repeat(2, 1, 1, 1), torch.cat((full, empty))
    )
    assert observed.item() == pytest.approx(reference.item() / 2)


@pytest.mark.parametrize("pairs", [False, True])
def test_all_seven_existing_terms_and_mask_stay_exact(pairs):
    rng = np.random.default_rng(18104)
    target = torch.full((2, 3, 32, 32), 0.005)
    frozen = target + 1 / 65535
    output = frozen + torch.from_numpy(rng.normal(0, 1e-5, target.shape).astype(np.float32))
    batch = {
        "target": target,
        "variance": torch.full((2, 4, 16, 16), 6e-6),
        "pair_indices": torch.tensor([[0, 1]], dtype=torch.int64)
        if pairs
        else torch.empty((0, 2), dtype=torch.int64),
    }
    units = torch.full((int(pairs), 1, 1, 1), 2 / 65535)
    old, terms, mask = previous_objective(output, frozen, batch, units, 4)
    new, changed, selected = objective(output, frozen, batch, units, 4)
    assert set(changed) == set(terms) | {"flat_spatial"}
    assert all(torch.equal(v, changed[k]) for k, v in terms.items())
    assert torch.equal(mask, selected)
    assert torch.equal(new, old + changed["flat_spatial"])


def test_strong_target_texture_is_not_selected_by_existing_flat_mask():
    target = torch.zeros((1, 3, 16, 16), dtype=torch.float64)
    target[..., ::2] = 20 / 65535
    mask = flat_target_mask(target)
    assert not mask.any()
    output = (target * 0.5).requires_grad_()
    loss = flat_spatial_error_loss(output, target, mask)
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, output)[0]) == 0


@pytest.mark.parametrize("unit", [0, -1, True, float("nan"), float("inf")])
def test_invalid_units_reject(unit):
    value = torch.zeros((1, 3, 4, 4))
    with pytest.raises(ValueError, match="units"):
        flat_spatial_error_loss(value, value, flat_target_mask(value), unit_DN16=unit)


@pytest.mark.parametrize("window", [0, -1, 2, True, 3.5])
def test_invalid_windows_reject(window):
    value = torch.zeros((1, 3, 4, 4))
    with pytest.raises(ValueError, match="Window"):
        flat_spatial_error_loss(value, value, flat_target_mask(value), window=window)


@pytest.mark.parametrize("damage", ["nonfinite", "channels", "shape", "mask_dtype", "mask_shape"])
def test_invalid_tensor_contracts_reject(damage):
    value = torch.zeros((1, 3, 4, 4))
    target, mask = value.clone(), flat_target_mask(value)
    if damage == "nonfinite":
        value[0, 0, 0, 0] = float("nan")
    elif damage == "channels":
        value, target = value[:, :1], target[:, :1]
    elif damage == "shape":
        target = target[..., :-1]
    elif damage == "mask_dtype":
        mask = mask.float()
    else:
        mask = mask[..., :-1]
    with pytest.raises(ValueError):
        flat_spatial_error_loss(value, target, mask)
