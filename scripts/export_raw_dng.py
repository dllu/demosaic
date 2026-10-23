"""Restore RAW/XMP pairs to native RGB16 DNGs and edited full-resolution JPEGs.

Run with PYTHONPATH=src after sourcing scripts/env.sh. Input globs may be quoted.
Source RAWs/sidecars are read-only; model caches follow scripts/env.sh.
"""

import argparse
import gc
import glob
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import torch

from demosaic.calibration import estimate_noise
from demosaic.cfa import color_indices
from demosaic.dng import (
    adapt_darktable_xmp,
    copy_capture_metadata,
    export_path,
    render_darktable_jpeg,
    write_dng,
)
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.io import read_raw
from demosaic.noise import Sensor
from demosaic.precision import cudnn_autotune


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def select_pairs(patterns, *, only_with_xmp=False):
    inputs = set()
    for pattern in patterns:
        matches = glob.glob(str(Path(pattern).expanduser()))
        if not matches:
            raise FileNotFoundError(f"No input matched {pattern}")
        inputs.update(Path(path).resolve() for path in matches)
    pairs = []
    for source in sorted(inputs):
        if not source.is_file():
            raise ValueError(f"Input is not a file: {source}")
        candidates = [Path(str(source) + suffix) for suffix in (".xmp", ".XMP")]
        candidates.extend(source.with_suffix(suffix) for suffix in (".xmp", ".XMP"))
        xmp = next((path for path in candidates if path.is_file()), None)
        if xmp is None:
            if only_with_xmp:
                continue
            raise FileNotFoundError(f"No XMP for {source}; use --only-with-xmp to filter")
        pairs.append((source, xmp.resolve()))
    if not pairs:
        raise ValueError("No RAW/XMP pairs selected")
    return pairs


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("checkpoint", type=Path)
    root.add_argument("inputs", nargs="+", help="RAW filenames or quoted glob patterns")
    root.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Explicitly authorize this export directory; originals remain read-only",
    )
    root.add_argument("--only-with-xmp", action="store_true")
    root.add_argument("--suffix", help="Filename suffix; defaults to the checkpoint stem")
    root.add_argument("--darktable-cli", default="darktable-cli")
    root.add_argument("--shot", type=float)
    root.add_argument("--read", type=float)
    root.add_argument("--tile", type=int, default=512)
    root.add_argument("--overlap", type=int, default=64)
    root.add_argument("--batch-size", type=int, default=4)
    root.add_argument("--device", default="cuda")
    root.add_argument("--cudnn-benchmark", action="store_true")
    root.add_argument("--jpeg-quality", type=int, default=97)
    root.add_argument("--overwrite", action="store_true")
    return root


