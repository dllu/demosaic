"""Reconcile completed local originals, then resume the existing Commons downloader.

The archive-write exception is narrow: publish new verified originals and update
their operational index fields. Never overwrite an existing archive image.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import psutil

from demosaic.safety import writable_path

GIB = 2**30


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path, algorithm="sha256"):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": digest(path)}


def connection(path, *, readonly=True):
    db = (
        sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
        if readonly
        else sqlite3.connect(path)
    )
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("PRAGMA busy_timeout=60000")
    return db


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def validate_refs(items):
    for item in items:
        require(ref(item["path"]) == item, f"Frozen handoff input changed: {item['path']}")


def archive_root(path):
    path = Path(path).resolve()
    # PROMPT explicitly authorizes resuming the QI downloader. Preserve the
    # general read-only safety guard; this operator publishes only new files.
    return path if path == Path("/mnt/external/qi") else writable_path(path)


def verify_file(path, sha1, size):
    require(
        Path(path).is_file() and Path(path).stat().st_size == size, "Original byte count differs"
    )
    require(digest(path, "sha1") == sha1, "Original SHA1 differs")


def publish_new_copy(source, destination, sha1, size):
    """Create a verified new archive entry; existing entries are read-only."""
    source, destination = Path(source), Path(destination)
    if destination.exists():
        verify_file(destination, sha1, size)
        verify_file(source, sha1, size)
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=".local-handoff-", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        observed, count = hashlib.sha1(), 0
        with os.fdopen(descriptor, "wb") as writer, source.open("rb") as reader:
            while block := reader.read(4 * 2**20):
                observed.update(block)
                count += len(block)
                writer.write(block)
            writer.flush()
            os.fsync(writer.fileno())
        require(count == size and observed.hexdigest() == sha1, "Source copy checksum differs")
        verify_file(temporary, sha1, size)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            verify_file(destination, sha1, size)
            return False
        try:
            verify_file(destination, sha1, size)
        except BaseException:
            if destination.exists() and destination.samefile(temporary):
                destination.unlink()
            raise
        return True
    finally:
        temporary.unlink(missing_ok=True)


def load_downloader(path):
    sys.path.insert(0, str(Path(path).parent))
    spec = importlib.util.spec_from_file_location("frozen_commons_downloader", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reconcile(stage, archive, output, selected, operational, downloader, *, reserve_gib=608):
    stage, archive, output = Path(stage).resolve(), archive_root(archive), writable_path(output)
    require(
        stage != archive and not stage.is_relative_to(archive),
        "Separate local and archive roots required",
    )
    selected = {row["page_id"]: row for row in selected}
    source_db = stage / "quality_images.sqlite3"
    source_ref = ref(source_db)
    with connection(source_db) as db:
        local = {row["page_id"]: dict(row) for row in db.execute("SELECT * FROM images")}
    require(local.keys() == selected.keys(), "Local index membership differs")
    require(
        all(row["status"] in {"downloaded", "failed"} for row in local.values()),
        "Local sources remain unfinished",
    )
    index = archive / "quality_images.sqlite3"
    with connection(index) as db:
        before_counts = dict(db.execute("SELECT status,COUNT(*) FROM images GROUP BY status"))
        previous = {
            key: dict(db.execute("SELECT * FROM images WHERE page_id=?", (key,)).fetchone() or {})
            for key in selected
        }
        require(
            not db.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall(),
            "Unexpected archive triggers",
        )
    for key, original in selected.items():
        require(
            previous[key]
            and all(
                local[key][field] == previous[key].get(field) == value
                for field, value in original.items()
                if field not in operational
            ),
            "Immutable source/attribution fields differ",
        )
        require(
            previous[key]["status"] in {"pending", "downloaded"}, "Unexpected archive source status"
        )
    completed = [row for row in local.values() if row["status"] == "downloaded"]
    payload = sum(row["byte_size"] for row in completed)
    require(
        reserve_gib >= 608
        and shutil.disk_usage(archive).free >= reserve_gib * GIB + payload + 8 * GIB,
        "Insufficient archive copy/download reserve",
    )
    output.mkdir(parents=True, exist_ok=True)
    save(output / "archive-selected-rows-before.json", list(previous.values()))
    paths, copied, reused = {}, 0, 0
    for row in completed:
        record = downloader.DownloadRecord(
            **{
                field: row[field]
                for field in (
                    "page_id",
                    "title",
                    "original_url",
                    "byte_size",
                    "mime_type",
                    "sha1_hex",
                )
            }
        )
        target = downloader.destination_path(archive, record)
        source = stage / row["download_path"]
        require(
            source.resolve().is_relative_to(stage)
            and target.resolve() == target
            and target.is_relative_to(archive / "images"),
            "Original path escapes its root",
        )
        require(
            shutil.disk_usage(archive).free >= reserve_gib * GIB + row["byte_size"],
            "Archive reserve reached during copying",
        )
        fresh = publish_new_copy(source, target, row["sha1_hex"], row["byte_size"])
        copied += int(fresh)
        reused += int(not fresh)
        paths[row["page_id"]] = str(target.relative_to(archive))
    now = datetime.now(UTC).isoformat()
    updated = 0
    db = connection(index, readonly=False)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        for row in completed:
            key = row["page_id"]
            actual = dict(db.execute("SELECT * FROM images WHERE page_id=?", (key,)).fetchone())
            require(actual == previous[key], "Archive row changed before its transaction")
            if actual["status"] == "downloaded":
                require(
                    actual["download_path"] == paths[key]
                    and actual["downloaded_bytes"] == row["byte_size"],
                    "Existing downloaded index row differs",
                )
                continue
            cursor = db.execute(
                "UPDATE images SET status='downloaded',download_path=?,downloaded_bytes=?,http_etag=?,http_last_modified=?,last_error=NULL,downloaded_at=?,download_started_at=?,attempts=?,updated_at=? WHERE page_id=? AND status='pending' AND sha1_hex=?",
                (
                    paths[key],
                    row["byte_size"],
                    row["http_etag"],
                    row["http_last_modified"],
                    row["downloaded_at"],
                    row["download_started_at"],
                    actual["attempts"] + row["attempts"],
                    now,
                    key,
                    row["sha1_hex"],
                ),
            )
            require(cursor.rowcount == 1, "Archive row update coverage differs")
            updated += 1
        require(db.total_changes == updated, "Unexpected archive row changes")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    with connection(index) as db:
        after_counts = dict(db.execute("SELECT status,COUNT(*) FROM images GROUP BY status"))
        after = [
            dict(db.execute("SELECT * FROM images WHERE page_id=?", (key,)).fetchone())
            for key in selected
        ]
    expected_counts = Counter(before_counts)
    expected_counts["pending"] -= updated
    expected_counts["downloaded"] += updated
    require(
        {k: v for k, v in expected_counts.items() if v} == after_counts,
        "Archive status-count changes differ",
    )
    for row in after:
        key = row["page_id"]
        require(
            all(
                row[field] == value
                for field, value in selected[key].items()
                if field not in operational
            ),
            "Archive attribution changed",
        )
        if local[key]["status"] == "downloaded":
            require(
                row["status"] == "downloaded" and row["download_path"] == paths[key],
                "Reconciled row missing",
            )
        else:
            require(row == previous[key], "Failed local source changed its archive row")
    require(ref(source_db) == source_ref, "Local source index changed")
    save(output / "archive-selected-rows-after.json", after)
    result = {
        "status": "reconciled-verified-local-originals-into-archive",
        "local_index": source_ref,
        "new_files": copied,
        "existing_files_verified": reused,
        "index_rows_updated": updated,
        "downloaded_sources": len(completed),
        "local_failed_sources": len(local) - len(completed),
        "payload_bytes": payload,
        "counts_before": before_counts,
        "counts_after": after_counts,
        "rows_before": ref(output / "archive-selected-rows-before.json"),
        "rows_after": ref(output / "archive-selected-rows-after.json"),
        "training_admission": False,
        "scope": "New verified archive files and selected operational index fields only. Existing archive images, local originals/index, attribution, archive state keys, active corpora and model recipes preserved.",
    }
    save(output / "receipt.json", result)
    return result


def freeze(stage, preparation, root, archive, downloader):
    # Import only during freeze; the waiting worker does not load Torch.
    from stage_commons_local import OPERATIONAL

    stage, preparation, root = (
        Path(stage).resolve(),
        Path(preparation).resolve(),
        writable_path(root),
    )
    archive = archive_root(archive)
    require(not root.exists(), "Use a fresh handoff root")
    stage_plan, prep_plan = read(stage / "plan.json"), read(preparation / "plan.json")
    require(
        Path(stage_plan["root"]) == stage == Path(prep_plan["stage"]),
        "Stage/preparation identities differ",
    )
    selected = read(stage_plan["selection"]["path"])
    require(
        ref(stage_plan["selection"]["path"]) == stage_plan["selection"],
        "Selected attribution changed",
    )
    require(
        shutil.disk_usage(archive).free
        >= 608 * GIB + sum(row["byte_size"] for row in selected) + 8 * GIB,
        "Insufficient future handoff space",
    )
    root.mkdir(parents=True)
    source = root / "source"
    source.mkdir()
    copies = []
    for path in [Path(__file__), Path(downloader), Path(downloader).with_name("config.py")]:
        target = source / path.name
        shutil.copyfile(path, target)
        copies.append(ref(target))
    inputs = [ref(stage / name) for name in ("plan.json", "launch.json")]
    prep_owner_path = preparation / "launch.json"
    if not prep_owner_path.exists():
        prep_owner_path = preparation / "status.json"
        require(
            read(prep_owner_path)["status"]
            == "prepared-and-screened-quarantine-awaiting-independent-review",
            "Completed preparer identity missing",
        )
    inputs.extend(
        [
            stage_plan["selection"],
            ref(preparation / "plan.json"),
            ref(prep_owner_path),
            ref(Path(__file__).parents[1] / "src/demosaic/safety.py"),
        ]
    )
    archive_files = [ref(archive / "quality_images.sqlite3")]
    wal = archive / "quality_images.sqlite3-wal"
    if wal.exists():
        archive_files.append(ref(wal))
    plan = {
        "root": str(root),
        "stage": str(stage),
        "preparation": str(preparation),
        "archive": str(archive),
        "worker": ref(source / Path(__file__).name),
        "inputs": inputs,
        "archive_index_before": archive_files,
        "sources": copies,
        "operational_fields": sorted(OPERATIONAL),
        "download_owner": read(stage / "launch.json")["owner"],
        "preparation_owner": read(prep_owner_path)["owner"],
        "download_lock": str(Path(__file__).parents[1] / ".cache/commons-qi-download.lock"),
        "config_path": str(Path("/home/dllu/proj/pupphoto/config.toml")),
        "python": sys.executable,
        "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
        "wait_seconds": 14400,
        "workers": 2,
        "requests_per_second": 0.25,
        "reserve_gib": 608,
        "download_limit": 10000,
        "scope": "After exact local downloader/preparer exits and successful preparation, reconcile originals and resume the unchanged download-only CLI with a608GiB reserve/10,000-file limit. No source-photo modification, network duplication or active training admission.",
    }
    save(root / "plan.json", plan)
    return plan


def run(plan_path):
    plan = read(plan_path)
    root = writable_path(plan["root"])
    require(
        root == Path(plan_path).resolve().parent and ref(__file__) == plan["worker"],
        "Handoff worker/plan identity differs",
    )
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "Handoff must hide CUDA")
    validate_refs([*plan["inputs"], *plan["sources"], *plan["archive_index_before"]])
    os.nice(10)
    with (root / "claim").open("x") as claim:
        claim.write(str(os.getpid()))
    status = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        save(root / "status.json", status)
        print(json.dumps({"status": state}), flush=True)

    try:
        record("waiting-for-exact-local-download-and-preparation-exits")
        deadline = time.monotonic() + plan["wait_seconds"]
        while alive(plan["download_owner"]) or alive(plan["preparation_owner"]):
            require(time.monotonic() < deadline, "Local handoff wait exceeded its budget")
            time.sleep(20)
        prep_status = read(Path(plan["preparation"]) / "status.json")
        require(
            prep_status["status"] == "prepared-and-screened-quarantine-awaiting-independent-review",
            "Local preparation did not complete successfully",
        )
        validate_refs([prep_status["receipt"]])
        require(
            read(prep_status["receipt"]["path"])["training_admission"] is False,
            "Unexpected local training admission",
        )
        with Path(plan["download_lock"]).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            validate_refs([*plan["inputs"], *plan["sources"], *plan["archive_index_before"]])
            record("reconciling-verified-local-originals-and-attribution")
            downloader_path = Path(plan["worker"]["path"]).with_name("download_quality_images.py")
            downloader = load_downloader(downloader_path)
            selected = read(read(Path(plan["stage"]) / "plan.json")["selection"]["path"])
            result = reconcile(
                Path(plan["stage"]),
                Path(plan["archive"]),
                root / "reconciliation",
                selected,
                set(plan["operational_fields"]),
                downloader,
                reserve_gib=plan["reserve_gib"],
            )
            record(
                "resuming-reconciled-archive-download",
                reconciliation=ref(root / "reconciliation/receipt.json"),
            )
            command = [
                plan["python"],
                "-P",
                str(downloader_path),
                "download",
                "--root",
                plan["archive"],
                "--config",
                plan["config_path"],
                "--workers",
                str(plan["workers"]),
                "--requests-per-second",
                str(plan["requests_per_second"]),
                "--reserve-gib",
                str(plan["reserve_gib"]),
                "--download-limit",
                str(plan["download_limit"]),
                "--log-file",
                str(root / "download.log"),
            ]
            with (root / "download-stdout.log").open("w") as log:
                child = subprocess.Popen(
                    command,
                    env={**os.environ, "PYTHONPATH": str(downloader_path.parent)},
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    pass_fds=(lock.fileno(),),
                    start_new_session=True,
                )
                record(
                    "running-bounded-reconciled-archive-download",
                    child={"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
                )
                code = child.wait()
            require(code == 0, f"Archive downloader exited{code}")
            record(
                "completed-bounded-reconciled-archive-download",
                downloader_exit_code=code,
                imported_sources=result["downloaded_sources"],
            )
    except BaseException as error:
        record("failed-archive-handoff-no-automatic-retry", error=repr(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("freeze")
    for name in ("stage", "preparation", "root", "archive", "downloader"):
        command.add_argument("--" + name, required=True, type=Path)
    command = sub.add_parser("run")
    command.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        plan = freeze(args.stage, args.preparation, args.root, args.archive, args.downloader)
        print(
            json.dumps(
                {"root": plan["root"], "worker": plan["worker"], "reserve_gib": plan["reserve_gib"]}
            )
        )
    else:
        run(args.plan)


if __name__ == "__main__":
    main()
