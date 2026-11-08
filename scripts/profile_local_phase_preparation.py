"""CPU native feature/weight checks for the untrained local-phase variant."""

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

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V180-local-phase-preparation-v1"
PRIOR = ROOT.parent / "V178-phase-evidence-preparation-v1"


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


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


def model_hash(model):
    # Same tensor-only format as profile_raw_kernel_inference.model_hash.
    import torch

    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
        digest.update(flat.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def prepare():
    assert not ROOT.exists()
    old = read(PRIOR / "plan-v1.json")
    old_result = read(PRIOR / "result-v1.json")
    tests = REPO / ".cache/v180-local-phase-CPU-tests-v2.log"
    assert "112 passed" in tests.read_text()
    previous = read(ROOT.parent / "V178-phase-evidence-trial-v1/draft-v1.json")
    old_neural = {
        Path(path).name: digest
        for path, digest in previous["frozen_files"].items()
        if "/src/demosaic/" in path
    }
    assert len(old_neural) == 97
    for name, digest in old_neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert len(list((REPO / "src/demosaic").glob("*.py"))) == 98
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.2 + 2 + 0.15 + 0.03) * 2**30
    ROOT.mkdir()
    work = ROOT / "work"
    shutil.copytree(
        REPO / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    for name in [
        "scripts/profile_local_phase_preparation.py",
        "scripts/local_phase_projection.py",
        "scripts/phase_frequency_holdout.py",
        "scripts/green_phase_spectrum.py",
        "tests/test_late_local_phase_evidence_matching.py",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-CPU-native-local-features-and-weight-compatibility-not-quality",
            "created_unix_UTC": time.time(),
            "work": str(work),
            "runner": ref(work / "scripts/profile_local_phase_preparation.py"),
            "cases": old["cases"],
            "old_cases": old_result["cases"],
            "old_feature_profile": ref(PRIOR / "result-v1.json"),
            "checkpoint": old["checkpoint"],
            "sources": [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")],
            "prior97_neural_hashes": old_neural,
            "config": {
                "width": 16,
                "max_search": 9.0,
                "evidence_peaks": 4,
                "evidence_window": 65,
                "evidence_stride": 32,
            },
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "preserved_first_test": {
                "source": ref(REPO / ".cache/v180-local-phase-first-test-v1.py"),
                "log": ref(REPO / ".cache/v180-local-phase-model-CPU-tests-v1.log"),
                "correction": "23passed/1failed:bit equality between differently grouped off-grid rational interpolation expressions. Off-grid check allows4e-15 rounding;measured-center exact checks and feature/QR tolerances unchanged. No feature implementation change.",
            },
            "FP64_numpy_tolerance": {"rtol": 1e-8, "atol": 1e-8},
            "new_local_projection_GiB": 0.03,
            "new_external_projection_GiB": 0,
            "scope": "Six cached RAW/variance/CFA feature cases,including protected main sky/cab geometry only. No references/parents/targets interpreted. New FP32/FP64 features compared with NumPy local projections/interpolation at old independently verified bins;no old selector recomputation in the NumPy reference. One old checkpoint strict raw/EMA load;no actual matching/frozen/V143/DINO/sampler forward,optimizer update,noise/source/RAWdecode. New variant untrained;parameter/tensor parity does not identify the differing feature operator. Local interpolation is not calibrated covariance and can spread support or create grid/boundary artifacts. FP64 moments have unmeasured CUDA cost. Existing V175/V178 source/recipes unchanged;no new GPU job.",
        },
    )
    print("Prepared6nativeCPUcases/old97exact/new98th/onecheckpoint;no model forward", flush=True)


def run():
    import torch

    from demosaic.late_local_phase_evidence_matching import (
        LateLocalPhaseEvidenceMatchingDetail,
        local_phase_evidence_maps,
    )
    from demosaic.late_phase_evidence_matching import LatePhaseEvidenceMatchingDetail

    plan = read(ROOT / "plan-v1.json")
    for binding in plan["sources"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    for key in ["old_feature_profile", "checkpoint"]:
        assert ref(plan[key]["path"]) == plan[key]
    assert not torch.cuda.is_initialized()
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [6, 7])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    before_RNG = torch.get_rng_state().clone()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    test = Path(plan["work"]) / "tests/test_late_local_phase_evidence_matching.py"
    spec = importlib.util.spec_from_file_location("v180_independent_maps", test)
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    cases = []
    try:
        for ordinal, (case, old) in enumerate(
            zip(plan["cases"], plan["old_cases"], strict=True), 1
        ):
            assert case["id"] == old["id"] and ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                arrays = {key: archive[key] for key in ["packed", "variance", "colors"]}
            raw, variance, colors = [
                torch.from_numpy(arrays[key]) for key in ["packed", "variance", "colors"]
            ]
            assert (
                fingerprint(arrays["packed"]) == old["RAW"]
                and fingerprint(arrays["variance"]) == old["variance"]
            )
            started = time.perf_counter()
            fp32, aux32 = local_phase_evidence_maps(raw, variance, colors)
            seconds32 = time.perf_counter() - started
            started = time.perf_counter()
            fp64, aux64 = local_phase_evidence_maps(raw.double(), variance.double(), colors)
            seconds64 = time.perf_counter() - started
            assert aux32["bin_yx"].tolist() == aux64["bin_yx"].tolist() == old["FP32_bins"]
            assert torch.isfinite(fp32).all() and torch.isfinite(fp64).all()
            assert torch.equal(fp32.view(torch.int32), fp64.float().view(torch.int32))
            maximum = 0.0
            center_maximum = 0.0
            values_checked = 0
            for frame in range(len(raw)):
                layout = arrays["colors"][frame]
                greens = np.flatnonzero(layout == 1)
                selections = []
                for direction, (a, b) in enumerate([greens, greens[::-1]]):
                    peaks = []
                    for y, x in old["FP32_bins"][frame][direction]:
                        peaks.append(
                            {
                                "bin_yx": [y, x],
                                "principal_native_fxy": [
                                    float(np.fft.fftfreq(raw.shape[-1])[x] / 2),
                                    float(np.fft.fftfreq(raw.shape[-2])[y] / 2),
                                ],
                            }
                        )
                    selections.append(
                        {"selection_phase": int(a), "other_phase": int(b), "peaks": peaks}
                    )
                expected, powers, _ = independent.independent_maps(
                    raw[frame : frame + 1].double(),
                    variance[frame : frame + 1].double(),
                    colors[frame],
                    window=65,
                    stride=32,
                    selections=selections,
                )
                actual = fp64[frame : frame + 1].numpy()
                np.testing.assert_allclose(actual, expected, **plan["FP64_numpy_tolerance"])
                actual_power = aux64["local_center_power"][frame : frame + 1].numpy()
                np.testing.assert_allclose(actual_power, powers, **plan["FP64_numpy_tolerance"])
                maximum = max(maximum, float(np.max(abs(actual - expected))))
                center_maximum = max(center_maximum, float(np.max(abs(actual_power - powers))))
                values_checked += actual.size
            row = {
                "id": case["id"],
                "arrays": case["arrays"],
                "RAW": old["RAW"],
                "variance": old["variance"],
                "feature_shape": list(fp32.shape),
                "FP32_feature_bytes": fp32.numel() * fp32.element_size(),
                "FP32_seconds": seconds32,
                "FP64_seconds": seconds64,
                "FP32_feature_fingerprint": fingerprint(fp32.numpy()),
                "FP64_feature_fingerprint": fingerprint(fp64.numpy()),
                "old_FP32_and_new_FP32_FP64_bins_exact": True,
                "FP32_features_exact_FP64_cast": True,
                "FP64_numpy_feature_values": values_checked,
                "FP64_numpy_maximum_absolute_error": maximum,
                "local_center_power_maximum_absolute_error": center_maximum,
                "grid_shape": [len(aux32["centers_y"]), len(aux32["centers_x"])],
                "scope": case["scope"],
            }
            cases.append(row)
            save(ROOT / f"case-{ordinal:02d}-v1.json", row)
            del (
                raw,
                variance,
                colors,
                fp32,
                fp64,
                aux32,
                aux64,
                arrays,
                expected,
                powers,
                actual,
                actual_power,
            )
            gc.collect()
        checkpoint = torch.load(plan["checkpoint"]["path"], map_location="cpu", weights_only=True)
        states = {}
        for endpoint in ["raw", "EMA"]:
            state = dict(checkpoint["models"])
            if endpoint == "EMA":
                state.update(
                    {"network." + name: value for name, value in checkpoint["ema"].items()}
                )
            local = LateLocalPhaseEvidenceMatchingDetail(**plan["config"])
            global_module = LatePhaseEvidenceMatchingDetail(
                **{
                    key: value
                    for key, value in plan["config"].items()
                    if key not in ["evidence_window", "evidence_stride"]
                }
            )
            for module in [local, global_module]:
                module.initialize_from_local_matching(state)
                assert all(
                    torch.equal(module.state_dict()[name], value) for name, value in state.items()
                )
                assert module.phase_evidence_in.weight.count_nonzero() == 0
            assert len(state) == 188 and len(local.state_dict()) == 189
            assert model_hash(local) == model_hash(global_module)
            states[endpoint] = {
                "existing188_tensors_exact": True,
                "additional_zero_weights": 3120,
                "full_state_tensors": 189,
                "local_and_global_zero_adapter_tensor_hash": model_hash(local),
                "trainable_parameters": sum(
                    p.numel() for p in local.parameters() if p.requires_grad
                ),
                "trainable_tensors": sum(p.requires_grad for p in local.parameters()),
            }
            del local, global_module
        assert torch.equal(before_RNG, torch.get_rng_state()) and not torch.cuda.is_initialized()
        save(
            ROOT / "result-v1.json",
            {
                "status": "completed-native-CPU-local-feature-and-strict-state-preparation-not-quality",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "cases": cases,
                "endpoint_weight_compatibility": states,
                "feature_calls": 12,
                "feature_images": 36,
                "independent_numpy_images": 18,
                "independent_FP64_feature_values": sum(
                    row["FP64_numpy_feature_values"] for row in cases
                ),
                "old_checkpoint_CPU_loads": 1,
                "actual_matching_frozen_parent_DINO_sampler_forwards": 0,
                "new_optimizer_updates": 0,
                "new_sensor_source_draws": 0,
                "RAW_decodes": 0,
                "CUDA_initialized": False,
                "RNG_unchanged": True,
                "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "scope": plan["scope"],
            },
        )
        print(
            "PASS6nativecases/85196800NumPyvalues/12featurecalls/onecheckpoint/zeroactualNNforwards;untrained",
            flush=True,
        )
    except BaseException as error:
        save(
            ROOT / "failure-v1.json",
            {
                "status": "failed-preserve-prefix-no-automatic-retry",
                "owner": owner,
                "error": repr(error),
                "source": ref(__file__),
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    {"prepare": prepare, "run": run}[parser.parse_args().phase]()
