"""Inspect isolated bright samples in cached paired training references.

This diagnostic never changes references, masks or training admission. Candidates
can be real highlights. It uses the noisy capture's conditioning as a conservative
screen, not as a calibrated model of the low-ISO reference's residual noise.
"""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from demosaic import hotpixels
from demosaic.hotpixels import NEIGHBORS, repair_hot_pixels
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def isolated_reference_candidates(
    reference, count, *, shot, read, sigma=6.0, ratio=2.0, min_delta=0.005
):
    """Return per-color candidates and neighbor maxima, including masked sites.

    All nine samples must have actual measured support in the *same channel*.
    Registration may change CFA phase or combine different phases; neither the
    noisy CFA pattern nor a sum of sparse RGB channels identifies reference phase.
    The two-pixel border is omitted. No coherence or defect inference is made.
    """
    reference, count = np.asarray(reference), np.asarray(count)
    if (
        reference.ndim != 3
        or reference.shape[0] != 3
        or count.shape != reference.shape
        or min(reference.shape[1:]) < 5
    ):
        raise ValueError("Expected measured RGB samples and matching counts, at least 5x5")
    if (
        not np.isfinite(reference).all()
        or not np.isfinite(count).all()
        or np.any(count < 0)
        or not all(math.isfinite(x) for x in (shot, read, sigma, ratio, min_delta))
        or min(shot, read, min_delta) < 0
        or sigma <= 0
        or ratio <= 1
    ):
        raise ValueError("Nonfinite samples or invalid support/noise/thresholds")
    center = reference[:, 2:-2, 2:-2].astype(np.float64)
    supported = count[:, 2:-2, 2:-2] > 0
    height, width = reference.shape[-2:]
    maximum = np.full_like(center, -np.inf)
    for dy, dx in NEIGHBORS:
        region = (..., slice(2 + dy, height - 2 + dy), slice(2 + dx, width - 2 + dx))
        maximum = np.maximum(maximum, reference[region])
        supported &= count[region] > 0
    positive = maximum.clip(0)
    margin = np.maximum(min_delta, sigma * np.sqrt(shot * positive + read))
    sites = supported & (center > ratio * positive) & (center - maximum > margin)
    candidates = np.zeros(reference.shape, bool)
    neighbors = np.zeros(reference.shape, np.float64)
    candidates[:, 2:-2, 2:-2] = sites
    neighbors[:, 2:-2, 2:-2] = maximum
    return candidates, neighbors


