"""Native CPU correctness of the new readout, without matching/RGB inference."""

import argparse
import gc
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V184-wave-readout-preparation-v1"
BASE = ROOT.parent / "V183-coherent-pair-evidence-trial-v1"


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprint(value):
    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
    }


def completed_base():
    index = REPO / "docs/results/v183-coherent-pair-evidence-final-v1.json"
    verification = (
        REPO / "docs/results/v183-coherent-pair-evidence-publication-verification-v1.json"
    )
    final, verified = read(index), read(verification)
    assert (
        final["status"] == "completed-matched-trial-audited-actually-viewed-and-two-strict-exports"
    )
    assert (
        verified["status"]
        == "pass-exact-evidence-two-local-exports-comparison-tables-native-and-browser-pixels"
    )
    assert verified["publication"] == ref(index)
    for name in ["evidence-train", "review", "completion"]:
        launch = read(BASE / f"{name}-launch-v1.json")
        assert not owner_live(launch["owner"])
        assert not (BASE / f"{name}-failure-v1.json").exists()
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    for name in [
        "training-audit-v1.json",
        "quality-audit-v1.json",
        "native-viewing-completion-v1.json",
    ]:
        binding = final["copies"][name]["original"]
        assert ref(binding["path"]) == binding
    baseline = read(BASE / "plan-v1.json")
    for path, digest in baseline["frozen_files"].items():
        if "/src/demosaic/" in path:
            assert ref(REPO / "src/demosaic" / Path(path).name)["sha256"] == digest
    return {
        "publication": ref(index),
        "verification": ref(verification),
        "initializer": final["checkpoints"]["V183-coherent-pair-EMA"],
    }


