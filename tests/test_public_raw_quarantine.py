import hashlib
import json
import runpy
from pathlib import Path

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "scripts/prepare_public_raw_quarantine.py"))


@pytest.mark.parametrize("camera", ["Canon EOS M100", "EOS M100", "canon eos-m100", "Panasonic DMC-GH1", "DMC-GH1"])
def test_public_native_quarantine_preserves_unseen_camera_holdouts(camera):
    assert MODULE["protected_identity"](camera, {}) == "camera-held-out-for-unseen-development"


@pytest.mark.parametrize("camera", ["GFX100S", "GFX 100S", "FUJIFILM GFX100S"])
def test_entire_standing_date_family_is_excluded(camera):
    assert MODULE["protected_identity"](camera, {"DateTimeOriginal": "2023:12:31 18:12:01", "OriginalFileName": "DSCF3895.RAF"}) == "standing-GFX-capture-date-family"


@pytest.mark.parametrize("identifier", ["DSCF3835", "DSCF3842", "DSCF3879", "DSCF3880", "DSCF3883"])
def test_standing_capture_identifiers_do_not_need_usable_camera_metadata(identifier):
    assert MODULE["protected_identity"]("Unknown", {"OriginalRawFileName": identifier + ".RAF"}) == "standing-GFX-capture-identifier"


def test_unrelated_gfx_capture_is_only_a_quarantine_candidate():
    assert MODULE["protected_identity"]("GFX100S", {"DateTimeOriginal": "2022:08:01 12:00:00", "OriginalFileName": "DSCF1200.RAF"}) is None


def test_both_raws_and_camera_jpegs_are_protected_by_hash_and_stale_cache_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cache = Path(".cache/gfx-green-mesh-20231231")
    cache.mkdir(parents=True)
    sources, hashes = {}, set()
    for name in ("noisy.raf", "reference.raf", "noisy.jpg", "reference.jpg"):
        path = cache / name
        path.write_bytes(name.encode())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sources[name] = {"path": str(path), "sha256": digest}
        hashes.add(digest)
    config = Path("mesh.json")
    config.write_text(json.dumps({"sources": sources}))
    assert MODULE["qualitative_capture_hashes"](config) == hashes
    (cache / "reference.raf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="source hash differs"):
        MODULE["qualitative_capture_hashes"](config)
