import fcntl
import json
import sqlite3

import numpy as np
import pytest
from PIL import Image

from demosaic.prepare import prepare_commons


def test_parallel_ingestion_is_deterministic_readonly_and_recipe_checked(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    database = source / "quality_images.sqlite3"
    fields = [
        "title",
        "page_url",
        "original_url",
        "author",
        "license",
        "license_url",
        "attribution",
        "credit",
        "sha1",
        "sha1_hex",
        "download_path",
    ]
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE images ("
        + ",".join(f"{field} TEXT" for field in fields)
        + ",width INTEGER,height INTEGER,status TEXT)"
    )
    for i in range(8):
        name = f"source{i}.png"
        if i < 6:
            array = np.full((32, 40, 3), i * 20, dtype=np.uint8)
            Image.fromarray(array).save(source / name)
        key = "source0" if i == 7 else f"source{i}"
        values = [
            name,
            "https://commons.wikimedia.org/example",
            "https://example.com/image",
            "A photographer",
            "CC BY-NC 4.0" if i == 5 else "CC BY 4.0",
            "https://creativecommons.org/licenses/by/4.0",
            "Attribution",
            "Credit",
            key,
            key,
            name,
            40,
            32,
            "downloaded",
        ]
        connection.execute(
            "INSERT INTO images VALUES (" + ",".join("?" for _ in values) + ")", values
        )
    connection.commit()
    connection.close()
    original = database.read_bytes()
    destination = tmp_path / "prepared"
    first = prepare_commons(source, destination, factor=4, min_size=4, workers=1)
    manifest = (destination / "manifest.jsonl").read_bytes()
    second = prepare_commons(source, destination, factor=4, min_size=4, workers=2)
    assert first == second
    assert sum(first[s] for s in ("train", "val", "test")) == 5
    assert first["failed"] == 1
    assert first["unlicensed"] == 1
    assert (destination / "manifest.jsonl").read_bytes() == manifest
    assert database.read_bytes() == original
    assert not (source / "quality_images.sqlite3-shm").exists()
    for line in manifest.splitlines():
        row = json.loads(line)
        assert row["author"] == "A photographer"
        assert len(row["cache_sha256"]) == 64
    with pytest.raises(ValueError, match="recipe"):
        prepare_commons(source, destination, factor=8, min_size=4)
    with (destination / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="Another preparation"):
            prepare_commons(source, destination, factor=4, min_size=4)


def test_frozen_selection_rebins_originals_without_reassigning_splits(tmp_path):
    source = tmp_path / "originals"
    source.mkdir()
    rows = []
    for i, split in enumerate(["train", "val", "test", "excluded"]):
        name = f"{i}.png"
        Image.fromarray(np.full((32, 40, 3), 40 + i, np.uint8)).save(source / name)
        rows.append(
            {
                "id": str(i),
                "sha1": str(i),
                "sha1_hex": str(i),
                "download_path": name,
                "license": "CC BY 4.0",
                "split": split,
                "bin_factor": 8,
            }
        )
    manifest = tmp_path / "frozen.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows))
    original = manifest.read_bytes()
    output = tmp_path / "four"
    result = prepare_commons(
        source, output, factor=4, min_size=4, workers=2, selection_manifest=manifest
    )
    actual = [json.loads(s) for s in (output / "manifest.jsonl").read_text().splitlines()]
    assert {r["id"]: r["split"] for r in actual} == {"0": "train", "1": "val", "2": "test"}
    assert all(r["bin_factor"] == 4 and r["shape"] == [8, 10, 3] for r in actual)
    assert manifest.read_bytes() == original
    assert sum(result[s] for s in ["train", "val", "test"]) == 3
    manifest.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="recipe"):
        prepare_commons(source, output, factor=4, min_size=4, selection_manifest=manifest)


def test_live_downloader_wal_commits_are_visible_to_readonly_ingestion(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    Image.fromarray(np.full((32, 32, 3), 99, np.uint8)).save(source / "new.png")
    row = {
        "title": "New download",
        "page_url": "https://example.org",
        "original_url": "https://example.org/new.png",
        "author": "Fixture",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Fixture",
        "credit": "Fixture",
        "sha1": "new",
        "sha1_hex": "new",
        "download_path": "new.png",
        "width": 32,
        "height": 32,
        "status": "downloaded",
    }
    c = sqlite3.connect(source / "quality_images.sqlite3")
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute(
            "CREATE TABLE images ("
            + ",".join(f"{k} {'INTEGER' if k in ['width', 'height'] else 'TEXT'}" for k in row)
            + ")"
        )
        c.commit()
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        c.execute(
            "INSERT INTO images VALUES (" + ",".join("?" for _ in row) + ")", list(row.values())
        )
        c.commit()
        assert (source / "quality_images.sqlite3-wal").stat().st_size > 0
        result = prepare_commons(source, tmp_path / "prepared", factor=4, min_size=4)
        assert sum(result[s] for s in ["train", "val", "test"]) == 1
        assert c.execute("SELECT count(*) FROM images").fetchone()[0] == 1
    finally:
        c.close()
