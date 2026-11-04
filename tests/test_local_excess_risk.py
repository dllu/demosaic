"""Independent native-box values and full-output adjoints for local regret."""

import numpy as np
import pytest
import torch
from local_excess_risk import local_excess_risk, local_rms_regret


def independent(value, parent, target, scales, window, transition):
    """Enumerate real pixel coordinates, including repeated boundary samples."""
    n, channels, height, width = value.shape
    hop = window // 2
    total_boxes = n * (int(np.ceil(height / hop)) + 1) * (int(np.ceil(width / hop)) + 1)
    gradient = np.zeros_like(value)
    losses, differences = [], []
    for batch in range(n):
        image_differences = []
        unit = scales[batch, 0, 0, 0]
        for cy in range(0, int(np.ceil(height / hop)) * hop + 1, hop):
            row = []
            ys = np.clip(np.arange(cy - hop, cy + hop), 0, height - 1)
            for cx in range(0, int(np.ceil(width / hop)) * hop + 1, hop):
                xs = np.clip(np.arange(cx - hop, cx + hop), 0, width - 1)
                predicted = value[batch][:, ys[:, None], xs]
                previous = parent[batch][:, ys[:, None], xs]
                clean = target[batch][:, ys[:, None], xs]
                residual = (predicted - clean) / unit
                old = (previous - clean) / unit
                old_norm = np.sqrt(np.mean(old**2) + (1 / 65535 / unit) ** 2)
                new_norm = np.sqrt(np.mean(residual**2) + (1 / 65535 / unit) ** 2)
                d = new_norm - old_norm
                row.append(d)
                derivative = min(1, max(0, d) / transition)
                losses.append(
                    0
                    if d <= 0
                    else d**2 / (2 * transition)
                    if d < transition
                    else d - transition / 2
                )
                adjoint = (
                    derivative * residual / (new_norm * unit * channels * window**2 * total_boxes)
                )
                for channel in range(channels):
                    np.add.at(
                        gradient[batch, channel], (ys[:, None], xs[None, :]), adjoint[channel]
                    )
            image_differences.append(row)
        differences.append([image_differences])
    return np.mean(losses), gradient, np.asarray(differences)


@pytest.mark.parametrize(
    "shape,window", [((2, 3, 17, 23), 8), ((2, 3, 3, 5), 32), ((1, 3, 32, 48), 32)]
)
def test_numpy_values_and_full_adjoint(shape, window):
    rng = np.random.default_rng(15601)
    target = rng.uniform(0, 0.02, shape)
    parent = target + rng.normal(0, 0.003, shape)
    output = parent + rng.normal(0.0003, 0.001, shape)
    scales = np.linspace(0.002, 0.008, shape[0]).reshape(-1, 1, 1, 1)
    expected, gradient, differences = independent(output, parent, target, scales, window, 0.001)
    value = torch.tensor(output, requires_grad=True)
    arguments = [torch.tensor(v) for v in (parent, target, scales)]
    actual = local_excess_risk(value, *arguments, window=window, transition=0.001)
    actual.backward()
    assert actual.item() == pytest.approx(expected, rel=2e-12, abs=1e-14)
    np.testing.assert_allclose(value.grad, gradient, atol=1e-12, rtol=1e-11)
    np.testing.assert_allclose(
        local_rms_regret(value, *arguments, window=window).detach(),
        differences,
        atol=1e-14,
        rtol=1e-11,
    )


@pytest.mark.parametrize("perfect", [False, True])
def test_zero_parent_value_and_finite_zero_derivatives(perfect):
    parent = torch.full((1, 3, 7, 11), 0.02, dtype=torch.float64, requires_grad=True)
    target = parent.detach().clone() if perfect else torch.zeros_like(parent)
    target.requires_grad_()
    scale = torch.tensor([0.003], dtype=torch.float64).reshape(1, 1, 1, 1).requires_grad_()
    value = parent.detach().clone().requires_grad_()
    loss = local_excess_risk(value, parent, target, scale)
    first = torch.autograd.grad(loss, value, create_graph=True)[0]
    second = torch.autograd.grad(first.sum(), value)[0]
    assert loss == 0 and first.count_nonzero() == 0
    assert torch.isfinite(second).all()
    assert parent.grad is target.grad is scale.grad is None


def test_quiet_regression_is_visible_despite_better_whole_image_error():
    target = torch.zeros(1, 3, 64, 96, dtype=torch.float64)
    parent = torch.full_like(target, 0.1)
    parent[..., :48] = 0.01
    output = parent.clone()
    output[..., :48] = 0.02
    output[..., 48:] = 0.05
    assert output.square().mean() < parent.square().mean()
    assert local_excess_risk(output, parent, target, torch.ones(1, 1, 1, 1)) > 0
    assert local_excess_risk(parent / 2, parent, target, torch.ones(1, 1, 1, 1)) == 0


def test_tiny_positive_regret_survives_rationalization():
    parent = torch.full((1, 3, 3, 5), 0.5, dtype=torch.float64)
    output = (parent + 1e-12).requires_grad_()
    target = torch.zeros_like(parent)
    scale = torch.ones(1, 1, 1, 1, dtype=torch.float64)
    loss = local_excess_risk(output, parent, target, scale)
    loss.backward()
    assert loss > 0 and torch.isfinite(output.grad).all() and output.grad.min() > 0


def test_quadratic_hinge_region_has_independent_full_adjoint():
    parent = np.full((2, 3, 5, 9), 0.02)
    target = np.zeros_like(parent)
    output = parent + 1e-8
    scales = np.array([0.003, 0.007]).reshape(2, 1, 1, 1)
    expected, gradient, regret = independent(output, parent, target, scales, 8, 1e-4)
    assert regret.min() > 0 and regret.max() < 1e-4
    value = torch.tensor(output, requires_grad=True)
    actual = local_excess_risk(
        value, torch.tensor(parent), torch.tensor(target), torch.tensor(scales), window=8
    )
    actual.backward()
    assert actual.item() == pytest.approx(expected, rel=1e-8)
    np.testing.assert_allclose(value.grad, gradient, atol=1e-10, rtol=1e-8)


def test_bad_scales_and_geometry():
    rgb = torch.zeros(1, 3, 4, 4)
    for units in [torch.zeros(1, 1, 1, 1), torch.full((1, 1, 1, 1), float("nan")), torch.ones(1)]:
        with pytest.raises(ValueError):
            local_excess_risk(rgb, rgb, rgb, units)
    with pytest.raises(ValueError):
        local_excess_risk(rgb, rgb, rgb, torch.ones(1, 1, 1, 1), window=3)
    with pytest.raises(ValueError):
        local_excess_risk(rgb, rgb, rgb, torch.ones(1, 1, 1, 1), transition=0)
