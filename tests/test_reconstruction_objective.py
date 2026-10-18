"""Per-image weighting, masks and derivatives of the optional PSNR objective."""

import math

import numpy as np
import pytest
import torch
from test_losses import noise_batch

from demosaic.color import render
from demosaic.losses import image_log_mse, reconstruction_loss
from demosaic.paired_training import paired_reconstruction_loss


def test_per_image_logarithm_and_gradient_agree_with_independent_formula():
    values = np.array([[[[0.01, -0.03]]], [[[0.2, -0.4]]]], dtype=np.float32)
    error = torch.tensor(values, requires_grad=True)
    value = image_log_mse(error)
    mse = np.mean(values.astype(np.float64) ** 2, axis=(1, 2, 3))
    expected = sum(10 * math.log10(x) for x in mse) / len(mse)
    assert value.item() == pytest.approx(expected, abs=2e-6)
    assert abs(value.item() - 10 * math.log10(mse.mean())) > 1
    value.backward()
    gradient = 20 / math.log(10) * values / mse[:, None, None, None] / values.size
    np.testing.assert_allclose(error.grad.numpy(), gradient, rtol=1e-6)


def test_mask_counts_are_per_image_and_ignore_empty_and_nonfinite_invalid_samples():
    error = torch.tensor([[[[0.1, float("nan")]]], [[[0.2, 0.2]]], [[[float("nan"), 9.0]]]],
                         requires_grad=True)
    mask = torch.tensor([[[[True, False]]], [[[True, True]]], [[[False, False]]]])
    loss = image_log_mse(error, mask)
    assert loss.item() == pytest.approx((-20 + 20 * math.log10(0.2)) / 2, abs=2e-6)
    loss.backward()
    assert torch.isfinite(error.grad).all()
    assert error.grad[0, 0, 0, 1] == 0 and error.grad[2].count_nonzero() == 0


@pytest.mark.parametrize("empty", [False, True])
def test_exact_and_empty_targets_have_finite_values_and_zero_gradients(empty):
    error = torch.zeros(2, 3, 4, 4, requires_grad=True)
    loss = image_log_mse(error, torch.zeros_like(error, dtype=torch.bool) if empty else None)
    assert loss.item() == (0 if empty else -100)
    loss.backward()
    assert error.grad.count_nonzero() == 0


@pytest.mark.parametrize("paired", [False, True])
def test_new_policy_replaces_only_primary_terms_and_default_is_bitwise_unchanged(paired):
    batch = noise_batch()
    prediction = batch["target"] + torch.tensor([.002, .02])[:, None, None, None]
    function = paired_reconstruction_loss if paired else reconstruction_loss
    if paired:
        batch.update(sensor_reference=batch["target"], sensor_mask=torch.ones_like(
            prediction, dtype=torch.bool))
    original, parts = function(prediction, batch)
    explicit, _ = function(prediction, batch, objective="charbonnier-v1")
    assert torch.equal(original, explicit)
    changed, new_parts = function(prediction, batch, objective="image-log-mse-v1")
    if paired:
        first, second = "paired_sensor", "paired_coarse_rendered"
    else:
        first, second = "linear", "rendered"
    expected = original - parts[first] - .5 * parts[second] + new_parts[first] + .5 * new_parts[second]
    torch.testing.assert_close(changed, expected)
    torch.testing.assert_close(new_parts[first], image_log_mse(prediction - batch["target"]))
    assert set(parts) == set(new_parts)
    if not paired:
        display_error = render(prediction, batch["wb"], batch["matrix"]) - render(
            batch["target"], batch["wb"], batch["matrix"])
        torch.testing.assert_close(new_parts[second], image_log_mse(display_error))
    for name in set(parts) - {first, second}:
        assert torch.equal(parts[name], new_parts[name])


@pytest.mark.parametrize("function", [reconstruction_loss, paired_reconstruction_loss])
def test_unknown_policy_is_rejected_before_accessing_batch(function):
    with pytest.raises(ValueError, match="Unknown reconstruction objective"):
        function(None, {}, objective="typo")
