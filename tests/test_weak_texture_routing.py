import json
import random

import numpy as np
import pytest
import torch

from demosaic.data import CleanDataset


def dataset(tmp_path, **overrides):
    source = tmp_path / "source.npy"
    np.save(source, np.random.default_rng(9).integers(0, 65536, (128, 128, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split, "bin_factor": 4})
            for split in ["train", "val"]
        )
    )
    options = {
        "patch_size": 32,
        "synthetic_fraction": 0.2,
        "flat_fraction": 0.1,
        "seed": 52,
        "augmentation_downsample": 2,
        **overrides,
    }
    return CleanDataset(manifest, **options)


def test_only_replaced_procedural_draws_change(tmp_path):
    original = dataset(tmp_path)
    explicit_zero = dataset(tmp_path, weak_texture_fraction=0)
    candidate = dataset(tmp_path, weak_texture_fraction=0.1)
    seen = set()
    for index in range(60):
        draw = random.Random(52 + index).random()
        kind = (
            "flat" if draw < 0.1 else "weak" if draw < 0.2 else "strong" if draw < 0.3 else "photo"
        )
        seen.add(kind)
        a, b, c = (data[index]["rgb"] for data in [original, explicit_zero, candidate])
        assert torch.equal(a, b)
        assert torch.isfinite(c).all() and c.shape == (3, 32, 32)
        assert torch.equal(a, c) == (kind != "weak")
    assert seen == {"flat", "weak", "strong", "photo"}


def test_weak_draw_does_not_load_photo_or_generate_discarded_strong_sample(tmp_path, monkeypatch):
    data = dataset(tmp_path, weak_texture_fraction=0.1)
    index = next(i for i in range(100) if 0.1 <= random.Random(52 + i).random() < 0.2)

    def unused(*args, **kwargs):
        raise AssertionError("Unselected source must not be loaded/generated")

    monkeypatch.setattr("demosaic.data.np.load", unused)
    monkeypatch.setattr("demosaic.data.synthetic", unused)
    assert data[index]["rgb"].shape == (3, 32, 32)


def test_validation_keeps_only_its_fixed_photographic_crop(tmp_path):
    a = dataset(tmp_path, split="val", augmentation_downsample=1)
    b = dataset(tmp_path, split="val", augmentation_downsample=1, weak_texture_fraction=0.1)
    assert b.weak_texture_fraction == 0
    assert torch.equal(a[0]["rgb"], b[0]["rgb"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"weak_texture_fraction": -0.1},
        {"weak_texture_fraction": 0.21},
        {"weak_texture_fraction": float("nan")},
        {"weak_texture_fraction": 0.1, "augmentation_downsample": 1},
    ],
)
def test_invalid_weak_texture_fraction_fails(tmp_path, overrides):
    with pytest.raises(ValueError, match="Weak texture"):
        dataset(tmp_path, **overrides)
