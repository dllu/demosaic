import json

import numpy as np
import pytest
import torch
import yaml

from demosaic.train import train


@pytest.mark.parametrize(
    "warm_start,legacy_metadata,new_recipe",
    [(False, False, False), (True, False, False), (True, True, False), (True, False, True)],
)
def test_checkpoint_resume_matches_uninterrupted_training(
    tmp_path, warm_start, legacy_metadata, new_recipe
):
    """RNG, augmentation, draw position, optimizer, LR and EMA survive a restart."""
    source = tmp_path / "clean.npy"
    rng = np.random.default_rng(7)
    np.save(source, rng.integers(0, 65536, (40, 40, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split})
            for split in ("train", "val")
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 4,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    if new_recipe:
        config.update(broad_camera=True, normalized_sensor_weight=0.02)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    initialize = None
    if warm_start:
        initialize = train(path)
        config["run"] = str(tmp_path / "fine-full")
        path.write_text(yaml.safe_dump(config))
    full = train(path, initialize=initialize)
    with pytest.raises(ValueError, match="already has checkpoints"):
        train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, initialize=initialize, stop_after=2)
    assert torch.load(interrupted, weights_only=True)["step"] == 2
    if legacy_metadata:
        state = torch.load(interrupted, weights_only=True)
        del state["config"]["initialized_from"]
        torch.save(state, interrupted)
    resumed = train(path, resume=interrupted)
    expected = torch.load(full, weights_only=True)
    actual = torch.load(resumed, weights_only=True)
    assert actual["step"] == 4
    assert actual["config"].get("initialized_from") == expected["config"].get("initialized_from")
    for group in ("model", "ema"):
        for name, value in expected[group].items():
            assert torch.equal(actual[group][name], value), name


def test_explicit_fp32_guards_forward_and_backward_and_refuses_precision_change(
    tmp_path, monkeypatch
):
    import demosaic.train as training

    source = tmp_path / "clean.npy"
    np.save(source, np.full((40, 40, 3), 12000, np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "cache": source.name, "split": s}) for s in ("train", "val"))
    )
    constructor = training.JointDemosaic
    observed = {"forward": 0, "backward": 0}

    def check(stage):
        assert torch.backends.cudnn.conv.fp32_precision == "ieee"
        assert torch.backends.cuda.matmul.fp32_precision == "ieee"
        observed[stage] += 1

    def instrument(config):
        model = constructor(config)
        model.register_forward_pre_hook(lambda *args: check("forward"))
        model.register_full_backward_pre_hook(lambda *args: check("backward"))
        return model

    monkeypatch.setattr(training, "JointDemosaic", instrument)
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "run"),
        "device": "cpu",
        "steps": 2,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": True,
        "precision": "float32",
        "checkpoint_every": 2,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 1,
            "attention": False,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    previous = (torch.backends.cudnn.conv.fp32_precision, torch.backends.cuda.matmul.fp32_precision)
    try:
        torch.backends.cudnn.conv.fp32_precision = "tf32"
        torch.backends.cuda.matmul.fp32_precision = "tf32"
        checkpoint = train(path)
        assert observed["forward"] >= 3 and observed["backward"] == 2
        assert torch.backends.cudnn.conv.fp32_precision == "tf32"
        assert torch.backends.cuda.matmul.fp32_precision == "tf32"
        config["precision"] = "bfloat16"
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match="training precision differs"):
            train(path, resume=checkpoint)
    finally:
        torch.backends.cudnn.conv.fp32_precision, torch.backends.cuda.matmul.fp32_precision = (
            previous
        )
