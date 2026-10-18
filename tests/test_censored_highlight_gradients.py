"""Physical invariants and the actual clipped-display stationary counterexample."""

import importlib.util
from pathlib import Path

import pytest
import torch

from demosaic.cfa import PATTERNS, bilinear, color_indices, mosaic


def probe():
    spec = importlib.util.spec_from_file_location(
        "highlight_probe", Path("scripts/probe_censored_highlight_gradients.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("pattern", PATTERNS)
def test_censored_correction_cannot_change_valid_measured_channels(pattern):
    module = probe()
    labels = color_indices(pattern)[None]
    packed = 0.1 + 0.8 * torch.rand((1, 4, 16, 16), generator=torch.Generator().manual_seed(48))
    packed[:, :, ::3, 2::3] = 1
    gate = module.censor_gate(packed, labels)
    assert 0 <= gate.min() <= gate.max() <= 1
    censored = packed == 1
    assert torch.equal(mosaic(gate, labels), censored.float())
    correction = gate * torch.tensor([0.7, -0.4, 1.2])[None, :, None, None]
    assert mosaic(correction, labels)[~censored].count_nonzero() == 0
    almost_white = torch.full_like(packed, 1 - 1 / 65535)
    assert module.censor_gate(almost_white, labels).count_nonzero() == 0


@pytest.mark.parametrize("observation", ["ideal-clipped", "ADC16-black.03"])
def test_actual_training_loss_has_a_censored_gradient_barrier_with_a_feasible_solution(observation):
    module = probe()
    matrix = [
        [1.117647, -0.0588235, -0.0588235],
        [-0.0588235, 1.117647, -0.0588235],
        [-0.0588235, -0.0588235, 1.117647],
    ]
    batch, packed = module.fixture([3.6, 1.8, 0.9], matrix, observation=observation)
    base = bilinear(packed, batch["colors"])
    gate = module.censor_gate(packed, batch["colors"])
    start = [0.0, 0.1, 0.0]
    plateau = module.inspect_beta(base, gate, batch, start)
    assert plateau["rendered_MSE"] > 0.0005
    assert plateau["current_loss_beta_gradient"] == [0.0, 0.0, 0.0]
    assert plateau["interval_beta_gradient"][0] < -0.01
    assert plateau["interval_beta_gradient"][1] < -0.01
    assert plateau["interval_beta_gradient"][2] == 0
    delta = module.oracle_direction(base, gate, batch, start)
    oracle = module.inspect_beta(base, gate, batch, (torch.tensor(start) + delta).tolist())
    assert oracle["rendered_MSE"] < 1e-12
    assert oracle["valid_camera_MSE"] == plateau["valid_camera_MSE"]
    assert oracle["current_loss"] < plateau["current_loss"] / 4


def test_interval_constraints_accept_exposed_white_and_negative_black_without_fabricating_error():
    module = probe()
    reference = torch.tensor([0.0, 1.0, 0.4])
    prediction = torch.tensor([-0.2, 2.3, 0.4], requires_grad=True)
    error = module.interval_errors(prediction, reference)
    assert error.count_nonzero() == 0
    module.charbonnier(error).backward()
    assert prediction.grad.count_nonzero() == 0
    outside = torch.tensor([0.2, 0.8, 1.3], requires_grad=True)
    module.charbonnier(module.interval_errors(outside, reference)).backward()
    assert outside.grad[0] > 0 and outside.grad[1] < 0 and outside.grad[2] > 0
