"""Stage a bounded new Commons download without modifying the source archive."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from demosaic.prepare import free_license
from demosaic.safety import writable_path

GIB = 2**30
OPERATIONAL = {
    "status",
    "attempts",
    "download_path",
    "downloaded_bytes",
    "http_etag",
    "http_last_modified",
    "last_error",
    "download_started_at",
    "downloaded_at",
    "updated_at",
}


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def read(path):
    return json.loads(Path(path).read_text())


def connect(path, *, readonly=False):
    connection = (
        sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
        if readonly
        else sqlite3.connect(path)
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA temp_store=MEMORY")
    return connection


def lock_downloads():
    repository = Path(__file__).resolve().parents[1]
    handle = (repository / ".cache/commons-qi-download.lock").open("a")
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def select(root, source, downloader, *, byte_budget, max_images, reserve_gib):
    root = writable_path(root)
    repository = Path(__file__).resolve().parents[1]
    if not root.is_relative_to(repository / ".cache"):
        raise ValueError("Local staging must be under this repository's .cache")
    if byte_budget <= 0 or max_images <= 0 or reserve_gib < 224:
        raise ValueError("Expected a positive bounded selection and at least224GiB reserve")
    if shutil.disk_usage(repository).free < byte_budget + reserve_gib * GIB:
        raise ValueError("Selection plus local reserve exceeds current free space")
    root.mkdir(parents=True, exist_ok=False)
    handle = lock_downloads()
    source_db = source / "quality_images.sqlite3"
    source_refs = [ref(source_db)]
    wal = source_db.with_name(source_db.name + "-wal")
    if wal.exists():
        source_refs.append(ref(wal))
    now = datetime.now(UTC).isoformat()
    with connect(source_db, readonly=True) as src:
        src.execute("BEGIN")
        known = {r[0] for r in src.execute("SELECT sha1_hex FROM images WHERE status='downloaded'")}
        candidates = [
            dict(r)
            for r in src.execute(
                "SELECT page_id,sha1_hex,byte_size,license,original_url FROM images "
                "WHERE status='pending' AND eligible=1 AND in_category=1 "
                "AND width>=2048 AND height>=2048 AND width*height<=120000000 "
                "AND byte_size>0 AND byte_size<=268435456"
            )
        ]
        # Hash ordering spreads the subset across the archive's page IDs;
        # semantic diversity still needs later content/protected-scene review.
        candidates.sort(
            key=lambda r: hashlib.sha256(f"commons-local-v1:{r['page_id']}".encode()).digest()
        )
        selected, used, hashes = [], 0, set()
        for candidate in candidates:
            digest = candidate["sha1_hex"]
            url = urlsplit(candidate["original_url"] or "")
            if (
                not free_license(candidate["license"])
                or digest in known
                or digest in hashes
                or len(digest or "") != 40
                or any(c not in "0123456789abcdef" for c in digest)
                or url.scheme != "https"
                or url.hostname != "upload.wikimedia.org"
            ):
                continue
            if used + candidate["byte_size"] > byte_budget:
                continue
            row = dict(
                src.execute(
                    "SELECT * FROM images WHERE page_id=?", (candidate["page_id"],)
                ).fetchone()
            )
            selected.append(row)
            used += row["byte_size"]
            hashes.add(digest)
            if len(selected) == max_images:
                break
        if not selected:
            raise ValueError("No new eligible source originals fit the selection")
        database = root / "quality_images.sqlite3"
        with connect(database) as dest:
            schema = src.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('images','state')"
            ).fetchall()
            if len(schema) != 2:
                raise ValueError("Unexpected source index schema")
            for row in schema:
                dest.execute(row[0])
            for row in src.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name IN ('images','state') AND sql IS NOT NULL"
            ):
                dest.execute(row[0])
            for row in selected:
                target = dict(row)
                for field in OPERATIONAL:
                    target[field] = None
                target.update(status="pending", attempts=0, updated_at=now)
                keys = list(target)
                dest.execute(
                    f"INSERT INTO images ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
                    [target[k] for k in keys],
                )
            dest.execute(
                "INSERT INTO state VALUES (?,?,?)",
                ("stage_scope", "bounded pending subset; no active training admission", now),
            )
    for item in source_refs:
        if ref(item["path"]) != item:
            raise RuntimeError("Source index changed during staging; inspect before launching")
    snapshot = root / "selected-source-records.json"
    snapshot.write_text(json.dumps(selected, indent=2, allow_nan=False) + "\n")
    code = root / "source"
    code.mkdir()
    copies = []
    for path in [downloader, downloader.with_name("config.py")]:
        target = code / path.name
        shutil.copyfile(path, target)
        copies.append({"original": ref(path), "copy": ref(target)})
    plan = {
        "status": "frozen-bounded-new-local-Commons-download-selection",
        "root": str(root),
        "source_index": source_refs,
        "driver": ref(__file__),
        "selection": ref(snapshot),
        "initial_database": ref(database),
        "downloader_sources": copies,
        "config_path": str(downloader.with_name("config.toml").resolve()),
        "selected_images": len(selected),
        "selected_bytes": used,
        "byte_budget": byte_budget,
        "local_reserve_gib": reserve_gib,
        "maximum_images": max_images,
        "workers": 2,
        "requests_per_second": 0.25,
        "selection_policy": "Pending/category/eligible, canonical free_license, min2048 side/max120MP/max256MiB; unique SHA1 absent from downloaded archive; deterministic page-ID hash order, greedy byte cap; HTTPS Wikimedia upload URLs only.",
        "scope": "New local-only originals plus full attribution records. Original archive/index remain read-only. No preparation, training membership, protected split or active experiment changes. Later independent integrity, duplicate/protected-scene/content screening and a separate data study remain required.",
    }
    (root / "plan.json").write_text(json.dumps(plan, indent=2, allow_nan=False) + "\n")
    handle.close()
    print(
        json.dumps(
            {
                k: plan[k]
                for k in (
                    "root",
                    "selected_images",
                    "selected_bytes",
                    "byte_budget",
                    "local_reserve_gib",
                )
            }
        )
    )


def run(root):
    root = writable_path(root)
    plan = read(root / "plan.json")
    if root != Path(plan["root"]):
        raise ValueError("Staged download root differs from its frozen plan")
    if ref(__file__) != plan["driver"] or ref(plan["selection"]["path"]) != plan["selection"]:
        raise ValueError("Staged source/selection changed")
    for item in plan["downloader_sources"]:
        if ref(item["copy"]["path"]) != item["copy"]:
            raise ValueError("Frozen downloader source changed")
    selected = read(plan["selection"]["path"])
    with connect(root / "quality_images.sqlite3", readonly=True) as db:
        current = {r["page_id"]: dict(r) for r in db.execute("SELECT * FROM images")}
    if len(current) != len(selected) or sum(r["byte_size"] for r in selected) > plan["byte_budget"]:
        raise ValueError("Staged image/byte coverage differs")
    for row in selected:
        if any(row[k] != current[row["page_id"]][k] for k in row.keys() - OPERATIONAL):
            raise ValueError("Immutable attribution/source fields changed")
    handle = lock_downloads()
    os.set_inheritable(handle.fileno(), True)
    os.nice(10)
    env = dict(os.environ, PYTHONPATH=str(root / "source"))
    command = [
        sys.executable,
        "-P",
        str(root / "source/download_quality_images.py"),
        "download",
        "--root",
        str(root),
        "--config",
        plan["config_path"],
        "--workers",
        str(plan["workers"]),
        "--requests-per-second",
        str(plan["requests_per_second"]),
        "--reserve-gib",
        str(plan["local_reserve_gib"]),
        "--download-limit",
        str(plan["selected_images"]),
        "--log-file",
        str(root / "download.log"),
    ]
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["select", "run"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--source", type=Path, default=Path("/mnt/external/qi"))
    parser.add_argument(
        "--downloader",
        type=Path,
        default=Path("/home/dllu/proj/pupphoto/download_quality_images.py"),
    )
    parser.add_argument("--budget-gib", type=float, default=16)
    parser.add_argument("--max-images", type=int, default=5000)
    parser.add_argument("--reserve-gib", type=float, default=224)
    args = parser.parse_args()
    if args.mode == "select":
        select(
            args.root,
            args.source,
            args.downloader,
            byte_budget=int(args.budget_gib * GIB),
            max_images=args.max_images,
            reserve_gib=args.reserve_gib,
        )
    else:
        run(args.root)
