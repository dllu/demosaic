"""Verified acquisition of commercially usable paired RAW evaluation data."""

import hashlib
import json
import math
import re
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .safety import writable_path

CATALOG_URL = (
    "https://dataverse.uclouvain.be/api/datasets/:persistentId/"
    "?persistentId=doi:10.14428/DVN/DEQCIM"
)
DATA_URL = "https://dataverse.uclouvain.be/api/access/datafile/"
DEVELOPMENT_SCENES = ("2pilesofplates", "7D-1", "MuseeL-CopteArch-C500D", "D60-2")
RAW_SUFFIXES = {
    ".arw",
    ".cr2",
    ".cr3",
    ".crw",
    ".dng",
    ".nef",
    ".nrw",
    ".orf",
    ".pef",
    ".raf",
    ".raw",
    ".rw2",
    ".rwl",
    ".srw",
    ".3fr",
}


def iso_label(filename, *, required=True):
    match = re.search(r"_ISO(\d+)_sha1=", filename)
    if not match:
        if not required:
            return None
        raise ValueError(f"Missing ISO label in publisher filename: {filename}")
    return int(match[1])


def select_pairs(dataset, files, split, *, scenes=None):
    """Freeze selection from metadata alone; never use image quality or predictions.

    Development scenes are outside the publisher's test reserve. RawNIND's
    pretrained comparator may have seen them, so they are not an unbiased test
    of that comparator. Official test scenes remain separate from development.
    """
    if split not in ("development", "test"):
        raise ValueError("Split must be development or test")
    lookup = {entry["dataFile"]["filename"]: entry for entry in files}
    bayer = dataset["Bayer"]
    if scenes is None:
        scenes = (
            DEVELOPMENT_SCENES
            if split == "development"
            else sorted(name for name, row in bayer.items() if row.get("test_reserve"))
        )
    if not scenes or len(set(scenes)) != len(scenes):
        raise ValueError("Select at least one unique scene")
    output = []
    for scene in scenes:
        row = bayer[scene]
        filenames = [x["filename"] for x in row["clean_images"] + row["noisy_images"]]
        reserved = bool(row.get("test_reserve")) or any("_TEST_" in name for name in filenames)
        if reserved != (split == "test"):
            raise ValueError(f"Scene {scene} belongs to the other split")
        # The published descriptor also lists XMP sidecars as clean images.
        clean = sorted(
            (x for x in row["clean_images"] if Path(x["filename"]).suffix.lower() in RAW_SUFFIXES),
            key=lambda x: x["filename"],
        )[:2]
        candidates = [
            x
            for x in row["noisy_images"]
            if Path(x["filename"]).suffix.lower() in RAW_SUFFIXES
            and (label := iso_label(x["filename"], required=False)) is not None
            and 0 < label <= 12800
        ]
        if len(candidates) < 2 or not clean:
            raise ValueError(f"Scene {scene} lacks the required clean/noisy observations")
        moderate = min(
            candidates,
            key=lambda x: (abs(math.log2(iso_label(x["filename"]) / 1600)), x["filename"]),
        )
        remaining = [x for x in candidates if x["filename"] != moderate["filename"]]
        high = max(remaining, key=lambda x: (iso_label(x["filename"]), x["filename"]))

        def describe(image, role):
            entry = lookup[image["filename"]]
            if entry.get("restricted"):
                raise ValueError(f"Publisher restricts {image['filename']}")
            file = entry["dataFile"]
            return {
                "filename": file["filename"],
                "file_id": int(file["id"]),
                "bytes": int(file["filesize"]),
                "publisher_checksum": file["checksum"],
                "sha1": image["sha1"],
                "iso_label": iso_label(file["filename"], required=role != "reference"),
                "role": role,
                "url": DATA_URL + str(int(file["id"])),
            }

        output.append(
            {
                "scene": scene,
                "split": split,
                "unknown_sensor": bool(row.get("unknown_sensor")),
                "clean": [describe(x, "reference") for x in clean],
                "noisy": [
                    describe(x, "noisy")
                    for x in sorted(
                        (moderate, high), key=lambda x: (iso_label(x["filename"]), x["filename"])
                    )
                ],
            }
        )
    return output


def verify_file(path, record):
    digests = {name: hashlib.new(name) for name in ("md5", "sha1", "sha256")}
    size = 0
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            size += len(chunk)
            for digest in digests.values():
                digest.update(chunk)
    expected = record["publisher_checksum"]
    algorithm = expected["type"].lower().replace("-", "")
    if algorithm not in digests:
        raise ValueError(f"Unsupported publisher checksum {algorithm}")
    if size != record["bytes"] or digests[algorithm].hexdigest() != expected["value"].lower():
        raise ValueError(f"Publisher size/checksum mismatch for {record['filename']}")
    if record.get("sha1") and digests["sha1"].hexdigest() != record["sha1"]:
        raise ValueError(f"Filename SHA1 mismatch for {record['filename']}")
    return {**record, "sha256": digests["sha256"].hexdigest(), "path": str(Path(path).resolve())}


