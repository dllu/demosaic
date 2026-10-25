import hashlib
import json
import random
from collections import Counter

import numpy as np
import pytest
import torch

from demosaic.paired import TRAINING_SCENES
from demosaic.paired_training import PairedDataset, normalized_camera_weights


def camera_manifest(tmp_path):
    cases = []
    for index, scene in enumerate(sorted(TRAINING_SCENES)[:5]):
        camera = "many-scenes" if index < 4 else "one-scene"
        level = .10 + index * .01 if index < 4 else .70
        raw = np.full((64, 64), level, np.float32)
        rgb = np.full((3, 64, 64), level, np.float32)
        mask = np.zeros_like(rgb, dtype=bool)
        for phase, color in enumerate((0, 1, 1, 2)):
            mask[color, phase // 2::2, phase % 2::2] = True
        path = tmp_path / f"group-{index}.npz"
        np.savez(path, raw=raw, reference_rgb=rgb, sensor_reference=rgb * mask, sensor_mask=mask)
        cases.append({
            "scene": scene, "unknown_sensor": False,
            "metadata": {"camera": camera, "pattern": "RGGB", "white_balance": [1., 1., 1.],
                         "camera_to_srgb": np.eye(3).tolist()},
            "conditioning": {"shot": .001, "read": .000001},
            "crops": [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
        })
    path = tmp_path / "paired.json"
    path.write_text(json.dumps({"split": "train", "cases": cases}))
    return path


@pytest.mark.parametrize("weights,expected_many", [
    (None, .8),
    ({"many-scenes": 1, "one-scene": 1}, .5),
    ({"many-scenes": 3, "one-scene": 1}, .75),
])
def test_actual_samples_follow_camera_weights_and_share_weight_between_scenes(tmp_path, weights, expected_many):
    data = PairedDataset(camera_manifest(tmp_path), patch_size=32, seed=101,
                         camera_sampling_weights=weights)
    counts = Counter()
    for index in range(1600):
        value = float(data[index]["target"].mean())
        group = round((value - .10) / .01) if value < .3 else 4
        counts[group] += 1
    many = sum(counts[i] for i in range(4))
    assert abs(many / 1600 - expected_many) < .05
    assert all(.15 < counts[i] / many < .35 for i in range(4))


def test_weighted_samples_are_index_deterministic_and_preserve_global_rng(tmp_path):
    path = camera_manifest(tmp_path)
    first = PairedDataset(path, patch_size=32, camera_sampling_weights={"one-scene": 1, "many-scenes": 3})
    equivalent = PairedDataset(path, patch_size=32, camera_sampling_weights={"many-scenes": 6, "one-scene": 2})
    torch_state, python_state = torch.get_rng_state(), random.getstate()
    for index in (0, 1, 19, 41, 99):
        a, b, repeated = first[index], equivalent[index], first[index]
        assert a.keys() == b.keys() == repeated.keys()
        assert all(torch.equal(a[k], b[k]) and torch.equal(a[k], repeated[k]) for k in a)
    assert torch.equal(torch_state, torch.get_rng_state())
    assert python_state == random.getstate()


@pytest.mark.parametrize("weights", [
    {}, [], {"many-scenes": 0, "one-scene": 1},
    {"many-scenes": -1, "one-scene": 1}, {"many-scenes": True, "one-scene": 1},
    {"many-scenes": "1", "one-scene": 1}, {"many-scenes": float("nan"), "one-scene": 1},
    {"many-scenes": float("inf"), "one-scene": 1},
    {"many-scenes": 1}, {"many-scenes": 1, "unknown": 1},
    {"many-scenes": 1e308, "one-scene": 1e308},
    {"many-scenes": 5e-324, "one-scene": 1e308},
])
def test_invalid_or_incomplete_camera_weights_are_rejected(tmp_path, weights):
    with pytest.raises(ValueError, match="camera sampling"):
        PairedDataset(camera_manifest(tmp_path), patch_size=32, camera_sampling_weights=weights)


def test_weighted_group_cannot_mix_cameras(tmp_path):
    path = camera_manifest(tmp_path)
    data = json.loads(path.read_text())
    case = json.loads(json.dumps(data["cases"][0]))
    case["metadata"]["camera"] = "one-scene"
    data["cases"].append(case)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="scene group must have one camera"):
        PairedDataset(path, patch_size=32, camera_sampling_weights={"many-scenes": 1, "one-scene": 1})


def test_probability_order_is_canonical_and_default_has_no_weighting():
    assert normalized_camera_weights(None) is None
    result = normalized_camera_weights({"Sony": 24, "Nikon": 4, "Canon": 4})
    assert list(result) == ["Canon", "Nikon", "Sony"]
    assert result == {"Canon": .125, "Nikon": .125, "Sony": .75}
