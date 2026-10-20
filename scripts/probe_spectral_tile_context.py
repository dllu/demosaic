"""Generated CPU context sensitivity of the spectral operator, not model quality."""

import argparse
import hashlib
import math
import os
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import ref, save

from demosaic.cfa import PATTERNS, color_indices, malvar, mosaic
from demosaic.noise import add_noise, variance_map
from demosaic.prior import box_mean
from demosaic.raw_spectral import spectral_innovation
from demosaic.safety import writable_path


def digest(value):
    return hashlib.sha256(value.detach().numpy().tobytes(order="C")).hexdigest()


def scene(kind, size):
    y, x = torch.meshgrid(torch.arange(size), torch.arange(size), indexing="ij")
    wave = 0.001 * torch.sin(2 * math.pi * (x * math.cos(0.33) + y * math.sin(0.33)) / 14.5)
    if kind == "flat":
        value = torch.full_like(wave, 0.02)
    elif kind == "oblique-carrier":
        value = 0.02 + wave
    elif kind == "step-carrier":
        value = 0.02 + 0.30 * (x >= size // 2 + 16) + wave
    elif kind == "thin-grid":
        lines = ((x + 0.37 * y).remainder(37.0) < 2) | ((y - 0.21 * x).remainder(43.0) < 2)
        value = 0.02 + 0.04 * lines + wave
    else:
        raise ValueError(kind)
    return value[None, None] * torch.tensor([1.0, 0.9, 0.8])[None, :, None, None]


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    rng = torch.get_rng_state().clone()
    size, core_size, core_start = 768, 160, 304
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    rows, summaries, examples = [], [], {}
    with torch.inference_mode():
        for kind in ["flat", "oblique-carrier", "step-carrier", "thin-grid"]:
            clean_rgb = scene(kind, size)
            for label, shot, read in [
                ("ADC-only", 0.0, 0.0),
                ("high-noise", 0.00256, 0.0000262144),
            ]:
                for pattern in PATTERNS:
                    case = f"{kind}/{label}/{pattern}"
                    colors = color_indices(pattern)
                    seed = 20261020 + len(summaries)
                    generator = torch.Generator().manual_seed(seed)
                    packed = add_noise(
                        mosaic(clean_rgb, colors), shot, read, black_level=0.03, generator=generator
                    )
                    variance = variance_map(packed, shot, read)
                    # An observation-only coarse proxy, computed once on the
                    # entire field. Every context shares exactly the same
                    # base pixels; no clean target enters the forward.
                    base = box_mean(malvar(packed, colors, wb), 17)
                    full = spectral_innovation(base, packed, variance, colors, wb)
                    core = (
                        ...,
                        slice(core_start, core_start + core_size),
                        slice(core_start, core_start + core_size),
                    )
                    packed_core = (
                        ...,
                        slice(core_start // 2, (core_start + core_size) // 2),
                        slice(core_start // 2, (core_start + core_size) // 2),
                    )
                    reference = full[core]
                    case_rows = []
                    for tile in [256, 512]:
                        for dy in [-32, 0, 32]:
                            for dx in [-32, 0, 32]:
                                y, x = size // 2 - tile // 2 + dy, size // 2 - tile // 2 + dx
                                raw_roi = (
                                    ...,
                                    slice(y // 2, (y + tile) // 2),
                                    slice(x // 2, (x + tile) // 2),
                                )
                                rgb_roi = (..., slice(y, y + tile), slice(x, x + tile))
                                raw, var, coarse = packed[raw_roi], variance[raw_roi], base[rgb_roi]
                                cy, cx = core_start - y, core_start - x
                                assert (
                                    min(cy, cx, tile - cy - core_size, tile - cx - core_size) >= 16
                                )
                                local_core = (
                                    ...,
                                    slice(cy, cy + core_size),
                                    slice(cx, cx + core_size),
                                )
                                local_packed_core = (
                                    ...,
                                    slice(cy // 2, (cy + core_size) // 2),
                                    slice(cx // 2, (cx + core_size) // 2),
                                )
                                assert torch.equal(raw[local_packed_core], packed[packed_core])
                                assert torch.equal(var[local_packed_core], variance[packed_core])
                                assert torch.equal(coarse[local_core], base[core])
                                correction = spectral_innovation(coarse, raw, var, colors, wb)[
                                    local_core
                                ]
                                assert torch.isfinite(correction).all()
                                difference = correction.double() - reference.double()
                                t = math.log((tile // 2) ** 2 / 0.01)
                                row = {
                                    "case": case,
                                    "tile_native": tile,
                                    "offset_yx": [dy, dx],
                                    "context_native_xywh": [x, y, tile, tile],
                                    "common_native_xywh": [
                                        core_start,
                                        core_start,
                                        core_size,
                                        core_size,
                                    ],
                                    "threshold": 4 + 4 * math.sqrt(t) + 2 * t,
                                    "phase_mean_variance": var.mean((-2, -1)).flatten().tolist(),
                                    "correction_sha256": digest(correction),
                                    "core_difference_to_full_context_RMS_DN16": float(
                                        difference.square().mean().sqrt() * 65535
                                    ),
                                    "core_difference_to_full_context_max_DN16": float(
                                        difference.abs().max() * 65535
                                    ),
                                    "core_difference_mean_RGB_DN16": (
                                        difference.mean((-2, -1)) * 65535
                                    )
                                    .flatten()
                                    .tolist(),
                                    "core_correction_RMS_DN16": float(
                                        correction.double().square().mean().sqrt() * 65535
                                    ),
                                }
                                rows.append(row)
                                case_rows.append(row)
                                if dy == dx == 0:
                                    repeated = spectral_innovation(coarse, raw, var, colors, wb)[
                                        local_core
                                    ]
                                    assert digest(repeated) == row["correction_sha256"]
                                    if pattern == "RGGB" and label == "high-noise":
                                        examples[f"{kind}-{tile}"] = correction.numpy().copy()
                    if pattern == "RGGB" and label == "high-noise":
                        examples[f"{kind}-full"] = reference.numpy().copy()
                    summaries.append(
                        {
                            "case": case,
                            "seed": seed,
                            "shot": shot,
                            "read_variance": read,
                            "raw_sha256": digest(packed),
                            "variance_sha256": digest(variance),
                            "fixed_base_sha256": digest(base),
                            "common_core_raw_sha256": digest(packed[packed_core]),
                            "full_context_correction_sha256": digest(reference),
                            "all_common_core_raw_variance_base_pixels_exact": True,
                            "center_context_repeats_exact": True,
                            "by_tile": {
                                str(tile): {
                                    "min_RMS_DN16": min(
                                        r["core_difference_to_full_context_RMS_DN16"]
                                        for r in case_rows
                                        if r["tile_native"] == tile
                                    ),
                                    "max_RMS_DN16": max(
                                        r["core_difference_to_full_context_RMS_DN16"]
                                        for r in case_rows
                                        if r["tile_native"] == tile
                                    ),
                                    "max_absolute_DN16": max(
                                        r["core_difference_to_full_context_max_DN16"]
                                        for r in case_rows
                                        if r["tile_native"] == tile
                                    ),
                                }
                                for tile in [256, 512]
                            },
                        }
                    )
    assert len(rows) == 576 and len(summaries) == 32
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    np.savez(root / "example-corrections.npz", **examples)
    save(root / "per-context.json", rows)
    save(root / "per-case.json", summaries)
    result = {
        "status": "completed-generated-CPU-spectral-operator-context-diagnostic",
        "driver": ref(__file__),
        "sources": [
            ref(Path("src/demosaic") / n)
            for n in ["raw_spectral.py", "cfa.py", "noise.py", "prior.py"]
        ],
        "full_native_size": size,
        "common_native_xywh": [304, 304, 160, 160],
        "context_sizes": [256, 512],
        "context_offsets": [-32, 0, 32],
        "minimum_native_border_margin": 16,
        "unit_gate": 1.0,
        "fixed_base": "Global observation-only MHC followed by17px box mean; same base pixels in every context",
        "WB": wb.flatten().tolist(),
        "ADC_black_level": 0.03,
        "CFA_patterns": list(PATTERNS),
        "cases": 32,
        "context_rows": 576,
        "per_context": ref(root / "per-context.json"),
        "per_case": ref(root / "per-case.json"),
        "example_corrections": ref(root / "example-corrections.npz"),
        "all_source_core_and_repeat_checks_passed": True,
        "Torch_CPU_RNG_unchanged": True,
        "CUDA_initialized": False,
        "scope": "Generated CPU spectral operator only, with gate fixed1 and a fixed observation-only coarse base. Reference means full768-context operator, not GT. No learned checkpoint, DINO, training or photograph. Real model base/gates can vary with context as well; these differences cannot predict trained-model quality, visible seams or100MP behavior. No thresholds, data, defaults or active training change.",
    }
    save(root / "receipt.json", result)
    print({"receipt": ref(root / "receipt.json"), "cases": len(summaries), "contexts": len(rows)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.output)
