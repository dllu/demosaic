"""Guard a palette-only intervention and the exact legacy data path."""

import hashlib
import json
import math
import random

import numpy as np
import pytest
import torch
import yaml

from demosaic.data import CleanDataset, smooth_scene
from demosaic.train import train


def test_default_smooth_RGB_and_rng_match_prechange_golden():
    # Captured before adding the option, from data.py b3277bca23d8c17b...
    golden = {
        0: (
            "39ae34c9e07aef179666c5c586dac8a7233a3e08d41002cf94f604c661088ae9",
            "be86be265677bd80282e2880f437050d8f0494e78f944a0239e9490b6cd2cc7b",
        ),
        1: (
            "858abc9bf519fa676add205eb3e48bd90dbc091aae0a9ede42aa2f9af883b49a",
            "e3abf7fcf6c5cfed49d3d2b6b5fb66e8a6001e75b464754e0865e25f64204dcf",
        ),
        48: (
            "42ce0a7cdaa824a26aedd964b39626209cc7415390952673e4b3b56acf7d2979",
            "c0f6b9991e71462fea9d90469e8c6944b3bcf36c4f64c21afe4a835ee88868bf",
        ),
    }
    for seed, (rgb_hash, rng_hash) in golden.items():
        rng = random.Random(seed)
        x = smooth_scene(32, rng)
        assert hashlib.sha256(x.numpy().tobytes()).hexdigest() == rgb_hash
        assert hashlib.sha256(repr(rng.getstate()).encode()).hexdigest() == rng_hash
        assert torch.equal(x, smooth_scene(32, random.Random(seed), chroma_stops=0))


def test_wide_palette_keeps_neutral_rng_and_unclipped_mean():
    largest_ratio, neutral_count, colored_count = 0, 0, 0
    for seed in range(120):
        a, b = random.Random(seed), random.Random(seed)
        legacy, wide = smooth_scene(16, a), smooth_scene(16, b, chroma_stops=8)
        assert a.getstate() == b.getstate()
        assert wide.dtype == torch.float32 and torch.isfinite(wide).all()
        assert wide.min() >= 0 and wide.max() <= 1
        if torch.equal(legacy[0], legacy[1]) and torch.equal(legacy[1], legacy[2]):
            neutral_count += 1
            assert torch.equal(wide, legacy)
        else:
            colored_count += 1
            ratio = float(wide.mean((1, 2)).max() / wide.mean((1, 2)).min())
            assert ratio <= 2**8 + 1e-3
            largest_ratio = max(largest_ratio, ratio)
            if legacy.max() < 0.1:
                assert wide.max() < 1  # No clipping: channel mean must stay fixed.
                torch.testing.assert_close(wide.mean(0), legacy.mean(0), rtol=3e-7, atol=1e-9)
    assert neutral_count > 30 and colored_count > 30 and largest_ratio > 32


def data_fixture(tmp_path):
    np.save(
        tmp_path / "photo.npy",
        np.random.default_rng(9).integers(0, 65536, (128, 128, 3), dtype=np.uint16),
    )
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": s, "split": s, "cache": "photo.npy", "bin_factor": 4})
            for s in ["train", "val"]
        )
    )
    return manifest


def test_only_colored_smooth_draws_change_after_full_augmentation(tmp_path):
    manifest = data_fixture(tmp_path)
    options = {
        "patch_size": 32,
        "seed": 52,
        "synthetic_fraction": 0.2,
        "flat_fraction": 0.1,
        "weak_texture_fraction": 0.1,
        "augmentation_downsample": 2,
    }
    a, b = CleanDataset(manifest, **options), CleanDataset(manifest, **options, flat_chroma_stops=8)
    seen = set()
    for index in range(120):
        rng = random.Random(52 + index)
        draw = rng.random()
        if draw < 0.1:
            rng.uniform(-13, -1)
            kind = "neutral" if rng.random() < 0.5 else "colored"
        else:
            kind = "weak" if draw < 0.2 else "strong" if draw < 0.3 else "photo"
        seen.add(kind)
        x, y = a[index]["rgb"], b[index]["rgb"]
        assert torch.equal(x, y) == (kind != "colored")
    assert seen == {"neutral", "colored", "weak", "strong", "photo"}
    heldout = {"patch_size": 32, "split": "val", "synthetic_fraction": 0, "flat_fraction": 1}
    assert torch.equal(
        CleanDataset(manifest, **heldout)[0]["rgb"],
        CleanDataset(manifest, **heldout, flat_chroma_stops=8)[0]["rgb"],
    )


@pytest.mark.parametrize("value", [-0.1, 16.01, math.nan, math.inf])
def test_invalid_palette_fails_before_sampling_or_training_io(tmp_path, value):
    rng = random.Random(5)
    previous = rng.getstate()
    with pytest.raises(ValueError, match="Flat chroma stops"):
        smooth_scene(32, rng, chroma_stops=value)
    assert rng.getstate() == previous
    with pytest.raises(ValueError, match="Flat chroma stops"):
        CleanDataset(tmp_path / "absent.jsonl", flat_chroma_stops=value)
    config = tmp_path / "recipe.yaml"
    config.write_text(yaml.safe_dump({"flat_chroma_stops": value}))
    with pytest.raises(ValueError, match="Flat chroma stops"):
        train(config)


def equal_state(a, b):
    if isinstance(a, torch.Tensor):
        assert torch.equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            equal_state(a[key], b[key])
    elif isinstance(a, (list, tuple)):
        assert type(a) is type(b) and len(a) == len(b)
        for x, y in zip(a, b):
            equal_state(x, y)
    else:
        assert a == b


def test_wide_palette_trainer_persists_and_resumes_complete_state(tmp_path):
    manifest = data_fixture(tmp_path)
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "flat_chroma_stops": 8,
        "flat_fraction": 1,
        "synthetic_fraction": 0,
        "augmentation_downsample": 2,
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "seed": 48,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 1,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 0,
            "attention": False,
        },
    }
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.safe_dump(config))
    full = train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    partial = train(path, stop_after=2)
    assert torch.load(partial, weights_only=True)["config"]["flat_chroma_stops"] == 8
    resumed = train(path, resume=partial)
    a, b = (torch.load(p, weights_only=True) for p in [full, resumed])
    for field in [
        "model",
        "ema",
        "optimizer",
        "torch_rng",
        "python_rng",
        "cuda_rng",
        "best",
        "step",
    ]:
        equal_state(a[field], b[field])
    for changed in [0, 4]:
        config["flat_chroma_stops"] = changed
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match="flat chroma stops"):
            train(path, resume=resumed)
