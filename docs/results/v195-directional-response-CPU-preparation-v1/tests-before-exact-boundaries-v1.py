"""Independent explicit-DFT/spatial derivatives and weak-direction pressure checks."""

import math

import numpy as np
import pytest
import torch
from coherent_pair_objective import objective as previous_objective
from coherent_pair_objective import paired_coherent_response_loss
from directional_pair_objective import (
    objective,
    orientation_masks,
    paired_directional_response_loss,
)


def explicit_reference(output, target, pairs, floor):
    derivative = np.zeros_like(output, dtype=np.float64)
    loss = 0.0
    height, width = output.shape[-2:]
    n = height * width
    y, x = np.mgrid[:height, :width]
    ky, kx = np.meshgrid(np.fft.fftfreq(height), np.fft.fftfreq(width), indexing="ij")
    basis = np.exp(
        -2j * np.pi * (ky.ravel()[:, None] * y.ravel() + kx.ravel()[:, None] * x.ravel())
    ) / math.sqrt(n)
    regions = []
    for offset in [0, math.pi / 8]:
        labels = []
        for iy in range(height):
            for ix in range(width):
                cy, cx = divmod(min(iy * width + ix, (-iy) % height * width + (-ix) % width), width)
                angle = math.atan2(ky[cy, cx], kx[cy, cx]) % math.pi
                labels.append(min(3, int(((angle - offset) % math.pi) / (math.pi / 4))))
        for sector in range(4):
            mask = np.asarray(labels) == sector
            mask[0] = False
            regions.append(mask)
    for a, b in pairs:
        delta = target[a] - target[b]
        t = delta - delta.mean((1, 2), keepdims=True)
        error = output[a] - output[b] - delta
        error -= error.mean((1, 2), keepdims=True)
        coefficients = t.reshape(3, n) @ basis.T
        for mask in regions:
            sub = ((coefficients * mask) @ basis.conj()).reshape(t.shape)
            assert abs(sub.imag).max() < 1e-12
            sub = sub.real
            energy = np.mean(sub**2) + (floor / 65535) ** 2
            r = np.mean(error * sub) / energy
            loss += (math.sqrt(1 + r * r) - 1) / (len(pairs) * 8)
            direction = sub - sub.mean((1, 2), keepdims=True)
            grad = r / math.sqrt(1 + r * r) * direction / (energy * t.size * len(pairs) * 8)
            derivative[a] += grad
            derivative[b] -= grad
    return loss, derivative


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("floor", [0.25, 1.0, 4.0])
def test_explicit_real_basis_values_and_output_derivatives(dtype, floor):
    rng = np.random.default_rng(19501)
    target = rng.normal(0.003, 2 / 65535, (4, 3, 5, 7))
    target[2:] = 0.003 + (target[2:] - 0.003) * 0.1
    output = target + rng.normal(0, 3 / 65535, target.shape)
    value = torch.tensor(output, dtype=dtype, requires_grad=True)
    clean = torch.tensor(target, dtype=dtype, requires_grad=True)
    pairs = torch.tensor([[0, 1], [2, 3]])
    expected, derivative = explicit_reference(
        value.detach().double().numpy(), clean.detach().double().numpy(), pairs.numpy(), floor
    )
    loss = paired_directional_response_loss(value, clean, pairs, floor_DN16=floor)
    actual, gt = torch.autograd.grad(loss, (value, clean), allow_unused=True)
    assert gt is None and loss.dtype == dtype
    assert loss.item() == pytest.approx(
        expected, rel=3e-7 if dtype == torch.float32 else 1e-10, abs=1e-13
    )
    np.testing.assert_allclose(
        actual.numpy(),
        derivative,
        rtol=3e-6 if dtype == torch.float32 else 1e-9,
        atol=1e-6 if dtype == torch.float32 else 1e-10,
    )


def waves():
    y, x = torch.meshgrid(
        torch.arange(32, dtype=torch.float64), torch.arange(32, dtype=torch.float64), indexing="ij"
    )
    weak = (2 * torch.pi * (3 * x + y) / 32).cos() * 6 / 65535
    strong = (2 * torch.pi * (-x + 4 * y) / 32).cos() * 30 / 65535
    target = torch.full((2, 3, 32, 32), 0.003, dtype=torch.float64)
    target[0] += weak + strong
    value = torch.full_like(target, 0.003)
    value[0] += strong
    direction = torch.zeros_like(target)
    direction[0] += weak
    return target, value, direction, torch.tensor([[0, 1]])


def test_known_missing_weak_wave_gets_stronger_response_pressure_than_whole_projection():
    target, output, direction, pairs = waves()
    value = output.requires_grad_()
    loss = paired_directional_response_loss(value, target, pairs)
    r = -18 / 19
    assert loss.item() == pytest.approx((math.sqrt(1 + r * r) - 1) / 4, abs=1e-12)
    directional = torch.autograd.grad(loss, value)[0]
    whole = torch.autograd.grad(paired_coherent_response_loss(value, target, pairs), value)[0]
    ds = float((directional * direction).sum())
    ws = float((whole * direction).sum())
    assert ds < 0 and ws < 0 and abs(ds) > 10 * abs(ws)
    assert paired_directional_response_loss(target, target, pairs) == 0


