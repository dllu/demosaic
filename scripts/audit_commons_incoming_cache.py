"""Verify a completed incoming 8x snapshot and render content thumbnails, without admission."""

import argparse
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psutil
from PIL import Image, ImageDraw

from demosaic.prepare import free_license
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def unique(values):
    result = {r["id"]: r for r in values}
    assert len(values) == len(result)
    return result


def main(root, output):
    root, output = root.resolve(), writable_path(output)
    assert not output.exists() and not (root / "prepared8/manifest.jsonl.tmp").exists()
    status, owner = read(root / "workflow.json"), read(root / "controller.json")
    assert status["status"] == "audited-quarantine8-awaiting-reviewed-freeze"
    try:
        process = psutil.Process(owner["pid"])
        assert (
            abs(process.create_time() - owner["created"]) >= 0.01
            or process.status() == psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        pass
    os.nice(5)
    recipe = read(root / "selection-recipe.json")
    for name, digest in recipe["source_sha256"].items():
        assert sha(root / "source" / name) == digest
    assert sha(root / "selection.jsonl") == recipe["selection_sha256"]
    assert sha(recipe["base_manifest"]) == recipe["base_sha256"]
    assert sha(recipe["protected_references"]) == recipe["protected_sha256"]
    selected = rows(root / "selection.jsonl")
    selection = {r["sha1_hex"] or r["sha1"]: r for r in selected}
    prepared_path = root / "prepared8/manifest.jsonl"
    prepared_sha = sha(prepared_path)
    prepared = unique(rows(prepared_path))
    errors = rows(root / "prepared8/errors.jsonl")
    failed = unique(errors)
    assert len(selection) == len(selected) == recipe["selected"]
    assert (
        not prepared.keys() & failed.keys() and prepared.keys() | failed.keys() == selection.keys()
    )
    for key, row in prepared.items():
        assert all(row[field] == value for field, value in selection[key].items())
        assert free_license(row["license"]) and row["width"] >= 2048 and row["height"] >= 2048
        assert row["width"] * row["height"] <= recipe["max_pixels"]
    screen, duplicate = (
        read(root / "protected-screen/summary.json"),
        read(root / "audit8/audit.json"),
    )
    assert screen["manifest_sha256"] == prepared_sha
    assert (
        screen["references_sha256"] == recipe["protected_sha256"]
        and screen["protected_references"] == 42
    )
    assert (
        sha(root / "protected-screen/cleared.jsonl")
        == screen["cleared_sha256"]
        == duplicate["addition_sha256"]
    )
    assert sha(root / "protected-screen/quarantined.jsonl") == screen["quarantined_sha256"]
    cleared, flagged = [
        unique(rows(root / "protected-screen" / name))
        for name in ["cleared.jsonl", "quarantined.jsonl"]
    ]
    assert (
        len(prepared) == screen["candidates"]
        and len(cleared) == screen["cleared"]
        and len(flagged) == screen["quarantined"]
    )
    assert (
        not cleared.keys() & flagged.keys() and cleared.keys() | flagged.keys() == prepared.keys()
    )
    original = unique(rows(recipe["base_manifest"]))
    expanded_path = root / "audit8/manifest.jsonl"
    expanded = unique(rows(expanded_path))
    assert sha(expanded_path) == duplicate["manifest_sha256"] == status["candidate_manifest_sha256"]
    assert not original.keys() & cleared.keys()
    assert (
        expanded.keys() == original.keys() | cleared.keys() and not expanded.keys() & flagged.keys()
    )
    assert all(expanded[key] == value for key, value in original.items())
    assert Counter(r["split"] for r in expanded.values()) == duplicate["counts"] == status["counts"]
    for key, row in cleared.items():
        assert all(
            expanded[key][field] == value for field, value in row.items() if field != "split"
        )
        assert row["cache_sha256"] == prepared[key]["cache_sha256"] == expanded[key]["cache_sha256"]
        assert expanded[key]["split"] in ["train", "reserved", "excluded"]
        assert row["split"] == "train" or expanded[key]["split"] != "train"
    new_train = [r for key, r in expanded.items() if key not in original and r["split"] == "train"]
    assert len(new_train) == duplicate["added_train"] == status["new_train"]
    assert all(
        not any(n in str(r).upper() for n in ["DSCF3842", "DSCF3883", "DSCF3879", "DSCF3880"])
        for r in new_train
    )

    def check(row):
        path = (root / "prepared8" / row["cache"]).resolve()
        digest = sha(path)
        assert path.is_relative_to(root / "prepared8/images") and digest == row["cache_sha256"]
        values = np.load(path, mmap_mode="r", allow_pickle=False)
        assert values.dtype == np.uint16 and values.ndim == 3 and values.shape[-1] == 3
        assert list(values.shape) == row["shape"] and min(values.shape[:2]) >= recipe["min_size"]
        assert (
            row["bin_factor"] == 8
            and row["color_space"] == "linear-sRGB"
            and row["dtype"] == "uint16"
        )
        return {
            "id": row["id"],
            "cache_sha256": digest,
            "bytes": path.stat().st_size,
            "shape": list(values.shape),
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        files = list(pool.map(check, prepared.values()))
    assert sha(prepared_path) == prepared_sha
    output.mkdir(parents=True, exist_ok=False)
    samples = sorted(
        new_train,
        key=lambda r: hashlib.sha256(
            ("incoming-native-content-v1-" + r["id"]).encode()
        ).hexdigest(),
    )[:48]
    assert len(samples) == 48
    contacts = []
    for sheet in range(3):
        canvas = Image.new("RGB", (800, 704), "white")
        draw = ImageDraw.Draw(canvas)
        for i, row in enumerate(samples[sheet * 16 : (sheet + 1) * 16]):
            array = np.load(row["cache"], allow_pickle=False)
            linear = array.astype(np.float32) / 65535
            srgb = np.where(
                linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055
            )
            image = Image.fromarray(np.rint(np.clip(srgb, 0, 1) * 255).astype(np.uint8))
            image.thumbnail((192, 138), Image.Resampling.BOX)
            x, y = i % 4 * 200, i // 4 * 176
            canvas.paste(image, (x + (200 - image.width) // 2, y + 2))
            draw.text((x + 4, y + 142), row["id"][:12], fill="black")
            draw.text((x + 4, y + 155), row["title"].removeprefix("File:")[:30], fill="black")
        path = output / f"contact-{sheet}.png"
        canvas.save(path)
        contacts.append(
            {
                "path": str(path),
                "sha256": sha(path),
                "count": 16,
                "display": "Resized sRGB thumbnails for content spot checks, not native performance crops",
            }
        )
    result = {
        "status": "completed-independent-incoming-cache-and-membership-audit-awaiting-visual-review",
        "root": str(root),
        "producer_actual_exit_verified": True,
        "manifest": str(prepared_path),
        "manifest_sha256": prepared_sha,
        "candidate_manifest": str(expanded_path),
        "candidate_manifest_sha256": sha(expanded_path),
        "selection_sha256": recipe["selection_sha256"],
        "source_recipe_sha256": sha(root / "selection-recipe.json"),
        "cache_count": len(files),
        "cache_bytes": sum(r["bytes"] for r in files),
        "counts": duplicate["counts"],
        "new_training": len(new_train),
        "protected_quarantined": len(flagged),
        "errors": errors,
        "error_source_metadata": [selection[k] for k in failed],
        "every_selected_identity_prepared_or_failed_once": True,
        "complete_cache_SHA_dtype_shape_minimum_size_recipe_metadata_verified": True,
        "all_old_rows_and_holdout_assignments_exact": True,
        "all_protected_flags_excluded_and_new_holdouts_reserved": True,
        "files": files,
        "samples": samples,
        "contacts": contacts,
        "driver_sha256": sha(__file__),
        "scope": "Read-only caches and membership; no training admission, original/RAW decode, protected-final scoring or model change. Finite fingerprints and 48 resized content thumbnails cannot prove full semantic disjointness or native sharpness/noise quality.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "cache_count": len(files),
                "cache_bytes": result["cache_bytes"],
                "new_training": len(new_train),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    main(**vars(parser.parse_args()))
