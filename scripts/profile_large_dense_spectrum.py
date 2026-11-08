"""Native CPU QR measurements and overlap-add before dense spectral training."""

import argparse
import gc
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
ROOT = REPO / ".cache/quality-20261107/V193-large-dense-preparation-v1"
CONFIG = {
    "width": 16,
    "max_search": 9.0,
    "evidence_peaks": 4,
    "evidence_window": 65,
    "evidence_stride": 32,
    "dense_window": 129,
    "dense_stride": 64,
    "dense_support_windows": [33, 17],
}


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def fingerprint(value):
    import hashlib

    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
    }


def completed_base():
    from profile_dense_local_spectrum import completed_base as previous_base

    dependency = previous_base()
    index = REPO / "docs/results/v191-dense-spectrum-final-v1.json"
    proof = REPO / "docs/results/v191-dense-spectrum-publication-verification-v1.json"
    completed = REPO / "docs/results/v191-completed-execution-v1.json"
    final, verified, closed = read(index), read(proof), read(completed)
    assert (
        final["status"].startswith("completed-")
        and verified["publication"] == ref(index)
        and verified["status"].startswith("pass-")
    )
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    for owner in closed["all_terminal_owners"].values():
        assert not owner_live(owner)
    neural = dict(closed["previous102_neural_hashes_unchanged"])
    neural["late_dense_local_spectrum.py"] = closed["new_neural_source"]["sha256"]
    assert len(neural) == 103
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    diagnostic = REPO / "docs/results/v192-dense-support-v1.json"
    diagnostic_proof = REPO / "docs/results/v192-dense-support-publication-verification-v1.json"
    assert read(diagnostic_proof)["publication"] == ref(diagnostic) and read(diagnostic_proof)[
        "status"
    ].startswith("pass-")
    dependency.update(
        previous_publication=ref(index),
        previous_verification=ref(proof),
        previous_plan=final["plan"],
        V191_publication=ref(index),
        V191_verification=ref(proof),
        V191_plan=final["plan"],
        previous103_neural_hashes=neural,
        support_diagnostic=ref(diagnostic),
        support_diagnostic_verification=ref(diagnostic_proof),
        previous_completion=ref(completed),
    )
    return dependency


def prepare():
    dependency = completed_base()
    assert not ROOT.exists()
    assert (
        shutil.disk_usage(REPO).free > 40.025 * 2**30
        and psutil.virtual_memory().available > 32 * 2**30
    )
    tests = REPO / ".cache/v193-large-window-CPU-tests-v1.log"
    assert "9 passed" in tests.read_text()
    old = read(ROOT.parent / "V187-pooled-wave-preparation-v1/plan-v1.json")
    baseline = read(dependency["previous_plan"]["path"])
    ROOT.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts", "tests"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    plan = {
        "status": "fixed-native-CPU-dense-spectrum-measurement-and-synthesis-not-quality",
        "created_unix_UTC": time.time(),
        "runner": ref(work / "scripts/profile_large_dense_spectrum.py"),
        "work": str(work),
        "dependency": dependency,
        "config": CONFIG,
        "cases": old["cases"],
        "matched_V191_initial_module_hash": baseline["CPU_initialization"]["full_module_hash"],
        "CPU_tests": dict(ref(tests), text=tests.read_text()),
        "sources": [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")],
        "minimum_GiB": {"local": 40, "RAM": 32},
        "scope": "Six cached native batches; same V191 neural implementation and all103 sources unchanged. Densewindow129/stride64 replaces65/32, with33/17support and frozenmatching65/32 unchanged. Same508parameters/fourheadtensors/193state/189frozenV183EMA/initialhash. Full complexspectra/variance/context/nativeOLA independently checked againstQR/NumPy. No oldNN/sampler/parent-DINO,target/reference,newsource/noise,RAWdecode,original/dataz. CPU/RNGonly,externalread-only,newlocalforecast.025GiB/floor40/RAM32. V192analyticalsupport motivateslargerwindow but isnot RGBquality/falsepositiveproof. Window,carriergrid andpatchstridechangejointly; trainedqualitypending.",
    }
    save(ROOT / "plan-v1.json", plan)
    print("Prepared6nativeCPUcases/dense-local-spectrum/same508parameters")


