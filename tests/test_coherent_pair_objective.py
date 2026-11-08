"""Independent projection/derivative checks and invisible-error limitations."""

from itertools import pairwise

import numpy as np
import pytest
import torch
from coherent_pair_objective import objective, paired_coherent_response_loss
from flat_spatial_objective import objective as previous_objective


def independent(output, target, pairs, floor):
    derivative = np.zeros_like(output, dtype=np.float64)
    loss = 0.0
    for a, b in pairs:
        delta = target[a] - target[b]
        template = delta - delta.mean((1, 2), keepdims=True)
        error = output[a] - output[b] - delta
        error -= error.mean((1, 2), keepdims=True)
        unit = np.mean(template**2) + (floor / 65535) ** 2
        residual = np.mean(error * template) / unit
        loss += (np.sqrt(1 + residual**2) - 1) / len(pairs)
        direction = template - template.mean((1, 2), keepdims=True)
        d = residual / np.sqrt(1 + residual**2) * direction / (unit * template.size * len(pairs))
        derivative[a] += d
        derivative[b] -= d
    return loss, derivative


@pytest.mark.parametrize("floor", [0.25, 1, 4])
def test_values_and_derivatives_match_independent_per_pair_formula(floor):
    rng = np.random.default_rng(18301)
    target = rng.normal(0.003, 2 / 65535, (4, 3, 5, 7))
    target[2:] = 0.003 + (target[2:] - 0.003) * 0.1
    output = target + rng.normal(0, 3 / 65535, target.shape)
    pairs = np.array([[0, 1], [2, 3]])
    expected, derivative = independent(output, target, pairs, floor)
    value = torch.tensor(output, requires_grad=True)
    clean = torch.tensor(target, requires_grad=True)
    loss = paired_coherent_response_loss(value, clean, torch.tensor(pairs), floor_DN16=floor)
    actual, gt = torch.autograd.grad(loss, (value, clean), allow_unused=True)
    assert loss.item() == pytest.approx(expected, rel=1e-11, abs=1e-14)
    np.testing.assert_allclose(actual.numpy(), derivative, rtol=1e-10, atol=1e-9)
    assert gt is None


def wave_case():
    target = torch.zeros((2, 3, 8, 16), dtype=torch.float64)
    wave = torch.sin(torch.arange(16, dtype=torch.float64) * 2 * torch.pi / 8) / 65535
    target[0] += wave
    return target, torch.tensor([[0, 1]])


def test_descent_recovers_missing_coherent_response():
    target, pairs = wave_case()
    value = torch.zeros_like(target, requires_grad=True)
    loss = paired_coherent_response_loss(value, target, pairs)
    derivative = torch.autograd.grad(loss, value)[0]
    assert float((derivative * (target - value.detach())).sum()) < 0
    assert paired_coherent_response_loss(value.detach() - 1e-8 * derivative, target, pairs) < loss
    assert paired_coherent_response_loss(target, target, pairs) == 0
    torch.testing.assert_close(derivative[0], -derivative[1])


def test_channel_dc_pair_errors_are_invisible_and_pair_swap_is_invariant():
    target, pairs = wave_case()
    value = target + torch.tensor([0.125, -0.25, 0.0625])[None, :, None, None]
    value[1] += 0.0625
    assert paired_coherent_response_loss(value, target, pairs) < 1e-20
    value = target * 0.25
    assert paired_coherent_response_loss(value, target, pairs) == paired_coherent_response_loss(
        value, target, pairs.flip(1)
    )


def test_orthogonal_false_texture_is_invisible_so_existing_losses_are_required():
    target, pairs = wave_case()
    false = torch.cos(torch.arange(16, dtype=torch.float64) * 2 * torch.pi / 8) / 65535
    value = target.clone()
    value[0] += false
    assert paired_coherent_response_loss(value, target, pairs) < 1e-20
    assert (value - target).square().sum() > 0


def test_zero_target_change_has_zero_loss_and_gradient_even_for_false_texture():
    target, pairs = wave_case()
    target.zero_()
    value = torch.arange(target.numel(), dtype=torch.float64).reshape_as(target).requires_grad_()
    loss = paired_coherent_response_loss(value, target, pairs)
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0


