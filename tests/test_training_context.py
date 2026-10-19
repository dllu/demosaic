import importlib
import json
import random

import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import color_indices, mosaic
from demosaic.losses import reconstruction_loss
from demosaic.paired_training import paired_reconstruction_loss
from demosaic.training_context import (
    TrainingContext,
    crop_training_batch,
    require_resume_context,
)


def physical_batch(pattern="RGGB", size=32):
    # A spatial/color code ramp exposes off-by-one phase shifts and any averaging.
    rgb = torch.arange(3 * size * size, dtype=torch.float32).reshape(1, 3, size, size)
    rgb = rgb / 65535 + 0.15
    colors = color_indices(pattern)[None]
    packed = mosaic(rgb, colors)
    return {
        "packed": packed,
        "variance": packed * 0.001 + 1e-6,
        "colors": colors,
        "wb": torch.tensor([[2.0, 1.0, 1.5]]),
        "matrix": torch.eye(3)[None],
        "target": rgb,
        "sensor_target": rgb.clone(),
        "sensor_reference": rgb.clone(),
        "sensor_mask": (torch.arange(rgb.numel()).reshape_as(rgb) % 7 != 0),
        "shot": torch.full((1, 1, 1, 1), 0.001),
        "read": torch.full((1, 1, 1, 1), 1e-6),
    }


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_crop_preserves_measured_samples_target_masks_and_one_code_detail(pattern):
    batch = physical_batch(pattern)
    before = {key: value.clone() for key, value in batch.items()}
    python_rng, torch_rng = random.getstate(), torch.get_rng_state().clone()
    cropped = crop_training_batch(batch, 24)
    assert torch.equal(cropped["packed"], mosaic(cropped["target"], cropped["colors"]))
    assert torch.equal(cropped["packed"], batch["packed"][..., 2:14, 2:14])
    assert torch.equal(cropped["variance"], batch["variance"][..., 2:14, 2:14])
    for key in ("target", "sensor_target", "sensor_reference", "sensor_mask"):
        assert torch.equal(cropped[key], batch[key][..., 4:28, 4:28])
    assert torch.equal(cropped["target"][..., 1:] - cropped["target"][..., :-1],
                       batch["target"][..., 4:28, 5:28] - batch["target"][..., 4:28, 4:27])
    for key in ("colors", "wb", "matrix", "shot", "read"):
        assert cropped[key] is batch[key]
    assert all(torch.equal(batch[key], value) for key, value in before.items())
    assert python_rng == random.getstate() and torch.equal(torch_rng, torch.get_rng_state())


@pytest.mark.parametrize("paired", [False, True])
def test_different_input_contexts_supervise_exact_same_core_and_ignore_outer_targets(paired):
    batch = physical_batch()
    small, large = TrainingContext(32, 24, 16, 24), TrainingContext(32, 32, 16, 24)
    prediction = (batch["target"] + 0.005).detach().requires_grad_()
    auxiliary = mosaic(prediction, batch["colors"])
    small_prediction = prediction[..., 4:28, 4:28]
    small_auxiliary = auxiliary[..., 2:14, 2:14]
    s = small.supervision(small_prediction, small_auxiliary, batch)
    l = large.supervision(prediction, auxiliary, batch)
    assert torch.equal(s[0], l[0]) and torch.equal(s[1], l[1])
    assert all(torch.equal(s[2][key], l[2][key]) for key in batch)
    assert torch.equal(small.forward_batch(batch)["packed"],
                       large.forward_batch(batch)["packed"][..., 2:14, 2:14])

    def loss(parts):
        p, a, b = parts
        if paired:
            return paired_reconstruction_loss(p, b, a, multiscale_sensor_weight=0.1)[0]
        return reconstruction_loss(p, b, a, camera_supervision="sensor-valid-v1",
                                   normalized_sensor_weight=0.1,
                                   multiscale_sensor_weight=0.1,
                                   reference_interval_weight=0.01)[0]

    first, second = loss(s), loss(l)
    assert torch.equal(first, second)
    changed = {key: value.clone() for key, value in batch.items()}
    for key in ("target", "sensor_target", "sensor_reference", "sensor_mask"):
        value = changed[key]
        value[..., :8, :] = False if value.dtype == torch.bool else 1000
        value[..., 24:, :] = False if value.dtype == torch.bool else -1000
        value[..., :, :8] = False if value.dtype == torch.bool else 1000
        value[..., :, 24:] = False if value.dtype == torch.bool else -1000
    assert torch.equal(second, loss(large.supervision(prediction, auxiliary, changed)))
    second.backward()
    assert prediction.grad[..., 8:24, 8:24].abs().sum() > 0
    outside = prediction.grad.clone()
    outside[..., 8:24, 8:24] = 0
    assert torch.count_nonzero(outside) == 0


