"""CPU-only generation/augmentation preflight; no model training or quality score."""

import argparse
import hashlib
import json
import random
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from demosaic.data import augment_before_downsample
from demosaic.safety import writable_path
from demosaic.textures import weak_texture


def digest(value):
    return hashlib.sha256(value.detach().contiguous().numpy().tobytes()).hexdigest()


def contrast(value):
    channel = value[0].double()
    return float((channel / channel.mean() - 1).square().mean().sqrt())


def preflight(output):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    code = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, value in code.items():
        (output / "source" / name).write_bytes(value)
    shutil.copyfile(__file__, output / Path(__file__).name)
    records = []
    for kind in ["bandlimited", "fibers"]:
        for seed in range(16):
            rng = random.Random(20261016 + seed)
            started = time.perf_counter()
            rgb, recipe = weak_texture(512, rng, pixel_scale=2, kind=kind)
            generated_seconds = time.perf_counter() - started
            reduced = F.avg_pool2d(rgb, 2)
            started = time.perf_counter()
            augmented = augment_before_downsample(rgb, 256, rng)
            augmented_seconds = time.perf_counter() - started
            for value in [rgb, reduced, augmented]:
                assert value.dtype == torch.float32 and torch.isfinite(value).all()
                assert 0 < value.min() < value.max() < 1
            assert reduced.shape == augmented.shape == (3, 256, 256)
            rms_input, rms_reduced, rms_augmented = (contrast(v) for v in [rgb, reduced, augmented])
            ratio = rms_reduced / rms_input
            assert 0.8 < ratio <= 1.00001
            assert rms_augmented > 0
            records.append(
                {
                    "kind": kind,
                    "selection_seed": 20261016 + seed,
                    "recipe": recipe,
                    "input_sha256": digest(rgb),
                    "area2_sha256": digest(reduced),
                    "augmented_sha256": digest(augmented),
                    "rms_relative_contrast_input": rms_input,
                    "rms_relative_contrast_area2": rms_reduced,
                    "rms_relative_contrast_augmented": rms_augmented,
                    "area2_rms_retention": ratio,
                    "generated_seconds": generated_seconds,
                    "augmented_seconds": augmented_seconds,
                    "final_unique_16bit_codes": int(
                        torch.unique((augmented * 65535).round()).numel()
                    ),
                    "float_not_aligned_to_16bit_fraction": float(
                        ((augmented * 65535 - (augmented * 65535).round()).abs() > 1e-3)
                        .float()
                        .mean()
                    ),
                }
            )
            if seed < 2:
                path = output / f"{kind}-{seed}.npz"
                np.savez(
                    path, input=rgb.numpy(), area2=reduced.numpy(), augmented=augmented.numpy()
                )
                records[-1]["fixture"] = {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
    assert all(Path("src/demosaic", name).read_bytes() == value for name, value in code.items())
    assert not torch.cuda.is_initialized()
    summary = []
    for kind in ["bandlimited", "fibers"]:
        rows = [r for r in records if r["kind"] == kind]
        summary.append(
            {
                "kind": kind,
                "samples": len(rows),
                "area2_rms_retention_range": [
                    min(r["area2_rms_retention"] for r in rows),
                    max(r["area2_rms_retention"] for r in rows),
                ],
                "generated_ms_median_after_first_two": float(
                    np.median([r["generated_seconds"] * 1000 for r in rows[2:]])
                ),
                "augmented_ms_median_after_first_two": float(
                    np.median([r["augmented_seconds"] * 1000 for r in rows[2:]])
                ),
            }
        )
    result = {
        "scope": "32 experimental generated512px fields, pixel_scale2, existing geometry/PSF before finalarea2. CPU FP32/two threads; active training recipes unchanged. This is generation/routing execution, not learned-model quality or isolated training throughput.",
        "cuda_initialized": False,
        "summary": summary,
        "records": records,
        "source_files": {name: hashlib.sha256(value).hexdigest() for name, value in code.items()},
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"receipt": str(output / "receipt.json"), "summary": summary}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/mnt/external/demosaic/benchmarks/weak-texture-source-v1"),
    )
    args = parser.parse_args()
    torch.set_num_threads(2)
    preflight(args.output)