def test_floor_bounds_response_as_clean_difference_vanishes():
    target, pairs = wave_case()
    output = torch.zeros_like(target)
    losses = []
    norms = []
    for scale in [1, 1e-2, 1e-4, 0]:
        value = output.clone().requires_grad_()
        loss = paired_coherent_response_loss(value, target * scale, pairs)
        gradient = torch.autograd.grad(loss, value)[0]
        losses.append(float(loss.detach()))
        norms.append(float(gradient.norm()))
    assert all(a > b for a, b in pairwise(losses))
    assert all(a > b for a, b in pairwise(norms))


def test_empty_pairs_remain_connected_zero_without_changing_dtype():
    value = torch.zeros((2, 3, 4, 5), requires_grad=True)
    loss = paired_coherent_response_loss(
        value, value.detach(), torch.empty((0, 2), dtype=torch.int64)
    )
    assert loss.dtype == torch.float32 and loss == 0
    assert torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0


def test_empty_pair_zero_avoids_overflow_from_summing_finite_outputs():
    value = torch.full((4, 3, 2, 2), torch.finfo(torch.float32).max, requires_grad=True)
    loss = paired_coherent_response_loss(
        value, value.detach(), torch.empty((0, 2), dtype=torch.int64)
    )
    assert torch.isfinite(loss) and loss == 0
    assert torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0


@pytest.mark.parametrize("bad", ["target_shape", "channels", "nonfinite", "indices_dtype"])
def test_invalid_rgb_or_pair_contract_rejected(bad):
    a, pairs = wave_case()
    target = a.clone()
    if bad == "target_shape":
        target = target[..., :3]
    if bad == "channels":
        a = a[:, :2]
        target = a.clone()
    if bad == "nonfinite":
        a[0, 0, 0, 0] = float("nan")
    if bad == "indices_dtype":
        pairs = pairs.float()
    with pytest.raises(ValueError):
        paired_coherent_response_loss(a, target, pairs)


@pytest.mark.parametrize("pairs", [[[0, 0]], [[0, 1], [1, 2]], [[-1, 0]], [[0, 4]]])
def test_invalid_pair_members_rejected(pairs):
    a = torch.zeros((4, 3, 3, 5))
    with pytest.raises(ValueError):
        paired_coherent_response_loss(a, a, torch.tensor(pairs))


@pytest.mark.parametrize("floor", [0, -1, True, float("nan"), float("inf")])
def test_invalid_floor_rejected(floor):
    a, pairs = wave_case()
    with pytest.raises(ValueError):
        paired_coherent_response_loss(a, a, pairs, floor_DN16=floor)


@pytest.mark.parametrize("paired", [True, False])
def test_wrapper_retains_all_eight_terms_mask_and_fp32_total_order(paired):
    gen = torch.Generator().manual_seed(18302)
    target = 0.002 + torch.randn((4, 3, 19, 23), generator=gen) * 2 / 65535
    output = (target + torch.randn(target.shape, generator=gen) * 3 / 65535).requires_grad_()
    frozen = target + torch.randn(target.shape, generator=gen) * 4 / 65535
    pairs = torch.tensor([[0, 1], [2, 3]]) if paired else torch.empty((0, 2), dtype=torch.int64)
    batch = {"target": target, "variance": torch.full((4, 4, 10, 12), 1e-7), "pair_indices": pairs}
    units = torch.full((2 if paired else 0, 1, 1, 1), 16 / 65535)
    old, parts, mask = previous_objective(output, frozen, batch, units, 4.0)
    new, terms, selected = objective(output, frozen, batch, units, 4.0)
    assert set(terms) == set(parts) | {"coherent_response"}
    assert all(torch.equal(v, terms[k]) for k, v in parts.items()) and torch.equal(mask, selected)
    assert torch.equal(new, old + terms["coherent_response"])
    assert torch.isfinite(torch.autograd.grad(new, output)[0]).all()
