import importlib.util
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from stage_commons_local import OPERATIONAL

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/handoff_commons_local.py"
spec = importlib.util.spec_from_file_location("handoff_commons_local", SCRIPT)
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def indexed_stage(tmp_path, monkeypatch):
    stage, archive = tmp_path / "stage", tmp_path / "archive"
    stage.mkdir()
    archive.mkdir()
    source = stage / "original.jpg"
    source.write_bytes(b"a complete original fixture")
    row = {
        "page_id": 1,
        "title": "Fixture",
        "original_url": "https://upload.wikimedia.org/fixture.jpg",
        "byte_size": source.stat().st_size,
        "mime_type": "image/jpeg",
        "sha1_hex": handoff.digest(source, "sha1"),
        "license": "CC BY 4.0",
        "attribution": "Fixture author",
        "status": "pending",
        "attempts": 0,
        "download_path": None,
        "downloaded_bytes": 0,
        "http_etag": None,
        "http_last_modified": None,
        "last_error": None,
        "downloaded_at": None,
        "download_started_at": None,
        "updated_at": "before",
    }
    local = dict(
        row,
        status="downloaded",
        download_path=source.name,
        downloaded_bytes=row["byte_size"],
        attempts=1,
        downloaded_at="2026-10-19T00:00:00Z",
    )
    unrelated = dict(row, page_id=2, sha1_hex="b" * 40, attribution="Unrelated author")
    for folder, rows in [(stage, [local]), (archive, [row, unrelated])]:
        with sqlite3.connect(folder / "quality_images.sqlite3") as db:
            db.execute(
                "CREATE TABLE images(page_id INTEGER PRIMARY KEY,"
                + ",".join(key for key in row if key != "page_id")
                + ")"
            )
            for value in rows:
                db.execute(
                    "INSERT INTO images VALUES(" + ",".join("?" for _ in value) + ")",
                    list(value.values()),
                )
    monkeypatch.setattr(handoff.shutil, "disk_usage", lambda _: SimpleNamespace(free=2000 * 2**30))
    downloader = SimpleNamespace(
        DownloadRecord=lambda **kwargs: SimpleNamespace(**kwargs),
        destination_path=lambda root, record: root / "images" / f"{record.sha1_hex}.jpg",
    )
    return stage, archive, row, unrelated, downloader


def test_reconcile_preserves_attribution_unrelated_rows_and_is_idempotent(tmp_path, monkeypatch):
    stage, archive, row, unrelated, downloader = indexed_stage(tmp_path, monkeypatch)
    before = handoff.ref(stage / "quality_images.sqlite3")
    first = handoff.reconcile(stage, archive, tmp_path / "first", [row], OPERATIONAL, downloader)
    second = handoff.reconcile(stage, archive, tmp_path / "second", [row], OPERATIONAL, downloader)
    assert first["new_files"] == first["index_rows_updated"] == 1
    assert second["new_files"] == second["index_rows_updated"] == 0
    assert second["existing_files_verified"] == 1
    with handoff.connection(archive / "quality_images.sqlite3") as db:
        actual = dict(db.execute("SELECT * FROM images WHERE page_id=2").fetchone())
        imported = dict(db.execute("SELECT * FROM images WHERE page_id=1").fetchone())
    assert actual == unrelated and imported["attempts"] == 1
    assert imported["attribution"] == row["attribution"]
    assert handoff.ref(stage / "quality_images.sqlite3") == before


@pytest.mark.parametrize("damage", ["license", "attribution", "unfinished"])
def test_changed_metadata_or_unfinished_sources_stop_before_copying(tmp_path, monkeypatch, damage):
    stage, archive, row, _, downloader = indexed_stage(tmp_path, monkeypatch)
    with sqlite3.connect(stage / "quality_images.sqlite3") as db:
        if damage == "unfinished":
            db.execute("UPDATE images SET status='pending'")
        else:
            db.execute(f"UPDATE images SET {damage}='changed'")
    original_index = handoff.ref(archive / "quality_images.sqlite3")
    with pytest.raises(ValueError):
        handoff.reconcile(stage, archive, tmp_path / "operation", [row], OPERATIONAL, downloader)
    assert not (archive / "images").exists()
    assert handoff.ref(archive / "quality_images.sqlite3") == original_index


def test_insufficient_archive_reserve_stops_before_copying(tmp_path, monkeypatch):
    stage, archive, row, _, downloader = indexed_stage(tmp_path, monkeypatch)
    monkeypatch.setattr(handoff.shutil, "disk_usage", lambda _: SimpleNamespace(free=600 * 2**30))
    with pytest.raises(ValueError, match="reserve"):
        handoff.reconcile(stage, archive, tmp_path / "operation", [row], OPERATIONAL, downloader)
    assert not (archive / "images").exists()


@pytest.mark.parametrize("existing", [True, False])
def test_corrupt_bytes_never_replace_an_existing_original_or_publish_a_new_one(tmp_path, existing):
    source, destination = tmp_path / "local.jpg", tmp_path / "archive.jpg"
    source.write_bytes(b"original bytes")
    digest = handoff.digest(source, "sha1")
    if existing:
        destination.write_bytes(b"corrupted data")
    else:
        source.write_bytes(b"corrupted data")
    with pytest.raises(ValueError, match="checksum|SHA1"):
        handoff.publish_new_copy(source, destination, digest, 14)
    assert destination.read_bytes() == b"corrupted data" if existing else not destination.exists()
    assert not list(tmp_path.glob(".local-handoff-*"))


def test_failed_post_publish_check_removes_only_the_new_owned_entry(tmp_path, monkeypatch):
    source, destination = tmp_path / "local.jpg", tmp_path / "archive.jpg"
    source.write_bytes(b"original bytes")
    digest = handoff.digest(source, "sha1")
    verify = handoff.verify_file

    def fail_after_publish(path, *args):
        if path == destination:
            raise OSError("Injected archive post-publication failure")
        return verify(path, *args)

    monkeypatch.setattr(handoff, "verify_file", fail_after_publish)
    with pytest.raises(OSError, match="post-publication"):
        handoff.publish_new_copy(source, destination, digest, 14)
    assert source.read_bytes() == b"original bytes" and not destination.exists()
    assert not list(tmp_path.glob(".local-handoff-*"))
