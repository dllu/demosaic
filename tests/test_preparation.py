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
