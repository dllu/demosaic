"""Separate small-gradient supervision, flat error and genuine resumed updates."""

import numpy as np
import pytest
import torch
import yaml
from test_losses import noise_batch
from test_optimizer_batches import manifests, options

from demosaic.losses import reconstruction_loss, resolve_gradient_epsilon
from demosaic.train import train


def test_missing_gradient_option_is_exact_and_only_gradient_term_changes():
    batch = noise_batch()
    batch["sensor_target"] = batch["target"]
    original = batch["target"] + torch.linspace(-0.0002, 0.0003, 32)[None, None, None]
    results = []
    for gradient_epsilon in [None, 0.0003, 0.00003]:
        prediction = original.clone().requires_grad_()
        loss, terms = reconstruction_loss(
            prediction,
            batch,
            camera_supervision="sensor-valid-v1",
            reconstruction_charbonnier_epsilon=0.0003,
            gradient_charbonnier_epsilon=gradient_epsilon,
        )
        results.append((loss.detach(), terms, torch.autograd.grad(loss, prediction)[0]))
    assert torch.equal(results[0][0], results[1][0])
    assert torch.equal(results[0][2], results[1][2])
    assert all(torch.equal(results[0][1][k], results[1][1][k]) for k in results[0][1])
    assert not torch.equal(results[0][2], results[2][2])
    for key in ["linear", "rendered", "sensor", "highlight"]:
        assert torch.equal(results[0][1][key], results[2][1][key])
    assert results[2][1]["gradient"] < results[0][1]["gradient"]
    torch.testing.assert_close(
        results[2][0] - results[0][0],
        0.1 * (results[2][1]["gradient"] - results[0][1]["gradient"]),
        rtol=1e-4,
        atol=3e-10,
    )


@pytest.mark.parametrize("value", [0, -1e-4, True, float("nan"), float("inf"), 1e-30, "bad"])
def test_invalid_gradient_epsilon_rejects_before_batch_access(value):
    with pytest.raises(ValueError, match="epsilon"):
        reconstruction_loss(None, {}, gradient_charbonnier_epsilon=value)


@pytest.mark.parametrize("flat_target", [False, True])
def test_smaller_epsilon_corrects_faint_structure_and_penalizes_invented_flat_texture(flat_target):
    batch = noise_batch()
    target = torch.full_like(batch["target"], 0.05)
    wave = torch.sin(torch.arange(32) * 2 * torch.pi / 8)[None, None, None] * 1e-5
    prediction = target + wave if flat_target else target.clone()
    if not flat_target:
        target = target + wave
    batch["target"] = target
    gradients = []
    for epsilon in [0.0003, 0.00003]:
        p = prediction.detach().clone().requires_grad_()
        _, parts = reconstruction_loss(p, batch, gradient_charbonnier_epsilon=epsilon)
        g = torch.autograd.grad(parts["gradient"], p)[0]
        error = (prediction - target).detach()
        # A step toward the exact target must lower the gradient loss in both cases.
        projection = float((g * error).sum())
        assert projection > 0 and torch.isfinite(g).all()
        gradients.append(projection)
    assert gradients[1] > 2 * gradients[0]


@pytest.mark.parametrize("gradient_epsilon", [None, 0.00003])
def test_actual_resumed_training_and_legacy_inheritance(tmp_path, monkeypatch, gradient_epsilon):
    commons, native, pairs = manifests(tmp_path)
    recipe = {
        **options(4),
        "manifest": str(commons),
        "raw_clean_manifest": str(native),
        "paired_manifest": str(pairs),
        "paired_fraction": 0.25,
        "raw_clean_fraction": 0.25,
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 2,
        "seed": 51,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "raw_clean_workers": 0,
        "paired_workers": 0,
        "cpu_threads": 2,
        "warmup_steps": 1,
        "checkpoint_every": 2,
        "log_every": 1,
        "min_available_gb": 0,
        "val_batches": 1,
        "trace_observations": True,
        "camera_supervision": "sensor-valid-v1",
        "reconstruct_highlights": True,
        "reconstruction_charbonnier_epsilon": 0.0003,
        "gradient_charbonnier_epsilon": gradient_epsilon,
        "model": {
            "restoration_backbone": "packed-isotropic",
            "camera_conditioning": True,
            "width": 4,
            "isotropic_groups": 1,
            "isotropic_blocks": 1,
            "isotropic_local_width": 4,
            "isotropic_raw_gain": 32,
            "isotropic_residual_scale": 1 / 32,
        },
    }
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.safe_dump(recipe))
    full = torch.load(train(path), weights_only=True)
    recipe["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(recipe))
    checkpoint = train(path, stop_after=1)
    if gradient_epsilon is None:
        legacy = torch.load(checkpoint, weights_only=True)
        del legacy["config"]["gradient_charbonnier_epsilon"]
        torch.save(legacy, checkpoint)
        del recipe["gradient_charbonnier_epsilon"]
        path.write_text(yaml.safe_dump(recipe))
    actual = torch.load(train(path, resume=checkpoint), weights_only=True)
    assert actual["config"]["gradient_charbonnier_epsilon"] == resolve_gradient_epsilon(
        gradient_epsilon, 0.0003
    )
    for field in ["model", "ema"]:
        assert all(torch.equal(v, actual[field][k]) for k, v in full[field].items())
    for key, state in full["optimizer"]["state"].items():
        assert all(
            torch.equal(v, actual["optimizer"]["state"][key][name]) for name, v in state.items()
        )
    np.testing.assert_array_equal(full["torch_rng"], actual["torch_rng"])
    assert full["python_rng"] == actual["python_rng"]
    recipe["gradient_charbonnier_epsilon"] = 0.000003
    path.write_text(yaml.safe_dump(recipe))
    monkeypatch.setattr("demosaic.train.JointDemosaic", lambda *_: pytest.fail("constructed model"))
    with pytest.raises(ValueError, match="Resume gradient epsilon differs"):
        train(path, resume=checkpoint)
