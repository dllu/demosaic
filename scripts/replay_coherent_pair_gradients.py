"""CPU-only V183 loss/gradient replay on all20 audited saved V182 RGB batches."""

import argparse
import gc
import json
import os
import shutil
from pathlib import Path

import numpy as np
from phase_admission_protocol import read, ref

REPO = Path("/home/dllu/proj/demosaic")
BASE = REPO / ".cache/quality-20261107/V182-flat-spatial-loss-geometry-v1"
ROOT = REPO / ".cache/quality-20261107/V183-coherent-pair-output-replay-v1"


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def prepare():
    assert not ROOT.exists()
    audit = read(BASE / "independent-audit-v2.json")
    assert audit["status"].startswith("pass-V182-")
    assert audit["result"] == ref(BASE / "result-v1.json")
    tests = REPO / ".cache/v183-coherent-pair-CPU-tests-v2.log"
    assert "25 passed" in tests.read_text()
    ROOT.mkdir()
    work = ROOT / "work"
    (work / "scripts").mkdir(parents=True)
    (work / "tests").mkdir()
    for src in [
        "scripts/coherent_pair_objective.py",
        "scripts/replay_coherent_pair_gradients.py",
        "tests/test_coherent_pair_objective.py",
    ]:
        shutil.copyfile(REPO / src, work / src)
    plan = {
        "status": "prepared-CPU-output-gradient-replay-no-new-model-quality",
        "runner": ref(work / "scripts/replay_coherent_pair_gradients.py"),
        "work": str(work),
        "base": ref(BASE / "result-v1.json"),
        "base_audit": ref(BASE / "independent-audit-v2.json"),
        "base_plan": ref(BASE / "plan-v1.json"),
        "loss": {
            "weight": 0.25,
            "floor_DN16": 1,
            "centering": "independent camera-channel spatial means per pair",
        },
        "CPU_tests": dict(ref(tests), text=tests.read_text()),
        "scope": "Only CPU saved-output loss/derivative replay. No neural Module call,CUDA,optimizer,new source/noise,parent/DINO,RAWdecode or protectedinput. All20 native V182 RGB batches reused;53,477,376 output-gradient coordinates. Independent NumPy formula supplies each per-pair value/analytic derivative. Old8terms/mask exact in focused CPUwrapper tests;actual CUDA/network-gradient/restoration/trained-quality work remains.",
    }
    plan["sources"] = {str(p): ref(p)["sha256"] for p in work.rglob("*.py")}
    save(ROOT / "plan-v1.json", plan)


def run():
    plan = read(ROOT / "plan-v1.json")
    assert ref(__file__) == plan["runner"]
    for p, h in plan["sources"].items():
        assert ref(p)["sha256"] == h
    for key in ["base", "base_audit", "base_plan"]:
        assert ref(plan[key]["path"]) == plan[key]
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    from unittest.mock import patch

    import torch
    from coherent_pair_objective import paired_coherent_response_loss
    from test_coherent_pair_objective import independent

    from demosaic.prediction_archive import fingerprint

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    os.sched_setaffinity(0, [4, 5])
    os.nice(max(0, 10 - __import__("psutil").Process().nice()))
    rng = torch.get_rng_state().clone()
    rows = []
    coordinates = 0
    maximum_value_error = maximum_gradient_error = maximum_relative_L2_error = 0.0
    with patch.object(
        torch.nn.Module,
        "_call_impl",
        side_effect=AssertionError("Neural forward forbidden during saved-output replay"),
    ):
        for old in read(plan["base"]["path"])["rows"]:
            assert ref(old["output"]["path"]) == {k: old["output"][k] for k in ["path", "sha256"]}
            assert ref(old["batch"]["path"]) == old["batch"]
            arrays = dict(np.load(old["batch"]["path"], allow_pickle=False))
            assert {k: fingerprint(v) for k, v in arrays.items()} == old["inputs"]
            output = np.load(old["output"]["path"], allow_pickle=False)
            assert fingerprint(output) == old["output"]["values"]
            target = arrays["target"]
            pairs = arrays["pair_indices"]
            weight = 0.25 * old["domain_weight"]
            expected, derivative = (
                independent(output.astype(np.float64), target.astype(np.float64), pairs, 1)
                if len(pairs)
                else (0.0, np.zeros_like(output, dtype=np.float64))
            )
            value = torch.from_numpy(output).requires_grad_()
            clean = torch.from_numpy(target).requires_grad_()
            raw = paired_coherent_response_loss(value, clean, torch.from_numpy(pairs), floor_DN16=1)
            loss = weight * raw
            gradient, gt = torch.autograd.grad(loss, (value, clean), allow_unused=True)
            assert gt is None and loss.dtype == torch.float32
            actual = gradient.numpy()
            expected_gradient = (weight * derivative).astype(np.float32)
            np.testing.assert_allclose(actual, expected_gradient, rtol=2e-6, atol=1e-10)
            assert np.isclose(float(raw.detach()), expected, rtol=1e-6, atol=1e-8)
            value_error = abs(float(raw.detach()) - expected)
            gradient_error = float(np.max(np.abs(actual - expected_gradient)))
            relative = float(
                np.linalg.norm(actual.astype(np.float64) - expected_gradient.astype(np.float64))
                / max(np.linalg.norm(expected_gradient.astype(np.float64)), 1e-30)
            )
            maximum_value_error = max(maximum_value_error, value_error)
            maximum_gradient_error = max(maximum_gradient_error, gradient_error)
            maximum_relative_L2_error = max(maximum_relative_L2_error, relative)
            rows.append(
                {
                    "method": old["method"],
                    "step": old["step"],
                    "domain": old["domain"],
                    "batch": old["batch"],
                    "saved_RGB": old["output"],
                    "pairs": pairs.tolist(),
                    "coherent_response_loss": float(raw.detach()),
                    "independent_loss": expected,
                    "weighted_new_loss": float(loss.detach()),
                    "domain_weight": old["domain_weight"],
                    "output_gradient": fingerprint(actual),
                    "weighted_gradient_norm": float(np.linalg.norm(actual.astype(np.float64))),
                    "maximum_gradient_error": gradient_error,
                    "relative_L2_gradient_error": relative,
                }
            )
            coordinates += actual.size
            assert torch.equal(rng, torch.get_rng_state())
            del (
                value,
                clean,
                raw,
                loss,
                gradient,
                actual,
                expected_gradient,
                derivative,
                arrays,
                output,
                target,
            )
            gc.collect()
    assert len(rows) == 20 and coordinates == 53477376 and not torch.cuda.is_initialized()
    for p, h in plan["sources"].items():
        assert ref(p)["sha256"] == h
    save(
        ROOT / "result-v1.json",
        {
            "status": "pass-V183-CPU-native-output-loss-and-independent-analytic-gradients-no-neural-work",
            "plan": ref(ROOT / "plan-v1.json"),
            "rows": rows,
            "output_gradient_coordinates": coordinates,
            "maximum_loss_error": maximum_value_error,
            "maximum_FP32_gradient_error": maximum_gradient_error,
            "maximum_relative_L2_gradient_error": maximum_relative_L2_error,
            "all_eight_existing_terms_and_mask_checked_in_CPU_tests": True,
            "new_neural_forwards": 0,
            "new_optimizer_updates": 0,
            "new_noise_source_draws": 0,
            "CUDA_initialized": False,
            "Torch_CPU_RNG_unchanged": True,
            "scope": plan["scope"],
        },
    )
    print("PASS20saved-native-batches/53477376gradientcoordinates/zero neural-CUDA-updates")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else run()
