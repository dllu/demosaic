"""Share verified checkpoint copies in completed evaluations; preserve all paths/bytes.

Only report-owned content-addressed snapshots are eligible. Original model
archives and all active input directories/inodes remain physically separate.
"""

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import time
from collections import defaultdict
from pathlib import Path

import psutil

from demosaic.safety import writable_path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def props(path):
    s = Path(path).stat()
    return {
        "device": s.st_dev,
        "inode": s.st_ino,
        "size": s.st_size,
        "allocated": s.st_blocks * 512,
        "mode": s.st_mode,
        "mtime_ns": s.st_mtime_ns,
        "uid": s.st_uid,
        "gid": s.st_gid,
        "links": s.st_nlink,
    }


def inode(properties):
    return properties["device"], properties["inode"]


def check_refs(items):
    for item in items:
        require(ref(item["path"]) == item, f"Protected file changed: {item['path']}")


def collect_active(plans):
    """Bind existing immutable inputs/sources and reserve whole input directories."""
    references, directories, inodes = {}, set(), set()
    for filename in plans:
        value = read(filename)
        references[str(Path(filename).resolve())] = ref(filename)
        for item in value.get("inputs", []):
            references[item["path"]] = item
        for path, digest in value.get("frozen_files", {}).items():
            references[path] = {"path": path, "sha256": digest}
    check_refs(references.values())
    for path in references:
        p = Path(path)
        if p.is_file():
            directories.add(p.parent)
            inodes.add(inode(props(p)))
    return list(references.values()), directories, inodes


def prepare(root, evaluation, inventory, active_plans):
    root, evaluation = writable_path(root), writable_path(evaluation)
    require(not root.exists(), "Use a fresh consolidation root")
    protected, directories, protected_inodes = collect_active(active_plans)
    # Stat-only enumeration: never read or modify these original archives.
    archives = {}
    for name in ("models", "runs", "benchmarks", "references"):
        for path in (evaluation.parent / name).rglob("*.pt"):
            if path.is_file() and not path.is_symlink():
                archives[str(path)] = props(path)
    archive_inodes = {inode(value) for value in archives.values()}
    files, artifact_dirs, skipped = {}, set(), []
    for group in read(inventory)["candidate_groups"]:
        for candidate in group["files"]:
            path = Path(candidate["path"])
            if path.suffix != ".pt" or path.parent.name != "weights":
                continue
            if not path.is_relative_to(evaluation) or path.resolve() != path:
                continue
            match = re.fullmatch(r"weights-([0-9a-f]{64})\.pt", path.name)
            if match is None or any(path.is_relative_to(folder) for folder in directories):
                continue
            value = props(path)
            if inode(value) in archive_inodes | protected_inodes:
                continue
            if value["uid"] != os.getuid() or not stat.S_ISREG(value["mode"]):
                continue
            reports = [path.parent.parent / name for name in ("summary.json", "report.json")]
            report = next((p for p in reports if p.exists()), None)
            if report is None:
                continue
            data = read(report)
            if "native_crops" not in data or not any(
                model.get("sha256") == match[1] and model.get("snapshot") == str(path)
                for model in data.get("models", [])
            ):
                skipped.append(str(path))
                continue
            files[str(path)] = {"sha256": match[1], "properties": value}
            artifact_dirs.add(path.parent.parent)
    by_digest = defaultdict(list)
    for path, value in files.items():
        by_digest[value["sha256"]].append(path)
    groups = []
    for digest, paths in by_digest.items():
        unique = defaultdict(list)
        for path in paths:
            unique[inode(files[path]["properties"])].append(path)
        if len(unique) < 2:
            continue
        # Prefer a previously immutable/shared evaluation copy. Never an archive.
        ordered = sorted(
            unique.values(),
            key=lambda p: (bool(files[p[0]]["properties"]["mode"] & 0o222), -len(p), p[0]),
        )
        canonical = ordered[0][0]
        targets = [
            p[0] for p in ordered[1:] if len(p) == 1 and files[p[0]]["properties"]["links"] == 1
        ]
        if targets:
            groups.append({"sha256": digest, "canonical": canonical, "targets": targets})
    require(bool(groups), "No eligible completed snapshot copies")
    unchanged = []
    for folder in sorted(artifact_dirs):
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".png", ".md"}:
                unchanged.append(ref(path))
    root.mkdir(parents=True)
    plan = {
        "driver": ref(__file__),
        "evaluation": str(evaluation),
        "inventory": ref(inventory),
        "active_plans": [str(Path(p).resolve()) for p in active_plans],
        "protected": protected,
        "original_archive_properties": archives,
        "files": files,
        "groups": groups,
        "unchanged_report_metric_native_artifacts": unchanged,
        "expected_reclaimed_allocated_bytes": sum(
            files[p]["properties"]["allocated"] for g in groups for p in g["targets"]
        ),
        "skipped_unbound_report_snapshots": skipped,
        "scope": "Owned completed report checkpoint copies only. Full SHA verification required before replacement. All target paths/bytes/hashes retained; shared copies become read-only. Original archives, active-input directories/inodes, images, crops, metrics, training, evaluation and downloading remain untouched.",
    }
    save(root / "plan.json", plan)
    return plan


