import hashlib
import json

import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices, mosaic, unpack
from demosaic.paired_training import (
    PairedDataset,
    paired_reconstruction_loss,
    paired_step,
    transform,
)
from demosaic.train import train


def make_manifest(tmp_path):
    axis = torch.linspace(0, 1, 64)
    rgb = torch.stack(
        [
            0.04 + axis[:, None].expand(64, 64) * 0.1,
            0.05 + axis[None, :].expand(64, 64) * 0.1,
            0.06 + (axis[:, None] + axis[None, :]) * 0.05,
        ]
    )
    raw = unpack(mosaic(rgb[None], color_indices("RGGB")))[0, 0]
    mask = torch.zeros_like(rgb, dtype=torch.bool)
    for phase, color in enumerate(PATTERNS["RGGB"]):
        mask[color, phase // 2 :: 2, phase % 2 :: 2] = True
    crop = tmp_path / "paired.npz"
    np.savez(
        crop,
        raw=raw.numpy(),
        reference_rgb=rgb.numpy(),
        sensor_reference=(rgb * mask).numpy(),
        sensor_mask=mask.numpy(),
    )
    manifest = tmp_path / "paired.json"
    manifest.write_text(
        json.dumps(
            {
                "split": "train",
                "cases": [
                    {
                        "scene": "sewingmachine",
                        "unknown_sensor": False,
                        "metadata": {
                            "pattern": "RGGB",
                            "white_balance": [1.5, 1.0, 1.8],
                            "camera_to_srgb": torch.eye(3).tolist(),
                        },
                        "conditioning": {"shot": 0.001, "read": 1e-6},
                        "crops": [
                            {
                                "path": crop.name,
                                "sha256": hashlib.sha256(crop.read_bytes()).hexdigest(),
                            }
                        ],
                    }
                ],
            }
        )
    )
    return manifest


@pytest.mark.parametrize("pattern", list(PATTERNS))
@pytest.mark.parametrize("turns,flip", [(i, flip) for i in range(4) for flip in (False, True)])
def test_real_augmentation_preserves_sensor_and_measured_reference_phase(pattern, turns, flip):
    rgb = torch.rand(1, 3, 32, 48)
    colors = color_indices(pattern)
    raw = unpack(mosaic(rgb, colors))
    new_colors = transform(colors.reshape(2, 2), turns, flip).flatten()
    expected = mosaic(transform(rgb, turns, flip), new_colors)
    actual = torch.nn.functional.pixel_unshuffle(transform(raw, turns, flip), 2)
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)


def test_paired_loader_is_deterministic_and_rejects_protected_data(tmp_path):
    path = make_manifest(tmp_path)
    data = PairedDataset(path, patch_size=32)
    first, repeated = data[100], data[100]
    for key in first:
        assert torch.equal(first[key], repeated[key])
    torch.testing.assert_close(mosaic(first["target"][None], first["colors"])[0], first["packed"])
    batch = {k: v[None] for k, v in first.items()}
    loss, _ = paired_reconstruction_loss(batch["target"], batch, batch["packed"])
    torch.testing.assert_close(loss, torch.tensor(0.00016), atol=1e-7, rtol=1e-6)
    source = json.loads(path.read_text())
    source["split"] = "development"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="separate train"):
        PairedDataset(path, patch_size=32)
    source["split"] = "train"
    source["cases"][0]["unknown_sensor"] = True
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="protected/unknown"):
        PairedDataset(path, patch_size=32)


def test_paired_loss_ignores_unmeasured_values_and_fine_ahd_artifacts(tmp_path):
    data = PairedDataset(make_manifest(tmp_path), patch_size=32)[13]
    batch = {k: v[None] for k, v in data.items()}
    prediction = batch["target"].clone().requires_grad_()
    original, _ = paired_reconstruction_loss(prediction, batch)
    batch["sensor_reference"] = batch["sensor_reference"].masked_fill(~batch["sensor_mask"], 100)
    checker = (torch.arange(32)[:, None] + torch.arange(32)[None, :]) % 2 * 2 - 1
    batch["target"] = batch["target"] + checker * 0.04
    changed, _ = paired_reconstruction_loss(prediction, batch)
    torch.testing.assert_close(original, changed, atol=1e-7, rtol=1e-6)
    changed.backward()
    assert torch.isfinite(prediction.grad).all()