@pytest.mark.parametrize("rotation", range(4))
@pytest.mark.parametrize("flip", [False, True])
def test_d4_transport_of_nonboundary_analytic_carriers(rotation, flip):
    target, value, _, pairs = waves()
    expected = paired_directional_response_loss(value, target, pairs)
    target, value = [torch.rot90(v, rotation, (-2, -1)) for v in [target, value]]
    if flip:
        target, value = [v.flip(-1) for v in [target, value]]
    torch.testing.assert_close(
        paired_directional_response_loss(value, target, pairs), expected, rtol=1e-11, atol=1e-12
    )


def test_constant_errors_pair_swap_and_common_pixel_shift_are_invisible_or_invariant():
    target, value, _, pairs = waves()
    expected = paired_directional_response_loss(value, target, pairs)
    constants = torch.tensor([0.1, -0.2, 0.3], dtype=value.dtype)[None, :, None, None]
    torch.testing.assert_close(
        paired_directional_response_loss(value + constants, target, pairs),
        expected,
        atol=1e-11,
        rtol=1e-11,
    )
    torch.testing.assert_close(
        paired_directional_response_loss(value, target, pairs.flip(1)), expected
    )
    torch.testing.assert_close(
        paired_directional_response_loss(
            value.roll((3, -5), (-2, -1)), target.roll((3, -5), (-2, -1)), pairs
        ),
        expected,
    )


def test_unchanged_target_and_orthogonal_false_pattern_do_not_supply_flat_safety():
    target, value, _, pairs = waves()
    target.zero_()
    value = value.requires_grad_()
    loss = paired_directional_response_loss(value, target, pairs)
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0
    target, _, _, pairs = waves()
    y, x = torch.meshgrid(
        torch.arange(32, dtype=torch.float64), torch.arange(32, dtype=torch.float64), indexing="ij"
    )
    false = (2 * torch.pi * (3 * x + y) / 32).sin() / 65535
    out = target.clone()
    out[0] += false
    assert (
        paired_directional_response_loss(out, target, pairs) < 1e-20
        and torch.count_nonzero(out - target) > 0
    )


@pytest.mark.parametrize("shape", [(5, 7), (8, 10), (1, 1)])
def test_regions_are_disjoint_per_tiling_and_conjugate_closed(shape):
    m = orientation_masks(*shape, torch.device("cpu"))
    h, w = shape
    count = m.reshape(2, 4, h, w).sum(1)
    expected = torch.ones((h, w), dtype=count.dtype)
    expected[0, 0] = 0
    assert torch.equal(count[0], expected) and torch.equal(count[1], expected)
    yy = (-torch.arange(h)) % h
    xx = (-torch.arange(w)) % w
    assert torch.equal(m, m[:, yy][:, :, xx])


def test_empty_pairs_keep_connected_finite_zero_even_at_maximum_finite_output():
    value = torch.full((4, 3, 2, 2), torch.finfo(torch.float32).max, requires_grad=True)
    loss = paired_directional_response_loss(
        value, value.detach(), torch.empty((0, 2), dtype=torch.int64)
    )
    assert (
        torch.isfinite(loss)
        and loss == 0
        and torch.count_nonzero(torch.autograd.grad(loss, value)[0]) == 0
    )


@pytest.mark.parametrize("mode", ["whole", "directional"])
@pytest.mark.parametrize("paired", [True, False])
def test_both_wrappers_retain_nine_original_scalars_masks_and_exact_total_order(mode, paired):
    generator = torch.Generator().manual_seed(19502)
    target = 0.002 + torch.randn((4, 3, 19, 23), generator=generator) * 2 / 65535
    value = (target + torch.randn(target.shape, generator=generator) * 3 / 65535).requires_grad_()
    frozen = target + torch.randn(target.shape, generator=generator) * 4 / 65535
    pairs = torch.tensor([[0, 1], [2, 3]]) if paired else torch.empty((0, 2), dtype=torch.int64)
    batch = {"target": target, "variance": torch.full((4, 4, 10, 12), 1e-7), "pair_indices": pairs}
    units = torch.full((2 if paired else 0, 1, 1, 1), 16 / 65535)
    old, parts, mask = previous_objective(value, frozen, batch, units, 4.0)
    new, terms, selected = objective(value, frozen, batch, units, 4.0, mode=mode)
    assert set(terms) == set(parts) | {"response_addition"} and all(
        torch.equal(v, terms[k]) for k, v in parts.items()
    )
    assert torch.equal(mask, selected) and torch.equal(new, old + terms["response_addition"])
    if mode == "whole":
        assert torch.equal(terms["response_addition"], terms["coherent_response"])
    assert torch.isfinite(torch.autograd.grad(new, value)[0]).all()
