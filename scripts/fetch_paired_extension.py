"""Acquire additional RawNIND scenes into quarantine, without training admission.

Use the frozen publisher catalog and cached protected identities. The existing
training allowlist and prepared training manifest remain unchanged.
"""

import argparse
import fcntl
import hashlib
import inspect
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from demosaic.paired import (
    CATALOG_URL,
    DATA_URL,
    DEVELOPMENT_SCENES,
    TRAINING_SCENES,
    download_file,
    select_pairs,
    verify_file,
)
from demosaic.safety import writable_path

# Include related views conservatively, not only exact protected scene names.
EXCLUDED_FAMILIES = ("MuseeL-", "LucieB_", "7D-", "D60-", "boardgames_")


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def permissions_by_scene(text):
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        name, permission = line.split(":", 1)
        if not name.strip() or name.strip() in result:
            raise ValueError("Ambiguous publisher scene permissions")
        result[name.strip()] = permission.strip()
    return result


def plan_extension(dataset, version, permissions, protected, existing):
    if version["license"].get("rightsIdentifier") != "CC-BY-SA-4.0":
        raise ValueError("Expected the reviewed commercially usable dataset license")
    if not protected.get("protected"):
        raise ValueError("A nonempty protected identity receipt is required")
    if existing.get("split") != "train" or {
        row["scene"] for row in existing["selection"]
    } != set(TRAINING_SCENES):
        raise ValueError("Expected the complete fixed training selection")
    blocked_names = set(DEVELOPMENT_SCENES) | set(TRAINING_SCENES)
    blocked_names.update(row["scene"] for row in protected["protected"])
    blocked_hashes = {
        row["source"]["sha1"]
        for row in protected["protected"]
        if row.get("source", {}).get("sha1")
    }
    blocked_hashes.update(
        record["sha1"]
        for row in existing["selection"]
        for role in ["clean", "noisy"]
        for record in row[role]
    )
    grants = permissions_by_scene(permissions)
    selected, excluded, seen_hashes = [], [], set()
    for name, row in sorted(dataset["Bayer"].items()):
        filenames = [r["filename"] for key in ["clean_images", "noisy_images"] for r in row[key]]
        reason = None
        if name in blocked_names:
            reason = "Existing training or protected evaluation scene"
        elif row.get("test_reserve") or any("_TEST_" in f.upper() for f in filenames):
            reason = "Publisher test reserve or TEST filename"
        elif row.get("unknown_sensor"):
            reason = "Unknown sensor"
        elif name.startswith(EXCLUDED_FAMILIES):
            reason = "Conservatively excluded protected scene family"
        elif name in grants and not grants[name].startswith("CC0,"):
            reason = "Scene permission override lacks a reviewed commercial grant"
        if reason:
            excluded.append({"scene": name, "reason": reason})
            continue
        try:
            # Reuse the non-test metadata-only pair rule. This does not assign
            # a training split: every returned record is explicitly quarantined.
            pair, = select_pairs(dataset, version["files"], "development", scenes=[name])
            records = [r for role in ["clean", "noisy"] for r in pair[role]]
            identities = {r["sha1"] for r in records}
            if any(len(s) != 40 or any(c not in "0123456789abcdef" for c in s) for s in identities):
                raise ValueError("Invalid source SHA1 identity")
            if identities & (blocked_hashes | seen_hashes):
                raise ValueError("Source identity overlaps protected/existing/selected data")
            if len(identities) != len(records):
                raise ValueError("Repeated source identity within a scene")
            if any(r["bytes"] <= 0 for r in records):
                raise ValueError("Invalid publisher file size")
        except (KeyError, ValueError) as error:
            excluded.append({"scene": name, "reason": str(error)})
            continue
        pair["split"] = "quarantine"
        pair["permission"] = {
            "license": "CC0-1.0" if name in grants else "CC-BY-SA-4.0",
            "publisher_scene_text": grants.get(name),
            "basis": "permissions.txt override" if name in grants else "Publisher dataset license",
        }
        selected.append(pair)
        seen_hashes.update(identities)
    if not selected:
        raise ValueError("No eligible new paired scenes")
    records = [r for pair in selected for key in ["clean", "noisy"] for r in pair[key]]
    return {
        "format_version": 1,
        "split": "quarantine",
        "selection": selected,
        "excluded": excluded,
        "catalog_scenes": len(dataset["Bayer"]),
        "files": len(records),
        "bytes": sum(r["bytes"] for r in records),
        "dataset_license": version["license"],
        "dataset_doi": "10.14428/DVN/DEQCIM",
        "catalog_url": CATALOG_URL,
        "dataset_version": f"{version['versionNumber']}.{version['versionMinorNumber']}",
        "attribution": "Benoit Brummer and Christophe De Vleeschouwer, Raw Natural Image Noise Dataset. Individual CC0 credits in permissions.txt.",
        "selection_rule": "All metadata-eligible new Bayer scenes in sorted order; up to two filename-ordered clean frames, noisy ISO nearest1600 and highest remaining <=12800. No image quality or model scores enter selection.",
        "exclusions": {"scene_families": list(EXCLUDED_FAMILIES), "protected_names": sorted(blocked_names), "blocked_source_sha1": sorted(blocked_hashes)},
        "usage": "Quarantine only. Not training admission or an evaluation split. Review cached protected/Commons overlap, content, camera metadata and registration before any separate opt-in training extension.",
    }


