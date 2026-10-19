"""Preliminary metadata overlap retrieval for new Commons arrivals; never admission."""

import argparse
import json
import math
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from train_directional_interval_trial import read, ref, save

from demosaic.prepare import split_for
from demosaic.safety import writable_path

THRESHOLD = 0.55
OMIT = {"jpg", "jpeg", "png", "tif", "tiff", "dsc", "dscf", "img", "ansicht", "actm"}


def terms(title):
    """Same Unicode letter/character4gram features as the completed1188 review."""
    text = unicodedata.normalize("NFKD", title.removeprefix("File:").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    tokens = [t for t in re.findall(r"[^\W\d_]+", text) if len(t) >= 3 and t not in OMIT]
    result = set()
    for token in tokens:
        padded = "^" + token + "$"
        result.update(padded[i : i + 4] for i in range(max(1, len(padded) - 3)))
    return result


def retrieve(anchors, queries):
    """Sparse deterministic squared-smooth-IDF cosine, retaining five neighbors."""
    for rows in [anchors, queries]:
        if len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate title source identity")
    if {r["id"] for r in anchors} & {r["id"] for r in queries}:
        raise ValueError("Title query is already an anchor")
    if not anchors:
        raise ValueError("Expected held-out title anchors")
    vocabulary = [terms(r["title"]) for r in [*anchors, *queries]]
    frequency = Counter(t for ts in vocabulary for t in ts)
    weight = {t: (math.log((1 + len(vocabulary)) / (1 + n)) + 1) ** 2 for t, n in frequency.items()}
    postings, norms = defaultdict(list), []
    for index, ts in enumerate(vocabulary):
        norms.append(math.sqrt(math.fsum(weight[t] for t in sorted(ts))))
        if index < len(anchors):
            for term in sorted(ts):
                postings[term].append(index)
    results = []
    for index, row in enumerate(queries):
        scores = defaultdict(list)
        for term in sorted(vocabulary[len(anchors) + index]):
            for other in postings[term]:
                scores[other].append(weight[term])
        ranked = sorted(
            (
                (math.fsum(parts) / (norms[j] * norms[len(anchors) + index]), j)
                for j, parts in scores.items()
                if norms[j] and norms[len(anchors) + index]
            ),
            reverse=True,
        )[:5]
        neighbors = [
            {
                "score": value,
                "id": anchors[j]["id"],
                "split": anchors[j]["split"],
                "origin": anchors[j].get("anchor_origin", "existing-corpus"),
                "title": anchors[j]["title"],
                "same_author": row.get("author") == anchors[j].get("author"),
            }
            for value, j in ranked
        ]
        results.append(
            {
                "id": row["id"],
                "title": row["title"],
                "decision": "withhold-uninformative-title"
                if not neighbors
                else "withhold-title-risk"
                if neighbors[0]["score"] >= THRESHOLD
                else "no-title-flag",
                "neighbors": neighbors,
            }
        )
    return results


def main(base_path, arrivals_path, output):
    base_ref, arrivals_ref = ref(base_path), ref(arrivals_path)
    base = [json.loads(line) for line in base_path.read_text().splitlines()]
    arrivals = read(arrivals_path)
    if len({r["id"] for r in base}) != len(base):
        raise ValueError("Duplicate prior corpus identity")
    known = {r["id"] for r in base}
    new, seen = [], set()
    for row in arrivals:
        identity = row["sha1_hex"]
        if identity in known or identity in seen:
            raise ValueError("New arrival is already in the prior corpus or duplicated")
        seen.add(identity)
        bucket = split_for(identity)
        new.append(
            {
                **row,
                "id": identity,
                "split": "train" if bucket == "train" else "reserved",
                "initial_hash_bucket": bucket,
            }
        )
    held = [
        dict(r, anchor_origin="existing-corpus")
        for r in base
        if r["split"] in ["val", "test", "reserved"]
    ]
    held += [dict(r, anchor_origin="new-reserved") for r in new if r["split"] == "reserved"]
    queries = [r for r in new if r["split"] == "train"]
    results = retrieve(held, queries)
    assert ref(base_path) == base_ref and ref(arrivals_path) == arrivals_ref
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, output / "executed-source.py")
    policy = {
        "threshold": THRESHOLD,
        "features": "NFKD/accent-folded casefolded Unicode letter tokens>=3, unchanged omit set and unique boundary-padded character4grams; numeric tokens dropped.",
        "score": "Cosine with squared smooth IDF log((1+N)/(1+document_frequency))+1 over all anchors and queries. Deterministic sorted terms and math.fsum accumulation; same threshold/features as prior1188-source review.",
        "anchors": "Every prior val/test/reserved source and every newly reserved source hash bucket.",
        "action": "Preserve all new reserved sources; flag every new train title with top score>=.55 or no feature neighbor. A no-title-flag result is not training eligibility.",
        "timing": "Preliminary all-arrivals metadata analysis before complete new cache/protected/duplicate/content results. Recompute on the actual final candidate set before any coupled admission; IDF depends on its population.",
        "limits": "Metadata retrieval only. Generic vehicle/species/place names give false positives; aliases/crops/missing or cross-language metadata can evade flags. No scene identity/independence or source quality claim.",
    }
    save(output / "policy.json", policy)
    save(output / "decisions.json", results)
    save(output / "new-reserved.json", [r for r in new if r["split"] == "reserved"])
    report = {
        "status": "completed-preliminary-all-arrivals-title-retrieval-no-training-admission",
        "driver": ref(output / "executed-source.py"),
        "base": base_ref,
        "arrivals": arrivals_ref,
        "policy": ref(output / "policy.json"),
        "decisions": ref(output / "decisions.json"),
        "new_reserved": ref(output / "new-reserved.json"),
        "anchors": len(held),
        "prior_heldout_anchors": len(held) - sum(r["split"] == "reserved" for r in new),
        "new_reserved_anchors": sum(r["split"] == "reserved" for r in new),
        "train_queries": len(queries),
        "counts": dict(Counter(r["decision"] for r in results)),
        "new_reserved_top_risk_matches": sum(
            bool(r["neighbors"])
            and r["neighbors"][0]["origin"] == "new-reserved"
            and r["decision"] == "withhold-title-risk"
            for r in results
        ),
        "training_admission": False,
        "scope": policy["timing"],
    }
    save(output / "report.json", report)
    print({"report": ref(output / "report.json"), "counts": report["counts"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["base", "arrivals", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    main(args.base.resolve(), args.arrivals.resolve(), args.output.resolve())
