"""CPU-only native feature/strict-load preparation; no matching forward or training."""

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
ROOT = REPO / ".cache/quality-20261107/V178-phase-evidence-preparation-v1"


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


def fingerprint(array):
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
    }


def prepare():
    assert not ROOT.exists()
    live_path = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2/plan-v1.json"
    live = read(live_path)
    cache = read(live["cache"]["path"])
    design = read(live["design"]["path"])
    cases = []
    for domain in ["mesh", "photo", "mixed", "flat"]:
        row = next(
            r
            for r in cache["batches"]
            if r["metadata"]["domain"] == domain
            and any(
                row_noise > 0
                for key, row_noise in r["metadata"]["noise"].items()
                if key in ["shot", "read"]
            )
        )
        cases.append(
            {
                "id": f"training-{domain}-step{row['step']}",
                "arrays": row["arrays"],
                "scope": "Retained training RAW only;targets and parents not interpreted.",
            }
        )
    for name in ["main-overcast-sky", "mesh-nominal"]:
        row = next(r for r in design["observations"] if r["id"] == name)
        cases.append(
            {
                "id": name,
                "arrays": row["arrays"],
                "scope": "Protected cached RAW feature geometry only;no GT/reference/parent read or quality score.",
            }
        )
    names = [
        "src/demosaic/late_phase_evidence_matching.py",
        "tests/test_late_phase_evidence_matching.py",
        "scripts/green_phase_spectrum.py",
        "scripts/phase_frequency_holdout.py",
        "src/demosaic/late_local_noise_matching.py",
        "src/demosaic/late_nonlocal_residual.py",
        "scripts/profile_phase_evidence_preparation.py",
        "scripts/profile_raw_kernel_inference.py",
    ]
    tests = REPO / ".cache/v178-phase-evidence-CPU-tests-v3.log"
    assert "68 passed" in tests.read_text()
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.02) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.01) * 2**30
    assert psutil.virtual_memory().available > 40 * 2**30
    ROOT.mkdir()
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-CPU-only-native-feature-and-strict-load-preparation",
            "created_unix_UTC": time.time(),
            "V175_live_plan": ref(live_path),
            "cases": cases,
            "checkpoint": live["initial_checkpoint"],
            "sources": [dict(ref(REPO / name), text=(REPO / name).read_text()) for name in names],
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "prototype_failure": {
                "source": dict(
                    ref(REPO / ".cache/v178-phase-evidence-fp32-carrier-v1.py"),
                    text=(REPO / ".cache/v178-phase-evidence-fp32-carrier-v1.py").read_text(),
                ),
                "log": dict(
                    ref(REPO / ".cache/v178-phase-evidence-CPU-tests-v1.log"),
                    text=(REPO / ".cache/v178-phase-evidence-CPU-tests-v1.log").read_text(),
                ),
                "correction": "Integer FFT-bin periodic phase reduction before FP32 radians;no tolerance relaxation.23 new checks and68 combined checks now pass.",
            },
            "FP64_numpy_tolerance": {"rtol": 1e-8, "atol": 1e-8},
            "FP32_policy": "Record native FP32/FP64 bin equality and map errors descriptively,not a trained-quality or CUDA parity test. Independent FP32 fixtures retain3e-5 tolerance.",
            "scope": "CPU feature extraction on6 fixed cached cases only,each in FP32/FP64 plus independent NumPy reference. Strict raw/EMA model-weight compatibility uses one existing V172 checkpoint load. No full matching/frozen/V143/DINO/sampler forward,optimizer update,new sensor/source render or RAW decode. Test fixtures are separate. Protected real inputs stay excluded from training;no original/dataz access. New model remains untrained and requires CUDA parity/gradient/memory/admission plus full quality/native views before use. V175 source/recipe/live owner unchanged.",
        },
    )
    print("Prepared6CPUfeaturecases;oneoldcheckpoint;noGPUortraining", flush=True)


