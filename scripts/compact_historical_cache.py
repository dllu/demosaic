"""Hash-verified hard links for inactive historical artifacts; preserve paths and bytes.

Create a plan first, inspect it, then apply that exact plan. Only repository-local
.cache roots are accepted. This never walks symlinks or deletes unique artifacts.
Merged files become read-only: copy a checkpoint before resuming training.
"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import stat
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil

REPO = Path(__file__).resolve().parents[1]
SUFFIXES = {".npy", ".npz", ".pt", ".jsonl", ".json", ".tiff", ".png"}
FIELDS = ("dev", "ino", "size", "mode", "uid", "gid", "nlink", "mtime_ns", "ctime_ns", "blocks")


def identity(path):
    s = Path(path).lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid():
        raise ValueError(f"Not an owned regular file: {path}")
    return {k: getattr(s, "st_" + k) for k in FIELDS}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "xt") as stream:
        json.dump(value, stream, separators=(",", ":"))
        stream.write("\n")


def read(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        return json.load(stream)


def local_now():
    return datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()


def checked_root(value):
    path = Path(os.path.abspath(value))
    if not path.is_relative_to(REPO / ".cache") or path == REPO / ".cache":
        raise ValueError("Select explicit subdirectories of repository .cache")
    if path.resolve() != path or not path.is_dir():
        raise ValueError(f"Root must be a real directory without symlink ancestors: {path}")
    return path


def assert_inactive(roots, paths=None):
    """Reject scientific workers in selected roots, and all open candidate files."""
    for process in psutil.process_iter(["pid", "cmdline", "cwd"]):
        try:
            if process.pid == os.getpid():
                continue
            command = process.info["cmdline"] or []
            # Shell/editor sessions are harmless; Python experiments are not.
            if command and ("python" in Path(command[0]).name or "pytest" in command[0]):
                for root in roots:
                    if any(str(root) in arg for arg in command):
                        raise RuntimeError(f"Worker {process.pid} references {root}")
                    cwd = process.info["cwd"]
                    if cwd and Path(cwd).is_relative_to(root):
                        raise RuntimeError(f"Worker {process.pid} is in {root}")
            if paths is not None and process.uids().real == os.getuid():
                for handle in process.open_files():
                    if handle.path in paths:
                        raise RuntimeError(f"Candidate open by PID {process.pid}: {handle.path}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def plan(args):
    roots = [checked_root(value) for value in args.root]
    if any(a != b and a.is_relative_to(b) for a in roots for b in roots):
        raise ValueError("Roots must not overlap")
    assert_inactive(roots)
    cutoff = time.time_ns() - int(args.age_days * 86400 * 1e9)
    sizes = defaultdict(dict)
    for root in roots:
        for directory, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not Path(directory, d).is_symlink()]
            for name in names:
                path = Path(directory, name)
                if path.suffix not in SUFFIXES or path.is_symlink():
                    continue
                info = identity(path)
                if info["size"] < 65536 or info["mtime_ns"] > cutoff:
                    continue
                inode = (info["dev"], info["ino"])
                item = sizes[(info["dev"], info["size"])].setdefault(
                    inode, {"identity": info, "paths": []}
                )
                item["paths"].append(str(path))
    samples = defaultdict(list)
    considered = 0
    for (device, size), inodes in sizes.items():
        # Every existing alias must be within this explicit inventory.
        complete = [v for v in inodes.values() if len(v["paths"]) == v["identity"]["nlink"]]
        if len(complete) < 2:
            continue
        for item in complete:
            path = item["paths"][0]
            assert identity(path) == item["identity"]
            digest = hashlib.sha256()
            with Path(path).open("rb") as stream:
                for offset in sorted({0, max(0, size // 2 - 16384), max(0, size - 32768)}):
                    stream.seek(offset)
                    digest.update(stream.read(32768))
            assert identity(path) == item["identity"]
            samples[(device, size, digest.hexdigest())].append(item)
            considered += 1
    candidates = [items for items in samples.values() if len(items) > 1]
    print(json.dumps({"stage": "full-hash", "candidate_inodes": sum(map(len, candidates)),
                      "sampled_inodes": considered}), flush=True)
    groups = []
    total_hashed = 0
    last = time.monotonic()
    for items in candidates:
        hashes = defaultdict(list)
        for item in items:
            path = item["paths"][0]
            assert identity(path) == item["identity"]
            digest = sha(path)
            assert identity(path) == item["identity"]
            total_hashed += item["identity"]["size"]
            # Differing permissions/ownership are separate semantic objects.
            metadata = tuple(item["identity"][k] for k in ("mode", "uid", "gid"))
            hashes[(digest, metadata)].append(item)
        for (digest, _), copies in hashes.items():
            if len(copies) > 1:
                groups.append({"sha256": digest, "inodes": copies})
        if time.monotonic() - last > 10:
            print(json.dumps({"hashed_GiB": round(total_hashed / 2**30, 2),
                              "duplicate_groups": len(groups)}), flush=True)
            last = time.monotonic()
    savings = sum(v["identity"]["blocks"] * 512 for g in groups for v in g["inodes"][1:])
    result = {"status": "fully-hashed-historical-cache-plan", "created_local": local_now(),
              "driver": {"path": str(Path(__file__)), "sha256": sha(__file__)},
              "roots": list(map(str, roots)), "minimum_age_days": args.age_days,
              "groups": groups, "expected_reclaimed_bytes": savings,
              "full_hashed_bytes": total_hashed,
              "metadata_change": "Read-only shared inode; anchor mtime, inode/link count and ctime. "
              "Original per-path metadata recorded here. All paths and bytes preserved."}
    save(args.output, result)
    print(json.dumps({"plan": str(args.output), "groups": len(groups),
                      "reclaim_GiB": savings / 2**30}), flush=True)


def apply(args):
    data = read(args.plan)
    assert data["status"] == "fully-hashed-historical-cache-plan"
    roots = [checked_root(value) for value in data["roots"]]
    assert data["driver"]["sha256"] == sha(__file__)
    paths = {p for g in data["groups"] for v in g["inodes"] for p in v["paths"]}
    assert all(any(Path(p).is_relative_to(root) for root in roots) for p in paths)
    assert all(Path(p).resolve() == Path(p) for p in paths)
    assert_inactive(roots, paths)
    for group in data["groups"]:
        for item in group["inodes"]:
            for path in item["paths"]:
                assert identity(path) == item["identity"], path
    before = shutil.disk_usage(REPO).free
    replaced = 0
    last = time.monotonic()
    with Path(args.journal).open("x") as journal:
        for index, group in enumerate(data["groups"]):
            anchor = Path(group["inodes"][0]["paths"][0])
            for item in group["inodes"]:
                for path in item["paths"]:
                    assert identity(path) == item["identity"], path
            # Durable intent before changing permissions or storage identity.
            journal.write(json.dumps({"group": index, "sha256": group["sha256"],
                                      "anchor": str(anchor)}) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            os.chmod(anchor, anchor.stat().st_mode & ~0o222)
            for item in group["inodes"][1:]:
                for ordinal, value in enumerate(item["paths"]):
                    path = Path(value)
                    expected = dict(item["identity"])
                    # Earlier alias removal changes ctime/link count, never content.
                    actual = identity(path)
                    for field in FIELDS:
                        if field == "ctime_ns":
                            continue
                        want = expected[field] - ordinal if field == "nlink" else expected[field]
                        assert actual[field] == want, (path, field)
                    temporary = path.with_name(path.name + f".compact-{os.getpid()}")
                    assert not temporary.exists()
                    os.link(anchor, temporary, follow_symlinks=False)
                    os.replace(temporary, path)
                    replaced += 1
            assert sha(anchor) == group["sha256"]
            inode = anchor.stat().st_ino
            for item in group["inodes"]:
                for path in item["paths"]:
                    current = identity(path)
                    assert current["ino"] == inode and current["dev"] == item["identity"]["dev"]
                    assert current["size"] == item["identity"]["size"]
                    assert not current["mode"] & 0o222
            if time.monotonic() - last > 10:
                print(json.dumps({"groups_done": index + 1, "paths_replaced": replaced}), flush=True)
                last = time.monotonic()
    save(args.output, {"status": "pass-historical-cache-compaction", "created_local": local_now(),
                       "plan": {"path": str(Path(args.plan).resolve()), "sha256": sha(args.plan)},
                       "journal": {"path": str(Path(args.journal).resolve()),
                                   "sha256": sha(args.journal)},
                       "groups": len(data["groups"]), "paths_preserved": len(paths),
                       "paths_replaced": replaced,
                       "allocated_duplicate_bytes_reclaimed": data["expected_reclaimed_bytes"],
                       "local_free_before": before, "local_free_after": shutil.disk_usage(REPO).free,
                       "all_groups_rehashed_after_replacement": True,
                       "metadata_change": data["metadata_change"]})
    print(json.dumps({"result": str(args.output), "reclaimed_GiB":
                      data["expected_reclaimed_bytes"] / 2**30}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("plan")
    prepare.add_argument("--root", action="append", required=True)
    prepare.add_argument("--age-days", type=float, default=2)
    prepare.add_argument("--output", type=Path, required=True)
    execute = sub.add_parser("apply")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--journal", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan" and args.age_days < 2:
        parser.error("Historical compaction requires at least two days of inactivity")
    (plan if args.action == "plan" else apply)(args)


if __name__ == "__main__":
    main()