def download_file(directory, record):
    filename = record["filename"]
    if filename in (".", "..") or Path(filename).name != filename or "\\" in filename:
        raise ValueError(f"Unsafe publisher filename {filename!r}")
    directory = writable_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = writable_path(directory / filename)
    if destination.exists():
        return verify_file(destination, record)
    for attempt in range(3):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=directory, prefix=".download-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                with urllib.request.urlopen(record["url"], timeout=60) as response:
                    while chunk := response.read(1 << 20):
                        handle.write(chunk)
            verified = verify_file(temporary, record)
            if destination.exists():
                return verify_file(destination, record)
            temporary.replace(destination)
            temporary = None
            return {**verified, "path": str(destination)}
        except (OSError, urllib.error.URLError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)  # Only our unique temporary file.
    raise RuntimeError("Unreachable download state")


def fetch_paired(output, *, split="development", workers=2, scenes=None):
    if not 1 <= workers <= 4:
        raise ValueError("Use one to four download workers")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    catalog = writable_path(output / "dataverse-metadata.json")
    if not catalog.exists():
        payload = urllib.request.urlopen(CATALOG_URL, timeout=60).read()
        json.loads(payload)["data"]["latestVersion"]  # Reject an error document.
        catalog.write_bytes(payload)
    payload = catalog.read_bytes()
    version = json.loads(payload)["data"]["latestVersion"]
    license = version["license"]
    if license.get("rightsIdentifier") != "CC-BY-SA-4.0":
        raise ValueError("Publisher license differs from the reviewed commercially usable release")
    files = version["files"]
    auxiliary = []
    for entry in files:
        file = entry["dataFile"]
        if file["filename"] in ("dataset.yaml", "permissions.txt"):
            record = {
                "filename": file["filename"],
                "file_id": file["id"],
                "bytes": file["filesize"],
                "publisher_checksum": file["checksum"],
                "url": DATA_URL + str(file["id"]),
            }
            auxiliary.append(download_file(output, record))
    dataset = yaml.safe_load((output / "dataset.yaml").read_text())
    pairs = select_pairs(dataset, files, split, scenes=scenes)
    plan = {
        "split": split,
        "selection": pairs,
        "catalog_sha256": hashlib.sha256(payload).hexdigest(),
    }
    plan_path = writable_path(output / f"plan-{split}.json")
    plan_text = json.dumps(plan, indent=2) + "\n"
    if plan_path.exists() and plan_path.read_text() != plan_text:
        raise ValueError("This output directory already has a different selection; choose another")
    plan_path.write_text(plan_text)
    records = {r["filename"]: r for pair in pairs for key in ("clean", "noisy") for r in pair[key]}
    print(
        json.dumps(
            {
                "event": "paired-plan",
                "split": split,
                "scenes": len(pairs),
                "files": len(records),
                "bytes": sum(r["bytes"] for r in records.values()),
            }
        ),
        flush=True,
    )
    verified = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(lambda r: download_file(output / "files", r), records.values())
        for record in results:
            verified[record["filename"]] = record
            print(
                json.dumps(
                    {
                        "event": "paired-verified",
                        "filename": record["filename"],
                        "bytes": record["bytes"],
                    }
                ),
                flush=True,
            )
    for pair in pairs:
        for key in ("clean", "noisy"):
            pair[key] = [verified[r["filename"]] for r in pair[key]]
    result = {
        **plan,
        "selection": pairs,
        "format_version": 1,
        "catalog_url": CATALOG_URL,
        "dataset_doi": "10.14428/DVN/DEQCIM",
        "dataset_version": f"{version['versionNumber']}.{version['versionMinorNumber']}",
        "dataset_license": license,
        "auxiliary": auxiliary,
        "attribution": "Benoit Brummer and Christophe De Vleeschouwer, Raw Natural Image Noise Dataset (2025). See permissions.txt for individual scene credits and CC0 grants.",
        "selection_rule": "Up to two clean frames; noisy ISO nearest 1600 plus highest remaining ISO <=12800; metadata-only selection.",
        "usage": "Evaluation only. These images are not added to the Commons training manifest.",
        "development_caveat": "RawNIND may have trained on development scenes. Keep publisher test scenes separate until final model selection.",
    }
    writable_path(output / f"manifest-{split}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
