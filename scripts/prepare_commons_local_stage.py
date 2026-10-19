"""Prepare an isolated local Commons stage after its exact downloader exits.

This produces quarantined 4x/8x caches and protected-scene screening, never a
training corpus. Existing ingestion and screening operators remain unchanged.
"""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path

import psutil

from demosaic.safety import writable_path

GIB = 2**30
PREPARE_FIELDS = [
    "title",
    "page_url",
    "original_url",
    "author",
    "license",
    "license_url",
    "attribution",
    "credit",
    "sha1",
    "sha1_hex",
    "download_path",
    "width",
    "height",
]


def sha(path, algorithm="sha256"):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def alive(identity):
    try:
        process = psutil.Process(identity["pid"])
        return (
            abs(process.create_time() - identity["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def guard(root, *, reserve_gib, additional_bytes=0):
    require(reserve_gib >= 200, "Preparation requires at least200GiB local reserve")
    require(
        shutil.disk_usage(root).free >= reserve_gib * GIB + additional_bytes,
        "Insufficient local free space for preparation and its reserve",
    )
    require(psutil.virtual_memory().available >= 24 * GIB, "Less than24GiB available RAM")


def freeze(stage, root, references, *, reserve_gib=200, recover_from=None, after_status=None):
    repository = Path(__file__).resolve().parents[1]
    stage, root = Path(stage).resolve(), writable_path(root)
    require(
        root.is_relative_to(repository / ".cache")
        or root.is_relative_to(Path("/mnt/external/demosaic")),
        "Use a repository .cache or external demosaic preparation root",
    )
    require(not root.exists(), "Preparation root already exists")
    download = read(stage / "plan.json")
    require(stage == Path(download["root"]), "Download stage moved")
    selection = read(download["selection"]["path"])
    require(ref(download["selection"]["path"]) == download["selection"], "Selection changed")
    payload = sum(
        (row["width"] // factor) * (row["height"] // factor) * 6
        for row in selection
        for factor in (4, 8)
    )
    # All pending original bytes still count, independently of downloader progress.
    guard(
        root.parent,
        reserve_gib=reserve_gib,
        additional_bytes=download["selected_bytes"] + payload + 4 * GIB,
    )
    inputs = [ref(stage / name) for name in ("plan.json", "launch.json")]
    inputs.append(download["selection"])
    inputs.append(ref(references))
    protected = read(references)
    for row in protected["protected"]:
        cache = Path(references).parent / row["screen_cache"]
        require(sha(cache) == row["screen_sha256"], "Protected cache changed")
        inputs.append(ref(cache))
        if "manifest" in row:
            require(sha(row["manifest"]) == row["manifest_sha256"], "Protected manifest changed")
            inputs.append(ref(row["manifest"]))
    inputs = list({item["path"]: item for item in inputs}.values())
    recovery = None
    if recover_from is not None:
        old_root = Path(recover_from).resolve()
        old_plan, old_status = read(old_root / "plan.json"), read(old_root / "status.json")
        require(
            Path(old_plan["root"]) == old_root and Path(old_plan["work"]) == old_root / "work",
            "Failed preparation plan moved",
        )
        require(
            old_status["status"] == "failed-local-preparation" and not alive(old_status["owner"]),
            "Only a failed, exited preparer may supply recovery caches",
        )
        require(
            old_plan["stage"] == str(stage)
            and old_plan["references"] == str(Path(references).resolve()),
            "Recovery source/scene references differ",
        )
        for path, digest in old_plan["frozen_files"].items():
            require(sha(path) == digest, "Failed preparer's frozen source changed")
        recovery = {"root": str(old_root), "factors": {}}
        inputs.extend(ref(old_root / name) for name in ("plan.json", "status.json"))
        for factor in (4, 8):
            partial = Path(old_plan["work"]) / "outputs" / f"prepared{factor}"
            manifest = partial / "manifest.jsonl"
            if not manifest.exists():
                manifest = partial / "manifest.jsonl.tmp"
            if manifest.exists():
                recipe = partial / "recipe.json"
                recovery["factors"][str(factor)] = {
                    "root": str(partial),
                    "manifest": ref(manifest),
                    "recipe": ref(recipe),
                }
                inputs.extend((ref(manifest), ref(recipe)))
    dependency = None
    if after_status is not None:
        after_status = Path(after_status).resolve()
        state = read(after_status)
        dependency = {
            "status_path": str(after_status),
            "owner": state["controller"],
            "plan": state["plan"],
            "success_status": "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review",
        }
        inputs.append(state["plan"])
    root.mkdir()
    work = root / "work"
    sources = list((repository / "src/demosaic").glob("*.py"))
    sources.extend(
        repository / "scripts" / name
        for name in (Path(__file__).name, "stage_commons_local.py", "screen_commons_protected.py")
    )
    frozen = {}
    for source in sources:
        target = work / source.relative_to(repository)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        frozen[str(target)] = sha(target)
    plan = {
        "root": str(root),
        "work": str(work),
        "stage": str(stage),
        "download_owner": read(stage / "launch.json")["owner"],
        "download_lock": str(repository / ".cache/commons-qi-download.lock"),
        "references": str(Path(references).resolve()),
        "inputs": inputs,
        "frozen_files": frozen,
        "estimated_cache_payload_bytes": payload,
        "reserve_gib": reserve_gib,
        "wait_seconds": 10800,
        "workers": 1,
        "scope": "Quarantined 4x/8x caches, full original/cache integrity, rounded-area consistency and protected-scene screening. No existing corpus or original is modified. New holdouts remain reserved; duplicate/content review and a separate data recipe are still required. No training admission.",
    }
    if recovery is not None:
        plan["recovery"] = recovery
        plan["minimum_stable_available_gib"] = 48
        plan["stable_memory_seconds"] = 60
    if dependency is not None:
        plan["after_completion"] = dependency
    save(root / "plan.json", plan)
    return plan


def reuse_partial_caches(plan, output, selection, factor):
    """Copy only manifest-bound atomic arrays; leave the failed run untouched."""
    import numpy as np

    partial = plan.get("recovery", {}).get("factors", {}).get(str(factor))
    if partial is None:
        return {"factor": factor, "copied": 0, "bytes": 0}
    old_plan = read(Path(plan["recovery"]["root"]) / "plan.json")
    for path, digest in old_plan["frozen_files"].items():
        require(sha(path) == digest, "Failed preparer's frozen source changed")
    for key in ("manifest", "recipe"):
        require(ref(partial[key]["path"]) == partial[key], "Partial-cache metadata changed")
    source = Path(partial["root"])
    require(
        read(partial["recipe"]["path"])
        == {
            "version": 1,
            "factor": factor,
            "source": plan["stage"],
            "transfer": "linear-sRGB",
            "dtype": "uint16",
            "selection_manifest_sha256": sha(output / "selection.jsonl"),
        },
        "Partial-cache recipe differs",
    )
    expected = {row["sha1_hex"]: row for row in selection}
    seen, copied_bytes = set(), 0
    destination = output / f"prepared{factor}"
    for line in Path(partial["manifest"]["path"]).read_text().splitlines():
        row = json.loads(line)
        identity = row["id"]
        require(identity in expected and identity not in seen, "Unexpected partial-cache identity")
        seen.add(identity)
        require(
            all(row[key] == value for key, value in expected[identity].items()),
            "Partial-cache attribution differs",
        )
        relative = Path("images") / identity[:2] / f"{identity}.npy"
        require(
            row["cache"] == str(relative)
            and row["bin_factor"] == factor
            and row["color_space"] == "linear-sRGB"
            and row["dtype"] == "uint16",
            "Partial-cache identity/path/recipe differs",
        )
        original = source / relative
        require(
            not original.is_symlink() and original.resolve().is_relative_to(source.resolve()),
            "Partial-cache path escapes its source",
        )
        guard(Path(plan["root"]), reserve_gib=plan["reserve_gib"])
        require(sha(original) == row["cache_sha256"], "Partial-cache bytes changed")
        array = np.load(original, mmap_mode="r", allow_pickle=False)
        require(
            array.dtype == np.uint16
            and array.ndim == 3
            and array.shape[-1] == 3
            and list(array.shape) == row["shape"]
            and min(array.shape[:2]) >= 2048 // factor,
            "Invalid partial-cache array",
        )
        del array
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), "Recovery destination already exists")
        temporary = target.with_suffix(".reuse.tmp")
        with temporary.open("xb") as writer:
            try:
                with original.open("rb") as reader:
                    shutil.copyfileobj(reader, writer, length=8 * 1024**2)
                writer.flush()
                require(sha(temporary) == row["cache_sha256"], "Copied partial-cache bytes differ")
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        temporary.replace(target)
        copied_bytes += target.stat().st_size
    return {"factor": factor, "copied": len(seen), "bytes": copied_bytes}


def downloaded_records(stage):
    """Bind every immutable source field and independently rehash every original."""
    from stage_commons_local import OPERATIONAL

    from demosaic.prepare import free_license

    plan = read(stage / "plan.json")
    selected = {row["page_id"]: row for row in read(plan["selection"]["path"])}
    with sqlite3.connect(
        f"file:{stage / 'quality_images.sqlite3'}?mode=ro", uri=True
    ) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA temp_store=MEMORY")
        actual = {row["page_id"]: dict(row) for row in connection.execute("SELECT * FROM images")}
    require(actual.keys() == selected.keys(), "Local index membership changed")
    require(
        all(row["status"] in {"downloaded", "failed"} for row in actual.values()),
        "Downloader exited with unfinished sources; resume it before preparation",
    )
    records, failed = [], []
    for identity, row in actual.items():
        require(
            all(
                row[key] == value
                for key, value in selected[identity].items()
                if key not in OPERATIONAL
            ),
            "Immutable attribution/source fields changed",
        )
        require(free_license(row["license"]), "Unaccepted source license")
        if row["status"] == "failed":
            failed.append(
                {"page_id": identity, "sha1_hex": row["sha1_hex"], "error": row["last_error"]}
            )
            continue
        original = (stage / row["download_path"]).resolve()
        require(original.is_relative_to(stage) and original != stage, "Original escapes stage")
        require(original.stat().st_size == row["byte_size"], "Original byte count differs")
        require(sha(original, "sha1") == row["sha1_hex"], "Original SHA1 differs")
        records.append({key: row[key] for key in PREPARE_FIELDS})
    require(bool(records), "No verified downloaded originals")
    return sorted(records, key=lambda row: row["sha1_hex"]), failed


def audit_caches(output, selection):
    import numpy as np

    expected = {row["sha1_hex"]: row for row in selection}
    prepared, failures = {}, {}
    for factor in (4, 8):
        root = output / f"prepared{factor}"
        values = [json.loads(line) for line in (root / "manifest.jsonl").read_text().splitlines()]
        rows = {row["id"]: row for row in values}
        errors = [json.loads(line) for line in (root / "errors.jsonl").read_text().splitlines()]
        failed = {row["id"]: row for row in errors}
        require(
            len(rows) == len(values) and len(failed) == len(errors),
            "Duplicate cache/error identity",
        )
        require(
            not rows.keys() & failed.keys() and rows.keys() | failed.keys() == expected.keys(),
            "Cache/failure partition differs",
        )
        for identity, row in rows.items():
            require(
                all(row[key] == value for key, value in expected[identity].items()),
                "Cache attribution changed",
            )
            cache = (root / row["cache"]).resolve()
            require(cache.is_relative_to(root), "Cache path escapes preparation")
            require(sha(cache) == row["cache_sha256"], "Cache SHA256 differs")
            array = np.load(cache, mmap_mode="r", allow_pickle=False)
            require(
                array.dtype == np.uint16 and array.ndim == 3 and array.shape[-1] == 3,
                "Invalid cache type",
            )
            require(
                list(array.shape) == row["shape"] and min(array.shape[:2]) >= 2048 // factor,
                "Invalid cache shape",
            )
            require(
                row["bin_factor"] == factor and row["color_space"] == "linear-sRGB",
                "Cache recipe differs",
            )
        prepared[factor], failures[factor] = rows, errors
    samples, maximum = 0, 0
    for identity in prepared[4].keys() & prepared[8].keys():
        four, eight = [
            np.load(
                output / f"prepared{factor}" / prepared[factor][identity]["cache"],
                mmap_mode="r",
                allow_pickle=False,
            )
            for factor in (4, 8)
        ]
        h, w = eight.shape[:2]
        for top in range(0, h, 32):
            count = min(32, h - top)
            band = four[top * 2 : (top + count) * 2, : w * 2].astype(np.uint32)
            reduced = np.rint(band.reshape(count, 2, w, 2, 3).mean(axis=(1, 3))).astype(np.int32)
            difference = np.abs(reduced - eight[top : top + count].astype(np.int32))
            maximum = max(maximum, int(difference.max()))
            samples += difference.size
    require(maximum <= 1, "4x/8x area relation exceeds one uint16 code")
    return {
        "prepared": {factor: len(rows) for factor, rows in prepared.items()},
        "errors": failures,
        "area_samples": samples,
        "area_max_uint16_codes": maximum,
    }


def run(plan_path):
    plan = read(plan_path)
    root, stage = Path(plan["root"]), Path(plan["stage"])
    require(root == Path(plan_path).resolve().parent, "Preparation plan moved")
    require(
        Path(__file__).resolve() == Path(plan["work"]) / "scripts" / Path(__file__).name,
        "Run the frozen worker",
    )
    for path, digest in plan["frozen_files"].items():
        require(sha(path) == digest, "Frozen preparation source changed")
    for item in plan["inputs"]:
        require(ref(item["path"]) == item, "Frozen preparation input changed")
    require(not os.environ.get("CUDA_VISIBLE_DEVICES", "missing"), "Preparation must hide CUDA")
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
        dependency = plan.get("after_completion")
        deadline = time.monotonic() + plan["wait_seconds"]
        if dependency is not None:
            record("waiting-for-exact-GPU-review-closure-exit")
            while alive(dependency["owner"]):
                require(time.monotonic() < deadline, "Review closure wait exceeded declared budget")
                time.sleep(20)
            state = read(dependency["status_path"])
            require(
                state["controller"] == dependency["owner"]
                and state["plan"] == dependency["plan"]
                and state["status"] == dependency["success_status"],
                "Review closure did not complete successfully with the declared identity",
            )
        if "recovery" in plan:
            record("waiting-for-stable-memory-before-cache-recovery")
            since = None
            while True:
                require(time.monotonic() < deadline, "Stable-memory wait exceeded declared budget")
                if psutil.virtual_memory().available >= plan["minimum_stable_available_gib"] * GIB:
                    since = time.monotonic() if since is None else since
                    if time.monotonic() - since >= plan["stable_memory_seconds"]:
                        break
                else:
                    since = None
                time.sleep(10)
        record("waiting-for-exact-local-downloader-exit")
        while alive(plan["download_owner"]):
            require(time.monotonic() < deadline, "Local download wait exceeded declared budget")
            time.sleep(20)
        # Never race a local resume or another archive downloader after owner exit.
        with Path(plan["download_lock"]).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for item in plan["inputs"]:
                require(ref(item["path"]) == item, "Frozen preparation input changed while waiting")
            guard(
                root,
                reserve_gib=plan["reserve_gib"],
                additional_bytes=plan["estimated_cache_payload_bytes"] + 4 * GIB,
            )
            record("verifying-all-original-bytes-and-attribution")
            import torch
            from screen_commons_protected import screen

            from demosaic import prepare

            torch.set_num_threads(1)
            require(not torch.cuda.is_initialized(), "CPU preparation initialized CUDA")
            selection, failed = downloaded_records(stage)
            output = writable_path(Path(plan["work"]) / "outputs")
            output.mkdir(exist_ok=False)
            manifest = output / "selection.jsonl"
            manifest.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selection)
            )
            save(output / "download-failures.json", failed)
            original_prepare_one = prepare.prepare_one

            def guarded_prepare_one(*args, **kwargs):
                guard(root, reserve_gib=plan["reserve_gib"])
                return original_prepare_one(*args, **kwargs)

            prepare.prepare_one = guarded_prepare_one
            reused = []
            try:
                for factor in (4, 8):
                    reused.append(reuse_partial_caches(plan, output, selection, factor))
                    record(
                        f"preparing-quarantined-{factor}x",
                        originals=len(selection),
                        download_failures=len(failed),
                    )
                    prepare.prepare_commons(
                        stage,
                        output / f"prepared{factor}",
                        factor=factor,
                        min_size=2048 // factor,
                        workers=1,
                        selection_manifest=manifest,
                    )
            finally:
                prepare.prepare_one = original_prepare_one
            save(output / "reused-caches.json", reused)
            record("auditing-all-cache-bytes-and-area-consistency")
            audit = audit_caches(output, selection)
            save(output / "cache-audit.json", audit)
            guard(root, reserve_gib=plan["reserve_gib"])
            record("screening-cached-protected-scenes-and-GFX-family")
            screening = screen(
                output / "prepared8/manifest.jsonl",
                Path(plan["references"]),
                stage,
                output / "protected-screen",
            )
            # Preserve every new hash holdout separately; neither list is admitted.
            candidates = [
                json.loads(line)
                for line in Path(screening["cleared_manifest"]).read_text().splitlines()
            ]
            for row in candidates:
                row["split"] = "reserved" if row["split"] != "train" else "quarantine"
            candidate_path = output / "screened-candidates.jsonl"
            candidate_path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates)
            )
            receipt = {
                "plan": ref(plan_path),
                "selection": ref(manifest),
                "cache_audit": ref(output / "cache-audit.json"),
                "reused_caches": ref(output / "reused-caches.json"),
                "screening": ref(output / "protected-screen/summary.json"),
                "candidates": ref(candidate_path),
                "candidate_counts": dict(Counter(row["split"] for row in candidates)),
                "download_failures": len(failed),
                "cuda_initialized": torch.cuda.is_initialized(),
                "training_admission": False,
                "manual_content_review_complete": False,
                "remaining": "Independent duplicate/content and known-series review, 4x/8x matching membership freeze, manual content review and a separate training recipe. Finite protected fingerprints do not prove scene disjointness.",
            }
            save(output / "receipt.json", receipt)
            record(
                "prepared-and-screened-quarantine-awaiting-independent-review",
                receipt=ref(output / "receipt.json"),
            )
    except Exception as error:
        record("failed-local-preparation", error=f"{type(error).__name__}: {error}")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("freeze")
    command.add_argument("--stage", required=True, type=Path)
    command.add_argument("--root", required=True, type=Path)
    command.add_argument("--references", required=True, type=Path)
    command.add_argument("--reserve-gib", type=int, default=200)
    command.add_argument("--recover-from", type=Path)
    command.add_argument("--after-status", type=Path)
    command = sub.add_parser("run")
    command.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        print(
            json.dumps(
                freeze(
                    args.stage,
                    args.root,
                    args.references,
                    reserve_gib=args.reserve_gib,
                    recover_from=args.recover_from,
                    after_status=args.after_status,
                ),
                indent=2,
            )
        )
    else:
        run(args.plan)


if __name__ == "__main__":
    main()
