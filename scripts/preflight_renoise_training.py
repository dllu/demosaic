"""Verify every retained scene can supply an exact fresh-noise sensor signal."""

import argparse
import os
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
import torch
from renoise_cached_training import SensorSignalUnavailable, clean_sensor, noise_seed
from train_directional_bank_trial import read, ref, save

from demosaic.prediction_archive import fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    repo = Path(__file__).resolve().parents[1]
    reference = read(repo / ".cache/quality-20261107/V172-local-noise-matching-v1/plan-v1.json")
    cache = read(reference["cache"]["path"])
    assert ref(reference["cache"]["path"]) == reference["cache"]
    units = read(reference["pair_units"]["path"])["rows"]
    assert len(cache["batches"]) == len(units) == 1000
    rows, domains = [], Counter()
    rng = torch.get_rng_state().clone()
    for item, unit in zip(cache["batches"], units, strict=True):
        assert psutil.virtual_memory().available > 32 * 2**30
        assert ref(item["arrays"]["path"]) == item["arrays"]
        a = dict(np.load(item["arrays"]["path"]))
        assert {k: fingerprint(v) for k, v in a.items()} == item["inputs"]
        assert unit["step"] == item["step"] and unit["batch"] == item["arrays"]
        try:
            clean = clean_sensor(a, item["metadata"]).numpy()
        except SensorSignalUnavailable as error:
            domains[item["metadata"]["domain"]] += 1
            rows.append(
                {
                    "step": item["step"],
                    "arrays": item["arrays"],
                    "domain": item["metadata"]["domain"],
                    "target": fingerprint(a["target"]),
                    "paired": bool(len(a["pair_indices"])),
                    "noisy": bool(np.any(a["variance"] > 0)),
                    "fresh_noise_eligible": False,
                    "reason": str(error),
                    "policy": "Retain exact original noisy arrays and cached parent;do not re-noise a clipped target.",
                }
            )
            continue
        # Independent NumPy phase sampling; no torch mosaic in this reference.
        expected = np.stack(
            [
                np.stack([rgb[int(c), k // 2 :: 2, k % 2 :: 2] for k, c in enumerate(layout)])
                for rgb, layout in zip(a["target"].clip(min=0), a["colors"], strict=True)
            ]
        )
        np.testing.assert_array_equal(clean, expected)
        pairs = a["pair_indices"]
        if len(pairs):
            first, second = pairs.T
            increment = (
                item["metadata"]["noise"]["shot"]
                * (clean[first] - clean[second]).astype(np.float64).__abs__()
            ).mean((1, 2, 3))
            np.testing.assert_allclose(
                increment,
                item["metadata"]["sensor"]["increment_mean_variance"],
                rtol=3e-7,
                atol=1e-15,
            )
            calculated = np.maximum(np.sqrt(increment), 2 / 65535).astype(np.float32)
            np.testing.assert_allclose(
                calculated, unit["candidate_units_FP32"], rtol=3e-7, atol=1e-12
            )
        domains[item["metadata"]["domain"]] += 1
        noisy = bool(np.any(a["variance"] > 0))
        rows.append(
            {
                "step": item["step"],
                "arrays": item["arrays"],
                "domain": item["metadata"]["domain"],
                "clean_packed": fingerprint(clean),
                "target": fingerprint(a["target"]),
                "paired": bool(len(pairs)),
                "noisy": noisy,
                "fresh_noise_eligible": True,
            }
        )
        if item["step"] % 100 == 0:
            print("Verified retained scene", item["step"], flush=True)
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    assert sum(r["noisy"] for r in rows) == 900
    seeds = [noise_seed(row, (row - 1) % 1000 + 1) for row in range(1, 9001)]
    assert len(set(seeds)) == 9000
    save(
        args.output,
        {
            "status": "pass-all1000-bindings-with-exact-sensor-eligibility-and-clipped-target-exclusions",
            "cache": reference["cache"],
            "pair_units": reference["pair_units"],
            "rows": rows,
            "domains": dict(domains),
            "noisy_rows_per_pass": 900,
            "ADC_rows_per_pass": 100,
            "planned_passes": 9,
            "fresh_noise_eligible_noisy_rows_per_pass": sum(
                r["noisy"] and r["fresh_noise_eligible"] for r in rows
            ),
            "retained_cached_noisy_rows_per_pass": sum(
                r["noisy"] and not r["fresh_noise_eligible"] for r in rows
            ),
            "planned_new_noisy_realizations": 9
            * sum(r["noisy"] and r["fresh_noise_eligible"] for r in rows),
            "planned_new_training_images": 32400,
            "unique_scene_batches": 1000,
            "unique_noisy_scene_batches": 900,
            "new_scene_or_geometry_renders": 0,
            "planned_noise_seeds_unique": 9000,
            "sensor_noise_draws": 0,
            "new_neural_forwards": 0,
            "CUDA_initialized": False,
            "global_CPU_RNG_unchanged": True,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "sources": [
                dict(ref(p), text=p.read_text())
                for p in [Path(__file__), repo / "scripts/renoise_cached_training.py"]
            ],
            "scope": "All retained input bindings checked;eligible sensor signals reproduce paired original hashes or lie inside unpaired reference-white bounds. Clipped/ambiguous target cases retain exact original noisy arrays and cached parents;never re-noise an unproven target. Fresh noise and parent inference still pending. Source/camera/geometry/calibration/targets stay fixed;no new source or protected-media reads.",
        },
    )
    print(
        "PASS1000 bindings/900 noisy;eligible noisy",
        sum(r["noisy"] and r["fresh_noise_eligible"] for r in rows),
        ";no source/noise/neural draws",
        flush=True,
    )


if __name__ == "__main__":
    main()
