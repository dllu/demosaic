"""Immutable checkpoint snapshots shared across evaluation directories."""

import errno
import fcntl
import hashlib
import os
import stat
import tempfile
from pathlib import Path

from .safety import writable_path


def _digest(stream):
    stream.seek(0)
    return hashlib.file_digest(stream, "sha256").hexdigest()


def _validate(path, digest, source_stat, *, immutable=False):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Checkpoint snapshot must be a regular file: {path}")
    properties = path.stat()
    if (properties.st_dev, properties.st_ino) == (
        source_stat.st_dev,
        source_stat.st_ino,
    ) and source_stat.st_mode & 0o222:
        raise ValueError(f"Snapshot aliases a mutable source checkpoint: {path}")
    if immutable and properties.st_mode & 0o222:
        raise ValueError(f"Shared checkpoint cache file is writable: {path}")
    with path.open("rb") as stream:
        if _digest(stream) != digest:
            raise ValueError(f"Checkpoint snapshot checksum differs: {path}")


def _copy_once(reader, target, digest, source_stat):
    """Publish only a complete verified copy; remove only our temporary file."""
    handle, name = tempfile.mkstemp(prefix=".checkpoint-", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        observed = hashlib.sha256()
        reader.seek(0)
        with os.fdopen(handle, "wb") as writer:
            while chunk := reader.read(1 << 20):
                writer.write(chunk)
                observed.update(chunk)
        if observed.hexdigest() != digest:
            raise ValueError("Source checkpoint changed while its snapshot was copied")
        temporary.chmod(0o444)
        try:
            os.link(temporary, target)
        except FileExistsError:
            _validate(target, digest, source_stat, immutable=True)
    finally:
        temporary.unlink(missing_ok=True)


def freeze_checkpoint(source, destination, *, cache_dir=None):
    """Snapshot one opened source version, sharing verified immutable copies.

    Reports retain their existing weights-SHA256.pt paths and bytes. New cache
    entries are copies of the opened source inode; mutable originals are never
    hard-linked. Same-filesystem report snapshots share the immutable cache inode.
    Cross-filesystem outputs get a separate verified copy. Existing corrupt
    snapshots/cache files are rejected rather than overwritten.
    """
    source, destination = Path(source), writable_path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if cache_dir is None:
        # Standard callers pass evaluation/PANEL/weights, sharing this directory
        # across panels. Very shallow authorized outputs keep their cache local.
        try:
            cache_dir = writable_path(destination.parent.parent / ".checkpoint-cache")
        except ValueError:
            cache_dir = destination / ".checkpoint-cache"
    cache = writable_path(cache_dir)
    with source.open("rb") as reader:
        source_stat = os.fstat(reader.fileno())
        digest = _digest(reader)
        frozen = destination / f"weights-{digest}.pt"
        if frozen.exists() or frozen.is_symlink():
            _validate(frozen, digest, source_stat)
            return frozen, digest
        cache.mkdir(parents=True, exist_ok=True)
        canonical = cache / frozen.name
        with (cache / f"{digest}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if canonical.exists() or canonical.is_symlink():
                _validate(canonical, digest, source_stat, immutable=True)
            else:
                _copy_once(reader, canonical, digest, source_stat)
            try:
                os.link(canonical, frozen)
            except FileExistsError:
                _validate(frozen, digest, source_stat)
            except OSError as error:
                if error.errno != errno.EXDEV:
                    raise
                with canonical.open("rb") as cached:
                    _copy_once(cached, frozen, digest, source_stat)
            _validate(frozen, digest, source_stat)
        return frozen, digest
