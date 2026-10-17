"""Freeze coupled Commons manifests with reviewed training title-series removed.

Only metadata is processed. Original records/cache paths and every nontraining
line are preserved. Use a new destination; running experiments never change.
"""

import argparse
import hashlib
import json
import os
import shutil
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def normalize(value):
    return unicodedata.normalize("NFC", value).casefold()


def validate_policy(policy):
    rules = policy.get("rules", [])
    if policy.get("format_version") != 1 or not rules:
        raise ValueError("Expected version1 policy with explicit reviewed rules")
    if len({r["id"] for r in rules}) != len(rules):
        raise ValueError("Duplicate rule identities")
    for rule in rules:
        prefixes = rule.get("title_prefixes", [])
        if rule.get("kind") not in ("capture_series", "shared_site"):
            raise ValueError("Unknown reviewed grouping kind")
        if not prefixes or any(
            not isinstance(p, str) or not p.startswith("File:") or not p[5:].strip()
            for p in prefixes
        ):
            raise ValueError("Rules need nonempty Commons title prefixes")
        if not rule.get("query_seed_ids"):
            raise ValueError("Each rule needs a reviewed validation seed")
    return rules


def matching_rules(title, rules):
    title = normalize(title)
    return [
        r["id"] for r in rules if any(title.startswith(normalize(p)) for p in r["title_prefixes"])
    ]


def read_manifest(path, factor):
    lines = Path(path).read_bytes().splitlines(keepends=True)
    records = [json.loads(line) for line in lines]
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate source identities")
    for r in records:
        if r["split"] in ("train", "val", "test") and not Path(r["cache"]).is_absolute():
            raise ValueError(
                "Cache paths must be absolute to preserve literal records on relocation"
            )
        if r["split"] == "train" and (
            r["bin_factor"] != factor
            or r["dtype"] != "uint16"
            or r["color_space"] != "linear-sRGB"
            or len(r["cache_sha256"]) != 64
            or len(r["shape"]) != 3
            or r["shape"][2] != 3
            or min(r["shape"][:2]) < 2048 // factor
        ):
            raise ValueError("Training cache metadata does not support the declared binning/patch")
    return lines, records


def quarantine(manifest8, manifest4, policy_path, output):
    manifest8, manifest4, policy_path = [
        Path(p).resolve() for p in (manifest8, manifest4, policy_path)
    ]
    output = writable_path(output)
    if output.exists():
        raise ValueError("Destination already exists; choose a new frozen version")
    inputs = {"bin8": ref(manifest8), "bin4": ref(manifest4), "policy": ref(policy_path)}
    policy = json.loads(policy_path.read_text())
    rules = validate_policy(policy)
    data = {8: read_manifest(manifest8, 8), 4: read_manifest(manifest4, 4)}
    by = {factor: {r["id"]: r for r in records} for factor, (_, records) in data.items()}
    for split in ("train", "val", "test"):
        ids = [{r["id"] for r in records if r["split"] == split} for _, records in data.values()]
        if ids[0] != ids[1]:
            raise ValueError("Coupled manifests disagree on source split membership")
    for rule in rules:
        for identity in rule["query_seed_ids"]:
            if any(
                identity not in b
                or b[identity]["split"] != "val"
                or rule["id"] not in matching_rules(b[identity]["title"], [rule])
                for b in by.values()
            ):
                raise ValueError(
                    "Reviewed query seed is missing, not validation, or does not match its rule"
                )
    matches = {
        factor: {
            r["id"]: matching_rules(r["title"], rules)
            for r in records
            if r["split"] == "train" and matching_rules(r["title"], rules)
        }
        for factor, (_, records) in data.items()
    }
    if matches[8] != matches[4]:
        raise ValueError("Coupled metadata produces different training quarantines")
    for rule in rules:
        for identity in rule.get("reviewed_training_seed_ids", []):
            if (
                identity in by[8]
                and by[8][identity]["split"] == "train"
                and rule["id"] not in matches[8].get(identity, [])
            ):
                raise ValueError("A reviewed training seed would escape its stated rule")
    output.mkdir(parents=True)
    shutil.copyfile(policy_path, output / "policy.json")
    shutil.copyfile(__file__, output / "source.py")
    outputs = {}
    for factor, (lines, records) in data.items():
        retained = b"".join(
            line for line, r in zip(lines, records, strict=True) if r["id"] not in matches[factor]
        )
        removed = b"".join(
            line for line, r in zip(lines, records, strict=True) if r["id"] in matches[factor]
        )
        path, quarantine_path = (
            output / f"manifest{factor}.jsonl",
            output / f"quarantined{factor}.jsonl",
        )
        path.write_bytes(retained)
        quarantine_path.write_bytes(removed)
        nontrain = b"".join(
            line for line, r in zip(lines, records, strict=True) if r["split"] != "train"
        )
        kept_rows = [r for r in records if r["id"] not in matches[factor]]
        outputs[f"bin{factor}"] = {
            "manifest": ref(path),
            "quarantine": ref(quarantine_path),
            "before_counts": dict(Counter(r["split"] for r in records)),
            "after_counts": dict(Counter(r["split"] for r in kept_rows)),
            "unchanged_nontraining_literal_lines_sha256": hashlib.sha256(nontrain).hexdigest(),
        }
    removed_records = [
        {"source": by[8][identity], "matched_rule_ids": hit}
        for identity, hit in sorted(matches[8].items())
    ]
    reasons_path = output / "quarantine-reasons.jsonl"
    reasons_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in removed_records)
    )
    report = {
        "status": "completed-reviewed-series-metadata-quarantine-for-future-training",
        "created_UTC": datetime.now(UTC).isoformat(),
        "operator": ref(__file__),
        "inputs": inputs,
        "outputs": outputs,
        "reasons": ref(reasons_path),
        "quarantined_training_sources": len(matches[8]),
        "per_rule_training_counts": dict(Counter(k for hits in matches[8].values() for k in hits)),
        "retained_cache_records_and_all_nontraining_lines_unchanged": True,
        "actual_cache_decodes_or_neural_forwards": 0,
        "limits": "Known manually reviewed title-series/site exclusions only, not full scene independence. Metadata-only subset: no new cache-byte verification, resampling, split reassignment, deletion, source modification, model scoring or active recipe change. Existing cache audits remain parent evidence; other aliases/scenes can remain unmatched.",
    }
    for value in inputs.values():
        if ref(value["path"]) != value:
            raise ValueError(
                "Input changed while freezing; preserve this failed output and choose a new version"
            )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest8", required=True, type=Path)
    parser.add_argument("--manifest4", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.nice(10)
    print(
        json.dumps(quarantine(args.manifest8, args.manifest4, args.policy, args.output), indent=2)
    )


if __name__ == "__main__":
    main()
