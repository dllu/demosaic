"""Quarantine new Commons candidates resembling cached protected scenes.

This is data identity screening, not model scoring or training admission.
Original/prepared images and protected references stay read-only.
"""

import argparse
import fcntl
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
from PIL import Image
from PIL import __version__ as pillow_version

from demosaic.audit import fingerprint, orientations, thumbnail
from demosaic.prepare import free_license
from demosaic.safety import writable_path


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def views(array):
    height, width = array.shape[:2]
    regions = [(0, 0, width, height)]
    for fraction, points in [
        (0.75, [(0.5, 0.5)]),
        (0.5, [(0.5, 0.5), (0, 0), (1, 0), (0, 1), (1, 1)]),
    ]:
        h, w = int(height * fraction), int(width * fraction)
        regions.extend((int((width - w) * x), int((height - h) * y), w, h) for x, y in points)
    result = []
    for x, y, w, h in regions:
        for orientation, grey in enumerate(orientations(thumbnail(array[y : y + h, x : x + w]))):
            std = float(grey.std())
            result.append(
                {
                    "roi": [x, y, w, h],
                    "orientation": orientation,
                    "ratio": w / h if orientation % 2 == 0 else h / w,
                    "informative": std > 0.005,
                    "hash": fingerprint(grey),
                    "normalized": ((grey - grey.mean()) / max(std, 1e-6)).reshape(-1),
                }
            )
    return result


def protected_pool(path):
    path = Path(path)
    data = json.loads(path.read_text())
    pool = []
    for index, entry in enumerate(data["protected"]):
        if "manifest" in entry and digest(entry["manifest"]) != entry["manifest_sha256"]:
            raise ValueError("Protected input manifest changed")
        cache = path.parent / entry["screen_cache"]
        if digest(cache) != entry["screen_sha256"]:
            raise ValueError("Protected screen checksum changed")
        array = np.load(cache, mmap_mode="r", allow_pickle=False)
        if array.dtype != np.uint16 or array.ndim != 3 or array.shape[-1] != 3:
            raise ValueError("Protected screen must be linear uint16 RGB")
        descriptors = views(array)
        if not any(v["informative"] for v in descriptors):
            raise ValueError("Protected reference has no usable spatial information")
        pool.extend((index, entry["scene"], v) for v in descriptors)
    if not pool:
        raise ValueError("No protected references")
    return {
        "entries": pool,
        "hashes": np.stack([v["hash"] for _, _, v in pool]),
        "normalized": np.stack([v["normalized"] for _, _, v in pool]),
        "ratios": np.array([v["ratio"] for _, _, v in pool]),
        "informative": np.array([v["informative"] for _, _, v in pool]),
    }


def matches(array, pool):
    candidates = views(array)
    correlations = np.stack([v["normalized"] for v in candidates]) @ pool["normalized"].T / 1024
    found = {}
    for i, candidate in enumerate(candidates):
        if not candidate["informative"]:
            continue
        distance = np.bitwise_count(pool["hashes"] ^ candidate["hash"]).sum(-1)
        eligible = pool["informative"] & (
            np.abs(np.log(pool["ratios"] / candidate["ratio"])) <= 0.04
        )
        for j in np.flatnonzero(eligible & ((distance <= 40) | (correlations[i] >= 0.95))):
            index, scene, other = pool["entries"][j]
            row = {
                "protected_index": index,
                "scene": scene,
                "hamming": int(distance[j]),
                "correlation": float(correlations[i, j]),
                "candidate_roi": candidate["roi"],
                "protected_roi": other["roi"],
                "candidate_orientation": candidate["orientation"],
                "protected_orientation": other["orientation"],
            }
            prior = found.get(index)
            if prior is None or (row["correlation"], -row["hamming"]) > (
                prior["correlation"],
                -prior["hamming"],
            ):
                found[index] = row
    return list(found.values())


def metadata_reason(row, source):
    text = " ".join(str(row.get(k, "")) for k in ["title", "download_path", "original_url"]).upper()
    if any(name in text for name in ["DSCF3842", "DSCF3883", "DSCF3879", "DSCF3880"]):
        return "Standing GFX capture identifier"
    source = Path(source).resolve()
    path = (source / row["download_path"]).resolve()
    if source not in path.parents:
        raise ValueError("Original path escapes corpus")
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            model = "".join(c for c in str(exif.get(272, "")) if c.isalnum()).upper()
            nested = exif.get_ifd(0x8769) if 0x8769 in exif else {}
            date = nested.get(36867, nested.get(36868, exif.get(306, "")))
            date = date.decode("ascii", errors="replace") if isinstance(date, bytes) else str(date)
            date = date.strip()
    except (OSError, ValueError, SyntaxError) as error:
        return f"Original metadata unreadable: {type(error).__name__}"
    if model.endswith("GFX100S") and date.startswith(("2023:12:31", "2023-12-31")):
        return "Standing GFX camera/date family"
    return None


