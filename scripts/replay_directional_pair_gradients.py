"""CPU-only V195 directional loss/gradient replay on all20 audited saved V182 RGB batches."""

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
ROOT = REPO / ".cache/quality-20261108/V195-directional-response-CPU-v1"


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def prepare():
    assert not (ROOT / "plan-v2.json").exists()
    audit = read(BASE / "independent-audit-v2.json")
    assert audit["status"].startswith("pass-V182-")
    assert audit["result"] == ref(BASE / "result-v1.json")
    tests = ROOT / "CPU-tests-v2.log"
    assert "26 passed" in tests.read_text()
    ROOT.mkdir(exist_ok=True)
    assert shutil.disk_usage(REPO).free > 32.005 * 2**30
    assert __import__("psutil").virtual_memory().available > 32 * 2**30
    work = ROOT / "work-v2"
    (work / "scripts").mkdir(parents=True, exist_ok=True)
    (work / "tests").mkdir(exist_ok=True)
    for src in [
        "scripts/directional_pair_objective.py",
        "scripts/directional_pair_reference.py",
        "scripts/replay_directional_pair_gradients.py",
        "tests/test_directional_pair_objective.py",
    ]:
        shutil.copyfile(REPO / src, work / src)
    plan = {
        "status": "prepared-CPU-output-gradient-replay-no-new-model-quality",
        "runner": ref(work / "scripts/replay_directional_pair_gradients.py"),
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
        "scope": "CPU-only new directional response loss/derivative replay on all20audited savedV182trainingRGBbatches/53477376outputgradientcoordinates. Production Cartesian half-open orientation regions with canonical Nyquist conjugates; independentNumPy angular comparisons and inverseFFTreal subtemplates/spatial analytic derivatives. Two offset four-region tilings reuse targets; not independent confidence. Newweight.25/domain,floor1DN16 perregion.26CPUcontracts retainall9oldscalars/masks andcheckboth whole/directional added-weight wrappers. No neural Module/CUDA/optimizer/checkpoint load,newsource/noise,parent-DINO,RAWdecode/protectedinput. ActualGPUheadgradients/restoration andmatchedtrainedquality stillrequired.",
    }
    plan["directional_diagnostic"] = ref(
        REPO / "docs/results/v194-orientation-response-completed-v1.json"
    )
    plan["directional_diagnostic_proof"] = ref(
        REPO / "docs/results/v194-orientation-response-publication-verification-v1.json"
    )
    plan["all103_neural_hashes"] = read(REPO / "docs/results/v193-completed-execution-v1.json")[
        "previous103_neural_hashes_unchanged"
    ]
    plan["native_reference_fixture_bridge"] = (
        "Independent NumPy native helper agrees with explicit dense real Fourier-basis reference at5x7 and8x10 before this replay; fullnative comparison remains required."
    )
    plan["trial_intent"] = (
        "Matched two-arm head retraining from the same completedV187EMA state,withfresh identical headAdam/EMA clocks. Control retainsnine oldterms plus.25whole-response addition; directionalarm retainsnine oldterms plus.25eight-region addition. Bothsame508parameters/frozen189/all103neuralsources/data/budget. Whole-response totalweight.5 versuswhole.25+directional.25; equalnominalextraweights do notmean equalgradientnorms. No trainedqualityclaim or finaltraininglaunch in this CPUplan."
    )
    assert __import__("shutil").disk_usage(REPO).free > 32.005 * 2**30
    for name, digest in plan["all103_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    plan["resource_reassessment"] = ref(ROOT / "preparation-storage-stop-v1.json")
    plan["minimum_GiB"] = {"local": 32, "RAM": 32}
    plan["new_local_forecast_GiB"] = 0.005
    plan["resource_scope"] = (
        "Prospective CPU-only saved-output derivative calculation; persistent output is small receipts,not modelpredictions/checkpoints/large arrays. Local free35GiB atpreparation,32GiBreserve plus.005GiB forecast; RAM32GiB floor. This is not a change to any older model trial plan. Check both reserves beforeeachsavedbatch."
    )
    plan["preparation_filename_correction"] = ref(ROOT / "preparation-filename-stop-v2.json")
    plan["sources"] = {str(p): ref(p)["sha256"] for p in work.rglob("*.py")}
    save(ROOT / "plan-v2.json", plan)


def run():
    plan = read(ROOT / "plan-v2.json")
    assert ref(__file__) == plan["runner"]
    for p, h in plan["sources"].items():
        assert ref(p)["sha256"] == h
    for key in ["base", "base_audit", "base_plan"]:
        assert ref(plan[key]["path"]) == plan[key]
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert ref(plan["directional_diagnostic"]["path"]) == plan["directional_diagnostic"]
    assert ref(plan["directional_diagnostic_proof"]["path"]) == plan["directional_diagnostic_proof"]
    from unittest.mock import patch

    import torch
    from directional_pair_objective import paired_directional_response_loss
    from directional_pair_reference import independent

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
            assert shutil.disk_usage(REPO).free > plan["minimum_GiB"]["local"] * 2**30
            assert (
                __import__("psutil").virtual_memory().available > plan["minimum_GiB"]["RAM"] * 2**30
            )
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
            raw = paired_directional_response_loss(
                value, clean, torch.from_numpy(pairs), floor_DN16=1
            )
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
                    "directional_response_loss": float(raw.detach()),
                    "independent_loss": expected,
                    "weighted_new_loss": float(loss.detach()),
                    "domain_weight": old["domain_weight"],
                    "output_gradient": fingerprint(actual),
                    "weighted_gradient_norm": float(np.linalg.norm(actual.astype(np.float64))),
                    "maximum_gradient_error": gradient_error,
                    "relative_L2_gradient_error": relative,
                }
            )
            print(
                "native-directional-replay",
                len(rows),
                old["domain"],
                old["step"],
                "loss",
                float(raw.detach()),
                "maxGradientError",
                gradient_error,
                flush=True,
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
    for name, digest in plan["all103_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    for p, h in plan["sources"].items():
        assert ref(p)["sha256"] == h
    save(
        ROOT / "result-v2.json",
        {
            "status": "pass-V195-CPU-native-directional-loss-and-independent-spatial-gradients-no-neural-work",
            "plan": ref(ROOT / "plan-v2.json"),
            "rows": rows,
            "output_gradient_coordinates": coordinates,
            "maximum_loss_error": maximum_value_error,
            "maximum_FP32_gradient_error": maximum_gradient_error,
            "maximum_relative_L2_gradient_error": maximum_relative_L2_error,
            "all_nine_existing_terms_and_mask_checked_in_CPU_tests": True,
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
