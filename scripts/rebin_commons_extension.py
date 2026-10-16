"""Rebin only admitted new sources, then reuse a frozen 4x base without copying pixels."""

import argparse
import fcntl
import hashlib
import json
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from demosaic.prepare import free_license, prepare_commons
from demosaic.safety import writable_path

ACTIVE = {"train", "val", "test"}
REBIN_FIELDS = {"cache", "cache_sha256", "shape", "bin_factor"}


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            result.update(block)
    return result.hexdigest()


def records(path):
    path = Path(path)
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate source identities")
    for row in rows:
        row["cache"] = str((path.parent / row["cache"]).resolve())
    return rows


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


@contextmanager
def owned_output(output):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".rebin.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another process owns this extension rebinning") from None
        yield output


def membership(base_manifest, expanded_manifest):
    base_manifest, expanded_manifest = Path(base_manifest), Path(expanded_manifest)
    base, expanded = records(base_manifest), records(expanded_manifest)
    audit = json.loads((expanded_manifest.parent / "audit.json").read_text())
    if (
        audit["base_sha256"] != digest(base_manifest)
        or audit["manifest_sha256"] != digest(expanded_manifest)
        or audit["counts"] != dict(Counter(r["split"] for r in expanded))
    ):
        raise ValueError("Expanded audit does not match its input manifests")
    old = {r["id"]: r for r in base}
    new = {r["id"]: r for r in expanded}
    if not old.keys() <= new.keys() or any(old[k] != new[k] for k in old):
        raise ValueError("Expansion changed an existing source or protected split")
    for row in expanded:
        if (
            row["bin_factor"] != 8
            or row["dtype"] != "uint16"
            or row["color_space"] != "linear-sRGB"
        ):
            raise ValueError("Membership must come from homogeneous audited 8x data")
        if row["id"] not in old and row["split"] not in {"train", "reserved", "excluded"}:
            raise ValueError("New validation/test sources must remain reserved")
    selected = [r for r in expanded if r["id"] not in old and r["split"] == "train"]
    if any(not free_license(r["license"]) for r in selected):
        raise ValueError("New training sources require a free license")
    return base, expanded, selected


