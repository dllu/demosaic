"""Read-only Commons ingestion with attribution and source-disjoint splits."""

import hashlib
import io
import json
import re
import sqlite3
from collections import deque
from concurrent.futures import ThreadPoolExecutor
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
    source: Path,
    destination: Path,
    *,
    limit=0,
    factor=8,
    min_size=256,
    max_pixels=120_000_000,
    workers=2,
    selection_manifest=None,
):
    """Atomic caches; restart safely reuses finished samples. Never alter source."""
    source, destination = source.resolve(), writable_path(destination)
    if destination == source or source in destination.parents:
        raise ValueError("Choose a separate output directory, outside the source corpus")
    destination.mkdir(parents=True, exist_ok=True)
    if not 1 <= workers <= 8 or factor < 1 or min_size < 1 or limit < 0:
        raise ValueError("Invalid worker count, binning, size or limit")
    import fcntl

    # OS lock protects this destination only; never interrupt other work.
    lock = (destination / ".prepare.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError(f"Another preparation job owns {destination}") from None
    recipe = {
        "version": 1,
        "factor": factor,
        "source": str(source),
        "transfer": "linear-sRGB",
        "dtype": "uint16",
    }
    selection = None
    if selection_manifest is not None:
        payload = Path(selection_manifest).read_bytes()
        recipe["selection_manifest_sha256"] = hashlib.sha256(payload).hexdigest()
        selection = [json.loads(line) for line in payload.splitlines()]
    recipe_path = destination / "recipe.json"
    if recipe_path.exists() and json.loads(recipe_path.read_text()) != recipe:
        lock.close()
        raise ValueError("Cache recipe differs; choose a new destination")
    recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
    query = """SELECT title, page_url, original_url, author, license, license_url,
        attribution, credit, sha1, sha1_hex, download_path, width, height
        FROM images WHERE status='downloaded' AND width>=? AND height>=?
        AND width*height<=? ORDER BY sha1"""
    if selection is None:
        # Honour committed WAL rows while the downloader runs. Materialize just
        # metadata, then release the read snapshot before lengthy image work so
        # a long preparation cannot pin the downloader's WAL/checkpoints.
        connection = sqlite3.connect(f"file:{source / 'quality_images.sqlite3'}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            selection = [
                dict(row)
                for row in connection.execute(
                    query, (min_size * factor, min_size * factor, max_pixels)
                )
            ]
        finally:
            connection.close()
    counts = {"train": 0, "val": 0, "test": 0, "failed": 0, "unlicensed": 0}
    seen = set()
    manifest_tmp = destination / "manifest.jsonl.tmp"
    errors_tmp = destination / "errors.jsonl.tmp"

    def records():
        for row in selection:
            if row.get("split", "train") not in ("train", "val", "test"):
                continue
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
                split=row.get("split", split_for(key)),
                bin_factor=factor,
                color_space="linear-sRGB",
                dtype="uint16",
            )
            cache = destination / "images" / key[:2] / f"{key}.npy"
            record["cache"] = str(cache.relative_to(destination))
            yield record

    iterator = iter(records())
    # Bounded prefetch: never queue the whole corpus or many decoded originals.
    with (
        ThreadPoolExecutor(max_workers=workers) as pool,
        manifest_tmp.open("w") as output,
        errors_tmp.open("w") as errors,
    ):
        pending = deque()
        exhausted = False
        total = 0
        while pending or not exhausted:
            while not exhausted and len(pending) < 2 * workers:
                record = next(iterator, None)
                if record is None:
                    exhausted = True
                    break
                pending.append(
                    pool.submit(
                        prepare_one, record, source, destination, factor, min_size, max_pixels
                    )
                )
            if not pending:
                break
            record, error = pending.popleft().result()
            if error is None:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[record["split"]] += 1
                total += 1
            else:
                counts["failed"] += 1
                errors.write(json.dumps({"id": record["id"], "error": error}) + "\n")
                continue
            if total % 50 == 0:
                output.flush()
                print(json.dumps({"prepared": total, **counts}), flush=True)
            if limit and total >= limit:
                for future in pending:
                    future.cancel()
                break
    manifest_tmp.replace(destination / "manifest.jsonl")
    errors_tmp.replace(destination / "errors.jsonl")
    (destination / "summary.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts), flush=True)
    lock.close()
    return counts


def prepare_one(record, source, destination, factor, min_size, max_pixels):
    cache = destination / record["cache"]
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
                profile = ImageCms.ImageCmsProfile(io.BytesIO(icc)) if icc else None
                # Gray profiles describe gray samples, not three RGB channels.
                # Preserve that interpretation until the ICC transform outputs
                # sRGB. Other inputs retain the existing RGB conversion path.
                gray = (
                    profile is not None
                    and image.mode in ("1", "L", "LA")
                    and profile.profile.xcolor_space.strip() == "GRAY"
                )
                image = image.convert("L" if gray else "RGB")
                if profile is not None:
                    image = ImageCms.profileToProfile(
                        image,
                        profile,
                        ImageCms.createProfile("sRGB"),
                        outputMode="RGB",
                    )
                binned = bin_linear(image, factor)
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.with_suffix(".tmp").open("wb") as handle:
                np.save(handle, binned, allow_pickle=False)
            cache.with_suffix(".tmp").replace(cache)
        array = np.load(cache, mmap_mode="r", allow_pickle=False)
        if (
            array.dtype != np.uint16
            or array.ndim != 3
            or array.shape[-1] != 3
            or min(array.shape[:2]) < min_size
        ):
            raise ValueError("Invalid cache dimensions or dtype")
        record["shape"] = array.shape
        record["cache_sha256"] = hashlib.sha256(cache.read_bytes()).hexdigest()
        return record, None
    except (OSError, ValueError, SyntaxError, ImageCms.PyCMSError) as error:
        return record, str(error)