def execute():
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.late_local_noise_matching import LateLocalNoiseMatchingDetail
    from demosaic.late_phase_evidence_matching import (
        LatePhaseEvidenceMatchingDetail,
        phase_evidence_maps,
    )

    assert not torch.cuda.is_initialized()
    plan = read(ROOT / "plan-v1.json")
    (ROOT / "run.claim").open("x").close()
    for binding in plan["sources"]:
        assert ref(binding["path"])["sha256"] == binding["sha256"]
        assert Path(binding["path"]).read_text() == binding["text"]
    os.nice(10)
    os.sched_setaffinity(0, [4, 5])
    torch.set_num_threads(2)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    spec = importlib.util.spec_from_file_location(
        "v178_independent_reference", REPO / "tests/test_late_phase_evidence_matching.py"
    )
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    rows = []
    for case in plan["cases"]:
        assert psutil.virtual_memory().available > 32 * 2**30
        assert shutil.disk_usage(REPO).free > 48 * 2**30
        assert ref(case["arrays"]["path"]) == case["arrays"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as source:
            raw, variance, colors = [source[k] for k in ["packed", "variance", "colors"]]
        raw = torch.from_numpy(raw.copy())
        variance = torch.from_numpy(variance.copy())
        colors = torch.from_numpy(colors.copy())
        if colors.ndim == 1:
            colors = colors[None].expand(len(raw), -1)
        records = {}
        with torch.no_grad():
            started = time.monotonic()
            f32, a32 = phase_evidence_maps(raw.float(), variance.float(), colors)
            seconds32 = time.monotonic() - started
            started = time.monotonic()
            f64, a64 = phase_evidence_maps(raw.double(), variance.double(), colors)
            seconds64 = time.monotonic() - started
        assert torch.isfinite(f32).all() and torch.isfinite(f64).all()
        maximum_numpy_error = 0.0
        numpy_bins = []
        for index in range(len(raw)):
            expected, selected = reference.independent_maps(
                raw[index : index + 1].double(),
                variance[index : index + 1].double(),
                colors[index],
                4,
            )
            np.testing.assert_allclose(
                f64[index : index + 1].numpy(), expected, **plan["FP64_numpy_tolerance"]
            )
            maximum_numpy_error = max(
                maximum_numpy_error, float(np.max(abs(f64[index : index + 1].numpy() - expected)))
            )
            numpy_bins.append([[p["bin_yx"] for p in d["peaks"]] for d in selected])
        assert a64["bin_yx"].tolist() == numpy_bins
        same_bins = torch.equal(a32["bin_yx"], a64["bin_yx"])
        error = f32.double() - f64 if same_bins else None
        records = {
            "id": case["id"],
            "arrays": case["arrays"],
            "RAW": fingerprint(raw.numpy()),
            "variance": fingerprint(variance.numpy()),
            "feature_shape": list(f32.shape),
            "feature_logical_bytes": f32.numel() * 4,
            "FP32_seconds": seconds32,
            "FP64_seconds": seconds64,
            "FP32_feature_fingerprint": fingerprint(f32.numpy()),
            "FP64_feature_fingerprint": fingerprint(f64.numpy()),
            "FP64_numpy_maximum_absolute_error": maximum_numpy_error,
            "FP32_FP64_selection_identical": same_bins,
            "FP32_FP64_RMS_difference": float(error.square().mean().sqrt()) if same_bins else None,
            "FP32_FP64_maximum_absolute_difference": float(error.abs().max())
            if same_bins
            else None,
            "FP32_bins": a32["bin_yx"].tolist(),
            "FP32_nominal_power": a32["nominal_power"].tolist(),
            "scope": case["scope"],
        }
        rows.append(records)
        save(ROOT / f"case-{len(rows):02d}-v1.json", records)
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "shape": list(f32.shape),
                    "FP32_seconds": seconds32,
                    "FP64_numpy_max_abs": maximum_numpy_error,
                    "same_bins": same_bins,
                }
            ),
            flush=True,
        )
        del f32, f64, a32, a64, expected, error, raw, variance, colors
        gc.collect()
    assert ref(plan["checkpoint"]["path"]) == plan["checkpoint"]
    state = torch.load(plan["checkpoint"]["path"], map_location="cpu", weights_only=True)
    old, new = LateLocalNoiseMatchingDetail(), LatePhaseEvidenceMatchingDetail()
    assert state["updates"] == 900
    old.load_state_dict(state["models"], strict=True)
    compatibility = []
    for endpoint in ["raw", "EMA"]:
        if endpoint == "EMA":
            old.network.load_state_dict(state["ema"], strict=True)
        new.initialize_from_local_matching(old.state_dict())
        assert all(
            torch.equal(value, new.state_dict()[name]) for name, value in old.state_dict().items()
        )
        assert new.phase_evidence_in.weight.count_nonzero() == 0
        compatibility.append(
            {
                "endpoint": endpoint,
                "old_module_hash": model_hash(old),
                "new_module_hash": model_hash(new),
                "existing_tensors_exact": len(old.state_dict()),
                "added_zero_tensors": 1,
                "added_parameters": new.phase_evidence_in.weight.numel(),
            }
        )
    assert ref(plan["checkpoint"]["path"]) == plan["checkpoint"]
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-CPU-native-features-and-strict-initialization-no-training",
        "owner": owner,
        "plan": ref(ROOT / "plan-v1.json"),
        "cases": rows,
        "strict_baseline_compatibility": compatibility,
        "feature_module_calls": 12,
        "feature_images": 2 * sum(r["feature_shape"][0] for r in rows),
        "independent_numpy_image_references": sum(r["feature_shape"][0] for r in rows),
        "existing_checkpoint_loads": 1,
        "actual_matching_frozen_parent_DINO_sampler_forwards": 0,
        "new_optimizer_updates": 0,
        "new_sensor_source_draws": 0,
        "RAW_decodes": 0,
        "CUDA_initialized": False,
        "trainable_parameters": sum(p.numel() for p in new.parameters() if p.requires_grad),
        "frozen_parameters": sum(p.numel() for p in new.frozen.parameters()),
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "scope": plan["scope"],
    }
    save(ROOT / "result-v1.json", result)
    print("CompletedCPUpreparation;GPUandtrainedqualitypending", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    prepare() if parser.parse_args().phase == "prepare" else execute()