def prepare():
    dependency = completed_base()
    assert not ROOT.exists()
    assert shutil.disk_usage(REPO).free > (48.5 + 0.015) * 2**30
    assert psutil.virtual_memory().available > 32 * 2**30
    tests = REPO / ".cache/v184-wave-readout-CPU-tests-v2.log"
    assert "31 passed" in tests.read_text()
    old = read(ROOT.parent / "V180-local-phase-preparation-v1/plan-v1.json")
    ROOT.mkdir()
    work = ROOT / "work"
    shutil.copytree(
        REPO / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    for name in [
        "scripts/profile_phase_wave_readout.py",
        "scripts/phase_admission_protocol.py",
        "tests/test_late_phase_wave_readout.py",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    baseline = read(BASE / "plan-v1.json")
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-native-CPU-wave-readout-correctness-not-quality",
            "created_unix_UTC": time.time(),
            "runner": ref(work / "scripts/profile_phase_wave_readout.py"),
            "work": str(work),
            "dependency": dependency,
            "config": baseline["module_config"],
            "cases": old["cases"],
            "prior_native_result": ref(
                ROOT.parent / "V180-local-phase-preparation-v1/result-v1.json"
            ),
            "previous98_neural_hashes": {
                Path(p).name: h
                for p, h in baseline["frozen_files"].items()
                if "/src/demosaic/" in p
            },
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "sources": [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")],
            "comparison_tolerance": {"rtol": 1e-5, "atol": 2e-6},
            "scope": "Six existing native RAW/variance/CFA cases, including protected sky and cab geometry for inference-feature correctness only. Compare new readout output with independent NumPy at zero and fixed nonzero untrained head; strict CPU V183 EMA initializer binding. No old matching/frozen/sampler/parent/DINO inference, optimizer, new noise/source, target/reference read or RAW decode. Native features retain old operator; no claim of image quality or calibrated confidence. All98 prior neural files unchanged; new99th file. Outputs are compact correctness receipts in repo; no external writes or dataz/original access.",
        },
    )
    print("Prepared6nativeCPUcases/frozenV183EMA/316parameterreadout;no forward")


def run():
    plan = read(ROOT / "plan-v1.json")
    assert ref(__file__) == plan["runner"]
    for binding in plan["sources"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    completed_base()
    assert ref(plan["prior_native_result"]["path"]) == plan["prior_native_result"]
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [6, 7])
    import torch

    from demosaic.late_local_phase_evidence_matching import local_phase_evidence_maps
    from demosaic.late_phase_wave_readout import LatePhaseWaveReadoutDetail, PhaseWaveReadout

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    before_rng = torch.get_rng_state().clone()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    spec = importlib.util.spec_from_file_location(
        "v184_independent_readout", Path(plan["work"]) / "tests/test_late_phase_wave_readout.py"
    )
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    head = independent.nonzero_head(torch.float32).eval()
    zero = PhaseWaveReadout().eval()
    old_module_forwards = []
    original_call = torch.nn.Module._call_impl

    def limited_call(module, *args, **kwargs):
        if not any(module is part for parent in [head, zero] for part in parent.modules()):
            old_module_forwards.append(type(module).__name__)
            raise RuntimeError("Old neural inference forbidden in CPU feature preparation")
        return original_call(module, *args, **kwargs)

    rows = []
    try:
        torch.nn.Module._call_impl = limited_call
        for case in plan["cases"]:
            assert ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                arrays = {k: archive[k] for k in ["packed", "variance", "colors"]}
            packed, variance, colors = [
                torch.from_numpy(arrays[k]) for k in ["packed", "variance", "colors"]
            ]
            started = time.perf_counter()
            evidence, aux = local_phase_evidence_maps(
                packed,
                variance,
                colors,
                peaks=plan["config"]["evidence_peaks"],
                window=plan["config"]["evidence_window"],
                stride=plan["config"]["evidence_stride"],
            )
            with torch.no_grad():
                initial = zero(evidence, aux["bin_yx"])
                assert initial.count_nonzero() == 0
                actual = head(evidence, aux["bin_yx"]).numpy()
            expected = independent.numpy_readout(head, evidence, aux["bin_yx"])
            np.testing.assert_allclose(actual, expected, **plan["comparison_tolerance"])
            row = {
                "id": case["id"],
                "arrays": case["arrays"],
                "input_fingerprints": {k: fingerprint(v) for k, v in arrays.items()},
                "bins_yx": aux["bin_yx"].tolist(),
                "feature_fingerprint": fingerprint(evidence.numpy()),
                "native_readout_fingerprint": fingerprint(actual),
                "native_values_checked": actual.size,
                "maximum_absolute_error": float(np.max(abs(actual - expected))),
                "initial_output_exact_zero": True,
                "seconds": time.perf_counter() - started,
            }
            rows.append(row)
            print(case["id"], actual.size, row["maximum_absolute_error"], flush=True)
            del arrays, packed, variance, colors, evidence, aux, actual, expected, initial
            gc.collect()
    finally:
        torch.nn.Module._call_impl = original_call
    entry = plan["dependency"]["initializer"]
    assert ref(entry["export"]["path"]) == entry["export"]
    exported = torch.load(entry["export"]["path"], map_location="cpu", weights_only=True)
    model = LatePhaseWaveReadoutDetail(**plan["config"]).initialize_from_evidence(
        exported["state_dict"]
    )
    assert len(exported["state_dict"]) == 189 and len(model.state_dict()) == 193
    assert all(torch.equal(model.state_dict()[n], v) for n, v in exported["state_dict"].items())
    assert sum(p.numel() for p in model.parameters() if p.requires_grad) == 316
    assert len([p for p in model.parameters() if p.requires_grad]) == 4
    assert not old_module_forwards and torch.equal(before_rng, torch.get_rng_state())
    assert not torch.cuda.is_initialized()
    save(
        ROOT / "result-v1.json",
        {
            "status": "pass-native-CPU-wave-readout-transport-and-frozen-V183-EMA-state-not-quality",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "cases": rows,
            "native_values_checked": sum(r["native_values_checked"] for r in rows),
            "maximum_absolute_error": max(r["maximum_absolute_error"] for r in rows),
            "inherited_tensors_exact": 189,
            "total_state_tensors": 193,
            "trainable_parameters": 316,
            "trainable_tensors": 4,
            "strict_CPU_export_loads": 1,
            "old_module_forwards": 0,
            "optimizer_updates": 0,
            "new_sensor_source_draws": 0,
            "CUDA_initialized": False,
            "CPU_RNG_unchanged": True,
            "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "scope": plan["scope"],
        },
    )
    print("PASS6nativecases/189inheritedtensors/316parameters/zeroOldNeuralForwards")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else run()
