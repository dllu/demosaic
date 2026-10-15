"""Conservative near-duplicate screening of protected validation/test sources."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .safety import writable_path


def thumbnail(array):
    grey = (
        array[..., 0].astype(np.float32) * 0.2126
        + array[..., 1].astype(np.float32) * 0.7152
        + array[..., 2].astype(np.float32) * 0.0722
    ) / 65535
    return np.asarray(Image.fromarray(grey).resize((32, 32), Image.Resampling.LANCZOS)).copy()


def orientations(thumb):
    return [np.rot90(thumb, k) for k in range(4)] + [np.rot90(thumb[:, ::-1], k) for k in range(4)]


def fingerprint(thumb):
    sampled = np.asarray(
        Image.fromarray(np.ascontiguousarray(thumb)).resize((17, 16), Image.Resampling.LANCZOS)
    )
    return np.packbits((sampled[:, 1:] > sampled[:, :-1]).ravel()).view(np.uint64)


def audit_split(manifest, output, *, max_hamming=8, min_correlation=0.99):
    """Keep train unchanged and exclude protected near-duplicates conservatively.

    Eight dihedral orientations, aspect-ratio checks and thumbnail correlation
    verify dHash candidates. Training-linked clusters lose all validation/test
    members; validation-linked clusters lose test members because validation
    already informed model selection. This is not complete scene recognition:
    different crops/views may remain. No original cache or manifest is modified.
    """
    if not 0 <= max_hamming <= 32 or not 0.9 <= min_correlation <= 1:
        raise ValueError("Invalid duplicate-screening thresholds")
    output = writable_path(output)
    if output == Path(manifest).resolve().parent:
        raise ValueError("Choose a separate audit directory to preserve source manifests")
    output.mkdir(parents=True, exist_ok=True)
    manifest = Path(manifest)
    payload = manifest.read_bytes()
    rows = [json.loads(line) for line in payload.splitlines()]
    thumbs, hashes, ratios, informative = [], [], [], []
    for index, row in enumerate(rows):
        array = np.load(manifest.parent / row["cache"], mmap_mode="r")
        thumb = thumbnail(array)
        thumbs.append(thumb)
        hashes.append(np.stack([fingerprint(t) for t in orientations(thumb)]))
        ratios.append(array.shape[1] / array.shape[0])
        informative.append(float(thumb.std()) > 0.005)
        if (index + 1) % 1000 == 0:
            print(json.dumps({"event": "fingerprint", "images": index + 1}), flush=True)
    hashes, ratios = np.stack(hashes), np.array(ratios)
    informative = np.array(informative)
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    pairs = []
    for index, row in enumerate(rows):
        if row["split"] not in ("val", "test") or not informative[index]:
            continue
        distances = np.bitwise_count(hashes ^ hashes[index, 0]).sum(axis=-1)
        candidates = np.flatnonzero((distances.min(1) <= max_hamming) & informative)
        target = thumbs[index]
        target = (target - target.mean()) / target.std()
        for other in candidates:
            if other == index or (rows[other]["split"] in ("val", "test") and other < index):
                continue
            for orientation in np.flatnonzero(distances[other] <= max_hamming):
                ratio = ratios[other] if orientation % 2 == 0 else 1 / ratios[other]
                if abs(np.log(ratio / ratios[index])) > 0.03:
                    continue
                candidate = orientations(thumbs[other])[orientation]
                candidate = (candidate - candidate.mean()) / candidate.std()
                correlation = float(np.mean(candidate * target))
                if correlation < min_correlation:
                    continue
                union(index, int(other))
                pairs.append(
                    {
                        "first": row["id"],
                        "second": rows[other]["id"],
                        "first_split": row["split"],
                        "second_split": rows[other]["split"],
                        "hamming": int(distances[other, orientation]),
                        "correlation": correlation,
                        "orientation": int(orientation),
                    }
                )
                break
    clusters = {}
    for i in range(len(rows)):
        clusters.setdefault(find(i), []).append(i)
    excluded = {}
    for group in clusters.values():
        train = [i for i in group if rows[i]["split"] == "train"]
        val = [i for i in group if rows[i]["split"] == "val"]
        test = [i for i in group if rows[i]["split"] == "test"]
        if train:
            excluded.update({i: "training_near_duplicate" for i in val + test})
        elif val:
            keep = min(val, key=lambda i: rows[i]["id"])
            excluded.update({i: "validation_near_duplicate" for i in val + test if i != keep})
        elif test:
            keep = min(test, key=lambda i: rows[i]["id"])
            excluded.update({i: "test_near_duplicate" for i in test if i != keep})
    for i, row in enumerate(rows):
        if row["split"] in ("val", "test") and not informative[i]:
            excluded[i] = "insufficient_fingerprint_contrast"
    counts = {}
    with (output / "manifest.jsonl").open("w") as stream:
        for i, original in enumerate(rows):
            row = dict(original)
            row["cache"] = str((manifest.parent / row["cache"]).resolve())
            if i in excluded:
                row["original_split"] = row["split"]
                row["split"] = "excluded"
                row["excluded_reason"] = excluded[i]
            counts[row["split"]] = counts.get(row["split"], 0) + 1
            stream.write(json.dumps(row) + "\n")
    report = {
        "method": "dihedral-dHash256-correlation-v1",
        "source_manifest": str(manifest),
        "source_manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "max_hamming": max_hamming,
        "min_correlation": min_correlation,
        "counts": counts,
        "matched_pairs": pairs,
        "excluded": [
            {"id": rows[i]["id"], "reason": reason} for i, reason in sorted(excluded.items())
        ],
        "limitation": "Near-duplicate screening; arbitrary crops and different views can remain.",
    }
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"event": "split_audit", "counts": counts, "pairs": len(pairs)}), flush=True)
    return report
