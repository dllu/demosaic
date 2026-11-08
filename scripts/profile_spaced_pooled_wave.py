"""Native CPU selection/wave checks before training the V187 pooled wave head."""

import argparse
import gc
import importlib.util
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from phase_admission_protocol import owner_live, read, ref
from profile_phase_wave_readout import completed_base as completed_initializer

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V189-spaced-pooled-preparation-v1"


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
    dependency = completed_initializer()
    index = REPO / "docs/results/v187-pooled-wave-final-v1.json"
    verification = REPO / "docs/results/v187-pooled-wave-publication-verification-v1.json"
    old = ROOT.parent / "V187-pooled-wave-trial-v1"
    final, verified = read(index), read(verification)
    assert final["status"].startswith("completed-") and verified["status"].startswith("pass-")
    assert verified["publication"] == ref(index)
    for k in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[k]["path"]) == final[k]
    for n in ["wave-train", "review"]:
        assert not owner_live(read(old / f"{n}-launch-v1.json")["owner"])
    for n in ["training-audit-v1.json", "quality-audit-v1.json"]:
        b = final["copies"][n]["original"]
        assert ref(b["path"]) == b and read(b["path"])["status"].startswith("pass-")
    plan = read(old / "plan-v1.json")
    neural = {Path(p).name: h for p, h in plan["frozen_files"].items() if "/src/demosaic/" in p}
    assert len(neural) == 101
    for n, digest in neural.items():
        assert ref(REPO / "src/demosaic" / n)["sha256"] == digest
    diagnostic = REPO / "docs/results/v188-selection-diversity-v1.json"
    proof = REPO / "docs/results/v188-selection-diversity-publication-verification-v1.json"
    assert read(proof)["status"].startswith("pass-") and read(proof)["publication"] == ref(
        diagnostic
    )
    dependency.update(
        previous_publication=ref(index),
        previous_verification=ref(verification),
        previous_plan=ref(old / "plan-v1.json"),
        previous101_neural_hashes=neural,
        frequency_diagnostic=ref(diagnostic),
        frequency_diagnostic_verification=ref(proof),
    )
    return dependency


