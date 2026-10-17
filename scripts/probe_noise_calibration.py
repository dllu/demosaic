"""Prespecified synthetic stress grid for the current single-RAW noise estimate.

No restoration model, camera-specific fit, protected source or production change.
Variance comparisons use the known pre-ADC model. Empirical moment diagnostics
restrict clean signal to(.03,.85) and retain ADC behavior. The legacy field name
uncensored_interior_samples counts that interval; it is not a no-clipping claim.
Coefficient identifiability is separate.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch

from demosaic.calibration import estimate_noise
from demosaic.noise import add_noise
from demosaic.safety import writable_path

PROFILES = [
    ("iso100-prior", 0.00002, 1.6e-9),
    ("iso1600-prior", 0.00032, 4.096e-7),
    ("iso12800-prior", 0.00256, 2.62144e-5),
    ("read-dominated", 0.00001, 0.000025),
    ("mixed", 0.0008, 0.00001),
    ("shot-dominated", 0.00128, 1e-9),
]
SCENES = [
    "broad-flat-fields",
    "affine-shading",
    "sparse-fine-texture",
    "clipped-and-dark",
    "narrow-span-gray",
]
LEVELS = [0.001, 0.005, 0.02, 0.08, 0.2, 0.6]
BLACK = 0.03


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def scene(name, seed):
    """1024px native Bayer fields; local RNG, fixed field structure and phases."""
    rng = np.random.default_rng(8000 + seed)
    levels = rng.uniform(0.01, 0.85, (8, 8))
    if name == "narrow-span-gray":
        levels = 0.18 + (levels - levels.mean()) * 0.005
    elif name == "clipped-and-dark":
        levels[:2] = np.array([0, 0.0001, 0.0005, 0.001, 0.95, 0.99, 1.0, 1.1])[None]
    values = np.repeat(np.repeat(levels, 128, 0), 128, 1)
    yy, xx = np.mgrid[:1024, :1024]
    if name == "affine-shading":
        values += 0.15 * values * ((xx % 128 - 63.5) + (yy % 128 - 63.5)) / 128
    elif name == "sparse-fine-texture":
        contaminated = np.repeat(
            np.repeat((np.arange(64).reshape(8, 8) + seed) % 4 == 0, 128, 0), 128, 1
        )
        texture = (
            np.sin(2 * np.pi * (xx / 7 + yy / 11)) + np.sin(2 * np.pi * (xx / 13 - yy / 5))
        ) / 2
        values += 0.04 * contaminated * texture
    if name != "narrow-span-gray":
        values *= np.tile([[0.65, 1.0], [1.0, 0.45]], (512, 512))
    return np.maximum(values, 0).astype(np.float32)


def variance_diagnostics(estimate, shot, read):
    if estimate.shot is None or estimate.read is None:
        return None
    truth = np.asarray(LEVELS, dtype=np.float64) * shot + read
    fitted = np.asarray(LEVELS, dtype=np.float64) * estimate.shot + estimate.read
    if not np.all(fitted > 0):
        return {"finite_positive": False, "signed_dB": None}
    return {"finite_positive": True, "signed_dB": (10 * np.log10(fitted / truth)).tolist()}


def moment_diagnostics(clean, noisy, shot, read):
    valid = (clean > 0.03) & (clean < 0.85)
    standardized = (
        (noisy.astype(np.float64) - clean) / np.sqrt(clean.astype(np.float64) * shot + read)
    )[valid]
    return {
        "uncensored_interior_samples": int(valid.sum()),
        "standardized_mean": float(standardized.mean()),
        "standardized_variance": float(standardized.var()),
        "scope": "Pixels with clean signal in(.03,.85); finite-sample diagnostic, not an exact ADC moment formula",
    }


def main(output):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    sources = {str(path): sha(path) for path in Path("src/demosaic").glob("*.py")}
    for path in [Path(__file__), *map(Path, sources)]:
        (archive / path.name).write_bytes(path.read_bytes())
    plan = {
        "profiles": [{"name": n, "shot": a, "read": b} for n, a, b in PROFILES],
        "scenes": SCENES,
        "seeds": list(range(8)),
        "cases": 240,
        "shape": [1024, 1024],
        "pattern": "RGGB",
        "variance_probe_levels": LEVELS,
        "ADC_bits": 16,
        "ADC_black": BLACK,
        "estimate_patch": 32,
        "estimate_max_patches": 4096,
        "estimate_bootstrap_seed": 42,
        "flag_threshold_absolute_variance_dB": 1.0,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "scope": "Synthetic stress of current estimator, no method changes. Six known PG profiles x five scene conditions x eight draws. Reliable is an internal fit flag, not proof of physical calibration. Compare variance functions, not poorly identifiable individual read coefficients. Full low-intensity probe range includes extrapolation outside accepted fitting intensities. No camera calibration, learned restoration, real quality score or production conditioning change.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    records = []
    clean_records = {}
    with (output / "cases.jsonl").open("x") as stream:
        for scene_index, name in enumerate(SCENES):
            for seed in range(8):
                clean = scene(name, seed)
                clean_path = output / f"scene{scene_index}-seed{seed}-clean-f32.npy"
                np.save(clean_path, clean, allow_pickle=False)
                clean_records[name, seed] = {"path": str(clean_path), "sha256": sha(clean_path)}
                for profile_index, (profile, shot, read) in enumerate(PROFILES):
                    noise_seed = 50000 + scene_index * 1000 + seed * 10 + profile_index
                    noisy = add_noise(
                        torch.from_numpy(clean),
                        shot,
                        read,
                        black_level=BLACK,
                        generator=torch.Generator().manual_seed(noise_seed),
                    ).numpy()
                    noisy_path = (
                        output
                        / f"scene{scene_index}-seed{seed}-profile{profile_index}-noisy-f32.npy"
                    )
                    np.save(noisy_path, noisy, allow_pickle=False)
                    estimate = estimate_noise(noisy)
                    row = {
                        "scene": name,
                        "seed": seed,
                        "profile": profile,
                        "shot": shot,
                        "read": read,
                        "noise_seed": noise_seed,
                        "clean": clean_records[name, seed],
                        "noisy": {"path": str(noisy_path), "sha256": sha(noisy_path)},
                        "estimate": estimate.to_dict(),
                        "variance_diagnostics": variance_diagnostics(estimate, shot, read),
                        "noise_moments": moment_diagnostics(clean, noisy, shot, read),
                    }
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
                    stream.flush()
                    records.append(row)
            print(json.dumps({"scene": name, "completed": len(records)}), flush=True)
    assert len(records) == 240 and not torch.cuda.is_initialized()
    for path, digest in sources.items():
        assert sha(path) == digest
    result = {
        "status": "completed-current-noise-estimator-synthetic-stress-awaiting-independent-summary",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "cases": str(output / "cases.jsonl"),
        "cases_sha256": sha(output / "cases.jsonl"),
        "case_count": len(records),
        "clean_arrays": len(clean_records),
        "noisy_arrays": len(records),
        "CUDA_initialized": False,
        "scope": plan["scope"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({"result": str(output / "result.json"), "case_count": len(records)}), flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
