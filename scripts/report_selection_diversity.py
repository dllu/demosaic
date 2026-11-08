"""Test pooled spectral allocation from closed V187 inputs, then hidden templates."""

import argparse
import gzip
import json
import math
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from frequency_coverage import sample_camera_rgb
from green_phase_spectrum import tapered_spectrum
from local_phase_projection import local_phase_projection
from phase_admission_protocol import owner_live, read, ref
from report_frequency_coverage import fingerprint, summarize
from spectral_selection_diversity import (
    pooled_score,
    select_pooled,
    selection_geometry,
    template_proximity,
)

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V188-selection-diversity-v1"
PREVIOUS = ROOT.parent / "V187-pooled-wave-trial-v1"
COVERAGE = ROOT.parent / "V186-frequency-coverage-v1"
METHODS = ["V185_actual8slots", "V187_actual8", "FP64_pooled8", "spaced8", "sector8"]


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def lines(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def completed():
    index = REPO / "docs/results/v187-pooled-wave-final-v1.json"
    proof = REPO / "docs/results/v187-pooled-wave-publication-verification-v1.json"
    final, verified = read(index), read(proof)
    assert final["status"].startswith("completed-") and verified["status"].startswith("pass-")
    assert verified["publication"] == ref(index)
    for k in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[k]["path"]) == final[k]
    for name in ["wave-train", "review", "train-review-controller", "review-render-controller"]:
        assert not owner_live(read(PREVIOUS / f"{name}-launch-v1.json")["owner"])
        assert not (PREVIOUS / f"{name}-failure-v1.json").exists()
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        assert read(PREVIOUS / name)["status"].startswith("pass-")
    previous = read(PREVIOUS / "plan-v1.json")
    neural = {Path(p).name: h for p, h in previous["frozen_files"].items() if "/src/demosaic/" in p}
    assert len(neural) == 101
    for n, h in neural.items():
        assert ref(REPO / "src/demosaic" / n)["sha256"] == h
    diagnostic = REPO / "docs/results/v186-frequency-coverage-v1.json"
    diagnostic_proof = (
        REPO / "docs/results/v186-frequency-coverage-publication-verification-v1.json"
    )
    assert read(diagnostic_proof)["publication"] == ref(diagnostic)
    assert read(COVERAGE / "verification-v2.json")["status"].startswith("pass-")
    return {
        "publication": ref(index),
        "verification": ref(proof),
        "previous_plan": ref(PREVIOUS / "plan-v1.json"),
        "actual_selection_journal": ref(PREVIOUS / "quality-observations-v1.jsonl.gz"),
        "previous_scores": ref(PREVIOUS / "scores-v1.json"),
        "coverage_publication": ref(diagnostic),
        "coverage_verification": ref(diagnostic_proof),
        "old_inputs": ref(COVERAGE / "input-selections-v1.jsonl.gz"),
        "old_templates": ref(COVERAGE / "postselection-template-v1.jsonl.gz"),
        "coverage_plan": ref(COVERAGE / "plan-v1.json"),
        "neural101_hashes": neural,
    }


