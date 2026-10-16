import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "prepare_paired_quarantine",
    Path(__file__).resolve().parents[1] / "scripts/prepare_paired_quarantine.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def inputs(tmp_path):
    screen = tmp_path / "screen"
    screen.mkdir()
    (screen / "recipe.json").write_text("{}\n")
    path = screen / "clear.json"
    path.write_text(
        json.dumps(
            {
                "split": "quarantine",
                "screen_recipe_sha256": module.sha(screen / "recipe.json"),
                "dataset_license": {"rightsIdentifier": "CC-BY-SA-4.0"},
                "attribution": "Fixture photographer",
                "selection": [{"scene": n, "split": "quarantine"} for n in ["a", "b"]],
            }
        )
    )
    (screen / "summary.json").write_text(
        json.dumps({"screen_clear_manifest_sha256": module.sha(path)})
    )
    return path


def fake_prepare(acquisition, output, *, size, grid):
    data = json.loads(acquisition.read_text())
    path = output / "crop.npz"
    np.savez(
        path,
        raw=np.zeros((size, size), np.float32),
        reference_rgb=np.zeros((3, size, size), np.float32),
        sensor_reference=np.zeros((3, size, size), np.float32),
        sensor_mask=np.ones((3, size, size), bool),
        sensor_count=np.ones((3, size, size), np.uint8),
    )
    prepared = {
        "split": data["split"],
        "cases": [
            {
                "scene": data["selection"][0]["scene"],
                "crops": [{"path": path.name, "sha256": module.sha(path)}],
            }
        ],
        "rejected": [],
    }
    (output / "manifest.json").write_text(json.dumps(prepared))
    return prepared


def test_preparation_aggregates_relative_crops_but_retains_quarantine(tmp_path, monkeypatch):
    manifest = inputs(tmp_path)
    monkeypatch.setattr(module, "prepare_pairs", fake_prepare)
    result = module.prepare(manifest, tmp_path / "prepared", size=32, grid=1)
    assert result["split"] == "quarantine" and len(result["cases"]) == 2
    assert all(o["status"] == "prepared" for o in result["outcomes"])
    assert result["cases"][0]["crops"][0]["path"].startswith("scenes/")
    assert "no training admission" in result["manual_review"]
    assert module.verify_crops(result, tmp_path / "prepared", 32) == 2
    with pytest.raises(ValueError, match="frozen"):
        module.prepare(manifest, tmp_path / "prepared", size=32, grid=1)


def test_interruption_reuses_verified_per_scene_outputs(tmp_path, monkeypatch):
    manifest = inputs(tmp_path)
    calls = []

    def interrupted(acquisition, output, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise KeyError("fixture interruption")
        return fake_prepare(acquisition, output, **kwargs)

    monkeypatch.setattr(module, "prepare_pairs", interrupted)
    with pytest.raises(KeyError):
        module.prepare(manifest, tmp_path / "prepared", size=32, grid=1)
    calls.clear()

    def resumed(acquisition, output, **kwargs):
        calls.append(1)
        return fake_prepare(acquisition, output, **kwargs)

    monkeypatch.setattr(module, "prepare_pairs", resumed)
    result = module.prepare(manifest, tmp_path / "prepared", size=32, grid=1)
    assert len(calls) == 1 and len(result["cases"]) == 2


def test_bad_scene_is_held_without_discarding_other_scenes(tmp_path, monkeypatch):
    manifest = inputs(tmp_path)

    def partial(acquisition, output, **kwargs):
        data = json.loads(acquisition.read_text())
        if data["selection"][0]["scene"] == "a":
            raise ValueError("Camera mismatch")
        return fake_prepare(acquisition, output, **kwargs)

    monkeypatch.setattr(module, "prepare_pairs", partial)
    result = module.prepare(manifest, tmp_path / "prepared", size=32, grid=1)
    assert [c["scene"] for c in result["cases"]] == ["b"]
    assert result["outcomes"][0]["status"] == "failed"
    assert result["split"] == "quarantine"


def test_crop_corruption_and_invalid_measured_mask_are_rejected(tmp_path):
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text(json.dumps({"split": "quarantine", "selection": [{"scene": "a"}]}))
    prepared = fake_prepare(acquisition, tmp_path, size=32, grid=1)
    path = tmp_path / "crop.npz"
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        module.verify_crops(prepared, tmp_path, 32)
    prepared = fake_prepare(acquisition, tmp_path, size=32, grid=1)
    with np.load(path) as values:
        arrays = dict(values)
    arrays["sensor_count"].fill(0)
    np.savez(path, **arrays)
    prepared["cases"][0]["crops"][0]["sha256"] = module.sha(path)
    with pytest.raises(ValueError, match="no measured"):
        module.verify_crops(prepared, tmp_path, 32)


def test_changed_screen_or_training_split_are_rejected(tmp_path):
    manifest = inputs(tmp_path)
    manifest.write_text(manifest.read_text() + "\n")
    with pytest.raises(ValueError, match="manifest changed"):
        module.prepare(manifest, tmp_path / "changed", size=32)
    data = json.loads(manifest.read_text())
    data["split"] = "train"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="quarantined"):
        module.prepare(manifest, tmp_path / "train", size=32)
