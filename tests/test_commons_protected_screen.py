import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "screen_commons_protected",
    Path(__file__).resolve().parents[1] / "scripts/screen_commons_protected.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def setup_sources(tmp_path, arrays):
    source = tmp_path / "originals"
    source.mkdir()
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    rows = []
    for i, array in enumerate(arrays):
        path = prepared / f"{i}.npy"
        np.save(path, array)
        Image.fromarray((array // 257).astype(np.uint8)).save(source / f"{i}.jpg")
        rows.append(
            {
                "id": hashlib.sha1(str(i).encode()).hexdigest(),
                "cache": path.name,
                "cache_sha256": module.digest(path),
                "download_path": f"{i}.jpg",
                "title": f"Image{i}",
                "split": "train",
                "license": "CC BY 4.0",
                "author": "Fixture author",
                "bin_factor": 8,
                "dtype": "uint16",
                "color_space": "linear-sRGB",
            }
        )
    manifest = prepared / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return source, manifest, rows


def references(tmp_path, array):
    path = tmp_path / "reference.npy"
    np.save(path, array)
    manifest = tmp_path / "references.json"
    manifest.write_text(
        json.dumps(
            {
                "protected": [
                    {
                        "scene": "heldout",
                        "screen_cache": path.name,
                        "screen_sha256": module.digest(path),
                    }
                ]
            }
        )
    )
    return manifest


def picture(seed):
    return np.random.default_rng(seed).integers(0, 65536, (128, 160, 3), dtype=np.uint16)


def test_rotated_overlap_is_quarantined_and_other_metadata_preserved(tmp_path):
    a, b = picture(1), picture(2)
    source, manifest, rows = setup_sources(tmp_path, [np.rot90(a)[:, ::-1], b])
    refs = references(tmp_path, a)
    result = module.screen(manifest, refs, source, tmp_path / "screen")
    assert result["cleared"] == result["quarantined"] == 1
    admitted = json.loads(Path(result["cleared_manifest"]).read_text())
    flagged = json.loads(Path(result["quarantined_manifest"]).read_text())
    assert admitted == {**rows[1], "cache": str(manifest.parent / rows[1]["cache"])}
    assert flagged["id"] == rows[0]["id"] and flagged["protected_screen"]["matches"]
    assert Path(flagged["cache"]).read_bytes() == (manifest.parent / rows[0]["cache"]).read_bytes()


def test_changed_reference_and_candidate_checksums_are_rejected(tmp_path):
    source, manifest, _ = setup_sources(tmp_path, [picture(4)])
    refs = references(tmp_path, picture(3))
    original = refs.read_text()
    data = json.loads(original)
    data["protected"][0]["screen_sha256"] = "0" * 64
    refs.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Protected screen checksum"):
        module.screen(manifest, refs, source, tmp_path / "bad-ref")
    refs.write_text(original)
    np.save(manifest.parent / "0.npy", picture(5))
    with pytest.raises(ValueError, match="Candidate cache checksum"):
        module.screen(manifest, refs, source, tmp_path / "bad-cache")
    assert not (tmp_path / "bad-cache/cleared.jsonl").exists()


def test_gfx_metadata_family_and_named_captures_are_held(tmp_path):
    source = tmp_path / "originals"
    source.mkdir()
    exif = Image.Exif()
    exif[272] = "FUJIFILM GFX100S"
    exif[306] = "2023:12:31 17:14:00"
    Image.new("RGB", (32, 32)).save(source / "gfx.jpg", exif=exif)
    row = {"download_path": "gfx.jpg", "title": "train"}
    assert module.metadata_reason(row, source) == "Standing GFX camera/date family"
    exif[306] = "2024:01:01 12:00:00"
    Image.new("RGB", (32, 32)).save(source / "gfx.jpg", exif=exif)
    assert module.metadata_reason(row, source) is None
    row["title"] = "DSCF3880 processed photograph"
    assert module.metadata_reason(row, source) == "Standing GFX capture identifier"
    with pytest.raises(ValueError, match="escapes"):
        module.metadata_reason({"download_path": "../elsewhere.jpg"}, source)


def test_output_lock_freeze_and_duplicate_identity_guards(tmp_path):
    source, manifest, rows = setup_sources(tmp_path, [picture(7)])
    refs = references(tmp_path, picture(6))
    output = tmp_path / "screen"
    output.mkdir()
    with (output / ".screen.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="owns output"):
            module.screen(manifest, refs, source, output)
    result = module.screen(manifest, refs, source, output)
    digest = module.digest(result["cleared_manifest"])
    with pytest.raises(ValueError, match="frozen"):
        module.screen(manifest, refs, source, output)
    assert module.digest(result["cleared_manifest"]) == digest
    manifest.write_text("".join(json.dumps(rows[0]) + "\n" for _ in range(2)))
    with pytest.raises(ValueError, match="Duplicate candidate"):
        module.screen(manifest, refs, source, tmp_path / "duplicate")


def test_interrupted_screen_reuses_unchanged_outcomes(tmp_path, monkeypatch):
    source, manifest, _ = setup_sources(tmp_path, [picture(9), picture(10)])
    refs = references(tmp_path, picture(8))
    original = module.matches
    calls = []

    def interrupted(array, pool):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("fixture interruption")
        return original(array, pool)

    monkeypatch.setattr(module, "matches", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        module.screen(manifest, refs, source, tmp_path / "screen")
    calls.clear()

    def resumed(array, pool):
        calls.append(1)
        return original(array, pool)

    monkeypatch.setattr(module, "matches", resumed)
    result = module.screen(manifest, refs, source, tmp_path / "screen")
    assert len(calls) == 1 and result["candidates"] == 2