def prepare():
    dep = completed()
    assert not ROOT.exists()
    assert (
        shutil.disk_usage(REPO).free > 40.030 * 2**30
        and psutil.virtual_memory().available > 32 * 2**30
    )
    tests = REPO / ".cache/v188-diversity-CPU-tests-v1.log"
    assert "20 passed" in tests.read_text()
    cases = read(dep["coverage_plan"]["path"])["cases"]
    assert len(cases) == 550 and sum(c["kind"] == "mesh" for c in cases) == 512
    ROOT.mkdir()
    work = ROOT / "work"
    sources = [
        "scripts/" + n + ".py"
        for n in [
            "report_selection_diversity",
            "spectral_selection_diversity",
            "frequency_coverage",
            "green_phase_spectrum",
            "local_phase_projection",
            "phase_admission_protocol",
            "report_frequency_coverage",
        ]
    ] + ["tests/test_spectral_selection_diversity.py"]
    for n in sources:
        d = work / n
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / n, d)
    plan = {
        "status": "fixed-input-only-diverse-eight-slot-allocation-then-hidden-template-proximity-not-quality",
        "created_unix_UTC": time.time(),
        "runner": ref(work / "scripts/report_selection_diversity.py"),
        "sources": [dict(ref(work / n), text=(work / n).read_text()) for n in sources],
        "dependency": dep,
        "cases": cases,
        "methods": METHODS,
        "CPU_tests": ref(tests),
        "independent_case_ids": [c["id"] for c in cases[:12]],
        "local_floor_GiB": 40,
        "RAM_floor_GiB": 32,
        "new_local_forecast_GiB": 0.030,
        "new_external_writes": 0,
        "scope": "Previous turn was progress: completed/published V187 matched508parameter900update run, both822case endpoints, independent audits and actual60native views. Residual weak crossings/falsewaves motivate this diagnostic. Reuse actual V185 and V187 bins; FP64 pooled8 bridges numerical ranking. Same two-green9neighbor pooled score, 1/16..1/3 center band,8slots for all counterfactuals. Spaced8 changes NMS radius from1 toceil(maxpackedaxis/65), leaving rank greedy; sector8 uses radius1 and at most2picks per four fixed45degree principal sectors. Absolute angular boundaries are arbitrary; postselection sector summaries use0 and22.5degree partitions, with minima only among sectors carrying at least5percent principal template energy. No target, reference, response or predictedRGB influences input selection. Parse closed V187 quality journal only for input bindings/bins; all550input rows close before clean arrays/saved response interpretation. Descriptive principal-CFA template proximity is not recovered amplitude, an upper bound, confidence, independent replications or a blind safety test. All512present/absent templates reuse exact present-minus-empty arrays; absent templates are hypothetical,not signal. Controls are32quiet+6real contexts/40ROIs; selected both-phase/local powers are not holdout tests. Real ISO100/AHD/JPEG refs never read or scored. No neural/checkpoint/model load, newRGB, decoder, source/noise draw, original/dataz access or neural-source changes. All101older neural files/receipts/checkpoints preserved. Allnew outputs local withprospective40GiBbuffer;externalread-only.",
    }
    save(ROOT / "plan-v1.json", plan)
    print("Prepared550inputcontexts/512postselectiontemplates/40ROIs;zero new model or quality")


