"""Independently reconstruct every fixed composition with NumPy signed Malvar."""

import argparse
import os
from pathlib import Path

import numpy as np
import torch
from diagnose_support_crossover import METHODS
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def main(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[4:6])
    plan = read(root / "plan-v1.json")
    guard(plan)
    review = read(root / "review-result-v1.json")
    collections = {
        method: read(binding["path"]) for method, binding in review["collections"].items()
    }
    assert set(collections) == set(METHODS)
    rows = []
    for index, case in enumerate(read(plan["design"]["path"])["observations"]):
        arrays = dict(np.load(case["arrays"]["path"]))
        base = np.load(case["parent"]["path"])
        binding = collections["native-native"]["observations"][index]["auxiliary"]
        assert ref(binding["path"]) == binding
        auxiliary = dict(np.load(binding["path"]))
        for value in auxiliary.values():
            assert value.dtype == np.float32 and np.isfinite(value).all()
        for name in ["native", "relative"]:
            support = auxiliary[f"{name}_support"]
            assert support.shape[1] == 1 and support.min() >= 0 and support.max() <= 1
        for method, (proposal, support) in METHODS.items():
            observation = collections[method]["observations"][index]
            assert observation["id"] == case["id"] and observation["auxiliary"] == binding
            assert observation["proposal"] == proposal and observation["support_map"] == support
            packed = auxiliary[f"{proposal}_proposal"]
            if support != "full":
                packed = packed * auxiliary[f"{support}_support"]
            assert packed.dtype == np.float32
            expected = base.astype(np.float64) + noisy_malvar(
                {"packed": packed, "colors": arrays["colors"], "wb": arrays["wb"]}
            )
            actual = np.load(observation["prediction"]["path"])
            difference = np.abs(expected - actual.astype(np.float64))
            allowance = 2 * np.spacing(np.abs(actual)).astype(np.float64) + 3e-9
            assert np.all(difference <= allowance), (case["id"], method, float(difference.max()))
            rows.append(
                {
                    "id": case["id"],
                    "method": method,
                    "prediction": observation["prediction"],
                    "maximum_abs_camera_RGB_difference": float(difference.max()),
                    "RMS_difference_DN16": float(np.sqrt(np.mean(difference**2)) * 65535),
                }
            )
    assert len(rows) == 4932 and not torch.cuda.is_initialized()
    save(
        root / "independent-reconstruction-v1.json",
        {
            "status": "pass-all4932-independent-fixed-compositions",
            "auditor": ref(__file__),
            "NumPy_Malvar_source": ref(Path(noisy_malvar.__code__.co_filename)),
            "review": ref(root / "review-result-v1.json"),
            "rows": rows,
            "cases": 822,
            "reconstructions": 4932,
            "maximum_abs_difference": max(row["maximum_abs_camera_RGB_difference"] for row in rows),
            "maximum_RMS_difference_DN16": max(row["RMS_difference_DN16"] for row in rows),
            "tolerance": "2 float32 ULPs at the final output plus3e-9 cameraRGB for signed fixed interpolation; independent float64 Malvar then parent addition",
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "All six fixed compositions on all822 cases, including originals and both real-scene priors/windows. Uses saved FP32 proposals/support maps and independent NumPy64 WB/stencils/reflect borders. No target/reference participates in reconstruction. This is a numerical composition audit, not quality proof.",
        },
    )
    print(
        "PASS4932 independent fixed compositions; max",
        max(row["maximum_abs_camera_RGB_difference"] for row in rows),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
