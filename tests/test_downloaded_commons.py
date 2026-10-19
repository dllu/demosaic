"""Keep new download preparation disjoint, immutable and resource bounded."""

import hashlib
import importlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("prepare_downloaded_commons")


def row(identity, **changes):
    value = {
        "sha1_hex": identity * 40,
        "license": "CC BY-SA 4.0",
        "width": 2048,
        "height": 2048,
        "byte_size": 3,
        "downloaded_bytes": 3,
        "status": "downloaded",
    }
    return value | changes


def test_selection_preserves_rows_and_excludes_known_duplicate_license_and_geometry(worker):
    records = [
        row("1"),
        row("2"),
        row("2"),
        row("3", license="CC BY-NC 4.0"),
        row("4", width=2047),
        row("5", width=20000, height=20000),
    ]
    before = json.dumps(records, sort_keys=True)
    selected, reasons = worker.select(records, {"1" * 40})
    assert selected == [records[1]]
    assert reasons == {
        "already_prepared": 1,
        "duplicate_SHA1": 1,
        "license_not_in_existing_whitelist": 1,
        "geometry": 2,
    }
    assert json.dumps(records, sort_keys=True) == before


@pytest.mark.parametrize(
    "change", [{"status": "pending"}, {"downloaded_bytes": 2}, {"sha1_hex": "invalid"}]
)
def test_selection_rejects_incomplete_or_invalid_originals(worker, change):
    with pytest.raises(ValueError):
        worker.select([row("1", **change)], set())


def test_fixture_limit_keeps_complete_accounting_and_never_changes_source_splits(worker):
    records = [row(str(i), split="val") for i in range(1, 4)]
    selected, excluded = worker.select(records, set(), limit=2)
    assert selected == records[:2] and excluded == {"engineering_limit": 1}
    assert all(r["split"] == "val" for r in selected)


@pytest.mark.parametrize("ram,disk,extra", [(47, 600, 0), (60, 559, 0), (60, 562, 3)])
def test_declared_memory_and_disk_reserves_stop_work(worker, monkeypatch, ram, disk, extra):
    monkeypatch.setattr(
        worker.psutil, "virtual_memory", lambda: SimpleNamespace(available=ram * 2**30)
    )
    monkeypatch.setattr(worker.shutil, "disk_usage", lambda _: SimpleNamespace(free=disk * 2**30))
    with pytest.raises(RuntimeError):
        worker.resources(
            {"root": "/mnt/external", "minimum_available_gib": 48, "reserve_gib": 560},
            additional_bytes=extra * 2**30,
        )


@pytest.mark.parametrize("damage", ["attribution", "original_bytes"])
def test_pinned_source_and_actual_bytes_cannot_change(worker, tmp_path, monkeypatch, damage):
    source = tmp_path / "archive"
    source.mkdir()
    original = source / "original.jpg"
    original.write_bytes(b"original")
    item = {
        "page_id": 1,
        "title": "original title",
        "download_path": original.name,
        "byte_size": 8,
        "sha1_hex": hashlib.sha1(b"original").hexdigest(),
    }
    with sqlite3.connect(source / "quality_images.sqlite3") as db:
        db.execute(
            "CREATE TABLE images (page_id INTEGER, title TEXT, download_path TEXT, byte_size INTEGER, sha1_hex TEXT)"
        )
        actual = dict(item)
        if damage == "attribution":
            actual["title"] = "changed credit/title"
        db.execute("INSERT INTO images VALUES (?,?,?,?,?)", tuple(actual.values()))
    selection = tmp_path / "selected.json"
    selection.write_text(json.dumps([item]))
    if damage == "original_bytes":
        original.write_bytes(b"tampered")
    monkeypatch.setattr(worker, "resources", lambda _: None)
    with pytest.raises(ValueError):
        worker.verify_originals({"source": str(source), "selection": {"path": str(selection)}})