def prepare_extension(base_manifest, expanded_manifest, output, source, *, workers=1):
    with owned_output(output) as destination:
        if (destination / "audit/manifest.jsonl").exists():
            raise ValueError("Frozen extension already exists; choose a new output")
        _, _, selected = membership(base_manifest, expanded_manifest)
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected)
        recipe = {
            "base_manifest": str(Path(base_manifest).resolve()),
            "base_sha256": digest(base_manifest),
            "expanded_manifest": str(Path(expanded_manifest).resolve()),
            "expanded_sha256": digest(expanded_manifest),
            "source": str(Path(source).resolve()),
            "factor": 4,
            "min_size": 512,
            "selected": len(selected),
            "selection_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        }
        recipe_path, selection = destination / "selection-recipe.json", destination / "selection.jsonl"
        if recipe_path.exists():
            if json.loads(recipe_path.read_text()) != recipe or digest(selection) != recipe[
                "selection_sha256"
            ]:
                raise ValueError("Selection recipe changed; choose a new output")
        else:
            temporary = selection.with_suffix(".jsonl.tmp")
            temporary.write_text(payload)
            temporary.replace(selection)
            atomic_json(recipe_path, recipe)
        counts = prepare_commons(
            Path(source),
            destination / "prepared4",
            factor=4,
            min_size=512,
            workers=workers,
            selection_manifest=selection,
        )
        prepared = records(destination / "prepared4/manifest.jsonl")
        if counts["failed"] or {r["id"] for r in prepared} != {r["id"] for r in selected}:
            raise ValueError("New-source preparation is incomplete; inspect producer errors")
        atomic_json(destination / "preparation.json", {"recipe": recipe, "counts": counts})
        return {"selected": len(selected), "counts": counts}


def verify_four(rows, expected):
    if {r["id"] for r in rows} != {r["id"] for r in expected}:
        raise ValueError("Rebinned source membership is incomplete or changed")
    by_id = {r["id"]: r for r in expected}
    for row in rows:
        original = by_id[row["id"]]
        if {k: v for k, v in row.items() if k not in REBIN_FIELDS} != {
            k: v for k, v in original.items() if k not in REBIN_FIELDS
        }:
            raise ValueError("Rebinning changed source metadata or protected split")
        if (
            row["bin_factor"] != 4
            or row["dtype"] != "uint16"
            or row["color_space"] != "linear-sRGB"
            or len(row["shape"]) != 3
            or row["shape"][-1] != 3
            or min(row["shape"][:2]) < 512
            or len(row["cache_sha256"]) != 64
            or not Path(row["cache"]).is_file()
        ):
            raise ValueError("Invalid or missing 4x cache metadata")
        pixels = np.load(row["cache"], mmap_mode="r", allow_pickle=False)
        if pixels.dtype != np.uint16 or list(pixels.shape) != row["shape"]:
            raise ValueError("4x cache header disagrees with declared pixels")


def freeze_extension(base_manifest, expanded_manifest, base_rebinned_manifest, output):
    base_manifest, expanded_manifest = Path(base_manifest), Path(expanded_manifest)
    base_rebinned_manifest = Path(base_rebinned_manifest)
    with owned_output(output) as destination:
        frozen = destination / "audit/manifest.jsonl"
        if frozen.exists():
            raise ValueError("Frozen extension already exists; choose a new output")
        base, expanded, selected = membership(base_manifest, expanded_manifest)
        base_audit = json.loads((base_rebinned_manifest.parent / "audit.json").read_text())
        if (
            base_audit.get("membership_sha256", base_audit.get("base_sha256"))
            != digest(base_manifest)
            or base_audit["manifest_sha256"] != digest(base_rebinned_manifest)
            or base_audit.get("factor", base_audit.get("recipe", {}).get("factor")) != 4
        ):
            raise ValueError("Frozen base 4x audit does not match the base 8x membership")
        base_four = records(base_rebinned_manifest)
        verify_four(base_four, [r for r in base if r["split"] in ACTIVE])
        recipe = json.loads((destination / "selection-recipe.json").read_text())
        if (
            recipe["base_sha256"] != digest(base_manifest)
            or recipe["expanded_sha256"] != digest(expanded_manifest)
            or recipe["selection_sha256"] != digest(destination / "selection.jsonl")
            or records(destination / "selection.jsonl") != selected
        ):
            raise ValueError("Prepared selection differs from audited membership")
        producer = destination / "prepared4"
        with (producer / ".prepare.lock").open("r") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("New-source preparation is still running") from None
            producer_recipe = json.loads((producer / "recipe.json").read_text())
            if (
                producer_recipe["factor"] != 4
                or producer_recipe["selection_manifest_sha256"] != recipe["selection_sha256"]
                or producer_recipe["source"] != recipe["source"]
            ):
                raise ValueError("New-source producer recipe changed")
            new_four = records(producer / "manifest.jsonl")
            verify_four(new_four, selected)
            if any(not Path(r["cache"]).is_relative_to(producer.resolve()) for r in new_four):
                raise ValueError("New cache path escapes its producer")
            all_four = {r["id"]: r for r in base_four + new_four}
            combined = [all_four[r["id"]] for r in expanded if r["split"] in ACTIVE]
            payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in combined)
            report = {
                "factor": 4,
                "membership_sha256": digest(expanded_manifest),
                "base_manifest": str(base_manifest.resolve()),
                "base_sha256": digest(base_manifest),
                "expanded_manifest": str(expanded_manifest.resolve()),
                "base_rebinned_manifest": str(base_rebinned_manifest.resolve()),
                "base_rebinned_sha256": digest(base_rebinned_manifest),
                "prepared_sha256": digest(producer / "manifest.jsonl"),
                "selection_recipe": recipe,
                "counts": dict(Counter(r["split"] for r in combined)),
                "new_training_caches": len(new_four),
                "reused_base_caches": len(base_four),
                "reserved_ids": [r["id"] for r in expanded if r["split"] == "reserved"],
                "excluded_ids": [r["id"] for r in expanded if r["split"] == "excluded"],
                "manifest_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                "verification": "Exact audited active source identities/splits and attribution preserved. Frozen base cache paths/hashes reused without copying pixels. Producer checksums retained; cache existence/shape/dtype headers verified, no full cache rehash at merge. Reserved/excluded sources omitted; use original8x validation separately.",
            }
            frozen.parent.mkdir(parents=True, exist_ok=True)
            temporary = frozen.with_suffix(".jsonl.tmp")
            temporary.write_text(payload)
            atomic_json(frozen.parent / "audit.json", report)
            temporary.replace(frozen)
            return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["prepare", "freeze"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("--base-manifest", type=Path, required=True)
        sub.add_argument("--expanded-manifest", type=Path, required=True)
        sub.add_argument("--output", type=Path, required=True)
        if command == "prepare":
            sub.add_argument("--source", type=Path, default=Path("/mnt/external/qi"))
            sub.add_argument("--workers", type=int, default=1)
        else:
            sub.add_argument("--base-rebinned-manifest", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    result = prepare_extension(**args) if command == "prepare" else freeze_extension(**args)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
