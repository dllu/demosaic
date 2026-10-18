"""Private admission, immutable base targets, and provenance rejection."""

import copy
import hashlib
import json

import numpy as np
import pytest
import torch

import demosaic.personal_admission as admission
from demosaic.raw_clean import RawCleanDataset


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    raw = {
        "id": "a" * 64,
        "split": "quarantine",
        "source_family": "personally-authorized-RAW",
        "source": {"sha256": "a" * 64, "original_path": "/private/fixture.raf"},
        "permission": {"scope": "Private training use only; no public redistribution"},
        "raw_metadata": {"white_balance": [2.0, 1.0, 1.8], "camera_to_srgb": np.eye(3).tolist()},
        "raw_shape": [4096, 4096],
        "caches": [],
    }
    bases = {}
    for factor, size in [(4, 512), (8, 256)]:
        cache = tmp_path / f"target{factor}.npy"
        values = np.broadcast_to(np.array([1311, 2907, 4111], np.uint16), (size, size, 3)).copy()
        np.save(cache, values)
        raw["caches"].append(
            {
                "path": str(cache),
                "sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
                "shape": list(values.shape),
                "dtype": "uint16",
                "bin_factor": factor,
                "color_space": "linear-camera-RGB",
            }
        )
        base = tmp_path / f"base{factor}.json"
        base.write_text(
            json.dumps(
                {
                    "split": "train",
                    "rows": [
                        {
                            "id": "b" * 64,
                            "split": "train",
                            "scene": "blood_oranges",
                            "cache": cache.name,
                            "cache_sha256": raw["caches"][-1]["sha256"],
                            "shape": list(values.shape),
                            "bin_factor": factor,
                            "color_space": "linear-camera-RGB",
                            "raw_metadata": raw["raw_metadata"],
                        }
                    ],
                }
            )
        )
        bases[factor] = base
    receipt = tmp_path / "review.json"
    receipt.write_text(
        json.dumps(
            {
                "kind": "reviewed-personal-raw-admission-v1",
                "status": "reviewed",
                "approved": [{"quarantine_record": raw, "training_scene": "private-fixture-group"}],
            }
        )
    )
    digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
    monkeypatch.setattr(admission, "REVIEWED_PERSONAL_ADMISSIONS", frozenset({digest}))
    candidate = {
        "format_version": 2,
        "split": "train",
        "personal_raw_admission": {"sha256": digest, "payload": receipt.read_text()},
    }
    return bases, receipt, candidate


@pytest.mark.parametrize("factor", [4, 8])
def test_separate_extension_retains_base_and_private_provenance(tmp_path, reviewed, factor):
    bases, review, _ = reviewed
    base = bases[factor]
    before = base.read_bytes()
    original = json.loads(before)["rows"][0]
    cache = base.parent / original["cache"]
    stamp, pixels = cache.stat().st_mtime_ns, cache.read_bytes()
    output = tmp_path / f"extension{factor}"
    result = admission.extend_personal_targets(base, review, output)
    assert len(result["rows"]) == 2
    assert {**result["rows"][0], "cache": original["cache"]} == original
    row = result["rows"][1]
    assert row["source"]["original_path"] == "/private/fixture.raf"
    assert row["permission"]["scope"].endswith("no public redistribution")
    assert "license" not in row and "not exact noiseless GT" in row["target_label"]
    assert (
        base.read_bytes() == before
        and cache.read_bytes() == pixels
        and cache.stat().st_mtime_ns == stamp
    )
    data = RawCleanDataset(
        output / "manifest.json", augmentation_downsample=2 if factor == 4 else 1
    )
    assert len(data) == 2
    for a, b in zip(data[11].values(), data[11].values(), strict=True):
        assert torch.equal(a, b)
    with pytest.raises(ValueError, match="new personal extension"):
        admission.extend_personal_targets(base, review, output)
    with pytest.raises(ValueError, match="existing personal RAW extension"):
        admission.extend_personal_targets(output / "manifest.json", review, tmp_path / "again")


@pytest.mark.parametrize(
    "change",
    [
        "cache",
        "metadata",
        "split",
        "scene",
        "no_admission",
        "stripped_family",
        "stripped_admission",
        "stripped_permission",
    ],
)
def test_private_rows_cannot_be_relabelled_or_admitted_by_split_edit(tmp_path, reviewed, change):
    _, _, candidate = reviewed
    manifest = copy.deepcopy(candidate)
    row = next(r for (_, f), r in admission.approved_personal_rows(manifest).items() if f == 4)
    if change == "cache":
        row["cache"] += ".other"
    elif change == "metadata":
        row["raw_metadata"]["white_balance"] = [1, 1, 1]
    elif change == "split":
        row["split"] = "test"
    elif change == "scene":
        row["scene"] = "blood_oranges"
    elif change == "no_admission":
        manifest.pop("personal_raw_admission")
    else:
        row.pop("source_family")
        row["scene"] = "blood_oranges"
        if change in ("stripped_admission", "stripped_permission"):
            row.pop("personal_admission_sha256")
        if change == "stripped_permission":
            row.pop("permission")
    manifest["rows"] = [row]
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="protected/non-camera"):
        RawCleanDataset(path, augmentation_downsample=2)


def test_self_signed_receipt_and_changed_cache_are_rejected(tmp_path, reviewed):
    bases, review, candidate = reviewed
    forged = copy.deepcopy(candidate)
    forged["personal_raw_admission"]["payload"] += " "
    forged["personal_raw_admission"]["sha256"] = hashlib.sha256(
        forged["personal_raw_admission"]["payload"].encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="unreviewed"):
        admission.approved_personal_rows(forged)
    row = next(iter(admission.approved_personal_rows(candidate).values()))
    with open(row["cache"], "r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    output = tmp_path / "corrupt"
    with pytest.raises(ValueError, match="checksum"):
        admission.extend_personal_targets(bases[4], review, output)
    assert not (output / "manifest.json").exists()
