"""Prepare aligned paired-RAW validation crops without model-dependent targets."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .calibration import estimate_noise
from .io import read_raw
from .noise import Sensor
from .paired import verify_file
from .registration import align_raw, calibrate_rgb, measured_reference
from .safety import writable_path


def read_reference(path):
    import rawpy

    raw, metadata = read_raw(path)
    with rawpy.imread(str(path)) as decoder:
        rgb = (
            decoder.postprocess(
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                output_color=rawpy.ColorSpace.raw,
                output_bps=16,
                no_auto_bright=True,
                use_camera_wb=False,
                use_auto_wb=False,
                user_wb=[1.0, 1.0, 1.0, 1.0],
                gamma=(1.0, 1.0),
                adjust_maximum_thr=0.0,
                median_filter_passes=0,
                user_flip=0,
            ).astype(np.float32)
            / 65535
        )
    rgb, calibration = calibrate_rgb(rgb, raw, metadata.pattern)
    return raw, rgb, metadata, calibration


def prepare_pairs(manifest, output, *, size=512, grid=3, max_shift=128):
    """Fixed sensor-coordinate grid, measured-CFA truth and auxiliary AHD RGB.

    Test preprocessing is possible, but callers must keep test targets out of
    model selection. This routine never loads or scores a learned model.
    """
    if size < 32 or size % 16 or not 1 <= grid <= 5 or max_shift < 0:
        raise ValueError("Invalid crop size, grid or registration range")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    payload = Path(manifest).read_bytes()
    source = json.loads(payload)
    code_digest = hashlib.sha256()
    source_files = {}
    for path in sorted(Path(__file__).parent.glob("*.py")):
        content = path.read_bytes()
        code_digest.update(path.name.encode() + content)
        source_files[path.name] = content
    archive = output / "source" / code_digest.hexdigest()
    protocol = {
        "format_version": 1,
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "source_sha256": code_digest.hexdigest(),
        "size": size,
        "grid": grid,
        "max_shift": max_shift,
        "split": source["split"],
        "registration": "green phase correlation + integer L1, scalar gain, max green L1 .035",
        "reference": "Measured clean CFA samples; independently calibrated LibRaw AHD RGB is auxiliary",
        "noise": "Reliable input-only Haar estimate; disclosed nominal ISO prior otherwise",
        "mask": "Measured clean raw <.99, transformed reference RGB in [-.005,.98), >=50% valid crop pixels",
    }
    protocol_path = output / "protocol.json"
    if protocol_path.exists() and json.loads(protocol_path.read_text()) != protocol:
        raise ValueError("Preparation protocol differs; choose a new output directory")
    archive.mkdir(parents=True, exist_ok=True)
    for name, content in source_files.items():
        (archive / name).write_bytes(content)
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n")
    (archive / "acquisition-manifest.json").write_bytes(payload)
    cases, rejected = [], []
    for scene in source["selection"]:
        references = []
        for record in scene["clean"]:
            verify_file(record["path"], record)
            raw, rgb, metadata, calibration = read_reference(record["path"])
            references.append((record, raw, rgb, metadata, calibration))
        for record in scene["noisy"]:
            verify_file(record["path"], record)
            raw, metadata = read_raw(record["path"])
            registered = []
            for ref, clean, rgb, refmeta, calibration in references:
                if refmeta.camera != metadata.camera or clean.shape != raw.shape:
                    raise ValueError("Reference/noisy camera or active sensor geometry differs")
                try:
                    alignment = align_raw(
                        clean, raw, refmeta.pattern, metadata.pattern, max_shift=max_shift
                    )
                except ValueError as exc:
                    rejected.append(
                        {
                            "scene": scene["scene"],
                            "noisy_sha256": record["sha256"],
                            "reference_sha256": ref["sha256"],
                            "reason": str(exc),
                        }
                    )
                    continue
                registered.append((ref, clean, rgb, refmeta, calibration, alignment))
            if not registered:
                print(
                    json.dumps(
                        {"event": "paired-rejected", "scene": scene["scene"], "iso": metadata.iso}
                    ),
                    flush=True,
                )
                continue
            estimate = estimate_noise(raw)
            if estimate.reliable:
                shot, read = estimate.shot, estimate.read
                method = "input-only-Haar-fit"
            else:
                shot, read = Sensor(iso=metadata.iso or record["iso_label"] or 100).coefficients()
                method = "nominal-ISO-fallback"
            h, w = raw.shape
            margin = max_shift + 32
            if min(h, w) < size + 2 * margin:
                raise ValueError("Sensor image is too small for the declared fixed crop grid")
            ys = np.unique(np.linspace(margin, h - margin - size, grid).astype(int) // 2 * 2)
            xs = np.unique(np.linspace(margin, w - margin - size, grid).astype(int) // 2 * 2)
            crops = []
            for y in ys:
                for x in xs:
                    rgb_sum = np.zeros((3, size, size), np.float32)
                    sensor_sum = np.zeros_like(rgb_sum)
                    sensor_count = np.zeros_like(rgb_sum, dtype=np.uint8)
                    for _, clean, rgb, refmeta, _, alignment in registered:
                        values, weights = measured_reference(
                            clean, refmeta.pattern, alignment, int(y), int(x), size
                        )
                        weights *= values < 0.99 * alignment.gain
                        sensor_sum += values * weights
                        sensor_count += weights
                        dy, dx = alignment.dy, alignment.dx
                        rgb_sum += (
                            rgb[y - dy : y - dy + size, x - dx : x - dx + size].transpose(2, 0, 1)
                            * alignment.gain
                        )
                    reference_rgb = rgb_sum / len(registered)
                    sensor_mean = sensor_sum / np.maximum(sensor_count, 1)
                    wb = np.asarray(metadata.white_balance, np.float32)
                    matrix = np.asarray(metadata.camera_to_srgb, np.float32)
                    linear_rgb = np.einsum("ij,jhw->ihw", matrix, reference_rgb * wb[:, None, None])
                    valid_pixel = (linear_rgb.min(0) >= -0.005) & (linear_rgb.max(0) < 0.98)
                    valid = (sensor_count > 0) & valid_pixel[None]
                    coverage = float(valid.any(0).mean())
                    identity = f"{scene['scene']}:{record['sha256']}:{y}:{x}"
                    if coverage < 0.5:
                        rejected.append(
                            {
                                "id": identity,
                                "reason": "less_than_half_valid_reference_pixels",
                                "coverage": coverage,
                            }
                        )
                        continue
                    name = f"crop-{hashlib.sha256(identity.encode()).hexdigest()[:24]}.npz"
                    path = writable_path(output / name)
                    temporary = path.with_suffix(".tmp")
                    with temporary.open("wb") as handle:
                        np.savez(
                            handle,
                            raw=raw[y : y + size, x : x + size],
                            reference_rgb=reference_rgb,
                            sensor_reference=sensor_mean,
                            sensor_mask=valid,
                            sensor_count=sensor_count,
                        )
                    temporary.replace(path)
                    with path.open("rb") as handle:
                        digest = hashlib.file_digest(handle, "sha256").hexdigest()
                    crops.append(
                        {
                            "id": identity,
                            "path": name,
                            "sha256": digest,
                            "xywh": [int(x), int(y), size, size],
                            "valid_fraction": coverage,
                        }
                    )
            case = {
                "scene": scene["scene"],
                "unknown_sensor": bool(scene.get("unknown_sensor")),
                "noisy": record,
                "metadata": asdict(metadata),
                "conditioning": {
                    "shot": shot,
                    "read": read,
                    "method": method,
                    "estimate": estimate.to_dict(),
                },
                "references": [
                    {
                        "sha256": ref["sha256"],
                        "alignment": alignment.to_dict(),
                        "rgb_calibration": calibration,
                    }
                    for ref, _, _, _, calibration, alignment in registered
                ],
                "crops": crops,
            }
            cases.append(case)
            (output / f"pair-{record['sha256'][:24]}.json").write_text(
                json.dumps(case, indent=2, allow_nan=False) + "\n"
            )
            print(
                json.dumps(
                    {
                        "event": "paired-prepared",
                        "scene": scene["scene"],
                        "iso": metadata.iso,
                        "references": len(registered),
                        "crops": len(crops),
                        "conditioning": method,
                        "shot": shot,
                        "read": read,
                    }
                ),
                flush=True,
            )
    result = {
        **protocol,
        "dataset_license": source["dataset_license"],
        "attribution": source["attribution"],
        "cases": cases,
        "rejected": rejected,
        "notes": [
            "Low-ISO references retain noise; AHD-derived RGB is not exact RGB ground truth.",
            "Development scenes may be in RawNIND training. Test targets must stay out of model selection.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
