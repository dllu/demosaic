"""Refit DINO lateral maps from retained, training-only encoder feature pairs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from demosaic.safety import writable_path


def fit_affine(features, targets, ridge=0.001):
    """Return float32 K×C weights and K biases; intercepts are unpenalized.

    Ridge acts on standardized input channels. The solve and moment estimates
    use float64; converting the coefficients matches the restoration layers.
    """
    x, y = np.asarray(features, dtype=np.float64), np.asarray(targets, dtype=np.float64)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or len(x) < 2 or not x.shape[1] or not y.shape[1]:
        raise ValueError("Expected paired nonempty N×C/N×K features with N >= 2")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(ridge) or ridge < 0:
        raise ValueError("Features, targets and nonnegative ridge must be finite")
    mx, my = x.mean(0), y.mean(0)
    cx, cy = x-mx, y-my
    std = np.maximum(np.sqrt(np.mean(cx**2, axis=0)), 1e-8)
    z = cx/std
    system = z.T@z/len(z) + ridge*np.eye(z.shape[1])
    rhs = z.T@cy/len(z)
    coefficients = np.linalg.solve(system, rhs)
    weight = (coefficients/std[:, None]).T
    bias = my-weight@mx
    weight, bias = weight.astype(np.float32), bias.astype(np.float32)
    if not np.isfinite(weight).all() or not np.isfinite(bias).all():
        raise ValueError("Fitted coefficients exceed finite float32 range")
    return weight, bias


def refit(feature_fit, output, *, ridge=0.001):
    """Reproduce four maps without loading an encoder or using check sources."""
    report = json.loads(Path(feature_fit).read_text())
    records = report["records"]
    if any(r["sample"]["source_record"]["split"] != "train" for r in records):
        raise ValueError("Feature fitting accepts declared training sources only")
    if any(r["sample"]["partition"] not in {"fit", "feature-check"} for r in records):
        raise ValueError("Unknown feature partition")
    ids = [r["sample"]["source_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Fit and feature-check sources must be distinct")
    selected = [r for r in records if r["sample"]["partition"] == "fit"]
    if not selected:
        raise ValueError("No training feature pairs selected for fitting")
    loaded = []
    for record in selected:
        binding = record["arrays"]
        path = Path(binding["path"])
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != binding["sha256"]:
            raise ValueError(f"Feature archive checksum mismatch: {path}")
        with np.load(path, allow_pickle=False) as archive:
            loaded.append({k: archive[k].copy() for k in archive.files})
    arrays = {}
    for stage in range(4):
        x = np.concatenate([a[f"X{stage}"] for a in loaded])
        y = np.concatenate([a[f"Y{stage}"] for a in loaded])
        arrays[f"weight{stage}"], arrays[f"bias{stage}"] = fit_affine(x, y, ridge)
    output = writable_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        np.savez(stream, **arrays)
    return {"fit_sources": len(selected), "feature_check_sources_used_for_fit": 0,
            "coefficient_tensors": len(arrays), "ridge": ridge}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-fit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ridge", type=float, default=0.001)
    args = parser.parse_args()
    print(json.dumps(refit(args.feature_fit, args.output, ridge=args.ridge)), flush=True)