def replace_verified_copy(path, source, digest, expected):
    """Retain the old inode until the verified atomic replacement succeeds."""
    path, source = Path(path), Path(source)
    require(
        props(path) == expected and expected["links"] == 1, "Target snapshot properties changed"
    )
    require(source.stat().st_mode & 0o222 == 0, "Canonical snapshot must be immutable")
    require(path.stat().st_dev == source.stat().st_dev, "Snapshots use different filesystems")
    require(sha(path) == digest and sha(source) == digest, "Snapshot checksum differs")
    temporary = path.with_name(path.name + f".new-link-{os.getpid()}")
    backup = path.with_name(path.name + f".old-link-{os.getpid()}")
    require(not temporary.exists() and not backup.exists(), "Replacement temporary path exists")
    os.link(path, backup)
    try:
        os.link(source, temporary)
        require(temporary.samefile(source), "Temporary link has wrong inode")
        os.replace(temporary, path)
        require(path.samefile(source) and sha(path) == digest, "Replacement verification failed")
    except BaseException:
        os.replace(backup, path)
        raise
    finally:
        temporary.unlink(missing_ok=True)
    backup.unlink()


def apply(root):
    root = writable_path(root)
    plan = read(root / "plan.json")
    require(ref(__file__) == plan["driver"], "Consolidation driver changed")
    require(not (root / "result.json").exists(), "Consolidation already completed")
    evaluation = writable_path(plan["evaluation"])
    check_refs(plan["protected"])
    check_refs(plan["unchanged_report_metric_native_artifacts"])
    for path, properties in plan["original_archive_properties"].items():
        require(props(path) == properties, "Original archive metadata changed")
    protected_directories = {Path(item["path"]).parent for item in plan["protected"]}
    excluded_inodes = {inode(value) for value in plan["original_archive_properties"].values()}
    excluded_inodes.update(inode(props(item["path"])) for item in plan["protected"])
    for group in plan["groups"]:
        for filename in [group["canonical"], *group["targets"]]:
            path = Path(filename)
            require(
                path == path.resolve()
                and path.is_relative_to(evaluation)
                and path.parent.name == "weights"
                and path.name == f"weights-{group['sha256']}.pt"
                and not any(path.is_relative_to(folder) for folder in protected_directories)
                and inode(props(path)) not in excluded_inodes,
                "Snapshot path escapes eligible inactive evaluation storage",
            )
    # No current project's writer may target a completed evaluation directory.
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            if process.pid != os.getpid():
                require(
                    not any(
                        plan["evaluation"] + "/" in argument
                        for argument in process.info["cmdline"] or []
                    ),
                    "A process still references the evaluation tree",
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    with (root / "claim").open("x") as claim:
        claim.write(str(os.getpid()))
    cache = Path(plan["evaluation"]) / ".checkpoint-cache"
    cache.mkdir(exist_ok=True)
    changes = []
    for group_index, group in enumerate(plan["groups"], 1):
        require(psutil.virtual_memory().available >= 24 * 2**30, "Less than24GiB available RAM")
        digest, source = group["sha256"], Path(group["canonical"])
        with (cache / f"{digest}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(
                props(source) == plan["files"][str(source)]["properties"],
                "Canonical snapshot changed",
            )
            # Validate the entire group before its first mutation.
            for path in [str(source), *group["targets"]]:
                require(
                    props(path) == plan["files"][path]["properties"] and sha(path) == digest,
                    "Snapshot changed or has corrupt bytes",
                )
            source.chmod(0o444)
            for filename in group["targets"]:
                replace_verified_copy(
                    filename, source, digest, plan["files"][filename]["properties"]
                )
                change = {
                    "path": filename,
                    "canonical": str(source),
                    "sha256": digest,
                    "old_properties": plan["files"][filename]["properties"],
                    "new_properties": props(filename),
                }
                changes.append(change)
                with (root / "changes.jsonl").open("a") as stream:
                    stream.write(json.dumps(change) + "\n")
        save(
            root / "status.json",
            {
                "status": "consolidating-completed-evaluation-snapshots",
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "groups_done": group_index,
                "replacements": len(changes),
                "updated_unix": time.time(),
            },
        )
        print(
            json.dumps(
                {
                    "replacements": len(changes),
                    "expected_total": sum(len(g["targets"]) for g in plan["groups"]),
                }
            ),
            flush=True,
        )
    check_refs(plan["protected"])
    check_refs(plan["unchanged_report_metric_native_artifacts"])
    for path, properties in plan["original_archive_properties"].items():
        require(props(path) == properties, "Original archive metadata changed")
    result = {
        "status": "completed-byte-preserving-owned-evaluation-snapshot-consolidation",
        "plan": ref(root / "plan.json"),
        "driver": ref(__file__),
        "replacements": len(changes),
        "checkpoint_digests": len(plan["groups"]),
        "reclaimed_allocated_bytes": sum(x["old_properties"]["allocated"] for x in changes),
        "protected_files_checked": len(plan["protected"]),
        "report_metric_native_files_unchanged": len(
            plan["unchanged_report_metric_native_artifacts"]
        ),
        "original_archives_unchanged": len(plan["original_archive_properties"]),
        "scope": plan["scope"],
    }
    save(root / "result.json", result)
    save(
        root / "status.json",
        {
            "status": result["status"],
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "result": ref(root / "result.json"),
            "updated_unix": time.time(),
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "apply"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--evaluation", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--active-plan", action="append", type=Path, default=[])
    args = parser.parse_args()
    os.nice(15)
    with writable_path(args.root.parent / "evaluation-snapshot-consolidation.lock").open(
        "a"
    ) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "prepare":
            result = prepare(args.root, args.evaluation, args.inventory, args.active_plan)
            print(
                json.dumps(
                    {
                        "groups": len(result["groups"]),
                        "replacements": sum(len(g["targets"]) for g in result["groups"]),
                        "expected_reclaimed_GiB": result["expected_reclaimed_allocated_bytes"]
                        / 2**30,
                        "protected": len(result["protected"]),
                        "unchanged_artifacts": len(
                            result["unchanged_report_metric_native_artifacts"]
                        ),
                    }
                )
            )
        else:
            print(json.dumps(apply(args.root)))


if __name__ == "__main__":
    main()
