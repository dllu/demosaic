"""SHA-pinned private training admissions; source pixels and receipts stay local."""

import hashlib
import json
from pathlib import Path

import numpy as np

from .safety import writable_path

# Reviewed source-only quality, protected-scene overlap and conservative grouping:
# docs/personal-native-quarantine.md. Only the receipt digest is public.
REVIEWED_PERSONAL_ADMISSIONS = frozenset(
    {
        "7779bda630bfba62b463742915747b5dbcedb54195227bdfb62d8e9c74ae4927",
    }
)


def approved_personal_rows(manifest):
    admission = manifest.get("personal_raw_admission")
    if admission is None:
        return {}
    if manifest.get("format_version") != 2 or manifest.get("split") != "train":
        raise ValueError("Personal RAW targets require an explicitly admitted train manifest")
    payload = admission.get("payload", "").encode()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != admission.get("sha256") or digest not in REVIEWED_PERSONAL_ADMISSIONS:
        raise ValueError("Personal RAW admission is unreviewed or its checksum changed")
    receipt = json.loads(payload)
    if (
        receipt.get("kind") != "reviewed-personal-raw-admission-v1"
        or receipt.get("status") != "reviewed"
    ):
        raise ValueError("Expected a completed personal RAW admission review")
    result = {}
    for item in receipt["approved"]:
        raw = item["quarantine_record"]
        if (
            raw["split"] != "quarantine"
            or raw["source_family"] != "personally-authorized-RAW"
            or raw["id"] != raw["source"]["sha256"]
            or not raw["source"].get("original_path")
            or not raw.get("permission")
            or not item["training_scene"]
        ):
            raise ValueError("Personal RAW identity/permission differs from admission")
        for cache in raw["caches"]:
            key = (raw["id"], cache["bin_factor"])
            if key in result or cache["bin_factor"] not in (4, 8):
                raise ValueError("Duplicated or unsupported personal RAW cache")
            if cache["dtype"] != "uint16" or cache["color_space"] != "linear-camera-RGB":
                raise ValueError("Personal targets must retain camera-linear uint16 values")
            result[key] = {
                "id": raw["id"],
                "split": "train",
                "scene": item["training_scene"],
                "source_family": raw["source_family"],
                "source": raw["source"],
                "permission": raw["permission"],
                "raw_metadata": raw["raw_metadata"],
                "raw_shape": raw["raw_shape"],
                "cache": cache["path"],
                "cache_sha256": cache["sha256"],
                "shape": cache["shape"],
                "color_space": cache["color_space"],
                "dtype": cache["dtype"],
                "bin_factor": cache["bin_factor"],
                "personal_admission_sha256": digest,
                "target_label": "camera-linear low-noise phase-bin estimate; not exact noiseless GT",
            }
    if not result:
        raise ValueError("Personal RAW admission contains no approved sources")
    return result


def extend_personal_targets(base_manifest, admission_path, output):
    """Publish a separate private manifest preserving all existing native rows."""
    import fcntl
    import shutil

    from .raw_clean import RawCleanDataset

    base_manifest = Path(base_manifest).resolve()
    base_payload = base_manifest.read_bytes()
    base = json.loads(base_payload)
    if base.get("personal_raw_admission") is not None:
        raise ValueError("Choose a base without an existing personal RAW extension")
    factors = {row["bin_factor"] for row in base["rows"]}
    if len(factors) != 1 or not factors <= {4, 8}:
        raise ValueError("Expected one native bin factor, 4 or 8")
    factor = next(iter(factors))
    downsample = 2 if factor == 4 else 1
    RawCleanDataset(base_manifest, augmentation_downsample=downsample)
    payload = Path(admission_path).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    result = {
        **base,
        "format_version": 2,
        "split": "train",
        "rows": [],
        "recipe": {
            "kind": "reviewed-native-personal-extension-v1",
            "bin_factor": factor,
            "base_manifest": str(base_manifest),
            "base_manifest_sha256": hashlib.sha256(base_payload).hexdigest(),
            "admission_path": str(Path(admission_path).resolve()),
            "admission_sha256": digest,
        },
        "personal_raw_admission": {"sha256": digest, "payload": payload.decode()},
        "notes": [
            *base.get("notes", []),
            "Private user-authorized targets and receipt; no public redistribution grant.",
            "Separate opt-in extension; existing source/cache files remain unchanged.",
            "Camera-linear low-noise estimates; not exact noiseless GT.",
        ],
    }
    allowed = approved_personal_rows(result)
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
            raise ValueError("Personal source overlaps an existing native source")
        path = Path(row["cache"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["cache_sha256"]:
            raise ValueError("Personal target cache checksum changed")
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if list(array.shape) != row["shape"] or array.dtype != np.uint16 or array.shape[-1] != 3:
            raise ValueError("Personal target cache header differs from admission")
        if min(array.shape[:2]) < 256 * downsample:
            raise ValueError("Personal target cache is too small")
        seen.add(identity)
        result["rows"].append(row)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another personal extension owns this output") from None
        if (output / "manifest.json").exists():
            raise ValueError("Choose a new personal extension output")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for path in [
            Path(__file__),
            Path(__file__).with_name("raw_clean.py"),
            Path(__file__).with_name("raw_admission.py"),
        ]:
            shutil.copyfile(path, archive / path.name)
        (archive / "base-manifest.json").write_bytes(base_payload)
        (archive / "admission.json").write_bytes(payload)
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        RawCleanDataset(temporary, augmentation_downsample=downsample)
        temporary.replace(output / "manifest.json")
    return result
