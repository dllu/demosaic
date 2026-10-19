import hashlib
import json

import numpy as np
import pytest
import torch

import demosaic.raw_admission as admission
from demosaic.raw_clean import RawCleanDataset


@pytest.fixture
def sources(tmp_path, monkeypatch):
    raw = {
        "id": "a" * 64, "file_id": 90000, "split": "quarantine",
        "source": {
            "sha256": "a" * 64, "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "url": "https://raw.pixls.us/getfile.php/90000/test.nef",
            "publisher_checksum": {"type": "SHA-256", "value": "a" * 64},
        },
        "raw_metadata": {"white_balance": [2.1, 1., 1.8], "camera_to_srgb": np.eye(3).tolist()},
        "raw_shape": [4096, 4096], "caches": [],
    }
    bases = {}
    for factor, size in [(4, 512), (8, 256)]:
        path = tmp_path / f"public{factor}.npy"
        values = np.broadcast_to(np.array([1501, 2003, 3907], np.uint16), (size, size, 3)).copy()
        np.save(path, values)
        raw["caches"].append({
            "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "shape": list(values.shape), "dtype": "uint16", "bin_factor": factor,
            "color_space": "linear-camera-RGB",
        })
        native = tmp_path / f"base{factor}.json"
        native.write_text(json.dumps({"split": "train", "rows": [{
            "id": "b" * 64, "split": "train", "scene": "blood_oranges",
            "cache": path.name, "cache_sha256": raw["caches"][-1]["sha256"],
            "shape": list(values.shape), "bin_factor": factor,
            "color_space": "linear-camera-RGB", "raw_metadata": raw["raw_metadata"],
        }]}))
        bases[factor] = native
    review = tmp_path / "admission.json"
    review.write_text(json.dumps({"kind": "reviewed-public-raw-admission-v1", "status": "reviewed", "approved": [raw]}))
    digest = hashlib.sha256(review.read_bytes()).hexdigest()
    monkeypatch.setattr(admission, "REVIEWED_ADMISSIONS", frozenset({digest}))
    candidate = {"format_version": 2, "split": "train", "public_raw_admission": {"sha256": digest, "payload": review.read_text()}}
    return bases, review, candidate


@pytest.mark.parametrize("factor", [4, 8])
def test_extension_is_separate_preserves_sources_and_loads_deterministically(tmp_path, sources, factor):
    bases, review, _ = sources
    before = bases[factor].read_bytes()
    source = json.loads(before)["rows"][0]
    cache = bases[factor].parent / source["cache"]
    cache_before = cache.read_bytes()
    stamp = cache.stat().st_mtime_ns
    output = tmp_path / f"extended{factor}"
    result = admission.extend_native_targets(bases[factor], review, output)
    assert len(result["rows"]) == 2
    old = {**result["rows"][0], "cache": source["cache"]}
    assert old == source
    assert bases[factor].read_bytes() == before
    assert cache.read_bytes() == cache_before and cache.stat().st_mtime_ns == stamp
    dataset = RawCleanDataset(output / "manifest.json", augmentation_downsample=2 if factor == 4 else 1)
    assert len(dataset) == 2
    assert "public-raw-pixls-90000" in dataset.scenes
    a, b = dataset[12], dataset[12]
    for key in a:
        torch.testing.assert_close(a[key], b[key], rtol=0, atol=0)
    assert a["camera_rgb"].dtype == torch.float32
    with pytest.raises(ValueError, match="new native extension"):
        admission.extend_native_targets(bases[factor], review, output)
    with pytest.raises(ValueError, match="original native"):
        admission.extend_native_targets(output / "manifest.json", review, tmp_path / "again")


@pytest.mark.parametrize("change", ["cache", "camera", "model", "source", "split", "protected_scene", "legacy_scene"])
def test_public_row_cannot_change_admitted_cache_camera_split_or_scene(tmp_path, sources, change):
    _, _, candidate = sources
    rows = admission.approved_public_rows(candidate)
    row = next(row for (_, factor), row in rows.items() if factor == 4)
    if change == "cache":
        row["cache"] += ".other"
    elif change == "camera":
        row["raw_metadata"]["white_balance"] = [1, 1, 1]
    elif change == "model":
        row["source"]["model"] = "unreviewed camera model"
    elif change == "source":
        row["source"]["url"] += ".other"
    elif change == "split":
        row["split"] = "test"
    else:
        row["scene"] = "7D-2" if change == "protected_scene" else "blood_oranges"
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps({**candidate, "rows": [row]}))
    with pytest.raises(ValueError, match="protected/non-camera"):
        RawCleanDataset(path, augmentation_downsample=2)


def test_changing_quarantine_split_or_self_signing_admission_does_not_enable_training(tmp_path, sources):
    _, _, candidate = sources
    row = next(iter(admission.approved_public_rows(candidate).values()))
    path = tmp_path / "forged.json"
    path.write_text(json.dumps({"split": "train", "rows": [row]}))
    with pytest.raises(ValueError, match="protected/non-camera"):
        RawCleanDataset(path)
    candidate["public_raw_admission"]["payload"] += " "
    candidate["public_raw_admission"]["sha256"] = hashlib.sha256(candidate["public_raw_admission"]["payload"].encode()).hexdigest()
    with pytest.raises(ValueError, match="unreviewed"):
        admission.approved_public_rows(candidate)


