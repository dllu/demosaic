"""Prepare newly downloaded Commons images without changing frozen evaluation sets.

New validation/test hash buckets are reserved, not added to active evaluation.
Conservative dHash/correlation screening excludes new near-duplicates of any
existing source and deduplicates new groups. This is not complete scene recognition.
"""

import argparse
import fcntl
import hashlib
import inspect
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import __version__ as pillow_version

from demosaic.audit import fingerprint, orientations, thumbnail
from demosaic.prepare import free_license, prepare_commons
from demosaic.safety import writable_path


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


class Fingerprints:
    def __init__(self, path):
        path = writable_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = path.with_suffix(".lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError("Another extension audit owns the fingerprint cache") from None
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT)")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS fingerprints (sha TEXT PRIMARY KEY,size INTEGER,mtime INTEGER,thumb BLOB,hashes BLOB,ratio REAL)"
        )
        algorithm = hashlib.sha256(
            (
                "".join(inspect.getsource(f) for f in [thumbnail, orientations, fingerprint])
                + np.__version__
                + pillow_version
            ).encode()
        ).hexdigest()
        prior = self.db.execute("SELECT value FROM metadata WHERE key='algorithm'").fetchone()
        if prior and prior[0] != algorithm:
            self.close()
            raise ValueError("Fingerprint algorithm differs; choose a new cache")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('algorithm',?)", (algorithm,))
        self.db.commit()
        self.hits = 0
        self.computed = 0

    def close(self):
        self.db.close()
        self.lock.close()

    def describe(self, row):
        path = Path(row["cache"])
        stat = path.stat()
        identity = row["cache_sha256"]
        cached = self.db.execute(
            "SELECT size,mtime,thumb,hashes,ratio FROM fingerprints WHERE sha=?", (identity,)
        ).fetchone()
        if (not cached or (stat.st_size, stat.st_mtime_ns) != cached[:2]) and checksum(
            path
        ) != identity:
            raise ValueError(f"Cache checksum changed: {row['id']}")
        if cached:
            self.hits += 1
            if (stat.st_size, stat.st_mtime_ns) != cached[:2]:
                self.db.execute(
                    "UPDATE fingerprints SET size=?,mtime=? WHERE sha=?",
                    (stat.st_size, stat.st_mtime_ns, identity),
                )
            return (
                np.frombuffer(cached[2], "<f4").reshape(32, 32),
                np.frombuffer(cached[3], "<u8").reshape(8, 4),
                cached[4],
            )
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if array.dtype != np.uint16 or array.ndim != 3 or array.shape[-1] != 3:
            raise ValueError("Expected prepared linear uint16 RGB cache")
        thumb = thumbnail(array)
        hashes = np.stack([fingerprint(t) for t in orientations(thumb)])
        ratio = array.shape[1] / array.shape[0]
        self.db.execute(
            "INSERT INTO fingerprints VALUES (?,?,?,?,?,?)",
            (
                identity,
                stat.st_size,
                stat.st_mtime_ns,
                thumb.astype("<f4").tobytes(),
                hashes.astype("<u8").tobytes(),
                ratio,
            ),
        )
        self.computed += 1
        return thumb, hashes, ratio


def audit_extension(
    base_manifest,
    addition_manifest,
    output,
    fingerprint_cache,
    *,
    max_hamming=8,
    min_correlation=0.99,
):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".extension.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another audit owns this extension output") from None
        return _audit_extension(
            base_manifest,
            addition_manifest,
            output,
            fingerprint_cache,
            max_hamming=max_hamming,
            min_correlation=min_correlation,
        )


