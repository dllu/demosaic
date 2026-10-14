import json

import numpy as np
import torch
import yaml

from demosaic.train import train


def test_checkpoint_resume_matches_uninterrupted_training(tmp_path):
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
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, stop_after=2)
    assert torch.load(interrupted, weights_only=True)["step"] == 2
    resumed = train(path, resume=interrupted)
    expected = torch.load(full, weights_only=True)
    actual = torch.load(resumed, weights_only=True)
    assert actual["step"] == 4
    for group in ("model", "ema"):
        for name, value in expected[group].items():
            assert torch.equal(actual[group][name], value), name
