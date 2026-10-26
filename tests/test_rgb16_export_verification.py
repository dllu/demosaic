import json

import numpy as np
import pytest
import verify_rgb16_exports as verification
from audit_quality_archive import binding, write


def export_fixture(tmp_path, monkeypatch, count=2, *, corrupt_second=False):
    checkpoints, models, frames, native = {}, [], [], []
    mappings = {}
    for index in range(count):
        label, sha = f"model{index}", str(index + 1) * 64
        checkpoints[label] = {"sha256": sha}
        models.append({"label": label, "sha256": sha})
        files = []
        for role in ("linear", "srgb"):
            path = tmp_path / f"{label}-{role}16.tiff"
            path.write_bytes(f"stand-in encoded file {index} {role}".encode())
            files.append(
                {"path": path.name, "sha256": binding(path)["sha256"], "bytes": path.stat().st_size}
            )
            # A read-only broadcast view exercises 102MP geometry without allocating
            # full frames; actual TIFF encoding/decoding has separate IO tests.
            value = (6554, 13107)[index]
            if corrupt_second and index == 1 and role == "linear":
                value += 1
            mappings[str(path)] = np.broadcast_to(np.uint16(value), (8746, 11662, 3))
        frames.append(
            {"model_label": label, "files": files, "timing": {"megapixels": 8746 * 11662 / 1e6}}
        )
        for region in range(6):
            path = tmp_path / f"{label}-native{region}.npy"
            np.save(
                path, np.full((1, 3, 160, 160), 0.1 * (index + 1), np.float32), allow_pickle=False
            )
            native.append(
                {
                    "checkpoint": {"sha256": sha},
                    "array": binding(path),
                    "region": {"name": f"region{region}", "noisy_xy": [160 * region, 0]},
                }
            )
    report = tmp_path / "report.json"
    write(report, {"models": models, "full_frames": frames})
    stage = tmp_path / "stage.json"
    write(stage, {"report": binding(report), "full_native_floats": native})
    monkeypatch.setattr(verification.tifffile, "memmap", lambda path, mode: mappings[str(path)])
    return binding(stage), checkpoints


@pytest.mark.parametrize("count", [1, 2])
def test_every_declared_endpoint_receives_native_export_verification(tmp_path, monkeypatch, count):
    stage, checkpoints = export_fixture(tmp_path, monkeypatch, count)
    result = verification.verify_exports(stage, checkpoints, tmp_path / "verified.json")
    receipt = json.loads((tmp_path / "verified.json").read_text())
    assert result == binding(tmp_path / "verified.json")
    assert len(receipt["models"]) == count
    assert receipt["RGB16_values_checked_against_retained_FP32"] == 460800 * count


def test_second_endpoint_corruption_is_detected(tmp_path, monkeypatch):
    stage, checkpoints = export_fixture(tmp_path, monkeypatch, corrupt_second=True)
    with pytest.raises(ValueError, match="model1 / region0"):
        verification.verify_exports(stage, checkpoints, tmp_path / "verified.json")
    assert not (tmp_path / "verified.json").exists()


def test_missing_endpoint_is_rejected(tmp_path, monkeypatch):
    stage, checkpoints = export_fixture(tmp_path, monkeypatch)
    checkpoints.pop("model1")
    with pytest.raises(ValueError, match="coverage"):
        verification.verify_exports(stage, checkpoints, tmp_path / "verified.json")


def test_duplicate_checkpoint_identities_are_rejected(tmp_path, monkeypatch):
    stage, checkpoints = export_fixture(tmp_path, monkeypatch)
    checkpoints["model1"]["sha256"] = checkpoints["model0"]["sha256"]
    with pytest.raises(ValueError, match="distinct"):
        verification.verify_exports(stage, checkpoints, tmp_path / "verified.json")


def test_duplicate_regions_cannot_substitute_for_coverage(tmp_path, monkeypatch):
    _stage, checkpoints = export_fixture(tmp_path, monkeypatch)
    path = tmp_path / "stage.json"
    data = json.loads(path.read_text())
    data["full_native_floats"][1]["region"]["name"] = "region0"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="six distinct"):
        verification.verify_exports(binding(path), checkpoints, tmp_path / "verified.json")
