"""Read-only Commons ingestion with attribution and source-disjoint splits."""

import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps

from .color import srgb_to_linear
from .safety import writable_path


def split_for(key: str) -> str:
    value = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100
    return "test" if value < 5 else "val" if value < 10 else "train"


def free_license(name: str) -> bool:
    return bool(re.fullmatch(r"CC BY(?:-SA)? [1-4]\.\d(?: [a-z-]+)?", name or "")) or name in {
        "CC0",
        "Public domain",
    }


def bin_linear(image: Image.Image, factor=8) -> np.ndarray:
    """Average *linear* source samples in bounded row bands; retain 16 bits."""
    if factor < 1:
        raise ValueError("Binning factor must be positive")
    width, height = image.size
    width, height = width // factor, height // factor
    if min(width, height) < 1:
        raise ValueError("Image too small for binning")
    result = np.empty((height, width, 3), np.uint16)
    for top in range(0, height, 32):
        rows = min(32, height - top)
        band = (
            np.asarray(
                image.crop((0, top * factor, width * factor, (top + rows) * factor)),
                dtype=np.float32,
            )
            / 255
        )
        band = srgb_to_linear(band)
        mean = band.reshape(rows, factor, width, factor, 3).mean(axis=(1, 3))
        result[top : top + rows] = np.rint(mean * 65535).astype(np.uint16)
    return result


def prepare_commons(
    source: Path, destination: Path, *, limit=0, factor=8, min_size=256, max_pixels=120_000_000
):
    """Atomic caches; restart safely reuses finished samples. Never alter source."""
    source, destination = source.resolve(), writable_path(destination)
    if destination == source or source in destination.parents:
        raise ValueError("Choose a separate output directory, outside the source corpus")
    destination.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        f"file:{source / 'quality_images.sqlite3'}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    query = """SELECT title, page_url, original_url, author, license, license_url,
        attribution, credit, sha1, sha1_hex, download_path, width, height
        FROM images WHERE status='downloaded' AND width>=? AND height>=?
        AND width*height<=? ORDER BY sha1"""
    counts = {"train": 0, "val": 0, "test": 0, "failed": 0, "unlicensed": 0}
    seen = set()
    manifest_tmp = destination / "manifest.jsonl.tmp"
    errors_tmp = destination / "errors.jsonl.tmp"
    with manifest_tmp.open("w") as output, errors_tmp.open("w") as errors:
        for row in connection.execute(query, (min_size * factor, min_size * factor, max_pixels)):
            record = dict(row)
            if not free_license(record["license"]):
                counts["unlicensed"] += 1
                continue
            key = record["sha1_hex"] or record["sha1"]
            if not key or key in seen:
                continue
            seen.add(key)
            record.update(
                id=key,
                split=split_for(key),
                bin_factor=factor,
                color_space="linear-sRGB",
                dtype="uint16",
            )
            cache = destination / "images" / key[:2] / f"{key}.npy"
            record["cache"] = str(cache.relative_to(destination))
            try:
                original = (source / record["download_path"]).resolve()
                if source not in original.parents:
                    raise ValueError("Image path escapes corpus")
                if not cache.exists():
                    with Image.open(original) as image:
                        if image.width * image.height > max_pixels:
                            raise ValueError("Image exceeds pixel budget")
                        image = ImageOps.exif_transpose(image)
                        icc = image.info.get("icc_profile")
                        image = image.convert("RGB")
                        if icc:
                            image = ImageCms.profileToProfile(
                                image,
                                ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                ImageCms.createProfile("sRGB"),
                                outputMode="RGB",
                            )
                        binned = bin_linear(image, factor)
                    if min(binned.shape[:2]) < min_size:
                        raise ValueError("Actual dimensions too small")
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    with cache.with_suffix(".tmp").open("wb") as handle:
                        np.save(handle, binned, allow_pickle=False)
                    cache.with_suffix(".tmp").replace(cache)
                shape = np.load(cache, mmap_mode="r", allow_pickle=False).shape
                record["shape"] = shape
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[record["split"]] += 1
            except (OSError, ValueError, SyntaxError, ImageCms.PyCMSError) as error:
                counts["failed"] += 1
                errors.write(json.dumps({"id": key, "error": str(error)}) + "\n")
                continue
            total = sum(counts[s] for s in ("train", "val", "test"))
            if total % 50 == 0:
                output.flush()
                print(json.dumps({"prepared": total, **counts}), flush=True)
            if limit and total >= limit:
                break
    connection.close()
    manifest_tmp.replace(destination / "manifest.jsonl")
    errors_tmp.replace(destination / "errors.jsonl")
    (destination / "summary.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts), flush=True)
    return counts
