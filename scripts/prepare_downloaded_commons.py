"""Prepare frozen, already-downloaded Commons arrivals into quarantined 4x/8x caches."""

import argparse
import fcntl
import json
import os
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path

import psutil
from prepare_commons_local_stage import PREPARE_FIELDS, audit_caches
from stage_commons_local import OPERATIONAL
from train_directional_interval_trial import guard, read, ref, save, sha

from demosaic.prepare import free_license
from demosaic.safety import writable_path


def select(records, known, limit=0):
    """Metadata/identity selection only; no model, image-content or quality score."""
    reasons, chosen, seen = Counter(), [], set()
    for row in sorted(records, key=lambda r: r["sha1_hex"]):
        identity = row["sha1_hex"]
        reason = (
            "already_prepared"
            if identity in known
            else "duplicate_SHA1"
            if identity in seen
            else "license_not_in_existing_whitelist"
            if not free_license(row["license"])
            else "geometry"
            if min(row["width"], row["height"]) < 2048 or row["width"] * row["height"] > 120_000_000
            else None
        )
        if len(identity) != 40 or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("Invalid canonical source identity")
        if row["status"] != "downloaded" or row["downloaded_bytes"] != row["byte_size"]:
            raise ValueError("Input arrivals must be completed downloads")
        if reason:
            reasons[reason] += 1
        else:
            chosen.append(row)
            seen.add(identity)
    if limit:
        reasons["engineering_limit"] += max(0, len(chosen) - limit)
        chosen = chosen[:limit]
    if not chosen:
        raise ValueError("No new licensed geometry-eligible arrivals")
    return chosen, dict(reasons)