def fetch(catalog, protected_path, output, *, download=False, workers=1, reserve_gib=512):
    if workers not in (1, 2) or reserve_gib < 64:
        raise ValueError("Use one or two workers and at least64GiB free reserve")
    catalog, protected_path = Path(catalog).resolve(), Path(protected_path).resolve()
    paths = [catalog / n for n in ["dataverse-metadata.json", "dataset.yaml", "permissions.txt", "manifest-train.json"]]
    paths.append(protected_path)
    version = json.loads(paths[0].read_text())["data"]["latestVersion"]
    lookup = {r["dataFile"]["filename"]: r for r in version["files"]}
    for path in paths[1:3]:
        entry = lookup[path.name]
        if entry.get("restricted"):
            raise ValueError("Publisher restricts auxiliary metadata")
        item = entry["dataFile"]
        verify_file(path, {"filename": path.name, "bytes": item["filesize"], "publisher_checksum": item["checksum"]})
    plan = plan_extension(
        yaml.safe_load(paths[1].read_text()), version, paths[2].read_text(),
        json.loads(protected_path.read_text()), json.loads(paths[3].read_text()),
    )
    plan["inputs"] = {str(p): sha(p) for p in paths}
    plan["script_sha256"] = sha(__file__)
    plan["paired_source_sha256"] = sha(inspect.getsourcefile(select_pairs))
    plan["runtime"] = {"workers": workers, "reserve_gib": reserve_gib}
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".download.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = output / "plan-quarantine.json"
        encoded = json.dumps(plan, indent=2) + "\n"
        if path.exists() and path.read_text() != encoded:
            raise ValueError("Frozen quarantine plan differs; use a new output")
        path.write_text(encoded)
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for p in [*paths, Path(__file__), Path(inspect.getsourcefile(select_pairs))]:
            (archive / p.name).write_bytes(p.read_bytes())
        print(json.dumps({"event": "quarantine-plan", "scenes": len(plan["selection"]), "files": plan["files"], "bytes": plan["bytes"], "download": download}), flush=True)
        if not download:
            return plan
        records = [r for pair in plan["selection"] for role in ["clean", "noisy"] for r in pair[role]]

        def acquire(record):
            if shutil.disk_usage(output).free < reserve_gib * 2**30 + workers * record["bytes"]:
                raise RuntimeError("Quarantine download reached its free-space reserve")
            if record["url"] != DATA_URL + str(record["file_id"]):
                raise ValueError("Source URL is not the frozen publisher endpoint")
            return download_file(output / "files", record)

        verified = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for record in pool.map(acquire, records):
                verified[record["filename"]] = record
                progress = {"event": "quarantine-verified", "files_done": len(verified), "files_total": len(records), "filename": record["filename"], "bytes": record["bytes"]}
                temporary = output / "progress.tmp"
                temporary.write_text(json.dumps(progress, indent=2) + "\n")
                temporary.replace(output / "progress.json")
                print(json.dumps(progress), flush=True)
        result = json.loads(encoded)
        for pair in result["selection"]:
            for role in ["clean", "noisy"]:
                pair[role] = [verified[r["filename"]] for r in pair[role]]
        assert all(sha(p) == digest for p, digest in plan["inputs"].items())
        temporary = output / "manifest-quarantine.tmp"
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(output / "manifest-quarantine.json")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("/mnt/external/demosaic/references/rawnind-train32"))
    parser.add_argument("--protected", type=Path, default=Path("/mnt/external/demosaic/audits/public-raw-protected-scenes-v2/result.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reserve-gib", type=int, default=512)
    args = parser.parse_args()
    fetch(args.catalog, args.protected, args.output, download=args.download, workers=args.workers, reserve_gib=args.reserve_gib)