def screen(manifest, references, source, output):
    manifest, references = Path(manifest).resolve(), Path(references).resolve()
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".screen.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another protected screen owns output") from None
        if (output / "summary.json").exists():
            raise ValueError("Screen output is frozen; choose a new directory")
        rows = [json.loads(line) for line in manifest.read_text().splitlines()]
        if len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate candidate identities")
        recipe = {
            "manifest": str(manifest),
            "manifest_sha256": digest(manifest),
            "references": str(references),
            "references_sha256": digest(references),
            "source": str(Path(source).resolve()),
            "script_sha256": digest(__file__),
            "audit_source_sha256": digest(inspect.getsourcefile(fingerprint)),
            "prepare_source_sha256": digest(inspect.getsourcefile(free_license)),
            "numpy_version": np.__version__,
            "pillow_version": pillow_version,
            "policy": "Seven full/center/corner views x8 dihedral orientations on both sides; informative std>.005, aspect4%, dHash<=40 OR correlation>=.95. Metadata blocks named standing captures and GFX100S2023-12-31 family. Flags are quarantined, not automatically admitted.",
        }
        recipe_path = output / "recipe.json"
        if recipe_path.exists() and json.loads(recipe_path.read_text()) != recipe:
            raise ValueError("Screen recipe changed")
        recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
        pool = protected_pool(references)
        cleared = []
        quarantined = []
        ledger = output / "outcomes"
        ledger.mkdir(exist_ok=True)
        for index, row in enumerate(rows):
            if row["split"] not in ["train", "val", "test"] or not free_license(row["license"]):
                raise ValueError("Expected licensed provisional producer splits")
            if not row["id"].isalnum():
                raise ValueError("Unsafe candidate identity")
            cache = manifest.parent / row["cache"]
            stat = cache.stat()
            outcome = ledger / f"{row['id']}.json"
            identity = {
                "cache_sha256": row["cache_sha256"],
                "cache_bytes": stat.st_size,
                "cache_mtime_ns": stat.st_mtime_ns,
            }
            source_root = Path(source).resolve()
            original = (source_root / row["download_path"]).resolve()
            if source_root not in original.parents:
                raise ValueError("Original path escapes corpus")
            original_stat = original.stat()
            identity.update(
                original_bytes=original_stat.st_size, original_mtime_ns=original_stat.st_mtime_ns
            )
            saved = json.loads(outcome.read_text()) if outcome.exists() else None
            if saved is None or saved["identity"] != identity:
                if digest(cache) != row["cache_sha256"]:
                    raise ValueError("Candidate cache checksum changed")
                array = np.load(cache, mmap_mode="r", allow_pickle=False)
                if array.dtype != np.uint16 or array.ndim != 3 or array.shape[-1] != 3:
                    raise ValueError("Expected uint16 RGB candidate")
                reason = metadata_reason(row, source)
                saved = {
                    "id": row["id"],
                    "identity": identity,
                    "metadata_reason": reason,
                    "matches": matches(array, pool),
                }
                temporary = outcome.with_suffix(".tmp")
                temporary.write_text(json.dumps(saved, indent=2) + "\n")
                temporary.replace(outcome)
            candidate = {**row, "cache": str(cache.resolve())}
            if saved["metadata_reason"] or saved["matches"]:
                quarantined.append({**candidate, "protected_screen": saved})
            else:
                cleared.append(candidate)
            if (index + 1) % 100 == 0:
                print(
                    json.dumps(
                        {
                            "event": "protected-screen",
                            "done": index + 1,
                            "total": len(rows),
                            "clear": len(cleared),
                            "quarantined": len(quarantined),
                        }
                    ),
                    flush=True,
                )
        for name, records in [("cleared.jsonl", cleared), ("quarantined.jsonl", quarantined)]:
            temporary = output / (name + ".tmp")
            temporary.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
            temporary.replace(output / name)
        result = {
            **recipe,
            "purpose": "Data identity review only; no models, predictions, protected-final scoring or training admission",
            "candidates": len(rows),
            "protected_references": len({i for i, _, _ in pool["entries"]}),
            "cleared": len(cleared),
            "quarantined": len(quarantined),
            "cleared_manifest": str(output / "cleared.jsonl"),
            "cleared_sha256": digest(output / "cleared.jsonl"),
            "quarantined_manifest": str(output / "quarantined.jsonl"),
            "quarantined_sha256": digest(output / "quarantined.jsonl"),
            "remaining": "Near-duplicate audit and separate reviewed freeze required. Finite fingerprints are not complete scene recognition; framing, lighting, crops or missing metadata can evade matches.",
        }
        (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(screen(args.manifest, args.references, args.source, args.output)), flush=True)


if __name__ == "__main__":
    main()
