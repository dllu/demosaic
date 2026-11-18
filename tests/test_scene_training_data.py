"""Full-cache lineage and exact observation/crop replay across experiment arms."""

import json

import numpy as np
import pytest
import torch
from prepare_scene_epoch_corpus import write_order
from train_scene_context import training_dataset

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


def test_prepared_scene_epochs_drive_the_training_reader(tmp_path):
    rows = []
    for i in range(3):
        image = np.full((72, 96, 3), 18_000 + 5000 * i, dtype=np.uint16)
        path = tmp_path / f"scene-{i}.npy"
        np.save(path, image)
        rows.append(
            {
                "id": f"scene-{i}",
                "cache": path.name,
                "cache_sha256": reference(path)["sha256"],
                "shape": list(image.shape),
                "split": "train",
                "bin_factor": 4,
                "color_space": "linear-sRGB",
                "dtype": "uint16",
            }
        )
    manifest = tmp_path / "manifest-train.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    order = write_order(manifest, rows, seed=91, steps=3, scenes_per_step=2)
    plan = {
        "train_manifest": reference(manifest),
        "photo_epoch_order": reference(order),
        "data_seed": 91,
        "patch_size": 32,
        "crops_per_scene": 2,
        "steps": 3,
        "scenes_per_step": 2,
    }
    dataset = training_dataset(plan)
    ids = [dataset.source_row(index)["id"] for index in range(6)]
    assert set(ids[:3]) == set(ids[3:]) == {row["id"] for row in rows}
    index = ids.index(ids[5])
    later, first = dataset[5], dataset[index]
    assert first.metadata["source_id"] == later.metadata["source_id"]
    assert first.metadata["recipe"]["noise_seed"] != later.metadata["recipe"]["noise_seed"]
    assert first.metadata["photo_epoch_order_sha256"] == plan["photo_epoch_order"]["sha256"]
    assert dataset[5].metadata == later.metadata
    with pytest.raises(ValueError, match="No planned ordinary"):
        dataset[6]
    with pytest.raises(ValueError, match="training layout/horizon"):
        training_dataset(plan | {"scenes_per_step": 3})
