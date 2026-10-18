"""Production loss keeps the independently established pre-clipping gradients."""

import pytest
import torch
from test_censored_highlight_gradients import probe
from test_losses import noise_batch

from demosaic.cfa import bilinear, mosaic
from demosaic.losses import reconstruction_loss, reference_white_interval_loss


@pytest.mark.parametrize("observation", ["ideal-clipped", "ADC16-black.03"])
def test_production_interval_matches_prototype_and_removes_actual_stationary_barrier(observation):
    module = probe()
    matrix = [
        [1.117647, -0.0588235, -0.0588235],
        [-0.0588235, 1.117647, -0.0588235],
        [-0.0588235, -0.0588235, 1.117647],
    ]
    batch, packed = module.fixture([3.6, 1.8, 0.9], matrix, observation=observation)
    beta = torch.tensor([0.0, 0.1, 0.0], requires_grad=True)
    prediction = (
        bilinear(packed, batch["colors"])
        + module.censor_gate(packed, batch["colors"]) * beta[None, :, None, None]
    )
    actual = reference_white_interval_loss(prediction, batch)
    expected = module.interval_loss(prediction, batch)
    assert torch.equal(actual, expected)
    assert torch.equal(
        torch.autograd.grad(actual, beta, retain_graph=True)[0],
        torch.autograd.grad(expected, beta, retain_graph=True)[0],
    )
    loss, parts = reconstruction_loss(
        prediction,
        batch,
        mosaic(prediction, batch["colors"]),
        camera_supervision="sensor-valid-v1",
        reference_interval_weight=0.1,
    )
    gradient = torch.autograd.grad(loss, beta)[0]
    assert "reference_interval" in parts and gradient[0] < -0.001 and gradient[1] < -0.001
    assert gradient[2] == 0


def test_reference_intervals_accept_feasible_white_black_and_interior_without_latent_target():
    batch = {
        "wb": torch.ones(1, 3),
        "matrix": torch.eye(3)[None],
        "target": torch.tensor([0.0, 1.0, 0.4])[None, :, None, None],
    }
    prediction = torch.tensor([-0.2, 2.3, 0.4], requires_grad=True)
    loss = reference_white_interval_loss(prediction[None, :, None, None], batch)
    loss.backward()
    assert loss.item() == pytest.approx(0.001) and prediction.grad.count_nonzero() == 0


def test_zero_weight_preserves_every_default_loss_term_and_gradient():
    batch = noise_batch()
    prediction = (batch["target"] + 0.01).requires_grad_()
    a, parts = reconstruction_loss(prediction, batch)
    ga = torch.autograd.grad(a, prediction)[0]
    b, terms = reconstruction_loss(prediction, batch, reference_interval_weight=0.0)
    gb = torch.autograd.grad(b, prediction)[0]
    assert torch.equal(a, b) and torch.equal(ga, gb) and parts.keys() == terms.keys()
    assert all(torch.equal(v, terms[k]) for k, v in parts.items())


@pytest.mark.parametrize("weight", [-0.1, float("inf"), float("nan")])
def test_invalid_weights_are_rejected(weight):
    with pytest.raises(ValueError, match="interval weight"):
        reconstruction_loss(None, {}, reference_interval_weight=weight)


def test_nonzero_interval_requires_physical_camera_supervision():
    with pytest.raises(ValueError, match="sensor-valid"):
        reconstruction_loss(None, {}, reference_interval_weight=0.1)
