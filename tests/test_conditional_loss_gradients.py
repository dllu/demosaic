from itertools import combinations

import numpy as np
import pytest
import torch
from analyze_conditional_loss_gradients import (
    component_gradients,
    direct_wrapper_error,
    forbid_neural_calls,
    options,
    physical_gradient_error,
)

from demosaic.cfa import mosaic


@pytest.mark.parametrize("size", [16, 32])
def test_full_objective_replay_matches_planned_wrapper_and_analytic_sensor_terms(monkeypatch, size):
    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbid_neural_calls)
    torch.set_num_threads(2)
    random = np.random.default_rng(17)
    clean = np.linspace(-0.02, 1.2, 3 * size * size, dtype=np.float32).reshape(1, 3, size, size)
    wb = np.array([[2.0, 1.0, 1.5]], dtype=np.float32)
    matrix = np.array(
        [[[1.1, -0.05, -0.05], [-0.05, 1.1, -0.05], [-0.05, -0.05, 1.1]]], dtype=np.float32
    )
    linear = torch.einsum(
        "bij,bjhw->bihw", torch.from_numpy(matrix), torch.from_numpy(clean * wb[..., None, None])
    ).clamp(0, 1)
    target = (
        torch.einsum("bij,bjhw->bihw", torch.linalg.inv(torch.from_numpy(matrix)), linear)
        / torch.from_numpy(wb)[..., None, None]
    ).numpy()
    assert not np.array_equal(target, clean)
    data = {"target": target, "sensor_target": clean, "wb": wb, "matrix": matrix}
    colors = np.array([[0, 1, 1, 2]])
    packed = mosaic(torch.from_numpy(clean), torch.from_numpy(colors)).numpy()
    inputs = [
        {
            "packed": packed,
            "variance": np.full_like(packed, 0.01),
            "colors": colors,
            "wb": wb,
            "matrix": matrix,
        }
        for _ in range(2)
    ]
    predictions = clean + random.normal(0, 0.02, (8, 3, size, size)).astype(np.float32)
    means = np.stack([(predictions[i] + predictions[j]) / 2 for i, j in combinations(range(8), 2)])
    values = np.concatenate([predictions, means])
    state = torch.random.get_rng_state().clone()
    loss, terms, gradients = component_gradients(values, data, colors, options())
    assert np.isfinite(gradients).all() and np.isfinite(loss)
    assert loss == pytest.approx(
        terms["linear"]
        + 0.5 * terms["rendered"]
        + 0.1 * (terms["gradient"] + terms["highlight"] + terms["sensor"])
    )
    physical = physical_gradient_error(values, data, colors, gradients, 0.0003)
    assert max(physical.values()) < 5e-5
    direct = direct_wrapper_error(
        values,
        data,
        inputs,
        gradients,
        {"shot": 0.00256, "read": 2.62144e-5, "black_level": 0.03, "ADC_bits": 16},
        options(),
    )
    assert max(direct.values()) < 1e-5
    assert torch.equal(state, torch.random.get_rng_state())
