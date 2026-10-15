import math

import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.losses import multiscale_sensor_loss, reconstruction_loss
from demosaic.paired_training import paired_reconstruction_loss


def batch_at(device="cpu"):
    colors = torch.stack([color_indices(p) for p in PATTERNS]).to(device)
    target = (
        torch.tensor([0.125, 0.25, 0.5], device=device)[None, :, None, None]
        .expand(4, 3, 64, 64)
        .clone()
    )
    return {
        "target": target,
        "colors": colors,
        "shot": torch.zeros(4, 1, 1, 1, device=device),
        "read": torch.full((4, 1, 1, 1), 2**-16, device=device),
        "wb": torch.ones(4, 3, device=device),
        "matrix": torch.eye(3, device=device)[None].expand(4, -1, -1),
    }


def measured_batch():
    batch = batch_at()
    mask = torch.zeros_like(batch["target"], dtype=torch.bool)
    for b in range(4):
        for phase, color in enumerate(batch["colors"][b]):
            y, x = divmod(phase, 2)
            mask[b, color, y::2, x::2] = True
    batch.update(sensor_mask=mask, sensor_reference=batch["target"] * mask)
    return batch


@pytest.mark.parametrize(
    "device",
    [
        "cpu",
        pytest.param(
            "cuda",
            marks=pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA physical loss"),
        ),
    ],
)
def test_multiscale_constant_error_has_expected_noise_units_in_all_cfas(device):
    batch = batch_at(device)
    delta = 2**-12
    prediction = (batch["target"] + delta).requires_grad_()
    with torch.autocast(device_type=device, dtype=torch.bfloat16, enabled=device == "cuda"):
        result = multiscale_sensor_loss(prediction, batch)
    expected = sum(math.sqrt((delta / 2**-8 * s) ** 2 + 1e-6) - 1e-3 for s in (4, 16, 32)) / 3
    assert result.dtype == torch.float32
    torch.testing.assert_close(result, torch.tensor(expected, device=device), atol=2e-7, rtol=2e-7)
    result.backward()
    assert torch.isfinite(prediction.grad).all() and prediction.grad.abs().sum() > 0


def test_coarse_loss_ignores_phasewise_zero_mean_fine_error():
    batch = batch_at()
    stripes = ((torch.arange(64) // 2) % 2 * 2 - 1).float()[None, None, None] / 128
    prediction = batch["target"] + stripes
    assert (
        mosaic(prediction, batch["colors"]) - mosaic(batch["target"], batch["colors"])
    ).abs().sum() > 0
    assert multiscale_sensor_loss(prediction, batch).item() == 0
    assert multiscale_sensor_loss(prediction + 2**-10, batch) > 0.1


def test_real_loss_uses_measured_samples_and_ignores_ahd_and_invalid_channels():
    batch = measured_batch()
    prediction = (batch["target"] + 2**-10).requires_grad_()
    expected = multiscale_sensor_loss(prediction, batch)
    batch["target"] = torch.full_like(prediction, 0.9)
    batch["sensor_reference"][~batch["sensor_mask"]] = 999
    actual = multiscale_sensor_loss(prediction, batch)
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)
    actual.backward()
    assert prediction.grad[~batch["sensor_mask"]].count_nonzero() == 0


@pytest.mark.parametrize("exclude", ["adc-only", "clipped-synthetic", "invalid-real"])
def test_multiscale_invalid_blocks_have_zero_loss_and_zero_gradient(exclude):
    batch = measured_batch() if exclude == "invalid-real" else batch_at()
    if exclude == "adc-only":
        batch["read"].zero_()
    if exclude == "invalid-real":
        batch["sensor_mask"].zero_()
    truth = torch.ones_like(batch["target"]) if exclude == "clipped-synthetic" else None
    prediction = (batch["target"] + 0.01).requires_grad_()
    loss = multiscale_sensor_loss(prediction, batch, truth)
    assert loss.item() == 0
    loss.backward()
    assert prediction.grad.count_nonzero() == 0


def test_a_single_invalid_reference_sample_does_not_leak_into_valid_block_loss():
    batch = measured_batch()
    prediction = batch["target"].clone()
    b, c, y, x = 0, int(batch["colors"][0, 0]), 0, 0
    batch["sensor_mask"][b, c, y, x] = False
    batch["sensor_reference"][b, c, y, x] = 1000
    prediction[b, c, y, x] = -1000
    assert multiscale_sensor_loss(prediction, batch).item() == 0


@pytest.mark.parametrize("paired", [False, True])
def test_multiscale_weight_is_opt_in_and_adds_the_same_term_to_both_objectives(paired):
    batch = measured_batch() if paired else batch_at()
    prediction = batch["target"] + 2**-10
    loss_function = paired_reconstruction_loss if paired else reconstruction_loss
    original, original_terms = loss_function(prediction, batch)
    disabled, disabled_terms = loss_function(prediction, batch, multiscale_sensor_weight=0)
    assert torch.equal(original, disabled) and original_terms.keys() == disabled_terms.keys()
    enabled, terms = loss_function(prediction, batch, multiscale_sensor_weight=0.01)
    assert "multiscale_sensor" not in original_terms
    torch.testing.assert_close(enabled, original + 0.01 * multiscale_sensor_loss(prediction, batch))
    torch.testing.assert_close(
        terms["multiscale_sensor"], multiscale_sensor_loss(prediction, batch)
    )


@pytest.mark.parametrize("weight", [-1, float("nan"), float("inf")])
def test_invalid_multiscale_weights_are_rejected(weight):
    batch = measured_batch()
    for loss in (reconstruction_loss, paired_reconstruction_loss):
        with pytest.raises(ValueError, match="finite and nonnegative"):
            loss(batch["target"], batch, multiscale_sensor_weight=weight)
