"""Prepare screened paired candidates without assigning a training split."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

import argparse
import fcntl
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from demosaic.realdata import prepare_pairs
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_crops(data, directory, size):
    count = 0
    for case in data["cases"]:
        for crop in case["crops"]:
            path = (directory / crop["path"]).resolve()
            if directory.resolve() not in path.parents or sha(path) != crop["sha256"]:
                raise ValueError("Prepared quarantine crop path/checksum differs")
            with np.load(path, allow_pickle=False) as arrays:
                for key in [
                    "raw",
                    "reference_rgb",
                    "sensor_reference",
                    "sensor_mask",
                    "sensor_count",
                ]:
                    shape = (size, size) if key == "raw" else (3, size, size)
                    if arrays[key].shape != shape:
                        raise ValueError("Prepared quarantine crop shape differs")
                    dtype = (
                        np.bool_
                        if key == "sensor_mask"
                        else np.uint8
                        if key == "sensor_count"
                        else np.float32
                    )
                    if arrays[key].dtype != dtype or not np.isfinite(arrays[key]).all():
                        raise ValueError("Prepared quarantine crop dtype/finiteness differs")
                if np.any(arrays["sensor_mask"] & (arrays["sensor_count"] == 0)):
                    raise ValueError("Valid reference mask has no measured samples")
            count += 1
    return count


def prepare(manifest, output, *, size=512, grid=3):
    manifest = Path(manifest).resolve()
    data = json.loads(manifest.read_text())
    if data["split"] != "quarantine" or any(p["split"] != "quarantine" for p in data["selection"]):
        raise ValueError("Only prepare quarantined scene records")
    review = json.loads((manifest.parent / "summary.json").read_text())
    if review["screen_clear_manifest_sha256"] != sha(manifest):
        raise ValueError("Screened quarantine manifest changed")
    if data["screen_recipe_sha256"] != sha(manifest.parent / "recipe.json"):
        raise ValueError("Screened quarantine recipe changed")
    if len({p["scene"] for p in data["selection"]}) != len(data["selection"]):
        raise ValueError("Duplicate quarantine scenes")
    recipe = {
        "manifest": str(manifest),
        "manifest_sha256": sha(manifest),
        "screen_summary_sha256": sha(manifest.parent / "summary.json"),
        "script_sha256": sha(__file__),
        "realdata_source_sha256": sha(inspect.getsourcefile(prepare_pairs)),
        "size": size,
        "grid": grid,
        "split": "quarantine",
        "scope": "Alignment/crop preparation only. Independent AHD RGB is auxiliary; clean RAW retains noise. Manual review and explicit training admission remain pending.",
    }
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "manifest.json").exists():
            raise ValueError("Prepared quarantine is frozen; use a new output")
        recipe_path = output / "recipe.json"
        if recipe_path.exists() and json.loads(recipe_path.read_text()) != recipe:
            raise ValueError("Quarantine preparation recipe changed")
        recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for p in [manifest, Path(__file__)]:
            (archive / p.name).write_bytes(p.read_bytes())
        ledger = output / "outcomes"
        ledger.mkdir(exist_ok=True)
        outcomes, cases, rejected = [], [], []
        for scene in data["selection"]:
            identity = hashlib.sha256(scene["scene"].encode()).hexdigest()[:20]
            directory = output / "scenes" / identity
            directory.mkdir(parents=True, exist_ok=True)
            selected = {**data, "selection": [scene]}
            acquisition = directory / "acquisition.json"
            encoded = json.dumps(selected, indent=2) + "\n"
            if acquisition.exists() and acquisition.read_text() != encoded:
                raise ValueError("Per-scene quarantine source changed")
            acquisition.write_text(encoded)
            outcome_path = ledger / f"{identity}.json"
            if outcome_path.exists():
                outcome = json.loads(outcome_path.read_text())
                if outcome["status"] == "prepared":
                    if sha(directory / "manifest.json") != outcome["manifest_sha256"]:
                        raise ValueError("Prepared scene manifest changed")
                    prepared = json.loads((directory / "manifest.json").read_text())
                    verify_crops(prepared, directory, size)
            else:
                try:
                    prepared = prepare_pairs(acquisition, directory, size=size, grid=grid)
                    if prepared["split"] != "quarantine":
                        raise ValueError("Preparation changed the quarantine split")
                    crops = verify_crops(prepared, directory, size)
                except (ValueError, RuntimeError, OSError) as error:
                    outcome = {"scene": scene["scene"], "status": "failed", "error": repr(error)}
                else:
                    outcome = {
                        "scene": scene["scene"],
                        "status": "prepared",
                        "cases": len(prepared["cases"]),
                        "crops": crops,
                        "manifest": str(directory / "manifest.json"),
                        "manifest_sha256": sha(directory / "manifest.json"),
                    }
                temporary = outcome_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(outcome, indent=2) + "\n")
                temporary.replace(outcome_path)
            outcomes.append(outcome)
            if outcome["status"] == "prepared":
                for case in prepared["cases"]:
                    case["crops"] = [
                        {**crop, "path": str(Path("scenes") / identity / crop["path"])}
                        for crop in case["crops"]
                    ]
                    cases.append(case)
                rejected.extend(prepared["rejected"])
            print(json.dumps({"event": "quarantine-scene-prepared", **outcome}), flush=True)
        result = {
            **recipe,
            "format_version": 1,
            "dataset_license": data["dataset_license"],
            "attribution": data["attribution"],
            "cases": cases,
            "rejected": rejected,
            "outcomes": outcomes,
            "manual_review": "Pending; no training admission",
        }
        assert sha(manifest) == recipe["manifest_sha256"]
        (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--grid", type=int, default=3)
    args = parser.parse_args()
    prepare(args.manifest, args.output, size=args.size, grid=args.grid)
