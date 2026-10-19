"""Render all source thumbnails from a completed Commons cache manifest.

These deliberately resized source-review sheets are not native performance
crops. Rendering does not review, approve or admit any image to training.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
from PIL import Image, ImageDraw

FIELDS = [
    "title",
    "page_url",
    "original_url",
    "author",
    "license",
    "license_url",
    "attribution",
    "credit",
    "sha1",
    "sha1_hex",
    "download_path",
    "width",
    "height",
]


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def preview(array, width=136, height=96):
    scale = min(width / array.shape[1], height / array.shape[0])
    target = (
        min(width, max(1, round(array.shape[1] * scale))),
        min(height, max(1, round(array.shape[0] * scale))),
    )
    channels = []
    for channel in range(3):
        plane = Image.fromarray(array[..., channel].astype(np.float32) / 65535)
        channels.append(np.asarray(plane.resize(target, Image.Resampling.BOX)))
    linear = np.stack(channels, 2)
    srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    return Image.fromarray(np.rint(np.clip(srgb, 0, 1) * 255).astype(np.uint8))


def inventory(manifest, selection):
    if manifest.name.endswith(".tmp"):
        raise ValueError("Never review a partial cache manifest")
    records = [json.loads(line) for line in manifest.read_text().splitlines()]
    expected = {r["sha1_hex"]: r for r in json.loads(selection.read_text())}
    if len(expected) != len(records) or {r["id"] for r in records} != set(expected):
        raise ValueError("Complete selected-source coverage is required")
    for row in records:
        if any(row[field] != expected[row["id"]][field] for field in FIELDS):
            raise ValueError("Prepared source attribution/identity changed")
        cache = (manifest.parent / row["cache"]).resolve()
        if not cache.is_relative_to("/mnt/external/demosaic"):
            raise ValueError("Source contact sheets must use external SSD caches")
        if (
            row["dtype"] != "uint16"
            or row["color_space"] != "linear-sRGB"
            or row["bin_factor"] not in {4, 8}
        ):
            raise ValueError("Unexpected source-review pixel recipe")
        row["cache"] = str(cache)
    return records


def render(manifest, selection, output):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to("/mnt/external/demosaic"):
        raise ValueError("Use a fresh external demosaic contact root")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Hide CUDA for source review")
    bindings = [ref(manifest), ref(selection), ref(__file__)]
    records = inventory(manifest, selection)
    output.mkdir(parents=True)
    # Preserve the exact executed renderer with each independently viewable set.
    shutil.copyfile(__file__, output / "executed-renderer.py")
    os.nice(10)
    started = time.monotonic()
    contacts = []
    for page in range(math.ceil(len(records) / 100)):
        if (
            psutil.virtual_memory().available < 48 * 2**30
            or shutil.disk_usage(output).free < 548 * 2**30
            or time.monotonic() - started > 3600
        ):
            raise RuntimeError("Source review exceeded declared RAM/disk/time reserves")
        sheet = Image.new("RGB", (1400, 1200), "#e8e8e8")
        draw = ImageDraw.Draw(sheet)
        group = records[page * 100 : (page + 1) * 100]
        for cell, row in enumerate(group):
            if ref(row["cache"])["sha256"] != row["cache_sha256"]:
                raise ValueError("Source-review cache bytes changed")
            array = np.load(row["cache"], mmap_mode="r", allow_pickle=False)
            if array.dtype != np.uint16 or list(array.shape) != row["shape"] or array.shape[2] != 3:
                raise ValueError("Source-review cache header changed")
            image = preview(array)
            x, y = cell % 10 * 140, cell // 10 * 120
            sheet.paste(image, (x + (140 - image.width) // 2, y + (96 - image.height) // 2))
            draw.text(
                (x + 3, y + 98),
                f"{page * 100 + cell:04d} {row['split'][0].upper()} {row['id'][:7]}",
                fill="black",
            )
            draw.text((x + 3, y + 109), row["title"].removeprefix("File:")[:21], fill="black")
        path = output / f"content-{page:02d}.png"
        sheet.save(path)
        contacts.append(
            {
                "PNG": ref(path),
                "indices": [page * 100, page * 100 + len(group) - 1],
                "count": len(group),
            }
        )
    for item in bindings:
        if ref(item["path"]) != item:
            raise ValueError("Source-review inputs changed during rendering")
    result = {
        "status": "prepared-all-source-thumbnails-awaiting-actual-content-review",
        "inputs": bindings,
        "new_rows": records,
        "contacts": contacts,
        "count": len(records),
        "bin_factors": sorted({r["bin_factor"] for r in records}),
        "all_cache_hashes_and_headers_checked": True,
        "elapsed_seconds": time.monotonic() - started,
        "display": "Full cached image fit within136x96, independent F32 linear-light RGB planes BOX-area resized then sRGB and RGB8. No exposure adjustment. Source thumbnails, not native performance crops.",
        "scope": "Complete selected-source content inventory before final protected/duplicate/title/content admission review. Manifest train/val/test letters are deterministic source-hash buckets, not approval. No restoration output, corpus admission or training changes.",
        "training_admission": False,
    }
    (output / "inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "inventory": ref(output / "inventory.json"),
                "pages": len(contacts),
                "sources": len(records),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["manifest", "selection", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    render(args.manifest, args.selection, args.output)
