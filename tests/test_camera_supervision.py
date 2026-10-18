"""Opt-in physical camera targets without changed observations or display truth."""

import numpy as np
import pytest
import torch
from test_losses import noise_batch

from demosaic.cfa import mosaic
from demosaic.data import camera_pair, degrade
from demosaic.losses import masked_reconstruction, reconstruction_loss
from demosaic.raw_clean import degrade_raw_clean


def test_default_ignores_retained_sensor_target_and_is_bitwise_unchanged():
    batch = noise_batch()
    prediction = (batch["target"] + 0.01).requires_grad_()
    old, parts = reconstruction_loss(prediction, batch)
    old.backward()
    gradient = prediction.grad.clone()
    prediction.grad = None
    with_extra = {**batch, "sensor_target": batch["target"] * 3}
    default, other = reconstruction_loss(
        prediction, with_extra, camera_supervision="reference-white-v1"
    )
    default.backward()
    assert torch.equal(old, default) and torch.equal(gradient, prediction.grad)
    assert all(torch.equal(v, other[k]) for k, v in parts.items())


def test_noiseless_sensor_unclipped_highlight_has_correct_camera_and_identical_display_terms():
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor(
        [
            [
                [1.117647, -0.0588235, -0.0588235],
                [-0.0588235, 1.117647, -0.0588235],
                [-0.0588235, -0.0588235, 1.117647],
            ]
        ]
    )
    scene = torch.tensor([1.4, 0.4, 0.2])[None, :, None, None].expand(1, 3, 32, 32)
    clean, target = camera_pair(scene, torch.linalg.inv(matrix), wb, reconstruct_highlights=True)
    colors = torch.tensor([[0, 1, 1, 2]])
    batch = {"target": target, "sensor_target": clean, "colors": colors, "wb": wb, "matrix": matrix}
    auxiliary = mosaic(clean, colors)
    old, parts = reconstruction_loss(clean, batch, auxiliary)
    changed, new = reconstruction_loss(
        clean, batch, auxiliary, camera_supervision="sensor-valid-v1"
    )
    assert parts["linear"] > 0.06 and new["linear"].item() == pytest.approx(0.001, abs=1e-9)
    assert new["sensor"].item() == pytest.approx(0.001, abs=1e-9)
    for key in ["rendered", "gradient", "highlight"]:
        assert torch.equal(parts[key], new[key])
    torch.testing.assert_close(
        changed, old - parts["linear"] - 0.1 * parts["sensor"] + new["linear"] + 0.1 * new["sensor"]
    )


@pytest.mark.parametrize("objective", ["charbonnier-v1", "image-log-mse-v1"])
@pytest.mark.parametrize("empty", [False, True])
def test_invalid_or_unobservable_samples_have_no_camera_gradient(objective, empty):
    error = torch.tensor([[[[0.1, float("nan")]]]], requires_grad=True)
    valid = torch.tensor([[[[not empty, False]]]])
    value = masked_reconstruction(error, valid, objective)
    value.backward()
    assert torch.isfinite(value) and torch.isfinite(error.grad).all()
    assert error.grad[0, 0, 0, 1] == 0
    if empty:
        assert value == 0 and error.grad.count_nonzero() == 0
    elif objective == "charbonnier-v1":
        assert value.item() == pytest.approx(float(np.sqrt(0.1**2 + 1e-6)), abs=1e-7)
    else:
        assert value.item() == pytest.approx(-20.0, abs=2e-6)


@pytest.mark.parametrize("native", [False, True])
def test_retaining_sensor_truth_keeps_every_legacy_field_and_RNG_exact(native):
    rgb = torch.rand((3, 3, 32, 32), generator=torch.Generator().manual_seed(81))
    kwargs = {
        "reconstruct_highlights": True,
        "preserve_negative_read_noise": True,
        "noise_free_fraction": 0.1,
    }
    if native:
        function = degrade_raw_clean
        clean = {
            "camera_rgb": rgb,
            "wb": torch.tensor([[2.0, 1.0, 1.5]]).expand(3, -1),
            "matrix": torch.eye(3).expand(3, -1, -1),
        }
    else:
        function = degrade
        clean = rgb
        kwargs.update(broad_camera=True)
    torch.manual_seed(53)
    initial = torch.get_rng_state()
    old = function(clean, **kwargs)
    end = torch.get_rng_state()
    torch.set_rng_state(initial)
    new = function(clean, **kwargs, retain_sensor_target=True)
    assert torch.equal(end, torch.get_rng_state())
    assert set(new) == set(old) | {"sensor_target"}
    assert all(torch.equal(value, new[key]) for key, value in old.items())
    assert (
        new["sensor_target"].dtype == torch.float32
        and new["sensor_target"].shape == new["target"].shape
    )
    # Rebuild the canonical display target independently from retained camera truth.
    rendered = torch.einsum(
        "bij,bjhw->bihw", new["matrix"], new["sensor_target"] * new["wb"][..., None, None]
    ).clamp(0, 1)
    reconstructed = (
        torch.einsum("bij,bjhw->bihw", torch.linalg.inv(new["matrix"]), rendered)
        / new["wb"][..., None, None]
    )
    torch.testing.assert_close(reconstructed, new["target"], rtol=2e-6, atol=2e-6)


def test_missing_or_unknown_camera_supervision_is_rejected():
    with pytest.raises(ValueError, match="Unknown camera supervision"):
        reconstruction_loss(None, {}, camera_supervision="typo")
    b = noise_batch()
    with pytest.raises(ValueError, match="retained clean camera target"):
        reconstruction_loss(b["target"], b, camera_supervision="sensor-valid-v1")