def payload(records):
    return sum((r["width"] // f) * (r["height"] // f) * 6 for r in records for f in (4, 8))


def resources(plan, *, additional_bytes=0):
    validate_disk_reserve(plan["reserve_gib"])
    if psutil.virtual_memory().available < plan["minimum_available_gib"] * 2**30:
        raise RuntimeError("Available memory is below the declared preparation reserve")
    if shutil.disk_usage(plan["root"]).free < plan["reserve_gib"] * 2**30 + additional_bytes:
        raise RuntimeError("External disk space is below the declared preparation reserve")


def validate_disk_reserve(reserve_gib):
    if type(reserve_gib) is not int or reserve_gib < 256:
        raise ValueError("External disk reserve must be an integer of at least256GiB")


def freeze(records_path, prior_paths, references, output, *, limit=0, reserve_gib=560):
    validate_disk_reserve(reserve_gib)
    repo = Path(__file__).resolve().parents[1]
    root = writable_path(output)
    if not root.is_relative_to(Path("/mnt/external/demosaic")) or root.exists():
        raise ValueError("Use a fresh external demosaic preparation root")
    if limit < 0:
        raise ValueError("A nonnegative fixture limit is required")
    inputs = [ref(records_path), *(ref(p) for p in prior_paths), ref(references)]
    protected = read(references)
    for row in protected["protected"]:
        cache = references.parent / row["screen_cache"]
        assert sha(cache) == row["screen_sha256"]
        inputs.append(ref(cache))
        if "manifest" in row:
            assert sha(row["manifest"]) == row["manifest_sha256"]
            inputs.append(ref(row["manifest"]))
    known = set()
    for path in prior_paths:
        known.update(json.loads(line)["id"] for line in path.read_text().splitlines())
    selected, excluded = select(read(records_path), known, limit)
    estimated = payload(selected)
    if shutil.disk_usage(root.parent).free < reserve_gib * 2**30 + estimated + 4 * 2**30:
        raise RuntimeError("Complete two-scale payload plus4GiB margin would consume the reserve")
    root.mkdir(parents=True)
    work = root / "work"
    files = list((repo / "src/demosaic").glob("*.py"))
    files += [
        repo / "scripts" / name
        for name in [
            Path(__file__).name,
            "prepare_commons_local_stage.py",
            "stage_commons_local.py",
            "screen_commons_protected.py",
            "train_directional_interval_trial.py",
        ]
    ]
    for source in files:
        destination = work / source.relative_to(repo)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    save(root / "selected-source-records.json", selected)
    plan = {
        "root": str(root),
        "work": str(work),
        "source": "/mnt/external/qi",
        "selection": ref(root / "selected-source-records.json"),
        "references": str(references),
        "arrival_records": ref(records_path),
        "prior_manifests": [ref(p) for p in prior_paths],
        "selected_originals": len(selected),
        "selection_exclusions": excluded,
        "engineering_only": bool(limit),
        "estimated_cache_bytes": estimated,
        "reserve_gib": reserve_gib,
        "minimum_available_gib": 48,
        "stable_memory_seconds": 0 if limit else 60,
        "resource_wait_seconds": 3600,
        "maximum_wall_seconds": 21600,
        "python": str((repo / ".venv/bin/python3").absolute()),
        "workers": 1,
        "worker": ref(work / "scripts" / Path(__file__).name),
        "download_lock": str(repo / ".cache/commons-qi-download.lock"),
        "inputs": list({r["path"]: r for r in inputs}.values()),
        "frozen_files": {str(p): sha(p) for p in work.rglob("*") if p.is_file()},
        "scope": "Already-downloaded, metadata/identity-selected new Commons originals only. Original/archive index read-only. Existing ingestion/color/area and protected screening operators unchanged; one CPU worker, hidden CUDA. Complete4x/8x caches remain quarantine/reserved; duplicate/content/known-series review and a separate coupled data recipe are still required. No active training/evaluation membership or model-quality claim.",
    }
    plan["inputs"].append(plan["selection"])
    guard(plan)
    save(root / "plan.json", plan)
    return plan


def verify_originals(plan):
    selected, source = read(plan["selection"]["path"]), Path(plan["source"]).resolve()
    # Release the read transaction before decoding. No long-lived source WAL pin.
    with sqlite3.connect(f"file:{source / 'quality_images.sqlite3'}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("BEGIN")
        for row in selected:
            actual = db.execute(
                "SELECT * FROM images WHERE page_id=?", (row["page_id"],)
            ).fetchone()
            if actual is None or any(
                actual[k] != v for k, v in row.items() if k not in OPERATIONAL
            ):
                raise ValueError("Pinned original identity/attribution differs from the live index")
    records, stamps = [], []
    for row in selected:
        resources(plan)
        path = (source / row["download_path"]).resolve()
        if not path.is_relative_to(source) or path == source:
            raise ValueError("Original path escapes the archive")
        before = path.stat()
        import hashlib

        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha1").hexdigest()
        if before.st_size != row["byte_size"] or digest != row["sha1_hex"]:
            raise ValueError("Original byte count or publisher SHA1 differs")
        stamps.append(
            {
                "path": str(path),
                "bytes": before.st_size,
                "mtime_ns": before.st_mtime_ns,
                "SHA1": digest,
            }
        )
        records.append({k: row[k] for k in PREPARE_FIELDS})
    return records, stamps


def run(plan_path):
    plan = read(plan_path)
    root = Path(plan["root"])
    assert root == plan_path.resolve().parent and ref(__file__) == plan["worker"]
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    guard(plan)
    os.nice(10)
    with (root / "worker.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", status)
        print(json.dumps({"status": value}), flush=True)

    try:
        record("waiting-for-stable-preparation-resources")
        since, deadline = None, time.monotonic() + plan["resource_wait_seconds"]
        while True:
            if time.monotonic() > deadline:
                raise RuntimeError("Stable preparation resource wait exhausted")
            try:
                resources(plan, additional_bytes=plan["estimated_cache_bytes"] + 4 * 2**30)
            except RuntimeError:
                since = None
            else:
                since = time.monotonic() if since is None else since
                if time.monotonic() - since >= plan["stable_memory_seconds"]:
                    break
            time.sleep(5)
        with Path(plan["download_lock"]).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            guard(plan)
            record("verifying-all-downloaded-originals-and-attribution")
            records, stamps = verify_originals(plan)
            import torch
            from screen_commons_protected import screen

            from demosaic import prepare

            torch.set_num_threads(1)
            assert not torch.cuda.is_initialized()
            output = root / "work/outputs"
            output.mkdir(exist_ok=False)
            manifest = output / "selection.jsonl"
            manifest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
            save(output / "original-integrity.json", stamps)
            original = prepare.prepare_one

            def guarded(*args, **kwargs):
                resources(plan)
                return original(*args, **kwargs)

            prepare.prepare_one = guarded
            try:
                for factor in (4, 8):
                    record(f"preparing-quarantined-{factor}x", originals=len(records))
                    prepare.prepare_commons(
                        Path(plan["source"]),
                        output / f"prepared{factor}",
                        factor=factor,
                        min_size=2048 // factor,
                        workers=1,
                        selection_manifest=manifest,
                    )
            finally:
                prepare.prepare_one = original
            resources(plan)
            record("auditing-all-cache-bytes-and-cross-scale-area")
            audit = audit_caches(output, records)
            save(output / "cache-audit.json", audit)
            resources(plan)
            record("screening-cached-protected-scenes-and-GFX-family")
            screening = screen(
                output / "prepared8/manifest.jsonl",
                Path(plan["references"]),
                Path(plan["source"]),
                output / "protected-screen",
            )
            candidates = [
                json.loads(line)
                for line in Path(screening["cleared_manifest"]).read_text().splitlines()
            ]
            for row in candidates:
                row["split"] = "quarantine" if row["split"] == "train" else "reserved"
            candidate_path = output / "screened-candidates.jsonl"
            candidate_path.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in candidates)
            )
            for stamp in stamps:
                stat = Path(stamp["path"]).stat()
                assert (stat.st_size, stat.st_mtime_ns) == (stamp["bytes"], stamp["mtime_ns"])
            guard(plan)
            assert not torch.cuda.is_initialized()
            receipt = {
                "plan": ref(plan_path),
                "original_integrity": ref(output / "original-integrity.json"),
                "selection": ref(manifest),
                "cache_audit": ref(output / "cache-audit.json"),
                "screening": ref(output / "protected-screen/summary.json"),
                "candidates": ref(candidate_path),
                "candidate_counts": dict(Counter(r["split"] for r in candidates)),
                "CUDA_initialized": False,
                "training_admission": False,
                "scope": plan["scope"],
            }
            save(output / "receipt.json", receipt)
            record(
                "prepared-and-screened-downloaded-quarantine-awaiting-independent-review",
                receipt=ref(output / "receipt.json"),
            )
    except BaseException as error:
        record("failed-downloaded-Commons-preparation-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("freeze")
    for name in ["records", "references", "output"]:
        command.add_argument("--" + name, type=Path, required=True)
    command.add_argument("--prior", type=Path, action="append", required=True)
    command.add_argument("--limit", type=int, default=0)
    command.add_argument("--reserve-gib", type=int, default=560)
    command = sub.add_parser("run")
    command.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        result = freeze(
            args.records.resolve(),
            [p.resolve() for p in args.prior],
            args.references.resolve(),
            args.output.resolve(),
            limit=args.limit,
            reserve_gib=args.reserve_gib,
        )
        print(
            {
                "plan": ref(Path(result["root"]) / "plan.json"),
                "selected": result["selected_originals"],
                "payload_GiB": result["estimated_cache_bytes"] / 2**30,
            }
        )
    else:
        run(args.plan.resolve())