def test_default_identity_and_unknown_spatial_field_guard():
    assert TrainingContext.from_config({"patch_size": 32}) is None
    batch = physical_batch()
    assert crop_training_batch(batch, 32) is batch
    with pytest.raises(ValueError, match="Unrecognized spatial"):
        crop_training_batch({**batch, "new_mask": batch["sensor_mask"]}, 24)


@pytest.mark.parametrize("override", [
    {"forward_patch_size": 322}, {"forward_patch_size": 318},
    {"forward_patch_size": 255}, {"loss_patch_size": 254},
    {"loss_patch_size": 324}, {"loss_patch_size": True},
    {"optimizer_batch_groups": 4}, {"validation_patch_size": -4},
    {"validation_patch_size": 20},
])
def test_refuse_phase_changes_invalid_extents_and_unsupported_grouping(override):
    config = {"patch_size": 320, "forward_patch_size": 256, "loss_patch_size": 256}
    with pytest.raises(ValueError):
        TrainingContext.from_config({**config, **override})


def test_resume_rejects_any_changed_geometry_and_accepts_equivalent_defaults():
    config = {"patch_size": 320, "forward_patch_size": 256,
              "loss_patch_size": 256, "validation_patch_size": 256}
    require_resume_context(config, config.copy())
    for key, size in (("patch_size", 384), ("forward_patch_size", 320),
                      ("loss_patch_size", 128), ("validation_patch_size", 320)):
        with pytest.raises(ValueError, match="Resume input context"):
            require_resume_context(config, {**config, key: size})
    require_resume_context({"patch_size": 256}, {"patch_size": 256, "loss_patch_size": 256})


def test_actual_trainer_crops_forward_loss_validation_and_resumes_exactly(tmp_path, monkeypatch):
    trainer = importlib.import_module("demosaic.train")
    path = tmp_path / "source.npy"
    np.save(path, np.random.default_rng(8).integers(0, 65536, (80, 80, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("\n".join(json.dumps({"id": s, "cache": path.name, "split": s})
                                  for s in ("train", "val")))
    config = {"manifest": str(manifest), "run": str(tmp_path / "full"),
              "device": "cpu", "steps": 4, "batch_size": 1, "patch_size": 64,
              "forward_patch_size": 48, "loss_patch_size": 32, "validation_patch_size": 32,
              "seed": 54, "workers": 0, "cpu_threads": 2, "amp": False,
              "warmup_steps": 1, "checkpoint_every": 4, "log_every": 1,
              "val_batches": 1, "min_available_gb": 0, "trace_observations": True,
              "model": {"width": 4, "encoder_blocks": [1], "middle_blocks": 0,
                        "decoder_blocks": [1], "attention": False}}
    calls = []
    original = trainer.JointDemosaic.forward

    def observed(self, packed, *args, **kwargs):
        calls.append((self.training, tuple(packed.shape[-2:])))
        return original(self, packed, *args, **kwargs)

    monkeypatch.setattr(trainer.JointDemosaic, "forward", observed)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(config))
    full = trainer.train(cfg)
    config["run"] = str(tmp_path / "resumed")
    cfg.write_text(yaml.safe_dump(config))
    interim = trainer.train(cfg, stop_after=2)
    resumed = trainer.train(cfg, resume=interim)
    left = torch.load(full, map_location="cpu", weights_only=True)
    right = torch.load(resumed, map_location="cpu", weights_only=True)
    assert left["step"] == right["step"] == 4
    for field in ("model", "ema"):
        assert left[field].keys() == right[field].keys()
        assert all(torch.equal(left[field][k], right[field][k]) for k in left[field])
    assert left["optimizer"]["param_groups"] == right["optimizer"]["param_groups"]
    assert left["optimizer"]["state"].keys() == right["optimizer"]["state"].keys()
    for key, values in left["optimizer"]["state"].items():
        assert values.keys() == right["optimizer"]["state"][key].keys()
        assert all(torch.equal(value, right["optimizer"]["state"][key][name])
                   for name, value in values.items())
    assert torch.equal(left["torch_rng"], right["torch_rng"])
    assert left["python_rng"] == right["python_rng"]
    assert {shape for training, shape in calls if training} == {(24, 24)}
    assert {shape for training, shape in calls if not training} == {(16, 16)}
    rows = [json.loads(s) for s in (full.parent / "metrics.jsonl").read_text().splitlines()]
    rows = [row for row in rows if row["event"] == "train"]
    assert all((r["context_source_size"], r["context_forward_size"], r["context_loss_size"])
               == (64, 48, 32) for r in rows)
    assert all(r["batch_sha256"] != r["context_forward_sha256"]
               != r["context_supervision_sha256"] for r in rows)