def test_cache_corruption_rejected_before_extension_publication(tmp_path, sources):
    bases, review, candidate = sources
    row = next(iter(admission.approved_public_rows(candidate).values()))
    with open(row["cache"], "r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    output = tmp_path / "bad"
    with pytest.raises(ValueError, match="checksum"):
        admission.extend_native_targets(bases[4], review, output)
    assert not (output / "manifest.json").exists()


def test_pinned_real_receipt_and_exclusions_match_the_reviewed_sources():
    from pathlib import Path

    path = Path(__file__).parents[1] / "docs/results/public-raw-admission-v1.json"
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest in admission.REVIEWED_ADMISSIONS
    receipt = json.loads(payload)
    assert {r["file_id"] for r in receipt["approved"]} == {2979, 3204, 3652, 4213, 4493, 6231}
    assert {r["file_id"] for r in receipt["rejected"]} == {2788, 3478, 7872}
    rows = admission.approved_public_rows({"format_version": 2, "split": "train", "public_raw_admission": {"sha256": digest, "payload": payload.decode()}})
    assert len(rows) == 12


def test_second_pinned_review_preserves_prior_sources_and_new_quality_exclusions():
    from pathlib import Path

    root = Path(__file__).parents[1] / "docs/results"
    prior = json.loads((root / "public-raw-admission-v1.json").read_text())
    payload = (root / "public-raw-admission-v2.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest in admission.REVIEWED_ADMISSIONS
    reviewed = json.loads(payload)
    assert len(reviewed["approved"]) == 75
    approved = {r["file_id"]: r for r in reviewed["approved"]}
    for row in prior["approved"]:
        assert approved[row["file_id"]] == row
    assert len(set(approved) - {r["file_id"] for r in prior["approved"]}) == 69
    assert not set(approved) & {r["file_id"] for r in reviewed["rejected"]}
    assert not set(approved) & {1275, 2401, 1118, 2788, 3478, 7872, 2980, 4494, 4215, 6232}
    assert all(r["bin4_any_channel_near_white_fraction"] <= .001 for r in reviewed["source_quality"]["verified"])
    assert len(reviewed["source_quality"]["verified"]) == 75
    rows = admission.approved_public_rows({"format_version": 2, "split": "train", "public_raw_admission": {"sha256": digest, "payload": payload.decode()}})
    assert len(rows) == 150


def test_third_pinned_review_preserves_prior75_and_only_adds_source_reviewed18():
    from pathlib import Path

    root = Path(__file__).parents[1] / "docs/results"
    prior_path = root / "public-raw-admission-v2.json"
    prior = json.loads(prior_path.read_text())
    payload = (root / "public-raw-admission-v3.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest in admission.REVIEWED_ADMISSIONS
    reviewed = json.loads(payload)
    assert reviewed["previous_admission"]["sha256"] == hashlib.sha256(prior_path.read_bytes()).hexdigest()
    assert reviewed["approved"][:75] == prior["approved"]
    assert reviewed["rejected"][:len(prior["rejected"])] == prior["rejected"]
    new = reviewed["approved"][75:]
    assert {row["file_id"] for row in new} == {
        1625, 2428, 5922, 2977, 4126, 5980, 1051, 5285, 6346,
        6664, 1008, 2235, 3670, 4423, 2886, 1749, 964, 3821,
    }
    assert len(reviewed["approved"]) == 93
    assert len({row["id"] for row in reviewed["approved"]}) == 93
    assert not {row["file_id"] for row in reviewed["approved"]} & {
        row["file_id"] for row in reviewed["rejected"]
    }
    assert {row["file_id"] for row in reviewed["rejected"][len(prior["rejected"]):]} == {
        7104, 7150, 8961, 1621, 1389, 3094, 4915, 1860, 1580,
        2974, 980, 2802, 2238, 3803, 3573, 1479, 1198, 1458,
    }
    assert len(reviewed["source_quality"]["verified"]) == 93
    assert all(row["bin4_any_channel_near_white_fraction"] <= .001
               for row in reviewed["source_quality"]["verified"])
    rows = admission.approved_public_rows({
        "format_version": 2, "split": "train",
        "public_raw_admission": {"sha256": digest, "payload": payload.decode()},
    })
    assert len(rows) == 186
    assert {factor for _, factor in rows} == {4, 8}
    assert {row["source"]["filename"].rsplit(".", 1)[-1].lower() for row in new} == {
        "cr2", "nef", "orf", "pef", "srw", "arw", "dng",
    }
    review_path = root / "public-raw-expansion-v3-source-review-v1.json"
    assert reviewed["public_review_summary"]["sha256"] == hashlib.sha256(review_path.read_bytes()).hexdigest()
    summary = json.loads(review_path.read_text())
    assert summary["counts"]["pixel_flag_pairs_actually_viewed"] == 49
    assert summary["excluded_new_file_ids"]["recognizable_existing_Commons_site"] == [1458]
