import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from demosaic import paired_admission as admission
from demosaic.paired import DEVELOPMENT_SCENES
from demosaic.paired_training import PairedDataset


def fixture(tmp_path):
    crop = tmp_path / "paired.npz"
    rgb = np.full((3, 64, 64), 0.2, np.float32)
    np.savez(
        crop,
        raw=rgb[0],
        reference_rgb=rgb,
        sensor_reference=rgb,
        sensor_mask=np.ones_like(rgb, bool),
    )
    case = {
        "scene": "new-reviewed-scene",
        "unknown_sensor": False,
        "paired_source_family": admission.SOURCE_FAMILY,
        "noisy": {"sha256": "1" * 64},
        "references": [{"sha256": "2" * 64}],
        "metadata": {
            "camera": "Fixture Known Camera",
            "pattern": "RGGB",
            "white_balance": [1.5, 1, 1.8],
            "camera_to_srgb": torch.eye(3).tolist(),
        },
        "conditioning": {"shot": 0.001, "read": 0.000001},
        "crops": [{"path": str(crop), "sha256": hashlib.sha256(crop.read_bytes()).hexdigest()}],
    }
    payload = {
        "format_version": 1,
        "source_family": admission.SOURCE_FAMILY,
        "scope": "reviewed-training-only",
        "protected_scene_names": list(DEVELOPMENT_SCENES),
        "evidence": {
            name + "_sha256": str(i) * 64
            for i, name in enumerate(
                ["acquisition_manifest", "screen_summary", "prepared_manifest", "manual_review"], 3
            )
        },
        "cases": [copy.deepcopy(case)],
    }
    data = {
        "split": "train",
        "cases": [case],
        "paired_extension_admission": {
            "payload": payload,
            "sha256": admission.payload_digest(payload),
        },
    }
    return data


def write(tmp_path, data):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return path


def pin(monkeypatch, data):
    digest = admission.payload_digest(data["paired_extension_admission"]["payload"])
    data["paired_extension_admission"]["sha256"] = digest
    monkeypatch.setattr(admission, "REVIEWED_ADMISSIONS", frozenset({digest}))


def test_self_signing_or_flipping_quarantine_does_not_admit_a_scene(tmp_path):
    data = fixture(tmp_path)
    with pytest.raises(ValueError, match="pinned review"):
        PairedDataset(write(tmp_path, data), patch_size=32)
    data.pop("paired_extension_admission")
    data["split"] = "quarantine"
    with pytest.raises(ValueError, match="separate train"):
        PairedDataset(write(tmp_path, data), patch_size=32)
    data["split"] = "train"
    with pytest.raises(ValueError, match="protected/unknown"):
        PairedDataset(write(tmp_path, data), patch_size=32)


def test_pinned_exact_case_is_deterministic_and_hashes_native_crops(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    pin(monkeypatch, data)
    dataset = PairedDataset(write(tmp_path, data), patch_size=32)
    assert dataset.names == ["new-reviewed-scene"]
    first, repeated = dataset[41], dataset[41]
    for key in first:
        torch.testing.assert_close(first[key], repeated[key], rtol=0, atol=0)
    Path(data["cases"][0]["crops"][0]["path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="crop checksum"):
        PairedDataset(write(tmp_path, data), patch_size=32)


@pytest.mark.parametrize("field", ["scene", "metadata", "crop", "conditioning"])
def test_relabeling_or_changing_a_reviewed_case_is_rejected(tmp_path, monkeypatch, field):
    data = fixture(tmp_path)
    pin(monkeypatch, data)
    case = data["cases"][0]
    if field == "scene":
        case["scene"] = "sewingmachine"
    elif field == "metadata":
        case["metadata"]["white_balance"] = [1, 1, 1]
    elif field == "crop":
        case["crops"][0]["path"] = "elsewhere.npz"
    else:
        case["conditioning"]["shot"] *= 2
    with pytest.raises(ValueError, match="protected/unknown"):
        PairedDataset(write(tmp_path, data), patch_size=32)


def test_missing_or_duplicated_admitted_cases_are_rejected(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    pin(monkeypatch, data)
    case = data["cases"].pop()
    with pytest.raises(ValueError, match="omits reviewed"):
        PairedDataset(write(tmp_path, data), patch_size=32)
    data["cases"] = [case, copy.deepcopy(case)]
    with pytest.raises(ValueError, match="Repeated reviewed"):
        PairedDataset(write(tmp_path, data), patch_size=32)


@pytest.mark.parametrize("bad", ["protected", "unknown", "family", "relative", "evidence"])
def test_even_a_pinned_receipt_requires_valid_protected_and_source_metadata(
    tmp_path, monkeypatch, bad
):
    data = fixture(tmp_path)
    payload = data["paired_extension_admission"]["payload"]
    if bad == "protected":
        payload["cases"][0]["scene"] = "2pilesofplates"
    elif bad == "unknown":
        payload["cases"][0]["unknown_sensor"] = True
    elif bad == "family":
        payload["cases"][0]["scene"] = "boardgames_bot"
    elif bad == "relative":
        payload["cases"][0]["crops"][0]["path"] = "paired.npz"
    else:
        payload["evidence"]["manual_review_sha256"] = "missing"
    data["cases"] = copy.deepcopy(payload["cases"])
    pin(monkeypatch, data)
    with pytest.raises(ValueError):
        PairedDataset(write(tmp_path, data), patch_size=32)


@pytest.mark.parametrize("camera", ["Canon EOS M100", "Panasonic LUMIX DMC-GH1", "Unknown"])
def test_unseen_or_unknown_cameras_cannot_be_admitted_under_a_different_scene_name(
    tmp_path, monkeypatch, camera
):
    data = fixture(tmp_path)
    payload = data["paired_extension_admission"]["payload"]
    payload["cases"][0]["metadata"]["camera"] = camera
    data["cases"] = copy.deepcopy(payload["cases"])
    pin(monkeypatch, data)
    with pytest.raises(ValueError, match="Invalid/protected"):
        PairedDataset(write(tmp_path, data), patch_size=32)