def test_paired_schedule_continues_at_global_step_without_rng_state():
    before = torch.get_rng_state()
    expected = [paired_step(s, 42, 0.5) for s in range(1, 50)]
    resumed = [paired_step(s, 42, 0.5) for s in range(25, 50)]
    assert expected[24:] == resumed
    assert any(expected) and not all(expected)
    assert torch.equal(before, torch.get_rng_state())


@pytest.mark.parametrize(
    "paired_fraction,native_fraction,step_rng,steps",
    [
        (0.5, 0.0, False, 4),
        (1.0, 0.0, False, 4),
        (0.0, 1.0, True, 8),
        (0.5, 0.25, True, 12),
        (0.5, 0.25, False, 12),
    ],
)
def test_paired_training_resume_matches_uninterrupted_weights(
    tmp_path, capsys, paired_fraction, native_fraction, step_rng, steps
):
    manifest = make_manifest(tmp_path)
    photo = tmp_path / "photo.npy"
    np.save(photo, np.full((40, 40, 3), 10000, np.uint16))
    commons = tmp_path / "commons.jsonl"
    commons.write_text(
        "\n".join(json.dumps({"id": s, "cache": photo.name, "split": s}) for s in ("train", "val"))
    )
    native = tmp_path / "native.json"
    native.write_text(
        json.dumps(
            {
                "split": "train",
                "rows": [
                    {
                        "split": "train",
                        "scene": "sewingmachine",
                        "cache": photo.name,
                        "cache_sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
                        "shape": [40, 40, 3],
                        "color_space": "linear-camera-RGB",
                        "raw_metadata": {
                            "white_balance": [1.5, 1.0, 1.8],
                            "camera_to_srgb": torch.eye(3).tolist(),
                        },
                    }
                ],
            }
        )
    )
    config = {
        "manifest": str(commons),
        "paired_manifest": str(manifest),
        "paired_fraction": paired_fraction,
        "raw_clean_manifest": str(native),
        "raw_clean_fraction": native_fraction,
        "data_seed_per_step": step_rng,
        "trace_observations": True,
        "log_every": 1,
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": steps,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": steps,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 1,
            "attention": False,
            "standardized_noise": True,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = train(path)
    full_draws = {
        row["step"]: (row["domain"], row["batch_sha256"])
        for line in capsys.readouterr().out.splitlines()
        if (row := json.loads(line)).get("event") == "train"
    }
    if native_fraction:
        domains = {domain for domain, _ in full_draws.values()}
        assert "native-RAW-synthetic" in domains
        if paired_fraction:
            assert domains == {"synthetic", "paired-RAW", "native-RAW-synthetic"}
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, stop_after=2)
    resumed = train(path, resume=interrupted)
    continued_draws = {
        row["step"]: (row["domain"], row["batch_sha256"])
        for line in capsys.readouterr().out.splitlines()
        if (row := json.loads(line)).get("event") == "train"
    }
    assert continued_draws == full_draws
    expected, actual = [torch.load(p, weights_only=True) for p in (full, resumed)]
    if paired_fraction:
        assert (
            actual["config"]["paired_manifest_sha256"]
            == hashlib.sha256(manifest.read_bytes()).hexdigest()
        )
    if native_fraction:
        assert (
            actual["config"]["raw_clean_manifest_sha256"]
            == hashlib.sha256(native.read_bytes()).hexdigest()
        )
    for group in ("model", "ema"):
        for name, value in expected[group].items():
            assert torch.equal(actual[group][name], value), name
    if native_fraction:
        for key, value, message in [
            ("raw_clean_fraction", native_fraction / 2, "native RAW fraction"),
            ("data_seed_per_step", not step_rng, "data RNG protocol"),
        ]:
            changed = {**config, key: value}
            path.write_text(yaml.safe_dump(changed))
            with pytest.raises(ValueError, match=message):
                train(path, resume=resumed)
        native.write_text(native.read_text() + "\n")
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match="native RAW manifest"):
            train(path, resume=resumed)
