"""Reviewed public RAW provenance and separate native-target extensions."""

import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np

from .safety import writable_path

# Deliberate data admission, reviewed in docs/public-raw-pilot.md and
# docs/public-raw-expansion-v2.md. Merely
# changing a quarantine manifest's split must never enable training.
REVIEWED_ADMISSIONS = frozenset({
    "367b12e3b64817ce06ba0791c4131c2bc77a75971dac2ede03fe227b732ffce0",
    "7b1eb85c10d738875f6e0abdda5274ed900c42783b48e0a6987e83d9e76ce591",
})


def approved_public_rows(manifest):
    """Return exact allowed rows from an embedded, SHA-pinned review receipt."""
    admission = manifest.get("public_raw_admission")
    if admission is None:
        return {}
    if manifest.get("format_version") != 2 or manifest.get("split") != "train":
        raise ValueError("Public RAW targets require an explicitly admitted train manifest")
    payload = admission.get("payload", "").encode()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != admission.get("sha256") or digest not in REVIEWED_ADMISSIONS:
        raise ValueError("Public RAW admission is unreviewed or its checksum changed")
    receipt = json.loads(payload)
    if receipt.get("kind") != "reviewed-public-raw-admission-v1" or receipt.get("status") != "reviewed":
        raise ValueError("Expected a completed public RAW admission review")
    result = {}
    for raw in receipt["approved"]:
        source = raw["source"]
        if (
            raw["split"] != "quarantine"
            or raw["id"] != source["sha256"]
            or source["license"] != "CC0-1.0"
            or source["license_url"] != "https://creativecommons.org/publicdomain/zero/1.0/"
            or urlsplit(source["url"]).netloc != "raw.pixls.us"
            or source["publisher_checksum"] != {"type": "SHA-256", "value": raw["id"]}
        ):
            raise ValueError("Public RAW source/license identity differs from admission")
        for cache in raw["caches"]:
            key = (raw["id"], cache["bin_factor"])
            if key in result or cache["bin_factor"] not in (4, 8):
                raise ValueError("Duplicated or unsupported public RAW cache")
            if cache["dtype"] != "uint16" or cache["color_space"] != "linear-camera-RGB":
                raise ValueError("Public RAW targets must retain camera-linear uint16 values")
            result[key] = {
                "id": raw["id"], "split": "train",
                "scene": f"public-raw-pixls-{raw['file_id']}",
                "source_family": "reviewed-raw-pixls-cc0",
                "source": source, "raw_metadata": raw["raw_metadata"],
                "raw_shape": raw["raw_shape"], "cache": cache["path"],
                "cache_sha256": cache["sha256"], "shape": cache["shape"],
                "color_space": cache["color_space"], "dtype": cache["dtype"],
                "bin_factor": cache["bin_factor"],
                "license": {"rightsIdentifier": "CC0-1.0", "uri": source["license_url"]},
                "attribution": f"raw.pixls.us file {raw['file_id']}; {source['url']}; CC0-1.0",
                "public_admission_sha256": digest,
            }
    if not result:
        raise ValueError("Public RAW admission contains no approved sources")
    return result


def extend_native_targets(base_manifest, admission_path, output):
    """Freeze a new dataset, preserving every base target and source identity."""
    import fcntl

    from .raw_clean import RawCleanDataset

    base_manifest = Path(base_manifest).resolve()
    base_payload = base_manifest.read_bytes()
    base = json.loads(base_payload)
    if base.get("public_raw_admission") is not None:
        raise ValueError("Choose the original native manifest, not an existing extension")
    factors = {row["bin_factor"] for row in base["rows"]}
    if len(factors) != 1 or not factors <= {4, 8}:
        raise ValueError("Expected one native bin factor, 4 or 8")
    factor = next(iter(factors))
    RawCleanDataset(base_manifest, augmentation_downsample=2 if factor == 4 else 1)
    payload = Path(admission_path).read_bytes()
    result = {
        "format_version": 2, "split": "train",
        "recipe": {
            "kind": "reviewed-native-public-extension-v1", "bin_factor": factor,
            "base_manifest": str(base_manifest),
            "base_manifest_sha256": hashlib.sha256(base_payload).hexdigest(),
            "admission_path": str(Path(admission_path).resolve()),
            "admission_sha256": hashlib.sha256(payload).hexdigest(),
        },
        "public_raw_admission": {"sha256": hashlib.sha256(payload).hexdigest(), "payload": payload.decode()},
        "rows": [],
        "notes": [
            "Separate opt-in extension; base/quarantine manifests and caches stay unchanged.",
            "Camera-linear low-noise phase-bin estimates, not exact noiseless RGB GT.",
            "No demosaicer, WB, matrix, gamma or 8-bit stage applied to target caches.",
            "Source clipping/chart exclusions and protected-scene review are pinned in admission.",
        ],
    }
    allowed = approved_public_rows(result)
    seen = set()
    for original in base["rows"]:
        row = {**original, "cache": str((base_manifest.parent / original["cache"]).resolve())}
        if row["id"] in seen:
            raise ValueError("Duplicate source in base native manifest")
        seen.add(row["id"])
        result["rows"].append(row)
    for (identity, cache_factor), row in allowed.items():
        if cache_factor != factor:
            continue
        if identity in seen:
            raise ValueError("Public source overlaps an existing native source")
        path = Path(row["cache"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["cache_sha256"]:
            raise ValueError("Public target cache checksum changed")
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if list(array.shape) != row["shape"] or array.dtype != np.uint16 or array.shape[-1] != 3:
            raise ValueError("Public target cache header differs from admission")
        if min(array.shape[:2]) < 256 * (2 if factor == 4 else 1):
            raise ValueError("Public target cache is too small")
        seen.add(identity)
        result["rows"].append(row)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another native extension owns this output") from None
        if (output / "manifest.json").exists():
            raise ValueError("Choose a new native extension output")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for path in [Path(__file__), Path(__file__).with_name("raw_clean.py")]:
            shutil.copyfile(path, archive / path.name)
        (archive / "base-manifest.json").write_bytes(base_payload)
        (archive / "admission.json").write_bytes(payload)
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        # Validate the complete candidate before publishing it to a trainer.
        RawCleanDataset(temporary, augmentation_downsample=2 if factor == 4 else 1)
        temporary.replace(output / "manifest.json")
    return result
