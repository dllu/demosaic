import importlib.util
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_commons_local_stage.py"
spec = importlib.util.spec_from_file_location("prepare_commons_local_stage", SCRIPT)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


@pytest.mark.parametrize(
    "free,available,reserve", [(1000, 1000, 199), (199, 1000, 200), (1000, 23, 200)]
)
def test_resource_guards_stop_before_image_work(tmp_path, monkeypatch, free, available, reserve):
    monkeypatch.setattr(
        preparation.shutil, "disk_usage", lambda _: SimpleNamespace(free=free * 2**30)
    )
    monkeypatch.setattr(
        preparation.psutil, "virtual_memory", lambda: SimpleNamespace(available=available * 2**30)
    )
    with pytest.raises(ValueError):
        preparation.guard(tmp_path, reserve_gib=reserve)


def test_pending_index_cannot_be_mistaken_for_a_complete_download(tmp_path):
    selected = tmp_path / "selected.json"
    selected.write_text(json.dumps([{"page_id": 1, "status": "pending"}]))
    (tmp_path / "plan.json").write_text(json.dumps({"selection": {"path": str(selected)}}))
    with sqlite3.connect(tmp_path / "quality_images.sqlite3") as connection:
        connection.execute("CREATE TABLE images(page_id INTEGER,status TEXT)")
        connection.execute("INSERT INTO images VALUES(1,'pending')")
    with pytest.raises(ValueError, match="unfinished sources"):
        preparation.downloaded_records(tmp_path)


@pytest.mark.parametrize("corruption", ["attribution", "bytes"])
def test_completed_originals_require_immutable_metadata_and_exact_hash(tmp_path, corruption):
    original = tmp_path / "original.jpg"
    original.write_bytes(b"original")
    row = {field: "" for field in preparation.PREPARE_FIELDS}
    row.update(
        page_id=1,
        status="pending",
        license="CC0",
        byte_size=8,
        sha1_hex=preparation.sha(original, "sha1"),
        download_path=None,
    )
    selected = tmp_path / "selected.json"
    selected.write_text(json.dumps([row]))
    (tmp_path / "plan.json").write_text(json.dumps({"selection": {"path": str(selected)}}))
    target = dict(row, status="downloaded", download_path="original.jpg")
    if corruption == "attribution":
        target["attribution"] = "changed"
    else:
        original.write_bytes(b"tampered")
    with sqlite3.connect(tmp_path / "quality_images.sqlite3") as connection:
        connection.execute("CREATE TABLE images(" + ",".join(target) + ")")
        connection.execute(
            "INSERT INTO images VALUES(" + ",".join("?" for _ in target) + ")",
            list(target.values()),
        )
    with pytest.raises(ValueError, match="Immutable attribution|Original SHA1"):
        preparation.downloaded_records(tmp_path)


@pytest.mark.parametrize("offset", [0, 2])
def test_area_audit_checks_saved_pixels_even_when_cache_hashes_match(tmp_path, offset):
    source = {"sha1_hex": "f" * 40, "license": "CC0", "attribution": "fixture"}
    for factor in (4, 8):
        root = tmp_path / f"prepared{factor}"
        root.mkdir()
        image = np.full(
            (2048 // factor, 2048 // factor, 3),
            1000 + (offset if factor == 8 else 0),
            dtype=np.uint16,
        )
        np.save(root / "image.npy", image, allow_pickle=False)
        row = {
            **source,
            "id": source["sha1_hex"],
            "cache": "image.npy",
            "shape": list(image.shape),
            "bin_factor": factor,
            "color_space": "linear-sRGB",
            "cache_sha256": preparation.sha(root / "image.npy"),
        }
        (root / "manifest.jsonl").write_text(json.dumps(row) + "\n")
        (root / "errors.jsonl").touch()
    if offset:
        with pytest.raises(ValueError, match="area relation"):
            preparation.audit_caches(tmp_path, [source])
    else:
        result = preparation.audit_caches(tmp_path, [source])
        assert result["area_samples"] == 256 * 256 * 3
        assert result["area_max_uint16_codes"] == 0
