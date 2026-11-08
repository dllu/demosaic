"""Measure conditional template evidence on all retained noisy training mesh pairs.

Exact hidden signal/background and clean physical variances enter this
diagnostic. No RGB restoration is produced, no inference rule is proposed,
and no real qualitative reference is treated as GT.
"""

import argparse
import hashlib
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from mesh_template_information import tiled_template_fit

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V176-template-information-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V176-template-information-v1")
CONTEXTS = [16, 32, 64, 128, 256, 512]


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def save(path, value):
    path = Path(path)
    assert not path.exists()
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprint(array):
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
    }


def sample_RGB(value, colors):
    return np.stack(
        [
            np.stack(
                [
                    rgb[int(color), phase // 2 :: 2, phase % 2 :: 2]
                    for phase, color in enumerate(layout)
                ]
            )
            for rgb, layout in zip(value, colors, strict=True)
        ]
    )


def prepare():
    assert not ROOT.exists() and not EXTERNAL.exists()
    live_plan_path = REPO / ".cache/quality-20261107/V175-fresh-noise-matching-v2/plan-v1.json"
    live_plan = read(live_plan_path)
    cache = read(live_plan["cache"]["path"])
    assert ref(live_plan["cache"]["path"]) == live_plan["cache"]
    selected = [
        row
        for row in cache["batches"]
        if row["metadata"]["domain"] == "mesh"
        and any(row["metadata"]["noise"][key] > 0 for key in ["shot", "read"])
    ]
    assert len(selected) == 307
    assert all(
        row["metadata"]["coupled_pairs"] == 2 and row["metadata"]["native_size"] == 512
        for row in selected
    )
    source_paths = [
        Path(__file__).resolve(),
        REPO / "scripts/mesh_template_information.py",
        REPO / "tests/test_mesh_template_information.py",
    ]
    tests = REPO / ".cache/v176-template-information-CPU-tests-v1.log"
    assert "16 passed" in tests.read_text()
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.01) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.05) * 2**30
    ROOT.mkdir()
    EXTERNAL.mkdir()
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-training-only-template-information-diagnostic",
            "external": str(EXTERNAL),
            "prior_preparation_rejection": ref(
                REPO / ".cache/v176-template-information-prepare-rejection-v1.json"
            ),
            "new_local_projection_GiB": 0.01,
            "new_external_projection_GiB": 0.05,
            "created_unix_UTC": time.time(),
            "source_cache": live_plan["cache"],
            "V175_training_plan": ref(live_plan_path),
            "parent_checkpoint_metadata": read(live_plan["training_provenance"]["path"])["parent"],
            "selected_steps": [row["step"] for row in selected],
            "noisy_mesh_batches": 307,
            "target_pairs": 614,
            "phase_groups": ["green", "all-CFA"],
            "native_contexts": CONTEXTS,
            "nuisance": "Separate affine offset/x/y plane for each observed CFA phase inside each context.",
            "weight_variance": "Known clean background: shot*background+read,not the supplied noisy variance proxy.",
            "actual_raw_variance": "Known clean present/absent signal: shot*clean+read;pre-ADC independent second moments. Quantization/clipping not included in the linear variance formula.",
            "context_selection": "For each width,choose the aligned nonoverlapping tile with largest known-template SNR. This uses GT,not observations or model outputs,and is an oracle best-window diagnostic.",
            "verification_pairs_from_first_batches": [row["step"] for row in selected[:12]],
            "descriptive_SNR_edges": [1, 3, 5],
            "sources": [dict(ref(path), text=path.read_text()) for path in source_paths],
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "candidate_quality_read": False,
            "scope": "All614 noisy training mesh pairs from the immutable V168 bank;307 batches,not independent repeated captures. Uses each member's original marginal noisy RAW separately,never the coupled present-minus-absent noisy difference. Exact hidden templates/background/known clean variances are diagnostic inputs,unavailable at inference. No source/geometry/noise render,model/checkpoint load or neural/parent/DINO/sampler forward;no real capture analysis or training recipe change. All candidate quality remains separate.",
        },
    )
    print(
        "Prepared307 retained batches/614 pairs;known-template diagnostic only;no pixel or model work",
        flush=True,
    )


