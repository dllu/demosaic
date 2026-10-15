import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.losses import noise_normalized_sensor_loss, reconstruction_loss


def noise_batch():
    return {
        "target": torch.full((2, 3, 32, 32), 0.1),
        "colors": color_indices("GBRG"),
        "shot": torch.zeros(2, 1, 1, 1),
        "read": torch.tensor([1e-6, 1e-4]).reshape(2, 1, 1, 1),
        "wb": torch.ones(2, 3),
        "matrix": torch.eye(3)[None].expand(2, -1, -1),
    }


def test_normalized_loss_treats_equal_noise_units_equally_in_shadows():
    batch = noise_batch()
    std = batch["read"].sqrt()
    prediction = (batch["target"] + 2 * std).requires_grad_()
    loss = noise_normalized_sensor_loss(prediction, batch, batch["target"])
    torch.testing.assert_close(loss, torch.tensor(2.0), atol=2e-6, rtol=2e-6)
    loss.backward()
    total_gradient = prediction.grad.flatten(1).sum(1)
    torch.testing.assert_close(total_gradient[0], 10 * total_gradient[1])
    assert torch.isfinite(prediction.grad).all()


@pytest.mark.parametrize("exclude", ["adc-only", "highlight"])
def test_normalized_loss_excludes_adc_only_and_reconstructed_highlights(exclude):
    batch = noise_batch()
    truth = batch["target"].clone()
    if exclude == "adc-only":
        batch["read"].zero_()
    else:
        truth[:, 0] = 1
    prediction = (batch["target"] + 0.01).requires_grad_()
    loss = noise_normalized_sensor_loss(prediction, batch, truth)
    assert loss.item() == 0
    loss.backward()
    assert prediction.grad.abs().sum() == 0


def test_optional_normalized_term_changes_loss_without_changing_legacy_default():
    batch = noise_batch()
    prediction = batch["target"] + 0.002
    legacy, terms = reconstruction_loss(prediction, batch)
    enabled, extended = reconstruction_loss(prediction, batch, normalized_sensor_weight=0.02)
    assert "normalized_sensor" not in terms
    torch.testing.assert_close(enabled, legacy + 0.02 * extended["normalized_sensor"])
