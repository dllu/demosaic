import errno
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from demosaic import checkpoint_cache
from demosaic.checkpoint_cache import freeze_checkpoint


def checkpoint(tmp_path, data=b"complete training checkpoint"):
    source = tmp_path / "latest.pt"
    source.write_bytes(data)
    return source, hashlib.sha256(data).hexdigest()


def test_panels_share_one_copy_but_never_the_mutable_original(tmp_path, monkeypatch):
    source, digest = checkpoint(tmp_path)
    cache = tmp_path / "evaluation" / ".checkpoint-cache"
    copies = []
    original_copy = checkpoint_cache._copy_once

    def count_copy(*args):
        copies.append(args[1])
        return original_copy(*args)

    monkeypatch.setattr(checkpoint_cache, "_copy_once", count_copy)
    snapshots = [
        freeze_checkpoint(source, tmp_path / "evaluation" / panel / "weights")
        for panel in ("known", "unseen", "known")
    ]
    first, second = snapshots[0][0], snapshots[1][0]
    canonical = cache / first.name
    assert all(actual == digest for _, actual in snapshots)
    assert first.name == f"weights-{digest}.pt"
    assert first.samefile(second) and first.samefile(canonical)
    assert not first.samefile(source)
    assert first.stat().st_mode & 0o222 == 0
    assert source.stat().st_mode & 0o200
    assert copies == [canonical]
    source.write_bytes(b"next in-place training update")
    assert first.read_bytes() == b"complete training checkpoint"


def test_parallel_same_and_different_panel_requests_publish_one_snapshot(tmp_path, monkeypatch):
    source, digest = checkpoint(tmp_path, bytes(range(256)) * 1024)
    copies = []
    original_copy = checkpoint_cache._copy_once

    def count_copy(*args):
        copies.append(args[1])
        return original_copy(*args)

    monkeypatch.setattr(checkpoint_cache, "_copy_once", count_copy)
    destinations = [
        tmp_path / "evaluation" / f"panel-{index % 4}" / "weights" for index in range(16)
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        snapshots = list(pool.map(lambda dest: freeze_checkpoint(source, dest), destinations))
    first = snapshots[0][0]
    assert len(copies) == 1
    assert all(path.samefile(first) and actual == digest for path, actual in snapshots)
    assert first.stat().st_nlink == 5  # Four reports plus their cache entry.
    assert not list(tmp_path.rglob("*.tmp"))


def test_atomic_source_replacement_preserves_one_complete_opened_version(tmp_path, monkeypatch):
    source, old_digest = checkpoint(tmp_path, b"previous complete checkpoint")
    replacement = tmp_path / "next.pt"
    replacement.write_bytes(b"new complete checkpoint")
    original_digest = checkpoint_cache._digest
    replaced = False

    def replace_after_hash(stream):
        nonlocal replaced
        digest = original_digest(stream)
        if not replaced:
            replacement.replace(source)
            replaced = True
        return digest

    monkeypatch.setattr(checkpoint_cache, "_digest", replace_after_hash)
    first, digest = freeze_checkpoint(source, tmp_path / "evaluation" / "panel" / "weights")
    assert digest == old_digest
    assert first.read_bytes() == b"previous complete checkpoint"
    second, digest = freeze_checkpoint(source, first.parent)
    assert digest == hashlib.sha256(b"new complete checkpoint").hexdigest()
    assert second.read_bytes() == b"new complete checkpoint"
    assert not second.samefile(first)


def test_in_place_source_change_during_copy_cannot_publish_mismatched_bytes(tmp_path, monkeypatch):
    source, _ = checkpoint(tmp_path)
    original_copy = checkpoint_cache._copy_once

    def mutate_before_copy(*args):
        source.write_bytes(b"a later update")
        return original_copy(*args)

    monkeypatch.setattr(checkpoint_cache, "_copy_once", mutate_before_copy)
    destination = tmp_path / "evaluation" / "panel" / "weights"
    with pytest.raises(ValueError, match="Source checkpoint changed"):
        freeze_checkpoint(source, destination)
    assert not list(tmp_path.rglob("weights-*.pt"))
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("corrupt_target", ["snapshot", "cache"])
def test_corrupt_existing_bytes_are_rejected_and_preserved(tmp_path, corrupt_target):
    source, digest = checkpoint(tmp_path)
    destination = tmp_path / "evaluation" / "panel" / "weights"
    cache = tmp_path / "evaluation" / ".checkpoint-cache"
    target = (destination if corrupt_target == "snapshot" else cache) / f"weights-{digest}.pt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt bytes")
    target.chmod(0o444)
    with pytest.raises(ValueError, match="checksum differs"):
        freeze_checkpoint(source, destination)
    assert target.read_bytes() == b"corrupt bytes"
    assert source.read_bytes() == b"complete training checkpoint"
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("unsafe_kind", ["symlink", "mutable-source-alias", "writable-cache"])
def test_unsafe_existing_cache_entries_are_rejected(tmp_path, unsafe_kind):
    source, digest = checkpoint(tmp_path)
    cache = tmp_path / "cache"
    cache.mkdir()
    canonical = cache / f"weights-{digest}.pt"
    if unsafe_kind == "symlink":
        canonical.symlink_to(source)
    elif unsafe_kind == "mutable-source-alias":
        os.link(source, canonical)
    else:
        canonical.write_bytes(source.read_bytes())
    with pytest.raises(ValueError):
        freeze_checkpoint(source, tmp_path / "panel" / "weights", cache_dir=cache)
    assert source.stat().st_mode & 0o200
    assert not list((tmp_path / "panel").rglob("*.pt"))


