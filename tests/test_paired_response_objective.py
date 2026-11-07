"""Independent pair indexing,pixel adjoints and physical increment units."""

import math

import numpy as np
import pytest
import torch
from paired_response_objective import paired_response_loss, paired_sensor_increment_units


@pytest.mark.parametrize("increment", [0.002, 1e-7])
def test_numpy_full_pixel_adjoint_and_nonconsecutive_pair_indices(increment):
    rng = np.random.default_rng(16011)
    target = rng.uniform(0.001, 0.05, (4, 3, 7, 11))
    output = target + rng.normal(0, increment, target.shape)
    scales = np.array([0.001, 0.003]).reshape(2, 1, 1, 1)
    pairs = np.array([[3, 0], [1, 2]], dtype=np.int64)
    gradient = np.zeros_like(output)
    expected = 0.0
    epsilon = 0.003
    count = len(pairs) * np.prod(output.shape[1:])
    for pair, (first, second) in enumerate(pairs):
        scale = float(scales[pair, 0, 0, 0])
        for channel in range(3):
            for y in range(7):
                for x in range(11):
                    r = (
                        (output[first, channel, y, x] - output[second, channel, y, x])
                        - (target[first, channel, y, x] - target[second, channel, y, x])
                    ) / scale
                    norm = math.sqrt(r * r + epsilon * epsilon)
                    expected += (norm - epsilon) / count
                    derivative = r / (scale * norm * count)
                    gradient[first, channel, y, x] += derivative
                    gradient[second, channel, y, x] -= derivative
    value = torch.tensor(output, requires_grad=True)
    loss = paired_response_loss(value, torch.tensor(target), torch.tensor(scales), pairs)
    loss.backward()
    assert loss.item() == pytest.approx(expected, rel=1e-8, abs=1e-14)
    np.testing.assert_allclose(value.grad, gradient, rtol=1e-10, atol=1e-12)


def test_matching_response_detaches_target_units_and_has_finite_derivatives():
    target = torch.arange(4 * 3 * 3 * 5, dtype=torch.float64).reshape(4, 3, 3, 5).requires_grad_()
    value = target.detach().clone().requires_grad_()
    units = torch.ones(2, 1, 1, 1, dtype=torch.float64, requires_grad=True)
    loss = paired_response_loss(value, target, units, [[0, 1], [2, 3]])
    first = torch.autograd.grad(loss, value, create_graph=True)[0]
    second = torch.autograd.grad(first.sum(), value)[0]
    assert loss == 0 and first.count_nonzero() == 0 and torch.isfinite(second).all()
    assert target.grad is units.grad is None


def test_swapping_pair_members_preserves_loss_and_full_output_adjoint():
    generator = torch.Generator().manual_seed(16012)
    target = torch.randn(4, 3, 5, 9, generator=generator, dtype=torch.float64)
    value = torch.randn(4, 3, 5, 9, generator=generator, dtype=torch.float64).requires_grad_()
    units = torch.tensor([0.2, 0.5], dtype=torch.float64).reshape(2, 1, 1, 1)
    a = paired_response_loss(value, target, units, [[0, 1], [2, 3]])
    b = paired_response_loss(value, target, units, [[1, 0], [3, 2]])
    assert a == b
    assert torch.equal(torch.autograd.grad(a, value)[0], torch.autograd.grad(b, value)[0])


def test_shared_wrong_texture_is_invisible_but_differential_quiet_error_is_seen():
    target = torch.zeros(2, 3, 8, 12, dtype=torch.float64)
    shared = torch.arange(96, dtype=torch.float64).reshape(1, 1, 8, 12).expand(2, 3, -1, -1) / 1000
    units = torch.ones(1, 1, 1, 1, dtype=torch.float64)
    assert shared.square().mean() > 0 and paired_response_loss(shared, target, units, [[0, 1]]) == 0
    different = shared.clone()
    different[0, :, :4] += 0.0001
    assert paired_response_loss(different, target, units, [[0, 1]]) > 0


def test_tiny_nonzero_error_retains_positive_loss_in_quadratic_region():
    output = torch.zeros(2, 3, 3, 5, dtype=torch.float64)
    output[0] = 1e-12
    output.requires_grad_()
    loss = paired_response_loss(
        output, torch.zeros_like(output), torch.ones(1, 1, 1, 1, dtype=torch.float64), [[0, 1]]
    )
    loss.backward()
    assert loss.item() == pytest.approx(1e-24 / (2 * 0.003), rel=1e-9)
    assert (
        torch.isfinite(output.grad).all() and output.grad[0].min() > 0 and output.grad[1].max() < 0
    )


def test_increment_units_match_explicit_sensor_coordinate_sum_and_detach():
    rng = np.random.default_rng(16013)
    a = rng.uniform(0, 0.1, (3, 4, 7, 11))
    b = a + rng.uniform(0, 0.002, a.shape)
    shot = np.array([0.0, 0.00128, 0.00256]).reshape(3, 1, 1, 1)
    expected = []
    for n in range(3):
        variance = sum(
            shot[n, 0, 0, 0] * abs(float(a[n, c, y, x] - b[n, c, y, x]))
            for c in range(4)
            for y in range(7)
            for x in range(11)
        ) / (4 * 7 * 11)
        expected.append(max(math.sqrt(variance), 16 / 65535))
    aa, bb = [torch.tensor(v, requires_grad=True) for v in [a, b]]
    coefficient = torch.tensor(shot, requires_grad=True)
    actual = paired_sensor_increment_units(aa, bb, coefficient)
    np.testing.assert_allclose(actual.flatten(), expected, rtol=1e-13, atol=0)
    assert not actual.requires_grad


def test_invalid_pair_geometry_and_units():
    rgb = torch.zeros(4, 3, 3, 5)
    unit = torch.ones(2, 1, 1, 1)
    for pairs in [[[0, 0], [2, 3]], [[0, 1], [1, 2]], [[0, 4], [1, 2]], [[0.0, 1.0], [2.0, 3.0]]]:
        with pytest.raises(ValueError):
            paired_response_loss(rgb, rgb, unit, pairs)
    with pytest.raises(ValueError):
        paired_response_loss(rgb, rgb, unit * 0, [[0, 1], [2, 3]])
    with pytest.raises(ValueError):
        paired_response_loss(rgb, rgb, unit, [[0, 1], [2, 3]], epsilon=0)