def finite(value):
    value = float(value)
    return value if np.isfinite(value) else None


def execute():
    plan = read(ROOT / "plan-v1.json")
    assert not (EXTERNAL / "result-v1.json").exists()
    (ROOT / "run.claim").open("x").close()
    for binding in plan["sources"]:
        assert (
            ref(binding["path"])["sha256"] == binding["sha256"]
            and Path(binding["path"]).read_text() == binding["text"]
        )
    assert ref(plan["source_cache"]["path"]) == plan["source_cache"]
    os.nice(10)
    os.sched_setaffinity(0, [4, 5])
    rows = []
    selected = {step for step in plan["selected_steps"]}
    source_rows = [
        row for row in read(plan["source_cache"]["path"])["batches"] if row["step"] in selected
    ]
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    inputs_checked = parents_checked = 0
    clipped_samples = total_samples = 0
    maximum_quantization_variance_fraction = 0.0
    with (EXTERNAL / "rows-v1.jsonl").open("x") as journal:
        for batch_number, item in enumerate(source_rows, 1):
            assert psutil.virtual_memory().available > 32 * 2**30
            for binding in [item["arrays"], item["parent"]]:
                assert ref(binding["path"]) == binding
            arrays = dict(np.load(item["arrays"]["path"]))
            parent = np.load(item["parent"]["path"])
            assert {key: fingerprint(value) for key, value in arrays.items()} == item["inputs"]
            assert fingerprint(parent) == item["parent_values"]
            inputs_checked += len(arrays)
            parents_checked += 1
            clean = sample_RGB(np.maximum(arrays["target"], np.float32(0)), arrays["colors"])
            parent_samples = sample_RGB(parent, arrays["colors"]).astype(np.float64)
            first, second = arrays["pair_indices"].T
            assert np.array_equal(arrays["colors"][first], arrays["colors"][second])
            assert fingerprint(clean[first]) == item["metadata"]["sensor"]["clean_packed_a"]
            assert fingerprint(clean[second]) == item["metadata"]["sensor"]["clean_packed_b"]
            shot, read_noise = [item["metadata"]["noise"][key] for key in ["shot", "read"]]
            expected_variance = (
                np.maximum(arrays["packed"].astype(np.float64), 0) * shot + read_noise
            )
            np.testing.assert_allclose(arrays["variance"], expected_variance, rtol=2e-7, atol=1e-12)
            black, bits = [item["metadata"]["sensor"][key] for key in ["black_level", "bit_depth"]]
            assert black == 0.03 and bits == 16
            adc_step = 1 / (((1 << bits) - 1) * (1 - black))
            packed = arrays["packed"].astype(np.float64)
            clipped = (packed >= 1 - 1e-7) | (packed <= -black / (1 - black) + 1e-7)
            clipped_samples += int(clipped.sum())
            total_samples += clipped.size
            for pair_index, (present, absent) in enumerate(arrays["pair_indices"]):
                background = clean[absent].astype(np.float64)
                signal = clean[present].astype(np.float64) - background
                weight_variance = shot * background + read_noise
                actual_present = shot * clean[present].astype(np.float64) + read_noise
                actual_absent = shot * background + read_noise
                maximum_quantization_variance_fraction = max(
                    maximum_quantization_variance_fraction,
                    float(
                        (adc_step**2 / 12) / min(np.mean(actual_present), np.mean(actual_absent))
                    ),
                )
                residuals = {
                    "raw_present": packed[present] - background,
                    "raw_absent": packed[absent] - background,
                    "parent_present": parent_samples[present] - background,
                    "parent_absent": parent_samples[absent] - background,
                }
                for group in plan["phase_groups"]:
                    indices = (
                        np.flatnonzero(arrays["colors"][present] == 1)
                        if group == "green"
                        else np.arange(4)
                    )
                    row = {
                        "step": item["step"],
                        "pair": pair_index,
                        "phase_group": group,
                        "original_inputs": item["arrays"],
                        "original_parent": item["parent"],
                        "source_recipe": item["metadata"]["cases"][int(present)]["source"],
                        "fine_ladder": item["metadata"].get("training_distribution")
                        == "fine-mesh-ladder-v1",
                        "noise": item["metadata"]["noise"],
                        "template_samples": int(signal[indices].size),
                        "windows": [],
                    }
                    for native in plan["native_contexts"]:
                        fit = tiled_template_fit(
                            signal[indices],
                            {key: value[indices] for key, value in residuals.items()},
                            weight_variance[indices],
                            {
                                "raw_present": actual_present[indices],
                                "raw_absent": actual_absent[indices],
                                "parent_present": None,
                                "parent_absent": None,
                            },
                            native // 2,
                        )
                        variance = fit["amplitude_variances"]["raw_present"]
                        snr = np.divide(
                            1,
                            np.sqrt(variance),
                            out=np.zeros_like(variance),
                            where=np.isfinite(variance) & (variance > 0),
                        )
                        location = np.unravel_index(np.argmax(snr), snr.shape)
                        window = {
                            "native_context": native,
                            "best_context_xywh": [
                                native * int(location[1]),
                                native * int(location[0]),
                                native,
                                native,
                            ],
                            "known_template_SNR": float(snr[location]),
                            "weighted_template_energy": float(
                                fit["weighted_template_energy"][location]
                            ),
                            "aligned_tiles": int(snr.size),
                            "informative_tiles": int(np.sum(snr > 0)),
                            "amplitudes": {
                                key: finite(value[location])
                                for key, value in fit["amplitudes"].items()
                            },
                            "raw_amplitude_standard_errors": {
                                key: finite(np.sqrt(fit["amplitude_variances"][key][location]))
                                for key in ["raw_present", "raw_absent"]
                            },
                        }
                        if native == 512:
                            assert snr.shape == (1, 1)
                            for key, truth in [("raw_present", 1), ("raw_absent", 0)]:
                                error = window["raw_amplitude_standard_errors"][key]
                                window[key + "_standardized_error"] = (
                                    (window["amplitudes"][key] - truth) / error if error else None
                                )
                        row["windows"].append(window)
                    rows.append(row)
                    journal.write(json.dumps(row, allow_nan=False) + "\n")
                    journal.flush()
            if batch_number % 10 == 0 or batch_number == 1:
                print(
                    "Processed retained mesh batches",
                    batch_number,
                    ";pair/group rows",
                    len(rows),
                    flush=True,
                )
    assert len(rows) == 1228 and parents_checked == 307
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    save(
        EXTERNAL / "result-v1.json",
        {
            "status": "completed-all614-training-pair-known-template-information",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "rows": rows,
            "original_input_fingerprints_checked": inputs_checked,
            "original_parent_arrays_checked": parents_checked,
            "observed_ADC_clipped_samples": clipped_samples,
            "sensor_samples_checked": total_samples,
            "maximum_ADC_quantization_variance_over_mean_physical_variance": maximum_quantization_variance_fraction,
            "new_neural_forwards": 0,
            "new_parent_DINO_forwards": 0,
            "new_source_renders": 0,
            "new_noise_draws": 0,
            "new_checkpoint_loads": 0,
            "Torch_imported": False,
            "RAW_decoder_imported": False,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": plan["scope"],
        },
    )
    print(
        "PASS614 training pairs/two phase groups/six context widths;no new noise,source,model or checkpoint work",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    args = parser.parse_args()
    (prepare if args.phase == "prepare" else execute)()