def run(args):
    if (args.shot is None) != (args.read is None):
        raise ValueError("Supply both --shot and --read, or neither for input-only estimation")
    if args.shot is not None and not all(
        math.isfinite(x) and x >= 0 for x in (args.shot, args.read)
    ):
        raise ValueError("Noise coefficients must be finite and nonnegative")
    if not 1 <= args.jpeg_quality <= 100:
        raise ValueError("JPEG quality must be in [1,100]")
    if shutil.which(str(args.darktable_cli)) is None:
        raise FileNotFoundError(f"darktable-cli not found: {args.darktable_cli}")
    checkpoint_path = args.checkpoint.expanduser().resolve()
    suffix = args.suffix if args.suffix is not None else checkpoint_path.stem
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", suffix):
        raise ValueError(
            "Suffix must start with a letter/digit and contain only letters, digits, _, . or -"
        )
    pairs = select_pairs(args.inputs, only_with_xmp=args.only_with_xmp)
    output = args.output_dir.expanduser().resolve()
    jobs, destinations = [], set()
    protected = {checkpoint_path, *(source for source, _ in pairs), *(xmp for _, xmp in pairs)}
    for source, xmp in pairs:
        stem = source.stem + "-" + suffix
        dng, jpeg = output / (stem + ".dng"), output / (stem + ".jpg")
        sidecar = Path(str(dng) + ".xmp")
        adapt_darktable_xmp(xmp.read_bytes())  # Validate all histories before inference.
        for path in (dng, jpeg, sidecar):
            export_path(path, output_root=output, source=source, overwrite=args.overwrite)
            if path in destinations or path in protected:
                raise ValueError(f"Output collides with another output or input: {path}")
            destinations.add(path)
        jobs.append((source, xmp, dng, jpeg))
    manifest_path = export_path(
        output / f"export-{suffix}.json", output_root=output, overwrite=args.overwrite
    )
    if manifest_path in protected:
        raise ValueError("Manifest must not overwrite an input")
    torch.set_num_threads(4)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "checkpoint": str(checkpoint_path),
        "precision": "IEEE FP32",
        "noise_policy": "Explicit coefficients or reliable input-only Haar fit, nominal ISO fallback",
        "preview": "Original darktable edits; identity RAW preparation; RAW/profiled denoising disabled; sRGB JPEG 4:4:4",
        "completed": [],
    }
    with cudnn_autotune(args.device, enabled=args.cudnn_benchmark, precision="float32"):
        model, checkpoint = load_checkpoint(checkpoint_path, args.device)
        if model.config.rgb_hidden_autocast:
            raise ValueError(
                "IEEE FP32 export requires a checkpoint without forced hidden autocast"
            )
        manifest["model_config"] = model.config.to_dict()
        manifest["checkpoint_sha256"] = checkpoint["loaded_sha256"]
        manifest["checkpoint_step"] = checkpoint.get("step")
        del checkpoint
        gc.collect()
        for source, xmp, dng, jpeg in jobs:
            print(f"Restoring {source.name}", flush=True)
            source_stat = source.stat()
            source_hash = digest(source)
            xmp_data = xmp.read_bytes()
            xmp_hash = hashlib.sha256(xmp_data).hexdigest()
            adapted = adapt_darktable_xmp(xmp_data)
            raw, metadata = read_raw(source)
            estimate = None
            if args.shot is None:
                estimate = estimate_noise(raw)
                shot, read = (
                    (estimate.shot, estimate.read)
                    if estimate.reliable
                    else Sensor(iso=metadata.iso or 100).coefficients()
                )
                noise_method = (
                    "input-only-Haar-fit" if estimate.reliable else "nominal-ISO-fallback"
                )
            else:
                shot, read, noise_method = args.shot, args.read, "explicit"
            rgb, stats = restore_tiled(
                model,
                raw,
                color_indices(metadata.pattern),
                shot=shot,
                read=read,
                tile=args.tile,
                overlap=args.overlap,
                batch_size=args.batch_size,
                device=args.device,
                wb=metadata.white_balance,
                matrix=metadata.camera_to_srgb,
                precision="float32",
                refinement_precision="float32",
            )
            del raw
            provenance = {
                "checkpoint_sha256": manifest["checkpoint_sha256"],
                "source_sha256": source_hash,
                "xmp_sha256": xmp_hash,
                "shot": shot,
                "read": read,
                "noise_method": noise_method,
                "noise_estimate": estimate.to_dict() if estimate else None,
                "inference": stats,
            }
            write_dng(
                dng,
                rgb.permute(1, 2, 0).numpy(),
                metadata=metadata,
                provenance=provenance,
                xmp=adapted,
                output_root=output,
                overwrite=args.overwrite,
            )
            del rgb
            gc.collect()
            metadata_copied = copy_capture_metadata(source, dng)
            sidecar = render_darktable_jpeg(
                dng,
                xmp,
                jpeg,
                executable=args.darktable_cli,
                output_root=output,
                quality=args.jpeg_quality,
                overwrite=args.overwrite,
            )
            copy_capture_metadata(source, jpeg)
            if (
                source.stat().st_size != source_stat.st_size
                or source.stat().st_mtime_ns != source_stat.st_mtime_ns
                or digest(xmp) != xmp_hash
            ):
                raise RuntimeError("Source changed during export")
            manifest["completed"].append(
                {
                    "source": str(source),
                    "xmp": str(xmp),
                    **provenance,
                    "capture_exif_copied": metadata_copied,
                    "outputs": [
                        {"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}
                        for path in (dng, jpeg, sidecar)
                    ],
                }
            )
            temporary = manifest_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(manifest, indent=2) + "\n")
            temporary.replace(manifest_path)
            print(f"Exported {dng.name} and {jpeg.name}", flush=True)
    return manifest


if __name__ == "__main__":
    run(parser().parse_args())
