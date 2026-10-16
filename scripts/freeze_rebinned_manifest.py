"""Freeze a completed rebinning while preserving an audited source membership."""

import argparse
import fcntl
import hashlib
import json
from collections import Counter
from pathlib import Path

from demosaic.safety import writable_path


def freeze(base_manifest, prepared_manifest, output, *, min_size=512):
    base_manifest, prepared_manifest = Path(base_manifest), Path(prepared_manifest)
    output = writable_path(output)
    if (output / "manifest.jsonl").exists():
        raise ValueError("Frozen manifest already exists; choose a new output")
    with (prepared_manifest.parent / ".prepare.lock").open("r") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Rebinning producer is still running; wait for completion") from None
        base_bytes, prepared_bytes = base_manifest.read_bytes(), prepared_manifest.read_bytes()
        original = [json.loads(line) for line in base_bytes.splitlines()]
        rows = [json.loads(line) for line in prepared_bytes.splitlines()]
        base = {r["id"]: r for r in original if r["split"] in ["train", "val", "test"]}
        if len({r["id"] for r in original}) != len(original) or len({r["id"] for r in rows}) != len(
            rows
        ):
            raise ValueError("Duplicate source identities")
        if {r["id"] for r in rows} != set(base):
            raise ValueError("Rebinned membership differs from complete audited selection")
        recipe = json.loads((prepared_manifest.parent / "recipe.json").read_text())
        source_hash = hashlib.sha256(base_bytes).hexdigest()
        if recipe.get("factor") != 4 or recipe.get("selection_manifest_sha256") != source_hash:
            raise ValueError("Rebinning recipe does not match the frozen selection/factor4")
        for row in rows:
            if row["split"] != base[row["id"]]["split"]:
                raise ValueError("Rebinning changed a protected source split")
            if (
                row["bin_factor"] != 4
                or row["dtype"] != "uint16"
                or row["color_space"] != "linear-sRGB"
            ):
                raise ValueError("Expected linear uint16 factor4 cache")
            if min(row["shape"][:2]) < min_size or len(row["cache_sha256"]) != 64:
                raise ValueError("Rebinned cache metadata is invalid or too small")
            cache = (prepared_manifest.parent / row["cache"]).resolve()
            if not cache.is_file() or prepared_manifest.parent.resolve() not in cache.parents:
                raise ValueError("Rebinned cache missing or outside producer directory")
            row["cache"] = str(cache)
        report = {
            "base_manifest": str(base_manifest.resolve()),
            "base_sha256": source_hash,
            "prepared_manifest": str(prepared_manifest.resolve()),
            "prepared_sha256": hashlib.sha256(prepared_bytes).hexdigest(),
            "recipe": recipe,
            "counts": dict(Counter(r["split"] for r in rows)),
            "base_excluded_ids": [r["id"] for r in original if r["split"] == "excluded"],
            "verification": "Exact active source identities and splits preserved; producer cache checksums retained. Original8x validation manifest remains separately fixed.",
        }
        output.mkdir(parents=True, exist_ok=True)
        temporary = output / "manifest.jsonl.tmp"
        temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        temporary.replace(output / "manifest.jsonl")
        report["manifest_sha256"] = hashlib.sha256(
            (output / "manifest.jsonl").read_bytes()
        ).hexdigest()
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", required=True, type=Path)
    parser.add_argument("--prepared-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(freeze(args.base_manifest, args.prepared_manifest, args.output), indent=2))


if __name__ == "__main__":
    main()