def guard(plan):
    assert ref(__file__) == plan["runner"]
    for b in plan["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for k, b in plan["dependency"].items():
        if k != "neural101_hashes":
            assert ref(b["path"]) == b


def resources(plan):
    while (
        shutil.disk_usage(REPO).free <= plan["local_floor_GiB"] * 2**30
        or psutil.virtual_memory().available <= plan["RAM_floor_GiB"] * 2**30
    ):
        print("Waiting before next CPU case for recorded local/RAM floor", flush=True)
        time.sleep(5)


def run():
    p = read(ROOT / "plan-v1.json")
    guard(p)
    completed()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "launch-v1.json").exists() and read(ROOT / "launch-v1.json")["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual launch binding")
    (ROOT / "run.claim").open("x").close()
    save(ROOT / "owner-v1.json", owner)
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    started = time.time()
    old = {r["id"]: r for r in lines(p["dependency"]["old_inputs"]["path"])}
    actual = {}
    ids = set(old)
    with gzip.open(p["dependency"]["actual_selection_journal"]["path"], "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["method"] == "V187-pooled-wave-raw" and r["id"] in ids:
                s = r["pooled"]["selection"]
                assert np.asarray(s["valid"]).all()
                actual[r["id"]] = {
                    "bins": np.asarray(s["bin_yx"])[0].transpose(1, 0, 2).reshape(-1, 2).tolist(),
                    "inputs": r["inputs"],
                }
    assert len(actual) == 550
    selections = []
    mismatches = []
    with gzip.open(ROOT / "input-selections-v1.jsonl.gz", "xt", compresslevel=6) as f:
        for index, c in enumerate(p["cases"]):
            resources(p)
            assert ref(c["arrays"]["path"]) == c["arrays"]
            with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                raw, var, colors = [a[k] for k in ["packed", "variance", "colors"]]
            inputs = {
                k: fingerprint(v)
                for k, v in zip(["packed", "variance", "colors"], [raw, var, colors], strict=True)
            }
            assert len(raw) == 1 and all(
                v == actual[c["id"]]["inputs"][k] == old[c["id"]]["inputs"][k]
                for k, v in inputs.items()
            )
            score, powers, greens = pooled_score(raw[0], var[0], colors[0])
            shape = score.shape
            r = math.ceil(max(shape) / 65)
            choices = {
                "V185_actual8slots": np.asarray(old[c["id"]]["bins"]["actual_high4"])
                .reshape(-1, 2)
                .tolist(),
                "V187_actual8": actual[c["id"]]["bins"],
            }
            for name, kw in [
                ("FP64_pooled8", {}),
                ("spaced8", {"radius": r}),
                ("sector8", {"quota": 2}),
            ]:
                choices[name] = select_pooled(score, **kw)["bins"]
            same = choices["V187_actual8"] == choices["FP64_pooled8"]
            if not same:
                mismatches.append(c["id"])
            stats = {}
            for method, bins in choices.items():
                assert len(bins) == 8
                y, x = np.asarray(bins).T
                phase = powers[:, y, x].T
                stats[method] = {
                    "global_two_phase_power": phase.tolist(),
                    "pooled_scores": score[y, x].tolist(),
                    "geometry_localwidth": selection_geometry(shape, bins, r),
                    "geometry_near1": selection_geometry(shape, bins, 1),
                    "global_max_min_phase_power": float(phase.min(1).max()),
                }
            row = {
                "index": index,
                "id": c["id"],
                "kind": c["kind"],
                "present": c.get("present"),
                "noise": c.get("noise", {}).get("name"),
                "arrays": c["arrays"],
                "inputs": inputs,
                "shape": list(shape),
                "colors": colors.tolist(),
                "bins": choices,
                "stats": stats,
                "actual_FP64_bins_exact": same,
            }
            selections.append(row)
            f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            f.flush()
            if (index + 1) % 50 == 0:
                print("input-only", index + 1, "/550", flush=True)
    save(
        ROOT / "input-completion-v1.json",
        {
            "status": "closed-all550input-only-allocations-before-clean-template-reads",
            "owner": owner,
            "journal": ref(ROOT / "input-selections-v1.jsonl.gz"),
            "cases": 550,
            "target_reads_before_close": 0,
            "FP64_bridge_mismatches": mismatches,
        },
    )
    # Only now are clean arrays and old diagnostic fractions interpreted.
    previous_templates = {r["id"]: r for r in lines(p["dependency"]["old_templates"]["path"])}
    scored = []
    controls = []
    unique_local = 0
    with (
        gzip.open(ROOT / "template-proximity-v1.jsonl.gz", "xt", compresslevel=6) as sf,
        gzip.open(ROOT / "control-ROI-v1.jsonl.gz", "xt", compresslevel=6) as cf,
    ):
        for c, s in zip(p["cases"], selections, strict=True):
            resources(p)
            assert c["id"] == s["id"]
            if c["kind"] == "mesh":
                with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                    colors = a["colors"]
                    present = np.maximum(a["target_present"], np.float32(0))
                    empty = np.maximum(a["target_empty"], np.float32(0))
                clean = sample_camera_rgb(present, colors).astype(float) - sample_camera_rgb(
                    empty, colors
                ).astype(float)
                greens = np.flatnonzero(colors[0] == 1)
                spectra = [tapered_spectrum(clean[0, g])["spectrum"] for g in greens]
                power = sum(abs(z) ** 2 for z in spectra)
                oldrow = previous_templates[c["id"]]
                assert (
                    fingerprint(clean) == oldrow["template_sensor_values"]
                    and fingerprint(power) == oldrow["template_power"]
                )
                for method in METHODS:
                    for label, radius in [
                        ("near1", 1),
                        ("localwidth", math.ceil(max(power.shape) / 65)),
                    ]:
                        v = template_proximity(power, s["bins"][method], radius)
                        if method == "V185_actual8slots":
                            assert (
                                abs(
                                    v["all_template_fraction"]
                                    - oldrow[f"actual_high4_{label}_template_fraction"]
                                )
                                < 1e-14
                            )
                        row = {
                            "id": c["id"],
                            "kind": "mesh",
                            "present": c["present"],
                            "method": method,
                            "neighborhood": label,
                            "radius": radius,
                            "template_sensor_values": fingerprint(clean),
                            "template_power": fingerprint(power),
                            "template_fraction": v["all_template_fraction"],
                            "minimum_substantial_sector_fraction_0": v["sectors"]["0"][
                                "minimum_proximity_among_sectors_with_at_least_5percent_power"
                            ],
                            "minimum_substantial_sector_fraction_22p5": v["sectors"]["22.5"][
                                "minimum_proximity_among_sectors_with_at_least_5percent_power"
                            ],
                            "sector_details": v["sectors"],
                        }
                        scored.append(row)
                        sf.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
                        sf.flush()
            else:
                with np.load(c["arrays"]["path"], allow_pickle=False) as a:
                    raw, var, colors = [a[k] for k in ["packed", "variance", "colors"]]
                regions = (
                    [{"name": c["id"], "ROI_xywh": c["ROI_xywh"]}]
                    if "ROI_xywh" in c
                    else c["source"]["cases"]
                )
                for region in regions:
                    x, y, w, h = region["ROI_xywh"]
                    center = np.asarray([[(y + h // 2) // 2, (x + w // 2) // 2]], dtype=np.int64)
                    greens = np.flatnonzero(colors[0] == 1)
                    cache = {}
                    for method in METHODS:
                        powers = []
                        for by, bx in s["bins"][method]:
                            values = []
                            for phase in greens:
                                key = (int(phase), by, bx)
                                if key not in cache:
                                    v = local_phase_projection(
                                        raw[0, phase],
                                        var[0, phase],
                                        [by, bx],
                                        window=65,
                                        centers_yx=center,
                                    )
                                    cache[key] = float(
                                        abs(v["coefficient"][0]) ** 2
                                        / max(float(v["noise_variance"][0]), (1 / 65535) ** 2)
                                    )
                                    unique_local += 1
                                values.append(cache[key])
                            powers.append(values)
                        row = {
                            "id": c["id"],
                            "ROI_name": region["name"],
                            "ROI_xywh": region["ROI_xywh"],
                            "kind": c["kind"],
                            "noise": s["noise"],
                            "method": method,
                            "center_packed_yx": center.tolist(),
                            "window": 65,
                            "bins": s["bins"][method],
                            "local_two_phase_power": powers,
                            "local_max_min_phase_power": float(np.asarray(powers).min(1).max()),
                            "global_max_min_phase_power": s["stats"][method][
                                "global_max_min_phase_power"
                            ],
                        }
                        controls.append(row)
                        cf.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
                        cf.flush()
    assert len(scored) == 5120 and len(controls) == 200
    result = {
        "status": "completed-550input-allocations-512hidden-template-cases-40local-ROIs-not-new-denoising-quality",
        "owner": owner,
        "plan": ref(ROOT / "plan-v1.json"),
        "input_completion": ref(ROOT / "input-completion-v1.json"),
        "input_journal": ref(ROOT / "input-selections-v1.jsonl.gz"),
        "template_journal": ref(ROOT / "template-proximity-v1.jsonl.gz"),
        "control_journal": ref(ROOT / "control-ROI-v1.jsonl.gz"),
        "input_cases": 550,
        "template_cases": 512,
        "template_measurements": len(scored),
        "ROI_method_measurements": len(controls),
        "stored_local_powers": sum(np.asarray(r["local_two_phase_power"]).size for r in controls),
        "unique_local_power_evaluations": unique_local,
        "FP64_bridge_mismatches": mismatches,
        "template_summary": summarize(scored, ["method", "present", "neighborhood"]),
        "control_summary": summarize(controls, ["method", "kind"]),
        "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "wall_seconds": time.time() - started,
        "new_neural_forwards": 0,
        "new_RGB_arrays": 0,
        "new_source_noise_draws": 0,
        "checkpoint_loads": 0,
        "scope": p["scope"],
    }
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    guard(p)
    save(ROOT / "result-v1.json", result)
    print("PASS550inputs/512templates/200ROI-methods/3200localpowers;no new inference", flush=True)


def launch():
    p = read(ROOT / "plan-v1.json")
    guard(p)
    assert not (ROOT / "launch-v1.json").exists() and not (ROOT / "run.claim").exists()
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "work/scripts"),
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    with (ROOT / "run-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), p["runner"]["path"], "run"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / "launch-v1.json",
        {"owner": owner, "runner": p["runner"], "plan": ref(ROOT / "plan-v1.json")},
    )
    print(json.dumps(owner))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "run"])
    args = parser.parse_args()
    if args.phase != "run":
        {"prepare": prepare, "launch": launch}[args.phase]()
    else:
        try:
            run()
        except BaseException as exc:
            save(ROOT / "failure-v1.json", {"error": repr(exc), "time_UTC": time.time()})
            raise
