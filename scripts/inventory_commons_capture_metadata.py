"""Training-JPEG/MPO header inventory for targeted ISO review; never decodes pixels."""

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil

REPO = Path(__file__).resolve().parents[1]
MANIFEST = Path("/mnt/external/demosaic/commons-post4557-reviewed-20261020-v1/manifest4.jsonl")


def ref(path):
    path = Path(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "sha256": digest}


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare(root):
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    snapshot = root / "metadata-worker.py"
    shutil.copyfile(__file__, snapshot)
    save(
        root / "plan.json",
        {
            "root": str(root),
            "manifest": ref(MANIFEST),
            "operator": ref(snapshot),
            "threads": 2,
            "expected_training_rows": 88508,
            "scope": "Training-source JPEG/MPO first-frame headers only. Record camera/ISO/exposure/software, never GPS or pixels. ISO/software metadata only selects visual-review candidates; it cannot establish noise, blur, excessive processing, non-photographic content or training eligibility. Unsupported headers are recorded, never excluded. Originals stay read-only. Declared original hashes are retained without a fresh whole-file hash claim for every original; selected views verify full originals/caches separately.",
        },
    )
    print(ref(root / "plan.json"))


def worker(plan_path):
    from PIL import ExifTags, Image, ImageFile

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    plan = json.loads(plan_path.read_text())
    assert ref(__file__) == plan["operator"] and ref(plan["manifest"]["path"]) == plan["manifest"]
    root = Path(plan["root"])
    (root / "worker.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(root / "owner.json", owner)
    assert psutil.virtual_memory().available > 32 * 2**30
    assert shutil.disk_usage(root).free > 64 * 2**30
    rows = [
        r
        for r in (
            json.loads(line) for line in Path(plan["manifest"]["path"]).read_text().splitlines()
        )
        if r["split"] == "train"
    ]
    assert len(rows) == plan["expected_training_rows"]
    decoded = []

    def forbidden(*_args, **_kwargs):
        decoded.append(True)
        raise AssertionError("This inventory may not decode image pixels")

    ImageFile.ImageFile.load = forbidden
    Image.MAX_IMAGE_PIXELS = None  # Header dimensions do not allocate decoded images.
    Image.init()

    def number(value):
        if isinstance(value, (tuple, list)):
            value = value[0] if value else None
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            return None

    def one(row):
        result = {"id": row["id"], "title": row["title"], "original_SHA1_declared": row["sha1_hex"]}
        path = (Path("/mnt/external/qi") / row["download_path"]).resolve()
        assert path.is_relative_to(Path("/mnt/external/qi"))
        try:
            with Image.open(path) as im:
                result["header_format"] = im.format
                if im.format not in ("JPEG", "MPO"):
                    result["metadata_error"] = "Unsupported header-only format: " + str(im.format)
                    return result
                exif = im.getexif()
                photo = exif.get_ifd(ExifTags.IFD.Exif)
                result.update(
                    ISO=number(photo.get(34855, exif.get(34855))),
                    exposure_seconds=number(photo.get(33434)),
                    f_number=number(photo.get(33437)),
                    camera_make=str(exif.get(271, ""))[:256],
                    camera_model=str(exif.get(272, ""))[:256],
                    software=str(exif.get(305, ""))[:512],
                    exif_present=bool(exif),
                )
        except (
            OSError,
            ValueError,
            TypeError,
            SyntaxError,
            OverflowError,
            KeyError,
            EOFError,
            struct.error,
        ) as error:
            result["metadata_error"] = type(error).__name__ + ": " + str(error)[:500]
        return result

    started, high, errors, known = time.monotonic(), [], 0, 0
    output = root / "per-source.jsonl"
    with output.open("x") as stream, ThreadPoolExecutor(max_workers=plan["threads"]) as pool:

        def bounded_records():
            iterator = iter(rows)
            pending = deque()
            for _ in range(32):
                row = next(iterator, None)
                if row is not None:
                    pending.append(pool.submit(one, row))
            while pending:
                yield pending.popleft().result()
                row = next(iterator, None)
                if row is not None:
                    pending.append(pool.submit(one, row))

        for done, record in enumerate(bounded_records(), 1):
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            errors += "metadata_error" in record
            iso = record.get("ISO")
            known += iso is not None and iso > 0
            if iso is not None and iso >= 3200:
                high.append(record)
            if done % 1024 == 0 or done == len(rows):
                stream.flush()
                assert not decoded and psutil.virtual_memory().available > 24 * 2**30
                assert time.monotonic() - started < 1800
                save(
                    root / "progress.json",
                    {
                        "owner": owner,
                        "training_rows_processed": done,
                        "total": len(rows),
                        "ISO_known": known,
                        "ISO_at_least3200": len(high),
                        "errors": errors,
                    },
                )
    assert not decoded and "torch" not in sys.modules
    assert ref(plan["manifest"]["path"]) == plan["manifest"]
    selected = {r["id"]: r for r in sorted(high, key=lambda r: (-r["ISO"], r["id"]))[:8]}
    for row in sorted(
        high, key=lambda r: hashlib.sha256(("ISO-review-v1:" + r["id"]).encode()).digest()
    )[:8]:
        selected.setdefault(row["id"], row)
    candidates = root / "review-candidates.json"
    save(
        candidates,
        {
            "sources_scored": 0,
            "complete": False,
            "header_inventory_complete": True,
            "high_loss": {},
            "IQA_proxies_not_automatic_labels": {},
            "metadata_candidates": [
                {
                    "id": r["id"],
                    "metadata_review_cue": "Recorded capture ISO; not a source-quality judgment",
                    "capture_metadata": r,
                }
                for r in selected.values()
            ],
            "scope": plan["scope"],
        },
    )
    save(
        root / "receipt.json",
        {
            "status": "completed-JPEG-header-inventory-awaiting-actual-visual-review",
            "plan": ref(plan_path),
            "owner": owner,
            "training_rows_processed": done,
            "headers_without_metadata_error": done - errors,
            "ISO_known": known,
            "ISO_at_least3200": len(high),
            "metadata_errors": errors,
            "pixel_decodes_attempted": len(decoded),
            "torch_imported": False,
            "CUDA_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "records": ref(output),
            "candidates": ref(candidates),
            "scope": plan["scope"],
        },
    )
    print(ref(root / "receipt.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else worker)(args.path.resolve())