def test_cross_filesystem_outputs_get_a_verified_independent_copy(tmp_path, monkeypatch):
    source, digest = checkpoint(tmp_path)
    destination = tmp_path / "panel" / "weights"
    cache = tmp_path / "cache"
    original_link = os.link

    def cross_device_link(src, dst):
        if src.parent == cache and dst.parent == destination and not src.name.endswith(".tmp"):
            raise OSError(errno.EXDEV, "cross-device link")
        return original_link(src, dst)

    monkeypatch.setattr(checkpoint_cache.os, "link", cross_device_link)
    frozen, actual = freeze_checkpoint(source, destination, cache_dir=cache)
    canonical = cache / frozen.name
    assert actual == digest
    assert frozen.read_bytes() == source.read_bytes()
    assert not frozen.samefile(canonical) and not frozen.samefile(source)
    assert frozen.stat().st_mode & 0o222 == 0
    assert not list(tmp_path.rglob("*.tmp"))


def test_existing_independent_snapshot_is_preserved_without_copying(tmp_path):
    source, digest = checkpoint(tmp_path)
    destination = tmp_path / "panel" / "weights"
    destination.mkdir(parents=True)
    existing = destination / f"weights-{digest}.pt"
    existing.write_bytes(source.read_bytes())
    properties = existing.stat()
    cache = tmp_path / "cache"
    frozen, actual = freeze_checkpoint(source, destination, cache_dir=cache)
    assert frozen == existing and actual == digest
    assert frozen.stat().st_ino == properties.st_ino
    assert frozen.stat().st_mtime_ns == properties.st_mtime_ns
    assert not cache.exists()


def test_an_existing_readonly_snapshot_can_be_a_source_without_another_copy(tmp_path):
    source, digest = checkpoint(tmp_path)
    cache = tmp_path / "cache"
    first, _ = freeze_checkpoint(source, tmp_path / "first" / "weights", cache_dir=cache)
    second, actual = freeze_checkpoint(first, tmp_path / "second" / "weights", cache_dir=cache)
    assert actual == digest
    assert first.samefile(second)
    assert not first.samefile(source)