def prepare():
    dependency = completed_base()
    assert not ROOT.exists()
    assert (
        shutil.disk_usage(REPO).free > (40 + 0.015) * 2**30
        and psutil.virtual_memory().available > 32 * 2**30
    )
    tests = REPO / ".cache/v189-spaced-model-CPU-tests-v3.log"
    assert "30 passed" in tests.read_text()
    old = read(ROOT.parent / "V187-pooled-wave-preparation-v1/plan-v1.json")
    base = read(dependency["previous_plan"]["path"])
    ROOT.mkdir()
    work = ROOT / "work"
    shutil.copytree(
        REPO / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    names = [
        "scripts/profile_spaced_pooled_wave.py",
        "scripts/profile_phase_wave_readout.py",
        "scripts/phase_admission_protocol.py",
        "scripts/green_phase_spectrum.py",
        "scripts/phase_frequency_holdout.py",
        "scripts/local_phase_projection.py",
        "scripts/frequency_coverage.py",
        "scripts/spectral_selection_diversity.py",
        "tests/test_late_spaced_pooled_wave.py",
        "tests/test_late_spatial_context_wave.py",
        "tests/test_late_local_phase_evidence_matching.py",
    ]
    for n in names:
        p = work / n
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / n, p)
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-native-CPU-pooled-selection-and-wave-correctness-not-quality",
            "created_unix_UTC": time.time(),
            "runner": ref(work / "scripts/profile_spaced_pooled_wave.py"),
            "work": str(work),
            "dependency": dependency,
            "config": base["module_config"],
            "cases": old["cases"],
            "matched_V187_initial_module_hash": base["CPU_initialization"]["full_module_hash"],
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "sources": [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")],
            "minimum_GiB": {"local": 40, "RAM": 32},
            "scope": "Six fixed cached native batches; V189 changes only pooled suppression radius from1 toceil(maxpackedaxis/65) relative to V187. Same two-green9neighbor pooled scores,band1/16..1/3,8unique slots and interleaved ranks; frozen V183 matching retains original one-phase selections. Same508headparams,4tensors,193state,189frozen/eval tensors,initialhash,window65/stride32,33+17support/stride8 and futurematched900updates/nine losses. Independent NumPy spaced bins,phasepowers,full fixed-bin waves/support/readout; no old matching/frozen/sampler/parent/DINO forward,target/reference read,newsource/noise orRAWdecode. Selection uses bothgreens,not holdouts orcalibratedconfidence. All101 older neural sources unchanged; new102ndsource. New CPU outputs localforecast.015GiB above40GiB buffer;externalread-only. V188 diagnostic audited both gains and tighter-proximity/quiet/absent costs; no quality claim before actual trial.",
        },
    )
    print("Prepared6nativeCPUcases/pooledselection/same508head;no forward")


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

    def model_hash(module):
        import hashlib

        digest = hashlib.sha256()
        for name, value in module.state_dict().items():
            value = value.detach().cpu().contiguous()
            digest.update(
                name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode()
            )
            flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
            digest.update(flat.view(torch.uint8).numpy().tobytes())
        return digest.hexdigest()

    from demosaic.late_spaced_pooled_wave import (
        LateSpacedPooledPhaseWaveDetail,
        fixed_bin_wave_maps,
        spaced_pooled_phase_bins,
    )
    from demosaic.late_spatial_context_wave import (
        SpatialContextWaveReadout,
        fixed_bin_support_context,
    )

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    before = torch.get_rng_state().clone()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    sys.path.insert(0, str(Path(plan["work"]) / "tests"))

    def module(n):
        s = importlib.util.spec_from_file_location(n, Path(plan["work"]) / "tests" / f"{n}.py")
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m

    independent = module("test_late_spaced_pooled_wave")
    headref = module("test_late_spatial_context_wave")
    head = headref.nonzero_head(torch.float32).eval()
    zero = SpatialContextWaveReadout().eval()
    original_call = torch.nn.Module._call_impl
    forbidden = []

    def limited(m, *args, **kwargs):
        if not any(m is part for parent in [head, zero] for part in parent.modules()):
            forbidden.append(type(m).__name__)
            raise RuntimeError("Only new head forwards allowed")
        return original_call(m, *args, **kwargs)

    rows = []
    try:
        torch.nn.Module._call_impl = limited
        for c in plan["cases"]:
            assert ref(c["arrays"]["path"]) == c["arrays"]
            with np.load(c["arrays"]["path"], allow_pickle=False) as archive:
                a = {k: archive[k] for k in ["packed", "variance", "colors"]}
            raw, var, colors = [torch.from_numpy(a[k]) for k in ["packed", "variance", "colors"]]
            started = time.perf_counter()
            bins, valid, pool = spaced_pooled_phase_bins(raw, var, colors, peaks=4)
            expected_bins, scores, powers = independent.numpy_selection(raw, var, colors, 4)
            np.testing.assert_array_equal(bins.numpy(), expected_bins)
            assert valid.all()
            np.testing.assert_allclose(pool["pooled_score"].numpy(), scores, rtol=2e-5, atol=3e-6)
            np.testing.assert_allclose(
                pool["global_nominal_power"].numpy(), powers, rtol=2e-5, atol=3e-6
            )
            evidence, wave = fixed_bin_wave_maps(
                raw, var, colors, bins, valid, window=65, stride=32
            )
            maps = []
            center_power = []
            for n in range(len(raw)):
                selections = independent.selections_for(bins[n : n + 1], colors[n], *raw.shape[-2:])
                m, p, _ = independent.independent_maps(
                    raw[n : n + 1],
                    var[n : n + 1],
                    colors[n],
                    peaks=4,
                    window=65,
                    stride=32,
                    selections=selections,
                )
                maps.append(m)
                center_power.append(p)
            expected_maps = np.concatenate(maps)
            np.testing.assert_allclose(evidence.numpy(), expected_maps, rtol=2e-5, atol=3e-6)
            np.testing.assert_allclose(
                wave["local_center_power"].numpy(),
                np.concatenate(center_power),
                rtol=1e-8,
                atol=1e-8,
            )
            support, support_aux = fixed_bin_support_context(
                raw, var, colors, bins, valid, windows=(33, 17), stride=8
            )
            expected_support, expected_power = headref.independent_support(
                raw, var, colors, bins, windows=[33, 17], stride=8
            )
            np.testing.assert_allclose(support.numpy(), expected_support, rtol=2e-5, atol=3e-6)
            np.testing.assert_allclose(
                support_aux["center_power"].numpy(), expected_power, rtol=1e-8, atol=1e-8
            )
            with torch.no_grad():
                initial = zero(evidence, bins, support)
                assert initial.count_nonzero() == 0
                actual = head(evidence, bins, support).numpy()
            expected = headref.numpy_readout(head, evidence, bins, support)
            np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=2e-6)
            row = {
                "id": c["id"],
                "arrays": c["arrays"],
                "input_fingerprints": {k: fingerprint(v) for k, v in a.items()},
                "bins_yx": bins.tolist(),
                "selection_bins_exact": True,
                "wave_feature_values_checked": evidence.numel(),
                "support_values_checked": support.numel(),
                "native_readout_values_checked": actual.size,
                "wave_feature_maximum_error": float(np.max(abs(evidence.numpy() - expected_maps))),
                "support_maximum_error": float(np.max(abs(support.numpy() - expected_support))),
                "readout_maximum_error": float(np.max(abs(actual - expected))),
                "wave_features": fingerprint(evidence.numpy()),
                "support": fingerprint(support.numpy()),
                "readout": fingerprint(actual),
                "initial_output_exact_zero": True,
                "seconds": time.perf_counter() - started,
            }
            rows.append(row)
            print(
                c["id"],
                row["wave_feature_values_checked"],
                row["readout_maximum_error"],
                flush=True,
            )
            del (
                a,
                raw,
                var,
                colors,
                evidence,
                wave,
                maps,
                center_power,
                expected_maps,
                support,
                support_aux,
                expected_support,
                expected_power,
                actual,
                expected,
                initial,
                pool,
                m,
                p,
            )
            gc.collect()
    finally:
        torch.nn.Module._call_impl = original_call
    entry = plan["dependency"]["initializer"]
    assert ref(entry["export"]["path"]) == entry["export"]
    exported = torch.load(entry["export"]["path"], map_location="cpu", weights_only=True)
    model = LateSpacedPooledPhaseWaveDetail(**plan["config"]).initialize_from_evidence(
        exported["state_dict"]
    )
    assert len(model.state_dict()) == 193 and len(exported["state_dict"]) == 189
    assert all(torch.equal(model.state_dict()[n], v) for n, v in exported["state_dict"].items())
    assert sum(p.numel() for p in model.parameters() if p.requires_grad) == 508
    assert model_hash(model) == plan["matched_V187_initial_module_hash"]
    assert (
        not forbidden
        and torch.equal(before, torch.get_rng_state())
        and not torch.cuda.is_initialized()
    )
    save(
        ROOT / "result-v1.json",
        {
            "status": "pass-native-CPU-pooled-bins-fixed-waves-support-readout-and-frozen-initial-state-not-quality",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "cases": rows,
            "wave_feature_values_checked": sum(r["wave_feature_values_checked"] for r in rows),
            "support_values_checked": sum(r["support_values_checked"] for r in rows),
            "native_values_checked": sum(r["native_readout_values_checked"] for r in rows),
            "maximum_wave_feature_error": max(r["wave_feature_maximum_error"] for r in rows),
            "maximum_support_error": max(r["support_maximum_error"] for r in rows),
            "maximum_readout_error": max(r["readout_maximum_error"] for r in rows),
            "inherited_tensors_exact": 189,
            "total_state_tensors": 193,
            "trainable_parameters": 508,
            "trainable_tensors": 4,
            "strict_CPU_export_loads": 1,
            "matched_V187_initial_module_hash": model_hash(model),
            "old_module_forwards": 0,
            "CUDA_initialized": False,
            "CPU_RNG_unchanged": True,
            "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "scope": plan["scope"],
        },
    )
    print("PASS6nativecases/193state/508params/zero-old-NN-forwards", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["prepare", "run"])
    a = p.parse_args()
    prepare() if a.phase == "prepare" else run()
