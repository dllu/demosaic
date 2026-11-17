"""Full-cache lineage and exact observation/crop replay across experiment arms."""

import json

import numpy as np
import torch

from demosaic.experiments.artifacts import reference
from demosaic.scene_training_data import ScenePhotoDataset


def test_full_source_replay_covers_augmentation_noise_coordinates_and_targets(tmp_path):
    rng = np.random.default_rng(52)
    image = rng.integers(0, 65536, (96, 160, 3), dtype=np.uint16)
    path = tmp_path / "source.npy"
    np.save(path, image)
    manifest = tmp_path / "manifest.jsonl"
    row = {
        "id": "fixture",
        "cache": path.name,
        "cache_sha256": reference(path)["sha256"],
        "shape": list(image.shape),
        "bin_factor": 4,
        "color_space": "linear-sRGB",
        "dtype": "uint16",
    }
    manifest.write_text(json.dumps(row) + "\n")
    a = ScenePhotoDataset(manifest, seed=91, patch_size=32)
    b = ScenePhotoDataset(manifest, seed=91, patch_size=32)
    sample, repeated = a[3], b[3]
    assert sample.metadata == repeated.metadata
    assert sorted(sample.metadata["native_hw"]) == [96, 160]
    for key in sample.crops:
        torch.testing.assert_close(sample.crops[key], repeated.crops[key], rtol=0, atol=0)
    assert a[4].metadata["scene_packed"] != sample.metadata["scene_packed"]
    reduced = ScenePhotoDataset(manifest, seed=91, patch_size=32, reduction=2)[3]
    assert sorted(reduced.metadata["native_hw"]) == [48, 80]
    np.testing.assert_array_equal(np.load(path), image)  # source remains read-only
