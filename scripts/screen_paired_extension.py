"""Screen both clean references of quarantined paired scenes; never admit training."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

import argparse
import fcntl
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image, ImageDraw

from demosaic.io import exif_identity
from demosaic.paired import verify_file
from demosaic.safety import writable_path

SHARED = Path(__file__).with_name("screen_commons_protected.py")
SPEC = importlib.util.spec_from_file_location("paired_shared_overlap", SHARED)
overlap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlap)


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def commons_pool(manifest):
    manifest = Path(manifest)
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    rows = [r for r in rows if r["split"] in ("val", "test")]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Expected unique protected Commons val/test sources")
    entries, hashes, normalized, ratios, informative = [], [], [], [], []
    for index, row in enumerate(rows):
        path = manifest.parent / row["cache"]
        if sha(path) != row["cache_sha256"]:
            raise ValueError("Protected Commons cache changed")
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if array.dtype != np.uint16 or array.ndim != 3 or array.shape[-1] != 3:
            raise ValueError("Protected Commons cache must be linear uint16 RGB")
        for view in overlap.views(array):
            hashes.append(view["hash"])
            normalized.append(view["normalized"])
            ratios.append(view["ratio"])
            informative.append(view["informative"])
            entries.append((index, row["id"], {k: view[k] for k in ["roi", "orientation"]}))
        if (index + 1) % 500 == 0:
            print(json.dumps({"event": "commons-reference-pool", "sources": index + 1}), flush=True)
    return {
        "entries": entries,
        "hashes": np.stack(hashes),
        "normalized": np.stack(normalized),
        "ratios": np.asarray(ratios),
        "informative": np.asarray(informative),
    }, [{k: row[k] for k in ["id", "split", "title", "cache_sha256"]} for row in rows]


def decode_reference(record, output):
    verified = verify_file(record["path"], record)
    if verified["sha256"] != record["sha256"]:
        raise ValueError("Acquired reference SHA256 changed")
    with rawpy.imread(record["path"]) as decoder:
        if decoder.raw_pattern is None or decoder.raw_pattern.shape != (2, 2):
            raise ValueError("Expected an ordinary Bayer reference")
        pattern = "".join(
            decoder.color_desc.decode("ascii")[
                decoder.raw_color(decoder.sizes.top_margin + y, decoder.sizes.left_margin + x)
            ]
            for y in range(2)
            for x in range(2)
        )
        if pattern not in ["RGGB", "BGGR", "GRBG", "GBRG"]:
            raise ValueError("Unsupported Bayer reference colors")
        sensor_shape = list(decoder.raw_image_visible.shape)
        rgb = decoder.postprocess(
            half_size=True,
            output_bps=16,
            gamma=(1, 1),
            use_camera_wb=True,
            no_auto_bright=True,
            adjust_maximum_thr=0,
            user_flip=0,
            output_color=rawpy.ColorSpace.sRGB,
        )
    height, width = (value // 4 * 4 for value in rgb.shape[:2])
    if min(height, width) < 128:
        raise ValueError("Reference too small for identity views")
    values = rgb[:height, :width].reshape(height // 4, 4, width // 4, 4, 3)
    cache = ((values.sum((1, 3), dtype=np.uint32) + 8) // 16).astype(np.uint16)
    path = output / f"{record['sha256']}.npy"
    with path.with_suffix(".tmp").open("wb") as handle:
        np.save(handle, cache)
    path.with_suffix(".tmp").replace(path)
    return {
        "source_sha256": record["sha256"],
        "source": record,
        "screen_cache": str(path),
        "screen_sha256": sha(path),
        "screen_shape": list(cache.shape),
        "identity": exif_identity(record["path"]),
        "pattern": pattern,
        "sensor_shape": sensor_shape,
        "render": "LibRaw half-size linear-sRGB/camera-WB/no auto bright/no rotation, then area4; identity screening only",
    }


def contact_pages(outcomes, output):
    for first in range(0, len(outcomes), 20):
        page = Image.new("RGB", (1000, 5 * 176), "white")
        draw = ImageDraw.Draw(page)
        for i, row in enumerate(outcomes[first : first + 20]):
            if "screen_cache" not in row:
                continue
            array = np.load(row["screen_cache"], allow_pickle=False).astype(np.float32) / 65535
            srgb = np.where(array <= 0.0031308, array * 12.92, 1.055 * array ** (1 / 2.4) - 0.055)
            image = Image.fromarray(np.rint(np.clip(srgb, 0, 1) * 255).astype(np.uint8))
            image.thumbnail((240, 142))
            x, y = (i % 4) * 250, (i // 4) * 176
            page.paste(image, (x, y + 24))
            draw.text((x + 2, y + 2), f"{row['scene']} [{row['reference_index']}]", fill="black")
            draw.text(
                (x + 2, y + 164),
                "HELD" if row["held"] else "screen clear; review pending",
                fill="black",
            )
        page.save(output / f"content-review-{first // 20:02d}.jpg", quality=92)


def screen(manifest, protected, commons, output):
    manifest, protected, commons = (Path(p).resolve() for p in [manifest, protected, commons])
    data = json.loads(manifest.read_text())
    if data["split"] != "quarantine" or any(p["split"] != "quarantine" for p in data["selection"]):
        raise ValueError("Screen only explicitly quarantined acquisitions")
    scenes = [p["scene"] for p in data["selection"]]
    if not scenes or len(set(scenes)) != len(scenes):
        raise ValueError("Expected unique quarantined scenes")
    if any(not 1 <= len(p["clean"]) <= 2 for p in data["selection"]):
        raise ValueError("Expected one or two clean references per scene")
    identities = [r["sha256"] for p in data["selection"] for r in p["clean"]]
    if len(set(identities)) != len(identities) or any(
        len(s) != 64 or any(c not in "0123456789abcdef" for c in s) for s in identities
    ):
        raise ValueError("Expected unique SHA256 reference identities")
    recipe = {
        "manifest": str(manifest),
        "manifest_sha256": sha(manifest),
        "protected": str(protected),
        "protected_sha256": sha(protected),
        "commons": str(commons),
        "commons_sha256": sha(commons),
        "script_sha256": sha(__file__),
        "shared_screen_sha256": sha(SHARED),
        "io_source_sha256": sha(inspect.getsourcefile(exif_identity)),
        "rawpy_version": rawpy.__version__,
        "numpy_version": np.__version__,
        "method": "Both clean references; seven full/center/corner views x8 dihedral transforms on both sides; informative std>.005, aspect4%, dHash<=40 OR correlation>=.95. Any flag/decode error holds the whole scene.",
        "scope": "Data identity and content review only. Finite screening cannot prove scene separation. No model scoring or training admission.",
    }
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".screen.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "summary.json").exists():
            raise ValueError("Screen result is frozen; use a new output")
        path = output / "recipe.json"
        if path.exists() and json.loads(path.read_text()) != recipe:
            raise ValueError("Screen recipe changed")
        path.write_text(json.dumps(recipe, indent=2) + "\n")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for p in [manifest, protected, commons, Path(__file__), SHARED]:
            (archive / p.name).write_bytes(p.read_bytes())
        cache, ledger = output / "screens", output / "outcomes"
        cache.mkdir(exist_ok=True)
        ledger.mkdir(exist_ok=True)
        protected_data = overlap.protected_pool(protected)
        common_data, common_sources = commons_pool(commons)
        outcomes = []
        for scene in data["selection"]:
            for index, record in enumerate(scene["clean"]):
                path = ledger / f"{record['sha256']}.json"
                if path.exists():
                    verified = verify_file(record["path"], record)
                    if verified["sha256"] != record["sha256"]:
                        raise ValueError("Saved reference source changed")
                    row = json.loads(path.read_text())
                    if row["source_sha256"] != record["sha256"]:
                        raise ValueError("Reference identity changed")
                    if "screen_cache" in row and sha(row["screen_cache"]) != row["screen_sha256"]:
                        raise ValueError("Saved reference screen changed")
                else:
                    row = {
                        "scene": scene["scene"],
                        "reference_index": index,
                        "source_sha256": record["sha256"],
                    }
                    try:
                        row.update(decode_reference(record, cache))
                    except (ValueError, OSError, RuntimeError, rawpy.LibRawError) as error:
                        row.update({"held": True, "reason": repr(error)})
                    else:
                        array = np.load(row["screen_cache"], mmap_mode="r", allow_pickle=False)
                        row["protected_matches"] = overlap.matches(array, protected_data)
                        row["commons_matches"] = overlap.matches(array, common_data)
                        row["held"] = bool(row["protected_matches"] or row["commons_matches"])
                        if not any(v["informative"] for v in overlap.views(array)):
                            row.update({"held": True, "reason": "No informative reference views"})
                        if not row["identity"].get("Model"):
                            row.update({"held": True, "reason": "Camera identity missing"})
                    temporary = path.with_suffix(".tmp")
                    temporary.write_text(json.dumps(row, indent=2) + "\n")
                    temporary.replace(path)
                outcomes.append(row)
                print(
                    json.dumps(
                        {
                            "event": "paired-reference-screen",
                            "scene": scene["scene"],
                            "reference": index,
                            "held": row["held"],
                        }
                    ),
                    flush=True,
                )
        held = {r["scene"] for r in outcomes if r["held"]}
        clear = [r for r in data["selection"] if r["scene"] not in held]
        contact_pages(outcomes, output)
        cleared = output / "manifest-screen-clear-quarantine.json"
        records = [r for p in clear for role in ["clean", "noisy"] for r in p[role]]
        cleared.write_text(
            json.dumps(
                {
                    **data,
                    "selection": clear,
                    "files": len(records),
                    "bytes": sum(r["bytes"] for r in records),
                    "manual_review": "Pending; screening clear is not training admission",
                    "screen_recipe_sha256": sha(output / "recipe.json"),
                },
                indent=2,
            )
            + "\n"
        )
        result = {
            **recipe,
            "references": outcomes,
            "protected_commons_sources": common_sources,
            "screen_clear_scenes": [r["scene"] for r in clear],
            "held_scenes": sorted(held),
            "screen_clear_manifest": str(cleared),
            "screen_clear_manifest_sha256": sha(cleared),
            "manual_review": "Pending; resized content contact sheets are not performance comparisons",
        }
        assert (
            sha(manifest) == recipe["manifest_sha256"]
            and sha(protected) == recipe["protected_sha256"]
            and sha(commons) == recipe["commons_sha256"]
        )
        (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--protected", type=Path, required=True)
    parser.add_argument("--commons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    screen(args.manifest, args.protected, args.commons, args.output)
