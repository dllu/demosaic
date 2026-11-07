import numpy as np
import pytest
import torch
from flat_target_anchor import flat_target_anchor_loss, flat_target_mask


def numpy_mask(target, window, tolerance):
    result = np.empty((len(target), 1, *target.shape[-2:]), dtype=bool)
    radius = window // 2
    height, width = target.shape[-2:]
    for n in range(len(target)):
        for y in range(height):
            for x in range(width):
                block = target[
                    n, :, max(0, y - radius) : y + radius + 1, max(0, x - radius) : x + radius + 1
                ]
                result[n, 0, y, x] = np.max(np.ptp(block, axis=(1, 2))) <= tolerance / 65535
    return result


@pytest.mark.parametrize("window", [1, 3, 17])
def test_independent_range_mask_loss_and_full_output_gradient(window):
    rng = np.random.default_rng(16201)
    target = rng.integers(0, 4, size=(2, 3, 9, 11)).astype(np.float64) / 65535
    target[0, :, :5, :6] = np.array([0.01, 0.02, 0.03])[:, None, None]
    target[1, :, 4:, 5:] = np.array([0.02, 0.05, 0.005])[:, None, None]
    output = torch.tensor(target + rng.normal(size=target.shape) * 10 / 65535, requires_grad=True)
    clean = torch.tensor(target, requires_grad=True)
    mask = flat_target_mask(clean, window=window, tolerance_DN16=1)
    expected = numpy_mask(target, window, 1)
    np.testing.assert_array_equal(mask.numpy(), expected)
    loss = flat_target_anchor_loss(output, clean, mask)
    error = (output.detach().numpy() - target) * 65535 / 16
    rho = error**2 / (np.sqrt(1 + error**2) + 1)
    assert float(loss.detach()) == pytest.approx(float(np.mean(rho * expected)), abs=1e-14)
    loss.backward()
    gradient = error / np.sqrt(1 + error**2) * (65535 / 16) / error.size * expected
    np.testing.assert_allclose(output.grad.numpy(), gradient, rtol=2e-14, atol=2e-14)
    assert clean.grad is None and not mask.requires_grad


def test_colored_constants_and_truncated_borders_are_eligible():
    target = torch.tensor([0.01, 0.025, 0.002], dtype=torch.float64)[None, :, None, None].expand(
        2, 3, 5, 7
    )
    assert flat_target_mask(target).all()
    assert flat_target_anchor_loss(target, target, flat_target_mask(target)) == 0


def test_edge_dilation_does_not_cross_channels_or_image_boundaries():
    target = torch.zeros(1, 3, 13, 19, dtype=torch.float64)
    target[:, 1, :, 9:] = 10 / 65535
    mask = flat_target_mask(target, window=5)
    assert mask[..., :7].all() and mask[..., 11:].all()
    assert not mask[..., 7:11].any()
    np.testing.assert_array_equal(mask.numpy(), numpy_mask(target.numpy(), 5, 1))


def test_sub_DN16_true_detail_is_rewarded_even_when_mask_selects_it():
    target = torch.zeros(1, 3, 9, 11, dtype=torch.float64)
    target[..., ::2] = 0.5 / 65535
    mask = flat_target_mask(target)
    assert mask.all()
    exact = target.clone().requires_grad_()
    assert flat_target_anchor_loss(exact, target, mask) == 0
    flat = torch.zeros_like(target, requires_grad=True)
    loss = flat_target_anchor_loss(flat, target, mask)
    assert loss > 0
    loss.backward()
    assert (flat.grad[..., ::2] < 0).all()
    assert (flat.grad[..., 1::2] == 0).all()


def test_mask_coverage_controls_weight_and_empty_masks_have_zero_adjoint():
    output = torch.full((1, 3, 4, 6), 8 / 65535, dtype=torch.float64, requires_grad=True)
    target = torch.zeros_like(output)
    full = torch.ones(1, 1, 4, 6, dtype=torch.bool)
    half = full.clone()
    half[..., :3] = False
    torch.testing.assert_close(
        flat_target_anchor_loss(output, target, half),
        flat_target_anchor_loss(output, target, full) * 0.5,
        rtol=0,
        atol=2e-16,
    )
    loss = flat_target_anchor_loss(output, target, ~full)
    loss.backward()
    assert loss == 0 and output.grad.count_nonzero() == 0


def test_per_image_independence_and_constant_error_analytic_units():
    clean = torch.zeros(2, 3, 4, 5, dtype=torch.float64)
    value = clean.clone()
    value[0] = 16 / 65535
    value[1] = -32 / 65535
    value.requires_grad_()
    mask = flat_target_mask(clean)
    together = flat_target_anchor_loss(value, clean, mask)
    separate = [
        flat_target_anchor_loss(value[n : n + 1], clean[n : n + 1], mask[n : n + 1])
        for n in range(2)
    ]
    torch.testing.assert_close(together, sum(separate) * 0.5, rtol=0, atol=2e-16)
    assert float(separate[0].detach()) == pytest.approx(np.sqrt(2) - 1)
    first = torch.autograd.grad(separate[0], value)[0]
    assert first[1].count_nonzero() == 0 and first[0].count_nonzero() == first[0].numel()


def test_common_pair_errors_are_anchored_without_penalizing_target_correction():
    from paired_response_objective import paired_response_loss

    target = torch.zeros(2, 3, 5, 7, dtype=torch.float64)
    target[1] = 0.02
    wrong = target + 8 / 65535
    units = torch.ones(1, 1, 1, 1, dtype=torch.float64) * 16 / 65535
    pairs = torch.tensor([[0, 1]])
    assert paired_response_loss(wrong, target, units, pairs) < 1e-25
    mask = flat_target_mask(target)
    assert flat_target_anchor_loss(wrong, target, mask) > 0
    assert flat_target_anchor_loss(target, target, mask) == 0


@pytest.mark.parametrize("window,tolerance", [(0, 1), (2, 1), (3, -1), (3, float("nan"))])
def test_invalid_mask_parameters(window, tolerance):
    with pytest.raises(ValueError):
        flat_target_mask(torch.zeros(1, 3, 5, 7), window=window, tolerance_DN16=tolerance)


@pytest.mark.parametrize("unit", [0, -1, float("nan"), float("inf")])
def test_invalid_anchor_units(unit):
    target = torch.zeros(1, 3, 5, 7)
    with pytest.raises(ValueError):
        flat_target_anchor_loss(target, target, flat_target_mask(target), unit_DN16=unit)
