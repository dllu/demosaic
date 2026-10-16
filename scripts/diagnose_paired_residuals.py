"""Inspect paired training-target residuals; never edit data or score a model."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.cfa import PATTERNS
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def correlation(a, b, valid):
    if valid.sum() < 64:
        return None
    x, y = a[valid], b[valid]
    denominator = np.sqrt(np.dot(x, x) * np.dot(y, y))
    return float(np.clip(np.dot(x, y) / denominator, -1, 1)) if denominator > 0 else None


def residual_diagnostics(raw, reference, valid, pattern, shot, read):
    raw, reference = np.asarray(raw, np.float64), np.asarray(reference, np.float64)
    valid = np.asarray(valid, bool)
    if raw.ndim != 2 or reference.shape != (3, *raw.shape) or valid.shape != reference.shape:
        raise ValueError("Expected a Bayer plane and matching RGB reference/mask")
    if pattern not in PATTERNS or min(raw.shape) < 16:
        raise ValueError("Expected a supported Bayer pattern and useful crop size")
    if not np.isfinite(raw).all() or not np.isfinite(reference).all():
        raise ValueError("Nonfinite paired measurements")
    if not np.isfinite([shot, read]).all() or min(shot, read) < 0:
        raise ValueError("Expected finite nonnegative conditioning")
    phases = []
    design, rhs = np.zeros((2, 2)), np.zeros(2)
    fit_samples = 0
    for phase, color in enumerate(PATTERNS[pattern]):
        y, x = divmod(phase, 2)
        observed, target = raw[y::2, x::2], reference[color, y::2, x::2]
        usable = valid[color, y::2, x::2] & (target > 0.005) & (target < 0.95) & (observed < 0.99)
        n = int(usable.sum())
        if n < 128:
            phases.append({"phase": phase, "color": color, "samples": n})
            continue
        sigma = np.sqrt(shot * target.clip(0) + read + 1 / (12 * 65535**2))
        residual = (observed - target) / sigma
        mean = float(residual[usable].mean())
        centered = residual - mean
        cx = correlation(centered[:, 1:], centered[:, :-1], usable[:, 1:] & usable[:, :-1])
        cy = correlation(centered[1:], centered[:-1], usable[1:] & usable[:-1])
        phases.append(
            {
                "phase": phase,
                "color": color,
                "samples": n,
                "mean_noise_units": mean,
                "rms_noise_units": float(np.sqrt(np.mean(residual[usable] ** 2))),
                "lag2_sensor_x": cx,
                "lag2_sensor_y": cy,
            }
        )
        # Same-color phase neighbors are two sensor pixels apart. Central
        # differences therefore span four native sensor pixels.
        gx = (target[1:-1, 2:] - target[1:-1, :-2]) / 4 / sigma[1:-1, 1:-1]
        gy = (target[2:, 1:-1] - target[:-2, 1:-1]) / 4 / sigma[1:-1, 1:-1]
        fit = (
            usable[1:-1, 1:-1]
            & usable[1:-1, 2:]
            & usable[1:-1, :-2]
            & usable[2:, 1:-1]
            & usable[:-2, 1:-1]
        )
        if fit.sum() < 128:
            continue
        g = np.stack([gx[fit], gy[fit]], axis=1)
        e = residual[1:-1, 1:-1][fit]
        g -= g.mean(0)
        e -= e.mean()
        design += g.T @ g
        rhs += g.T @ e
        fit_samples += len(e)
    correlations = [
        p[k] for p in phases for k in ["lag2_sensor_x", "lag2_sensor_y"] if p.get(k) is not None
    ]
    condition = float(np.linalg.cond(design))
    shift = (
        np.linalg.solve(design, rhs).tolist()
        if np.isfinite(condition) and condition < 1e5 and fit_samples >= 512
        else None
    )
    return {
        "phases": phases,
        "samples": sum(p["samples"] for p in phases),
        "mean_phase_lag_correlation": float(np.mean(correlations)) if correlations else None,
        "first_order_shift_xy_sensor_pixels": shift,
        "shift_fit_samples": fit_samples,
        "shift_design_condition": condition if np.isfinite(condition) else None,
    }


def diagnose(manifest, output):
    manifest = Path(manifest).resolve()
    payload = manifest.read_bytes()
    input_sha256 = hashlib.sha256(payload).hexdigest()
    driver = Path(__file__).read_bytes()
    data = json.loads(payload)
    if data["split"] not in ["train", "quarantine"]:
        raise ValueError("Diagnose only training/quarantine data; held-out scoring stays closed")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "acquisition-or-prepared-manifest.json").write_bytes(payload)
    (output / Path(__file__).name).write_bytes(driver)
    rows, grouped = [], defaultdict(list)
    for case in data["cases"]:
        for crop in case["crops"]:
            path = manifest.parent / crop["path"]
            if sha(path) != crop["sha256"]:
                raise ValueError("Paired target crop checksum changed")
            with np.load(path, allow_pickle=False) as arrays:
                result = residual_diagnostics(
                    arrays["raw"],
                    arrays["sensor_reference"],
                    arrays["sensor_mask"],
                    case["metadata"]["pattern"],
                    case["conditioning"]["shot"],
                    case["conditioning"]["read"],
                )
            row = {
                "scene": case["scene"],
                "camera": case["metadata"]["camera"],
                "iso": case["metadata"].get("iso"),
                "noisy_sha256": case["noisy"]["sha256"],
                "crop": crop,
                **result,
            }
            rows.append(row)
            grouped[(row["scene"], row["noisy_sha256"])].append(row)
    (output / "per-crop.jsonl").write_text(
        "".join(json.dumps(row, allow_nan=False) + "\n" for row in rows)
    )
    cases = []
    for (scene, source), values in grouped.items():
        correlations = [
            r["mean_phase_lag_correlation"]
            for r in values
            if r["mean_phase_lag_correlation"] is not None
        ]
        shifts = [
            r["first_order_shift_xy_sensor_pixels"]
            for r in values
            if r["first_order_shift_xy_sensor_pixels"] is not None
        ]
        cases.append(
            {
                "scene": scene,
                "noisy_sha256": source,
                "camera": values[0]["camera"],
                "iso": values[0]["iso"],
                "crops": len(values),
                "median_phase_lag_correlation": float(np.median(correlations))
                if correlations
                else None,
                "median_first_order_shift_xy": np.median(shifts, axis=0).tolist()
                if shifts
                else None,
            }
        )
    cases.sort(
        key=lambda c: (
            c["median_phase_lag_correlation"]
            if c["median_phase_lag_correlation"] is not None
            else -2
        ),
        reverse=True,
    )
    summary = {
        "manifest": str(manifest),
        "manifest_sha256": input_sha256,
        "script_sha256": hashlib.sha256(driver).hexdigest(),
        "case_count": len(cases),
        "crop_count": len(rows),
        "cases": cases,
        "per_crop_sha256": sha(output / "per-crop.jsonl"),
        "scope": "Training/quarantine data diagnostic only; no target edits, model prediction or held-out scoring.",
        "method": "Measured same-color CFA residuals normalized by declared shot/read plus ADC variance; phase-centered lag correlation at2 sensor pixels, first-order gradient fit for a rough x/y translation descriptor.",
        "selection": "Reference mask, target in(.005,.95), observed<.99, >=128 samples/phase. No rejection/admission threshold is applied.",
        "limitations": "Reference noise is omitted from the normalization proxy. Real correlated sensor noise, gain/black-level errors, defocus, motion, interpolation and clipping can cause correlation or apparent shifts. Neither a nonzero fit nor correlation proves misregistration. Inspect native pairs; do not automatically change targets or evaluation.",
    }
    assert sha(manifest) == summary["manifest_sha256"] and sha(__file__) == summary["script_sha256"]
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"cases": len(cases), "crops": len(rows), "inspection_priorities": cases[:8]}),
        flush=True,
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    diagnose(args.manifest, args.output)
