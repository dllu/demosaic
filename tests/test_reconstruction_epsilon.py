"""Loss-scale derivatives and checkpoint compatibility for reconstruction epsilon."""

import numpy as np
import pytest
import torch
import yaml
from test_losses import noise_batch
from test_optimizer_batches import manifests, options

from demosaic.cfa import mosaic
from demosaic.losses import (
    charbonnier,
    masked_reconstruction,
    reconstruction_loss,
    validate_reconstruction_epsilon,
)
from demosaic.train import train


@pytest.mark.parametrize("epsilon", [1e-3, 3e-4, 1e-4])
@pytest.mark.parametrize("masked", [False, True])
def test_values_and_gradients_match_independent_float64_formula(epsilon, masked):
    values = np.array([0, 1e-5, -2e-4, 0.003, -0.2], dtype=np.float32)
    valid = np.array([True, True, True, False, True]) if masked else np.ones(5, dtype=bool)
    error = torch.tensor(values, requires_grad=True)
    if masked:
        value = masked_reconstruction(
            error, torch.from_numpy(valid), "charbonnier-v1", epsilon=epsilon
        )
    else:
        value = charbonnier(error, epsilon=epsilon)
    value.backward()
    roots = np.sqrt(values.astype(np.float64) ** 2 + epsilon**2)
    assert value.item() == pytest.approx(roots[valid].mean(), rel=2e-7)
    derivative = np.where(valid, values / roots / valid.sum(), 0)
    np.testing.assert_allclose(error.grad.numpy(), derivative, rtol=2e-7, atol=1e-10)


@pytest.mark.parametrize(
    "epsilon", [0, -0.001, float("nan"), float("inf"), True, 1e-30, 1e30, None, "bad"]
)
def test_invalid_or_fp32_unsafe_epsilon_is_rejected_before_batch_access(epsilon):
    with pytest.raises(ValueError, match="epsilon"):
        reconstruction_loss(None, {}, reconstruction_charbonnier_epsilon=epsilon)


def test_normal_fp32_epsilon_limits_and_empty_masks_have_finite_zero_gradients():
    for epsilon in [1e-12, 1e12]:
        assert validate_reconstruction_epsilon(epsilon) == epsilon
        error = torch.tensor([0, float("nan")], requires_grad=True)
        loss = masked_reconstruction(
            error, torch.zeros(2, dtype=torch.bool), "charbonnier-v1", epsilon=epsilon
        )
        loss.backward()
        assert loss.item() == 0 and torch.equal(error.grad, torch.zeros(2))


@pytest.mark.parametrize("objective", ["charbonnier-v1", "image-log-mse-v1"])
def test_only_declared_reconstruction_terms_change(objective):
    batch = noise_batch()
    batch["sensor_target"] = batch["target"]
    prediction = batch["target"] + torch.linspace(-0.002, 0.003, 32)[None, None, None]
    auxiliary = mosaic(prediction, batch["colors"])
    kwargs = {
        "camera_supervision": "sensor-valid-v1",
        "reference_interval_weight": 0.1,
        "normalized_sensor_weight": 0.1,
        "multiscale_sensor_weight": 0.1,
        "objective": objective,
    }
    default, parts = reconstruction_loss(prediction, batch, auxiliary, **kwargs)
    explicit, explicit_parts = reconstruction_loss(
        prediction, batch, auxiliary, reconstruction_charbonnier_epsilon=0.001, **kwargs
    )
    assert torch.equal(default, explicit)
    assert all(torch.equal(parts[k], explicit_parts[k]) for k in parts)
    changed, changed_parts = reconstruction_loss(
        prediction, batch, auxiliary, reconstruction_charbonnier_epsilon=0.0003, **kwargs
    )
    assert not torch.equal(default, changed)
    for name in ["highlight", "reference_interval", "normalized_sensor", "multiscale_sensor"]:
        assert torch.equal(parts[name], changed_parts[name])
    if objective == "image-log-mse-v1":
        assert torch.equal(parts["linear"], changed_parts["linear"])
        assert torch.equal(parts["rendered"], changed_parts["rendered"])
    assert not torch.equal(parts["gradient"], changed_parts["gradient"])
    assert not torch.equal(parts["sensor"], changed_parts["sensor"])


@pytest.mark.parametrize("epsilon,legacy", [(0.001, True), (0.0003, False)])
def test_actual_mixed_training_serializes_resumes_and_rejects_changed_epsilon(
    tmp_path, epsilon, legacy
):
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
        "reconstruction_charbonnier_epsilon": epsilon,
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
    full = train(path)
    recipe["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(recipe))
    checkpoint = train(path, stop_after=1)
    if legacy:
        state = torch.load(checkpoint, weights_only=True)
        del state["config"]["reconstruction_charbonnier_epsilon"]
        torch.save(state, checkpoint)
        del recipe["reconstruction_charbonnier_epsilon"]
        path.write_text(yaml.safe_dump(recipe))
    resumed = train(path, resume=checkpoint)
    expected, actual = [torch.load(p, weights_only=True) for p in (full, resumed)]
    assert actual["config"]["reconstruction_charbonnier_epsilon"] == epsilon
    for field in ["model", "ema"]:
        assert all(torch.equal(v, actual[field][key]) for key, v in expected[field].items())
    for key, value in expected["optimizer"]["state"].items():
        assert all(
            torch.equal(v, actual["optimizer"]["state"][key][name]) for name, v in value.items()
        )
    assert torch.equal(expected["torch_rng"], actual["torch_rng"])
    assert expected["python_rng"] == actual["python_rng"]
    recipe["reconstruction_charbonnier_epsilon"] = 0.0001
    path.write_text(yaml.safe_dump(recipe))
    with pytest.raises(ValueError, match="Resume reconstruction epsilon differs"):
        train(path, resume=resumed)