def run():
    plan = read(ROOT / "plan-v1.json")
    assert ref(__file__) == plan["runner"]
    for b in plan["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    completed_base()
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    import torch
    from dense_spectrum_reference import measurements, native_readout
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_dense_local_spectrum import (
        DenseLocalSpectrumReadout,
        LateDenseLocalSpectrumDetail,
        dense_local_spectrum,
    )

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    before = torch.get_rng_state().clone()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    head, zero = DenseLocalSpectrumReadout().eval(), DenseLocalSpectrumReadout().eval()
    with torch.no_grad():
        head.context.weight.copy_(
            torch.linspace(-0.09, 0.07, head.context.weight.numel()).reshape_as(head.context.weight)
        )
        head.mixing.weight.copy_(
            torch.linspace(-0.05, 0.07, head.mixing.weight.numel()).reshape_as(head.mixing.weight)
        )
        head.mixing.bias.copy_(torch.linspace(-0.02, 0.03, 12))
    state = {n: v.numpy() for n, v in head.state_dict().items()}
    original_call = torch.nn.Module._call_impl

    def limited(module, *args, **kwargs):
        if not any(module is part for parent in [head, zero] for part in parent.modules()):
            raise RuntimeError("Only the new dense spectral readout may run")
        return original_call(module, *args, **kwargs)

    rows = []
    try:
        torch.nn.Module._call_impl = limited
        for case in plan["cases"]:
            assert (
                shutil.disk_usage(REPO).free > 40 * 2**30
                and psutil.virtual_memory().available > 32 * 2**30
            )
            assert ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as a:
                raw, var, colors = [a[k] for k in ["packed", "variance", "colors"]]
            start = time.perf_counter()
            context, coef, aux = dense_local_spectrum(
                torch.from_numpy(raw),
                torch.from_numpy(var),
                torch.from_numpy(colors),
                window=plan["config"]["dense_window"],
                stride=plan["config"]["dense_stride"],
                support_windows=tuple(plan["config"]["dense_support_windows"]),
            )
            expected, ec, eg = measurements(
                raw,
                var,
                colors,
                window=plan["config"]["dense_window"],
                stride=plan["config"]["dense_stride"],
                support_windows=tuple(plan["config"]["dense_support_windows"]),
            )
            np.testing.assert_allclose(context.numpy(), expected, rtol=4e-6, atol=4e-6)
            np.testing.assert_allclose(coef.numpy(), ec, rtol=4e-6, atol=3e-8)
            np.testing.assert_allclose(
                aux["aligned_spectra"].numpy(), eg["aligned_spectra"], rtol=2e-8, atol=3e-12
            )
            np.testing.assert_allclose(
                aux["propagated_variance"].numpy(), eg["propagated_variance"], rtol=2e-8, atol=3e-16
            )
            with torch.no_grad():
                actual = head(context, coef, aux).numpy()
                initial = zero(context, coef, aux)
            ergb = native_readout(state, expected, ec, eg)
            np.testing.assert_allclose(actual, ergb, rtol=1e-5, atol=3e-8)
            assert initial.count_nonzero() == 0
            row = {
                "id": case["id"],
                "input_bindings": {
                    k: fingerprint(v)
                    for k, v in zip(
                        ["packed", "variance", "colors"], [raw, var, colors], strict=True
                    )
                },
                "dense_context_values_checked": context.numel(),
                "complex_spectral_coordinates_checked": aux["aligned_spectra"].numel() * 2,
                "propagated_variances_checked": aux["propagated_variance"].numel(),
                "native_readout_values_checked": actual.size,
                "maximum_context_error": float(abs(context.numpy() - expected).max()),
                "maximum_complex_spectrum_error": float(
                    abs(aux["aligned_spectra"].numpy() - eg["aligned_spectra"]).max()
                ),
                "maximum_variance_error": float(
                    abs(aux["propagated_variance"].numpy() - eg["propagated_variance"]).max()
                ),
                "maximum_readout_error": float(abs(actual - ergb).max()),
                "context": fingerprint(context.numpy()),
                "coefficient": fingerprint(coef.numpy()),
                "readout": fingerprint(actual),
                "initial_output_exact_zero": True,
                "seconds": time.perf_counter() - start,
            }
            rows.append(row)
            print(
                case["id"],
                row["dense_context_values_checked"],
                row["maximum_readout_error"],
                flush=True,
            )
            del raw, var, colors, context, coef, aux, expected, ec, eg, actual, initial, ergb
            gc.collect()
    finally:
        torch.nn.Module._call_impl = original_call
    initializer = plan["dependency"]["initializer"]
    assert ref(initializer["export"]["path"]) == initializer["export"]
    state = torch.load(initializer["export"]["path"], map_location="cpu", weights_only=True)
    module = LateDenseLocalSpectrumDetail(**plan["config"]).initialize_from_evidence(
        state["state_dict"]
    )
    assert all(torch.equal(v, module.state_dict()[n]) for n, v in state["state_dict"].items())
    assert len(module.state_dict()) == 193 and len(state["state_dict"]) == 189
    assert model_hash(module) == plan["matched_V191_initial_module_hash"]
    assert torch.equal(before, torch.get_rng_state()) and not torch.cuda.is_initialized()
    save(
        ROOT / "result-v1.json",
        {
            "status": "pass-native-CPU-large-dense-spectra-QR-variance-native-synthesis-and-frozen-state-not-quality",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "cases": rows,
            "dense_context_values_checked": sum(r["dense_context_values_checked"] for r in rows),
            "complex_spectral_coordinates_checked": sum(
                r["complex_spectral_coordinates_checked"] for r in rows
            ),
            "propagated_variances_checked": sum(r["propagated_variances_checked"] for r in rows),
            "native_values_checked": sum(r["native_readout_values_checked"] for r in rows),
            "inherited_tensors_exact": 189,
            "total_state_tensors": 193,
            "trainable_parameters": 508,
            "trainable_tensors": 4,
            "matched_V191_initial_module_hash": model_hash(module),
            "old_module_forwards": 0,
            "CUDA_initialized": False,
            "CPU_RNG_unchanged": True,
            "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "scope": plan["scope"],
        },
    )
    print("PASS6nativeCPUcases/QRspectra-variance/synthesis/193state/508parameters", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else run()