def _audit_extension(
    base_manifest,
    addition_manifest,
    output,
    fingerprint_cache,
    *,
    max_hamming=8,
    min_correlation=0.99,
):
    if not 0 <= max_hamming <= 32 or not 0.9 <= min_correlation <= 1:
        raise ValueError("Invalid near-duplicate thresholds")
    output = writable_path(output)
    if (output / "manifest.jsonl").exists():
        raise ValueError("Frozen extension already exists; choose a new output")
    base_manifest, addition_manifest = Path(base_manifest), Path(addition_manifest)
    original, added = rows(base_manifest), rows(addition_manifest)
    if len({r["id"] for r in original}) != len(original) or len({r["id"] for r in added}) != len(
        added
    ):
        raise ValueError("Duplicate source identities within a manifest")
    existing = {r["id"] for r in original}
    skipped = [r["id"] for r in added if r["id"] in existing]
    added = [r for r in added if r["id"] not in existing]
    for r in added:
        if r["split"] not in ["train", "val", "test"] or not free_license(r["license"]):
            raise ValueError("New records require licensed prepared train/val/test sources")
    all_rows = []
    for manifest, group in [(base_manifest, original), (addition_manifest, added)]:
        for source in group:
            row = dict(source)
            row["cache"] = str((manifest.parent / row["cache"]).resolve())
            all_rows.append(row)
    if len({(r["bin_factor"], r["color_space"], r["dtype"]) for r in all_rows}) != 1:
        raise ValueError("Cannot mix cache recipes in one extension")
    store = Fingerprints(fingerprint_cache)
    try:
        descriptors = []
        for index, row in enumerate(all_rows):
            descriptors.append(store.describe(row))
            if (index + 1) % 500 == 0:
                store.db.commit()
                print(
                    json.dumps(
                        {
                            "event": "extension-fingerprint",
                            "sources": index + 1,
                            "computed": store.computed,
                            "reused": store.hits,
                        }
                    ),
                    flush=True,
                )
        store.db.commit()
        cache_stats = {"computed": store.computed, "reused": store.hits}
    finally:
        store.close()
    thumbs = [d[0] for d in descriptors]
    hashes = np.stack([d[1] for d in descriptors])
    ratios = np.array([d[2] for d in descriptors])
    informative = np.array([t.std() > 0.005 for t in thumbs])
    parent = list(range(len(all_rows)))
    edges = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j, edge):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)
            edges.append(edge)

    # Exact cache identity also protects flat images with ambiguous fingerprints.
    exact = {}
    for i, row in enumerate(all_rows):
        key = row["cache_sha256"]
        if key in exact:
            union(
                i,
                exact[key],
                {
                    "first": all_rows[exact[key]]["id"],
                    "second": row["id"],
                    "method": "cache-sha256",
                },
            )
        else:
            exact[key] = i
    nbase = len(original)
    for i in range(nbase, len(all_rows)):
        if not informative[i]:
            continue
        distances = np.bitwise_count(hashes[:i] ^ hashes[i, 0]).sum(-1)
        candidates = np.flatnonzero((distances.min(1) <= max_hamming) & informative[:i])
        target = (thumbs[i] - thumbs[i].mean()) / thumbs[i].std()
        base_match = find(i) < nbase
        for j in candidates:
            if j < nbase and base_match:
                continue
            for orientation in np.flatnonzero(distances[j] <= max_hamming):
                ratio = ratios[j] if orientation % 2 == 0 else 1 / ratios[j]
                if abs(np.log(ratio / ratios[i])) > 0.03:
                    continue
                other = orientations(thumbs[j])[orientation]
                other = (other - other.mean()) / other.std()
                correlation = float(np.mean(target * other))
                if correlation < min_correlation:
                    continue
                union(
                    i,
                    int(j),
                    {
                        "first": all_rows[j]["id"],
                        "second": all_rows[i]["id"],
                        "method": "dihedral-dhash256-correlation",
                        "hamming": int(distances[j, orientation]),
                        "correlation": correlation,
                        "orientation": int(orientation),
                    },
                )
                if j < nbase:
                    base_match = True
                break
        if (i - nbase + 1) % 100 == 0:
            print(
                json.dumps({"event": "extension-screen", "new_sources": i - nbase + 1}), flush=True
            )
    groups = {}
    for i in range(nbase, len(all_rows)):
        groups.setdefault(find(i), []).append(i)
    excluded = {}
    reserved = {}
    for root, members in groups.items():
        if root < nbase:
            excluded.update({i: "near_duplicate_of_existing" for i in members})
            continue
        useful = [i for i in members if informative[i]]
        excluded.update(
            {i: "insufficient_fingerprint_contrast" for i in members if not informative[i]}
        )
        if not useful:
            continue
        held = [i for i in useful if all_rows[i]["split"] in ["val", "test"]]
        keep = min(held or useful, key=lambda i: all_rows[i]["id"])
        excluded.update({i: "new_near_duplicate_cluster" for i in useful if i != keep})
        if held:
            reserved[keep] = all_rows[keep]["split"]
    for i in range(nbase, len(all_rows)):
        row = all_rows[i]
        if i in excluded:
            row["original_split"] = row["split"]
            row["split"] = "excluded"
            row["excluded_reason"] = excluded[i]
        elif i in reserved:
            row["reserved_split"] = reserved[i]
            row["split"] = "reserved"
    assert [(r["id"], r["split"]) for r in all_rows[:nbase]] == [
        (r["id"], r["split"]) for r in original
    ]
    report = {
        "base_manifest": str(base_manifest.resolve()),
        "base_sha256": checksum(base_manifest),
        "addition_manifest": str(addition_manifest.resolve()),
        "addition_sha256": checksum(addition_manifest),
        "base_counts": dict(Counter(r["split"] for r in original)),
        "counts": dict(Counter(r["split"] for r in all_rows)),
        "added_train": sum(r["split"] == "train" for r in all_rows[nbase:]),
        "new_reserved": len(reserved),
        "new_excluded": len(excluded),
        "skipped_existing_ids": skipped,
        "cache": cache_stats,
        "max_hamming": max_hamming,
        "min_correlation": min_correlation,
        "verified_union_edges": edges,
        "policy": "Every existing source/split preserved. New groups linked to any existing source excluded. New val/test buckets reserved; active evaluation membership unchanged. New-only duplicate groups retain one source, preferring a reserved bucket.",
        "limitation": "Near-duplicate screening, not complete scene recognition: arbitrary crops and different viewpoints can remain.",
    }
    output.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_rows)
    report["manifest_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    temporary = output / "manifest.jsonl.tmp"
    temporary.write_text(payload)
    receipt_tmp = output / "audit.json.tmp"
    receipt_tmp.write_text(json.dumps(report, indent=2) + "\n")
    receipt_tmp.replace(output / "audit.json")
    temporary.replace(output / "manifest.jsonl")
    print(
        json.dumps(
            {
                "event": "extension-complete",
                "counts": report["counts"],
                "added_train": report["added_train"],
                "reserved": len(reserved),
                "excluded": len(excluded),
            }
        ),
        flush=True,
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=Path("/mnt/external/qi"))
    parser.add_argument("--since", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fingerprint-cache", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    since = datetime.fromisoformat(args.since)
    if since.tzinfo is None:
        parser.error("--since requires an explicit timezone")
    since = since.astimezone(UTC).isoformat(timespec="seconds")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    recipe = {
        "base_sha256": checksum(args.base_manifest),
        "since": since,
        "source": str(args.source.resolve()),
        "factor": 8,
        "min_size": 256,
        "max_pixels": 120000000,
    }
    recipe_path = output / "selection-recipe.json"
    selection = output / "selection.jsonl"
    if recipe_path.exists():
        if json.loads(recipe_path.read_text()) != recipe:
            raise ValueError("Selection recipe differs; use a new output")
    else:
        known = {r["id"] for r in rows(args.base_manifest)}
        c = sqlite3.connect(f"file:{args.source / 'quality_images.sqlite3'}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        try:
            records = [
                dict(r)
                for r in c.execute(
                    "SELECT title,page_url,original_url,author,license,license_url,attribution,credit,sha1,sha1_hex,download_path,width,height FROM images WHERE status='downloaded' AND downloaded_at>=? AND width>=2048 AND height>=2048 AND width*height<=120000000 ORDER BY sha1",
                    (since,),
                )
            ]
        finally:
            c.close()
        records = [
            r
            for r in records
            if (r["sha1_hex"] or r["sha1"]) not in known and free_license(r["license"])
        ]
        selection.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
        recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
        print(json.dumps({"event": "extension-selection", "sources": len(records)}), flush=True)
    prepared = output / "prepared8"
    prepare_commons(
        args.source,
        prepared,
        factor=8,
        min_size=256,
        workers=args.workers,
        selection_manifest=selection,
    )
    audit_extension(
        args.base_manifest, prepared / "manifest.jsonl", output / "audit", args.fingerprint_cache
    )


if __name__ == "__main__":
    main()
