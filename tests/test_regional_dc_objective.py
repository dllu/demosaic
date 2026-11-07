"""Independent coordinates,RGB mean derivatives and targeted regional-bias cases."""

import numpy as np
import pytest
import torch
from regional_dc_objective import regional_dc_excess, regional_dc_regret


def reference(output, parent, target, scales, window, transition):
    batch, channels, height, width = output.shape
    hop = window // 2
    boxes = batch * (int(np.ceil(height / hop)) + 1) * (int(np.ceil(width / hop)) + 1)
    gradient = np.zeros_like(output)
    values, differences = [], []
    for n in range(batch):
        unit = max(scales[n, 0, 0, 0] / (window / 2), 1 / 65535)
        image = []
        for cy in range(0, int(np.ceil(height / hop)) * hop + 1, hop):
            ys = np.clip(np.arange(cy - hop, cy + hop), 0, height - 1)
            row = []
            for cx in range(0, int(np.ceil(width / hop)) * hop + 1, hop):
                xs = np.clip(np.arange(cx - hop, cx + hop), 0, width - 1)
                predicted = output[n][:, ys[:, None], xs]
                old = parent[n][:, ys[:, None], xs]
                clean = target[n][:, ys[:, None], xs]
                after = ((predicted - clean) / unit).mean((1, 2))
                before = ((old - clean) / unit).mean((1, 2))
                r1 = np.sqrt(np.mean(after**2) + (1 / 65535 / unit) ** 2)
                r0 = np.sqrt(np.mean(before**2) + (1 / 65535 / unit) ** 2)
                regret = r1 - r0
                row.append(regret)
                values.append(
                    0
                    if regret <= 0
                    else regret**2 / (2 * transition)
                    if regret < transition
                    else regret - transition / 2
                )
                slope = min(1, max(0, regret) / transition)
                for c in range(channels):
                    derivative = slope * after[c] / (channels * window**2 * unit * r1 * boxes)
                    np.add.at(gradient[n, c], (ys[:, None], xs[None, :]), derivative)
            image.append(row)
        differences.append([image])
    return np.mean(values), gradient, np.asarray(differences)


@pytest.mark.parametrize(
    "shape,window,increment",
    [
        ((2, 3, 17, 23), 8, 0.001),
        ((2, 3, 3, 5), 32, 0.001),
        ((1, 3, 32, 48), 32, 0.001),
        ((2, 3, 5, 9), 8, 1e-9),
    ],
)
def test_numpy_full_rgb_adjoint_and_padded_box_values(shape, window, increment):
    rng = np.random.default_rng(15801)
    target = rng.uniform(0, 0.02, shape)
    parent = target + rng.normal(0, 0.002, shape)
    output = parent + increment
    scales = np.linspace(0.003, 0.008, shape[0]).reshape(-1, 1, 1, 1)
    expected, gradient, boxes = reference(output, parent, target, scales, window, 1e-4)
    value = torch.tensor(output, requires_grad=True)
    args = [torch.tensor(v) for v in [parent, target, scales]]
    loss = regional_dc_excess(value, *args, window=window)
    loss.backward()
    assert loss.item() == pytest.approx(expected, rel=1e-7, abs=1e-13)
    np.testing.assert_allclose(value.grad, gradient, rtol=2e-7, atol=1e-10)
    np.testing.assert_allclose(
        regional_dc_regret(value, *args, window=window).detach(), boxes, rtol=1e-7, atol=1e-13
    )


@pytest.mark.parametrize("perfect", [False, True])
def test_parent_identity_detaches_inputs_and_has_finite_derivatives(perfect):
    parent = torch.full((2, 3, 7, 11), 0.02, dtype=torch.float64, requires_grad=True)
    target = (parent.detach().clone() if perfect else torch.zeros_like(parent)).requires_grad_()
    scales = torch.full((2, 1, 1, 1), 16 / 65535, dtype=torch.float64, requires_grad=True)
    value = parent.detach().clone().requires_grad_()
    loss = regional_dc_excess(value, parent, target, scales)
    first = torch.autograd.grad(loss, value, create_graph=True)[0]
    second = torch.autograd.grad(first.sum(), value)[0]
    assert loss == 0 and first.count_nonzero() == 0 and torch.isfinite(second).all()
    assert parent.grad is target.grad is scales.grad is None


def test_zero_mean_detail_is_distinct_from_regional_color_bias():
    target = torch.zeros(1, 3, 64, 96, dtype=torch.float64)
    detail = target.clone()
    yy, xx = torch.meshgrid(torch.arange(32), torch.arange(64), indexing="ij")
    detail[..., 16:48, 16:80] = ((xx + yy) % 2 * 2 - 1) * 0.002
    scale = torch.full((1, 1, 1, 1), 0.004, dtype=torch.float64)
    assert detail.square().mean() > 0 and regional_dc_excess(detail, target, target, scale) == 0
    offset = (
        target + torch.tensor([0.001, -0.001, 0.0005], dtype=torch.float64)[None, :, None, None]
    )
    assert regional_dc_excess(offset, target, target, scale) > 0


def test_improving_parent_color_bias_is_unpenalized():
    target = torch.zeros(1, 3, 33, 47, dtype=torch.float64)
    parent = torch.full_like(target, 0.002)
    scale = torch.full((1, 1, 1, 1), 0.004, dtype=torch.float64)
    assert regional_dc_excess(parent / 2, parent, target, scale) == 0
    assert regional_dc_excess(parent * 2, parent, target, scale) > 0


def test_quiet_bias_increase_is_seen_despite_lower_global_error():
    target = torch.zeros(1, 3, 64, 96, dtype=torch.float64)
    parent = torch.full_like(target, 0.1)
    parent[..., :48] = 0.001
    output = parent.clone()
    output[..., :48] = 0.002
    output[..., 48:] = 0.05
    assert output.square().mean() < parent.square().mean()
    assert regional_dc_excess(output, parent, target, torch.ones(1, 1, 1, 1)) > 0


def test_small_scale_floor_and_tiny_positive_bias_change():
    parent = torch.full((1, 3, 3, 5), 0.5, dtype=torch.float64)
    value = (parent + 1e-12).requires_grad_()
    loss = regional_dc_excess(
        value, parent, torch.zeros_like(parent), torch.full((1, 1, 1, 1), 1e-9, dtype=torch.float64)
    )
    loss.backward()
    assert loss > 0 and torch.isfinite(value.grad).all() and value.grad.min() > 0


def test_invalid_geometry_scales_and_transition():
    rgb = torch.zeros(1, 3, 4, 4)
    unit = torch.ones(1, 1, 1, 1)
    for scale in [torch.zeros_like(unit), unit * float("nan"), torch.ones(1)]:
        with pytest.raises(ValueError):
            regional_dc_excess(rgb, rgb, rgb, scale)
    with pytest.raises(ValueError):
        regional_dc_excess(rgb, rgb, rgb, unit, window=3)
    with pytest.raises(ValueError):
        regional_dc_excess(rgb, rgb, rgb, unit, transition=0)
