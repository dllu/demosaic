"""Personal originals stay unchanged; quarantine copies retain import identity."""

import hashlib
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def worker(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "personal_quarantine", "scripts/prepare_personal_raw_quarantine.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PERSONAL_ROOTS", (tmp_path / "originals",))
    (tmp_path / "originals").mkdir()
    return module


def source_file(tmp_path, contents=b"known original RAW bytes"):
    digest = hashlib.sha1(contents).hexdigest()
    source = tmp_path / "originals" / f"2026-06-18-12-00-00_DSCF0001_{digest}.raf"
    source.write_bytes(contents)
    return source


def test_copy_and_reuse_keep_original_and_cached_identity(worker, tmp_path):
    source = source_file(tmp_path)
    before = source.read_bytes(), source.stat().st_mtime_ns
    output = tmp_path / "cache"
    first = worker.cache_source(source, output)
    assert Path(first["path"]).read_bytes() == before[0]
    assert first["sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert worker.cache_source(source, output) == first
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before


def test_changed_cached_source_is_rejected_without_overwriting_original(worker, tmp_path):
    source = source_file(tmp_path)
    result = worker.cache_source(source, tmp_path / "cache")
    Path(result["path"]).write_bytes(b"corrupt cached bytes")
    with pytest.raises(AssertionError):
        worker.cache_source(source, tmp_path / "cache")
    assert source.read_bytes() == b"known original RAW bytes"
    assert Path(result["path"]).read_bytes() == b"corrupt cached bytes"


def test_wrong_import_hash_never_publishes_a_cached_RAW(worker, tmp_path):
    source = source_file(tmp_path)
    source.write_bytes(b"changed original bytes")
    with pytest.raises(AssertionError, match="import SHA1"):
        worker.cache_source(source, tmp_path / "cache")
    assert not (tmp_path / "cache" / source.name).exists()
    assert source.read_bytes() == b"changed original bytes"


def test_other_source_roots_are_rejected_before_copy(worker, tmp_path):
    source = tmp_path / "other.raf"
    source.write_bytes(b"unapproved source")
    with pytest.raises(ValueError, match="authorized"):
        worker.cache_source(source, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_source_without_import_hash_is_rejected(worker, tmp_path):
    source = tmp_path / "originals/plain.raf"
    source.write_bytes(b"original")
    with pytest.raises(ValueError, match="import-hashed"):
        worker.cache_source(source, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()
