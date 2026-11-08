"""Within-image CFA sample split on retained mesh RAW; no RGB restoration."""

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
from green_phase_spectrum import tapered_spectrum
from phase_frequency_holdout import describe_phase_holdout

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V177-phase-frequency-holdout-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V177-phase-frequency-holdout-v1")


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


def sample_RGB(rgb, colors):
    return np.stack(
        [
            np.stack([image[int(color), p // 2 :: 2, p % 2 :: 2] for p, color in enumerate(layout)])
            for image, layout in zip(rgb, colors, strict=True)
        ]
    )


def prepare():
    assert not ROOT.exists() and not EXTERNAL.exists()
    prior_path = REPO / ".cache/quality-20261107/V176-template-information-v1/plan-v1.json"
    prior = read(prior_path)
    assert ref(prior["source_cache"]["path"]) == prior["source_cache"]
    sources = [Path(__file__).absolute()] + [
        REPO / name
        for name in [
            "scripts/phase_frequency_holdout.py",
            "scripts/green_phase_spectrum.py",
            "tests/test_phase_frequency_holdout.py",
            "tests/test_green_phase_spectrum.py",
        ]
    ]
    tests = REPO / ".cache/v177-phase-frequency-CPU-tests-v2.log"
    assert "33 passed" in tests.read_text() and "failed" not in tests.read_text()
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 0.4 + 0.05) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25 + 0.1) * 2**30
    ROOT.mkdir()
    EXTERNAL.mkdir()
    save(
        ROOT / "plan-v1.json",
        {
            "status": "fixed-one-green-phase-selection-other-phase-measurement",
            "created_unix_UTC": time.time(),
            "prior_template_plan": ref(prior_path),
            "source_cache": prior["source_cache"],
            "selected_steps": prior["selected_steps"],
            "batches": 307,
            "pairs": 614,
            "observations": 1228,
            "directions_per_observation": 2,
            "peaks_per_direction": 4,
            "descriptive_other_power_edges": [1, 4, 16, 64],
            "frequency_band": "Principal packed band mapped to native radial1/16..1/3 cycles/pixel;one conjugate half-plane. Suppress3x3 neighbors/conjugates per selection direction.",
            "selection": "A-phase abs(Hann/affine-residual unitary FFT)^2/propagated supplied A variance only. No B values,clean target,template,parent or model output in that direction's bins/rank/power. B is measured at fixed A-selected bins. Both directions run separately;combining their results reuses both phases.",
            "phase_alignment": "Signed agreement after principal-band CFA position compensation;native aliases can reverse sign or make a carrier vanish in one phase. No automatic rejection by signed agreement.",
            "variance": "Input statistics use supplied noisy-intensity physical variance proxy. Post-selection scoring separately uses exact clean shot*x+read pre-ADC variance;no calibrated probability or Gaussian/real-sensor independence claim.",
            "target_access": "All4 observations' input-only selections are durably journaled per batch before target/pair_indices arrays are read. Full source npz hash verifies bytes without interpreting target values.",
            "sources": [dict(ref(p), text=p.read_text()) for p in sources],
            "CPU_tests": dict(ref(tests), text=tests.read_text()),
            "new_local_projection_GiB": 0.05,
            "new_external_projection_GiB": 0.1,
            "scope": "All retained noisy mesh training observations only;within-image CFA sample split,not held-out-image validation. Uses1228 member RAW observations separately,never coupled noisy differences. No restoration,model/checkpoint load,neural,parent/DINO,sampler,noise draw,source render,RAW decoder,real-media/original/dataz read or V175 recipe change. GT enters descriptive scoring only after fixed input selections. No threshold tuning,confidence calibration,model promotion or flat-safety claim. Future models still require independent quality and native comparisons.",
        },
    )
    print("Prepared307batches1228observations9824selectedpeaks", flush=True)


def execute(plan_path):
    plan = read(plan_path)
    assert not (EXTERNAL / "result-v1.json").exists()
    (ROOT / "run.claim").open("x").close()
    for binding in plan["sources"]:
        assert ref(binding["path"])["sha256"] == binding["sha256"]
        assert Path(binding["path"]).read_text() == binding["text"]
    assert ref(plan["source_cache"]["path"]) == plan["source_cache"]
    os.nice(10)
    os.sched_setaffinity(0, [4, 5])
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    save(ROOT / "owner-v1.json", owner)
    cache = read(plan["source_cache"]["path"])
    selected = set(plan["selected_steps"])
    batches = [r for r in cache["batches"] if r["step"] in selected]
    assert len(batches) == 307
    rows = []
    checked = 0
    with (
        (EXTERNAL / "input-only-selections-v1.jsonl").open("x") as selections,
        (EXTERNAL / "scored-rows-v1.jsonl").open("x") as scored,
    ):
        for number, item in enumerate(batches, 1):
            assert psutil.virtual_memory().available > 32 * 2**30
            assert shutil.disk_usage(REPO).free > 48 * 2**30
            assert shutil.disk_usage("/mnt/external").free > (111 + 0.5 + 1.25) * 2**30
            assert ref(item["arrays"]["path"]) == item["arrays"]
            with np.load(item["arrays"]["path"], allow_pickle=False) as source:
                inputs = {key: source[key] for key in ["packed", "variance", "colors"]}
                for key, value in inputs.items():
                    assert fingerprint(value) == item["inputs"][key]
                    checked += 1
                observation_selections = [
                    describe_phase_holdout(raw, variance, colors, count=plan["peaks_per_direction"])
                    for raw, variance, colors in zip(
                        inputs["packed"], inputs["variance"], inputs["colors"], strict=True
                    )
                ]
                assert len(observation_selections) == 4
                selection_record = {
                    "step": item["step"],
                    "original_inputs": item["arrays"],
                    "observations": observation_selections,
                }
                selections.write(json.dumps(selection_record, allow_nan=False) + "\n")
                selections.flush()
                os.fsync(selections.fileno())
                # Target/pair interpretation starts only after this durable input-only record.
                target, pairs = source["target"], source["pair_indices"]
                for key, value in [("target", target), ("pair_indices", pairs)]:
                    assert fingerprint(value) == item["inputs"][key]
                    checked += 1
                clean = sample_RGB(np.maximum(target, np.float32(0)), inputs["colors"])
                first, second = pairs.T
                assert fingerprint(clean[first]) == item["metadata"]["sensor"]["clean_packed_a"]
                assert fingerprint(clean[second]) == item["metadata"]["sensor"]["clean_packed_b"]
                shot, read_noise = [item["metadata"]["noise"][k] for k in ["shot", "read"]]
                for pair_index, (present, absent) in enumerate(pairs):
                    signal = clean[present].astype(np.float64) - clean[absent].astype(np.float64)
                    for member, index in [("present", int(present)), ("absent", int(absent))]:
                        directions = []
                        for direction in observation_selections[index]:
                            a, b = direction["selection_phase"], direction["other_phase"]
                            actual_a = shot * clean[index, a].astype(np.float64) + read_noise
                            actual_b = shot * clean[index, b].astype(np.float64) + read_noise
                            reference_a = tapered_spectrum(clean[index, a], actual_a)
                            reference_b = tapered_spectrum(clean[index, b], actual_b)
                            template_b = tapered_spectrum(signal[b])["spectrum"]
                            peaks = []
                            for peak in direction["peaks"]:
                                y, x = peak["bin_yx"]
                                va = float(reference_a["noise_variance"][y, x])
                                vb = float(reference_b["noise_variance"][y, x])
                                peaks.append(
                                    dict(
                                        peak,
                                        clean_selection_power=float(
                                            abs(reference_a["spectrum"][y, x]) ** 2 / va
                                        ),
                                        clean_other_power=float(
                                            abs(reference_b["spectrum"][y, x]) ** 2 / vb
                                        ),
                                        hidden_template_other_power=float(
                                            abs(template_b[y, x]) ** 2 / vb
                                        ),
                                        other_proxy_over_actual_variance=peak[
                                            "other_noise_variance"
                                        ]
                                        / vb,
                                    )
                                )
                            directions.append(
                                {"selection_phase": a, "other_phase": b, "peaks": peaks}
                            )
                        row = {
                            "step": item["step"],
                            "pair": pair_index,
                            "member": member,
                            "frame_index": index,
                            "original_inputs": item["arrays"],
                            "fine_ladder": item["metadata"].get("training_distribution")
                            == "fine-mesh-ladder-v1",
                            "directions": directions,
                        }
                        scored.write(json.dumps(row, allow_nan=False) + "\n")
                        scored.flush()
                        rows.append(row)
            if number % 25 == 0:
                print(
                    json.dumps(
                        {
                            "batches": number,
                            "observations": len(rows),
                            "RSS": psutil.Process().memory_info().rss,
                        }
                    ),
                    flush=True,
                )
    assert checked == 1535 and len(rows) == 1228
    assert sum(len(d["peaks"]) for r in rows for d in r["directions"]) == 9824
    save(
        EXTERNAL / "result-v1.json",
        {
            "status": "completed-all1228-input-only-selections-followed-by-GT-scoring",
            "owner": owner,
            "plan": ref(plan_path),
            "rows": rows,
            "input_selection_journal": ref(EXTERNAL / "input-only-selections-v1.jsonl"),
            "scored_journal": ref(EXTERNAL / "scored-rows-v1.jsonl"),
            "input_array_fingerprints_checked": checked,
            "npz_files_hashed": 307,
            "selected_peaks": 9824,
            "new_neural_forwards": 0,
            "new_parent_DINO_forwards": 0,
            "new_source_renders": 0,
            "new_noise_draws": 0,
            "new_checkpoint_loads": 0,
            "Torch_imported": "torch" in sys.modules,
            "RAW_decoder_imported": "rawpy" in sys.modules,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "scope": plan["scope"],
        },
    )
    print("Completed1228observations9824peaks;no restoration", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    parser.add_argument("--plan", type=Path, default=ROOT / "plan-v1.json")
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else execute(args.plan)