def _write(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def audit(manifest, output):
    manifest = Path(manifest).absolute()
    payload = manifest.read_bytes()
    data = json.loads(payload)
    if data["split"] not in ("train", "quarantine"):
        raise ValueError("Audit training/quarantine only; held-out protocols remain unchanged")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    code_paths = [Path(__file__).absolute(), Path(hotpixels.__file__).absolute()]
    sources = [{"path": str(path), "sha256": sha(path)} for path in code_paths]
    inputs, rows = {}, []
    by_camera = defaultdict(lambda: defaultdict(int))
    by_scene = defaultdict(lambda: defaultdict(int))
    report = output / "per-crop.jsonl"
    with report.open("x") as stream:
        for case in data["cases"]:
            metadata = case["metadata"]
            shot, read = (float(case["conditioning"][key]) for key in ("shot", "read"))
            for crop in case["crops"]:
                path = (manifest.parent / crop["path"]).absolute()
                digest = sha(path)
                if digest != crop["sha256"]:
                    raise ValueError(f"Prepared crop checksum mismatch: {path}")
                inputs[str(path)] = digest
                with np.load(path, allow_pickle=False) as archive:
                    raw, target = archive["raw"], archive["sensor_reference"]
                    count, valid = archive["sensor_count"], archive["sensor_mask"].astype(bool)
                    rgb = archive["reference_rgb"]
                assert target.shape == valid.shape == count.shape == (3, *raw.shape)
                if raw.shape[0] % 4 or raw.shape[1] % 4:
                    raise ValueError("Prepared paired dimensions must be divisible by four")
                assert np.isfinite(raw).all() and np.isfinite(rgb).all()
                assert not np.any(valid & (count == 0))
                candidates, maximum = isolated_reference_candidates(
                    target, count, shot=shot, read=read
                )
                repaired, input_summary = repair_hot_pixels(
                    raw, shot=shot, read=read, pattern=metadata["pattern"]
                )
                input_sites = raw != repaired
                accepted = candidates & valid
                shared_locations = candidates.any(0) & input_sites
                excess = target.astype(np.float64) - maximum
                coordinates = np.column_stack(np.nonzero(candidates))
                order = sorted(
                    range(len(coordinates)),
                    key=lambda i: (
                        bool(valid[tuple(coordinates[i])]),
                        float(excess[tuple(coordinates[i])]),
                    ),
                    reverse=True,
                )
                coarse_valid = (
                    valid.any(0).reshape(raw.shape[0] // 4, 4, raw.shape[1] // 4, 4).all((1, 3))
                )
                examples = []
                for index in order[:16]:
                    color, y, x = map(int, coordinates[index])
                    examples.append(
                        {
                            "color": color,
                            "xy": [x, y],
                            "reference": float(target[color, y, x]),
                            "same_channel_neighbor_max": float(maximum[color, y, x]),
                            "excess": float(excess[color, y, x]),
                            "measured_count": int(count[color, y, x]),
                            "sensor_loss_valid": bool(valid[color, y, x]),
                            "coarse_RGB_loss_block_valid": bool(coarse_valid[y // 4, x // 4]),
                            "input_detector_changes_same_location": bool(input_sites[y, x]),
                        }
                    )
                counts = {
                    "crops": 1,
                    "measured_samples": int((count > 0).sum()),
                    "valid_samples": int(valid.sum()),
                    "reference_candidates": int(candidates.sum()),
                    "reference_candidates_sensor_loss_valid": int(accepted.sum()),
                    "reference_candidates_sensor_loss_masked": int((candidates & ~valid).sum()),
                    "input_repair_sites": int(input_sites.sum()),
                    "input_and_reference_candidate_locations": int(shared_locations.sum()),
                }
                row = {
                    "scene": case["scene"],
                    "camera": metadata["camera"],
                    "iso": metadata["iso"],
                    "id": crop["id"],
                    "input": {"path": str(path), "sha256": digest},
                    "crop_xywh": crop["xywh"],
                    "conditioning": {"shot": shot, "read": read},
                    "counts": counts,
                    "examples": examples,
                    "reference_alignments": case["references"],
                    "input_detector_summary": input_summary,
                    "valid_candidate_excess_squared": float(np.square(excess[accepted]).sum()),
                    "valid_candidate_absolute_excess": float(excess[accepted].sum()),
                }
                rows.append(row)
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                for key, value in counts.items():
                    by_camera[metadata["camera"]][key] += value
                    by_scene[case["scene"]][key] += value
                if len(rows) % 32 == 0:
                    print(
                        json.dumps({"completed_crops": len(rows), "last_scene": case["scene"]}),
                        flush=True,
                    )
    assert manifest.read_bytes() == payload
    for path, digest in inputs.items():
        assert sha(path) == digest, path
    assert all(sha(item["path"]) == item["sha256"] for item in sources)
    if not rows:
        raise ValueError("No prepared paired crops to audit")
    totals = {key: sum(row["counts"][key] for row in rows) for key in rows[0]["counts"]}
    result = {
        "recorded_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "manifest": {"path": str(manifest), "sha256": hashlib.sha256(payload).hexdigest()},
        "sources": sources,
        "cases": len(data["cases"]),
        "totals": totals,
        "by_camera": dict(by_camera),
        "by_scene": dict(by_scene),
        "per_crop": {"path": str(report), "sha256": sha(report)},
        "inputs": inputs,
        "reference_detector": {
            "sigma": 6,
            "ratio": 2,
            "minimum_excess": 0.005,
            "neighbors": list(NEIGHBORS),
            "coherence_filter": False,
        },
        "counts_use_all_supported_measured_channels_not_noisy_CFA_phase": True,
        "candidate_is_a_proven_defect": False,
        "limitations": "Measured-reference bright-isolation screen, not a sensor defect map. Real tiny highlights/texture can trigger it. Uses noisy-input conditioning, not estimated reference noise. Missing/saturated reference samples already omitted during preparation cannot be recovered from these caches. Candidates are counted before and after existing masks; no masks, targets, data admission or training recipe change. Input repair's coherent-light filter is separate. Visual review is required.",
        "new_model_or_encoder_calls": 0,
        "optimizer_updates": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "CUDA_initialized": False,
    }
    _write(output / "result.json", result)
    print(json.dumps({"complete": True, "totals": totals}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.manifest, args.output)
