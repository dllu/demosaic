"""Read-only frequency-selection coverage on the completed V185 fixed inputs.

Select counterfactual bins from RAW only and close the entire input journal
before reading clean arrays. No neural inference, checkpoint load, RGB output,
RAW decode, source render or noise draw occurs. Saved V185 selections stay exact.
"""

import argparse
import gzip
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
from frequency_coverage import (
    eligible_bins,
    footprint,
    power_fraction,
    sample_camera_rgb,
    select_bins,
)
from green_phase_spectrum import tapered_spectrum
from local_phase_projection import local_phase_projection
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V186-frequency-coverage-v1"
PREVIOUS = ROOT.parent / "V185-spatial-context-trial-v1"
METHODS = ["actual_high4", "FP64_high4", "broad4", "balanced8"]


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


def require_completed():
    publication = REPO / "docs/results/v185-spatial-context-final-v1.json"
    verification = REPO / "docs/results/v185-spatial-context-publication-verification-v1.json"
    final, verified = read(publication), read(verification)
    assert final["status"].startswith("completed-") and verified["status"].startswith("pass-")
    assert verified["publication"] == ref(publication)
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    for name in ["wave-train", "review"]:
        assert not owner_live(read(PREVIOUS / f"{name}-launch-v1.json")["owner"])
        assert not (PREVIOUS / f"{name}-failure-v1.json").exists()
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        pair = final["copies"][name]
        assert ref(pair["original"]["path"]) == pair["original"]
        assert read(pair["original"]["path"])["status"].startswith("pass-")
    old = read(PREVIOUS / "plan-v1.json")
    neural = {Path(p).name: h for p, h in old["frozen_files"].items() if "/src/demosaic/" in p}
    assert len(neural) == 100
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    return {
        "publication": ref(publication),
        "verification": ref(verification),
        "plan": ref(PREVIOUS / "plan-v1.json"),
        "scores": ref(PREVIOUS / "scores-v1.json"),
        "selection_journal": ref(PREVIOUS / "quality-observations-v1.jsonl.gz"),
        "neural100_hashes": neural,
        "design": old["design"],
    }


def prepare():
    dependency = require_completed()
    assert not ROOT.exists()
    assert (
        shutil.disk_usage(REPO).free > (48.5 + 0.025) * 2**30
        and psutil.virtual_memory().available > 32 * 2**30
    )
    tests = REPO / ".cache/v186-frequency-coverage-CPU-tests-v2.log"
    assert "23 passed" in tests.read_text()
    design = read(dependency["design"]["path"])["observations"]
    cases = [c for c in design if c["kind"] in ["mesh", "mixed-quiet", "real"]]
    assert len(cases) == 550 and sum(c["kind"] == "mesh" for c in cases) == 512
    ROOT.mkdir()
    work = ROOT / "work"
    names = [
        "scripts/report_frequency_coverage.py",
        "scripts/frequency_coverage.py",
        "scripts/green_phase_spectrum.py",
        "scripts/local_phase_projection.py",
        "scripts/phase_admission_protocol.py",
        "scripts/phase_frequency_holdout.py",
        "tests/test_frequency_coverage.py",
    ]
    for name in names:
        dest = work / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, dest)
    plan = {
        "status": "fixed-read-only-RAW-selection-and-hidden-template-coverage-not-model-quality",
        "created_unix_UTC": time.time(),
        "dependency": dependency,
        "cases": cases,
        "runner": ref(work / "scripts/report_frequency_coverage.py"),
        "sources": [dict(ref(p), text=p.read_text()) for p in work.rglob("*.py")],
        "CPU_tests": dict(ref(tests), text=tests.read_text()),
        "methods": METHODS,
        "bands": {"high": [1 / 16, 1 / 3], "lower": [1 / 32, 1 / 16], "broad": [1 / 32, 1 / 3]},
        "peaks_per_direction": 4,
        "legacy_window_packed": 65,
        "near_bin_radius": 1,
        "local_bandwidth_radius": "ceil(packed_axis/65); square FFT proximity footprint, not exact local filter support",
        "descriptive_power_bins": [1, 4, 16, 64],
        "independent_verification_case_ids": [c["id"] for c in cases[:12]],
        "new_local_forecast_GiB": 0.025,
        "new_external_writes": 0,
        "scope": "Previous goal turn was progress: completed V185 training, both822case endpoints, native/browser audits and publication. This diagnostic asks whether the fixed high-frequency selection omits clean crossed-wire energy. Original actual V185 bins are reused exactly; FP64 high4 is a numerical bridge, broad4 retains the same candidate count, balanced8 adds a separate lower-octave bank and doubles candidate count. New bins use one RAW green phase only, other phase measurements cannot alter them. Complete550case input journal closes before clean target arrays or saved V185 response rows are interpreted. Clean spectra enter only post-selection scoring on512constructed present/absent inputs; absent uses the hypothetical present template, not actual signal. Fractions of principal CFA spectral power near selected bins are descriptive, never a reconstruction/recoverability bound or confidence test. Overlapping neighborhoods, reused phase directions, repeated noise/pattern variants and this reused development suite are not independent scene replications. No new inference, RGB restoration, checkpoint load, noise/source render, sensor draw, original/RAW decode or dataz access. Six protected real crops are input-only controls; no ISO100/JPEG reference is read or scored. Existing source/checkpoints/arrays/receipts remain unchanged; new100-neural-file hashes stay exact.",
    }
    save(ROOT / "plan-v1.json", plan)
    print(
        "Prepared550input-onlyselections/512postselectiontemplates;no neural code or quality change"
    )


def guard(plan):
    assert ref(__file__) == plan["runner"]
    for b in plan["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for key in ["publication", "verification", "plan", "scores", "selection_journal", "design"]:
        b = plan["dependency"][key]
        assert ref(b["path"]) == b


def selected_stats(spectra, noise, greens, bins):
    height, width = spectra.shape[-2:]
    fy, fx = [np.fft.fftfreq(n) / 2 for n in [height, width]]
    records = []
    for direction, (a, b) in enumerate([(0, 1), (1, 0)]):
        for rank, (y, x) in enumerate(bins[direction], 1):
            za = spectra[a, y, x] / math.sqrt(noise[a, y, x])
            zb = spectra[b, y, x] / math.sqrt(noise[b, y, x])
            dy, dx = greens[b] // 2 - greens[a] // 2, greens[b] % 2 - greens[a] % 2
            cross = za * np.conj(zb) * np.exp(2j * np.pi * (dy * fy[y] + dx * fx[x]))
            records.append(
                {
                    "direction": direction,
                    "rank": rank,
                    "bin_yx": [y, x],
                    "selection_power": float(abs(za) ** 2),
                    "other_phase_power": float(abs(zb) ** 2),
                    "bounded_cross_real": float(
                        cross.real / np.sqrt((1 + abs(za) ** 2) * (1 + abs(zb) ** 2))
                    ),
                }
            )
    return records


def measure_input(arrays, actual):
    packed, variance, colors = [arrays[k] for k in ["packed", "variance", "colors"]]
    assert len(packed) == 1 and variance.shape == packed.shape and colors.shape == (1, 4)
    greens = np.flatnonzero(colors[0] == 1)
    phase = [
        tapered_spectrum(
            packed[0, g].astype(np.float64) - float(packed[0, g, 0, 0]), variance[0, g]
        )
        for g in greens
    ]
    spectra = np.stack([p["spectrum"] for p in phase])
    noise = np.maximum(np.stack([p["noise_variance"] for p in phase]), (1 / 65535) ** 2)
    shape = tuple(int(n) for n in packed.shape[-2:])
    masks = {
        "FP64_high4": eligible_bins(shape, 1 / 16, 1 / 3),
        "lower4": eligible_bins(shape, 1 / 32, 1 / 16, upper_inclusive=False),
        "broad4": eligible_bins(shape, 1 / 32, 1 / 3),
    }
    choices = {"actual_high4": actual}
    for key, mask in masks.items():
        choices[key] = [select_bins(spectra[a], noise[a], mask, count=4) for a in range(2)]
    choices["balanced8"] = [actual[a] + choices["lower4"][a] for a in range(2)]
    stats = {k: selected_stats(spectra, noise, greens, choices[k]) for k in METHODS}
    return choices, stats


def summarize(rows, keys):
    output = []
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(k) for k in keys)].append(row)
    for key, items in groups.items():
        entry = dict(zip(keys, key, strict=True), cases=len(items))
        for field in items[0]:
            if field in keys:
                continue
            values = [r.get(field) for r in items]
            if all(type(v) in [float, int] and math.isfinite(v) for v in values):
                entry[field] = {
                    "mean": math.fsum(values) / len(values),
                    "median": float(np.median(values)),
                    "p10": float(np.quantile(values, 0.1)),
                    "p90": float(np.quantile(values, 0.9)),
                }
        output.append(entry)
    return output


def run():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    require_completed()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "launch-v1.json").exists() and read(ROOT / "launch-v1.json")["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual scientific owner; no array work")
    (ROOT / "run.claim").open("x").close()
    save(ROOT / "owner-v1.json", owner)
    os.nice(10)
    os.sched_setaffinity(0, [6, 7])
    started = time.time()
    actual = {}
    ids = {c["id"] for c in plan["cases"]}
    with gzip.open(plan["dependency"]["selection_journal"]["path"], "rt") as stream:
        for line in stream:
            record = json.loads(line)
            if record["method"] == "V185-spatial-context-raw" and record["id"] in ids:
                e = record["evidence"]
                assert e is not None and all(np.array(e["valid"]).ravel())
                actual[record["id"]] = {"bins": e["bin_yx"][0], "inputs": record["inputs"]}
    assert len(actual) == 550
    input_rows = []
    mismatch = 0
    path = ROOT / "input-selections-v1.jsonl.gz"
    with gzip.open(path, "xt", compresslevel=6) as journal:
        for index, case in enumerate(plan["cases"]):
            assert (
                shutil.disk_usage(REPO).free > 48.5 * 2**30
                and psutil.virtual_memory().available > 32 * 2**30
            )
            assert ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                arrays = {k: archive[k] for k in ["packed", "variance", "colors"]}
            inputs = {k: fingerprint(v) for k, v in arrays.items()}
            assert all(v == actual[case["id"]]["inputs"][k] for k, v in inputs.items())
            choices, stats = measure_input(arrays, actual[case["id"]]["bins"])
            same = choices["actual_high4"] == choices["FP64_high4"]
            mismatch += int(not same)
            row = {
                "index": index,
                "id": case["id"],
                "kind": case["kind"],
                "present": case.get("present"),
                "noise": case.get("noise", {}).get("name"),
                "arrays": case["arrays"],
                "inputs": inputs,
                "packed_shape": list(arrays["packed"].shape),
                "colors": arrays["colors"].tolist(),
                "bins": choices,
                "selected_stats": stats,
                "actual_vs_FP64_high4_bins_exact": same,
            }
            input_rows.append(row)
            journal.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            journal.flush()
            if (index + 1) % 50 == 0:
                print("input-only", index + 1, "/550", flush=True)
    # This binding exists before any exact clean array or saved response is read.
    save(
        ROOT / "input-completion-v1.json",
        {
            "status": "closed-all550-RAW-only-counterfactual-selections-before-target-scoring",
            "journal": ref(path),
            "cases": len(input_rows),
            "input_fingerprints": 3 * len(input_rows),
            "saved_actual_V185_bins_retained_exact": True,
            "actual_vs_FP64_case_mismatches": mismatch,
            "target_array_reads_before_close": 0,
            "owner": owner,
        },
    )
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    saved = read(plan["dependency"]["scores"]["path"])
    responses = {(r["id"], r["method"]): r for r in saved["rows"]}
    scored = []
    control = []
    with gzip.open(ROOT / "postselection-template-v1.jsonl.gz", "xt", compresslevel=6) as journal:
        for case, selection in zip(plan["cases"], input_rows, strict=True):
            assert case["id"] == selection["id"] and ref(case["arrays"]["path"]) == case["arrays"]
            if case["kind"] == "mesh":
                with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                    colors = archive["colors"]
                    present = np.maximum(archive["target_present"], np.float32(0))
                    empty = np.maximum(archive["target_empty"], np.float32(0))
                signal = sample_camera_rgb(present, colors).astype(np.float64) - sample_camera_rgb(
                    empty, colors
                ).astype(np.float64)
                greens = np.flatnonzero(colors[0] == 1)
                spectra = np.stack([tapered_spectrum(signal[0, g])["spectrum"] for g in greens])
                power = (abs(spectra) ** 2).sum(0)
                h, w = power.shape
                fy, fx = [np.fft.fftfreq(n) / 2 for n in [h, w]]
                radius = np.hypot(fy[:, None], fx[None, :])
                result = {
                    "id": case["id"],
                    "kind": "mesh",
                    "present": case["present"],
                    "seed": case["seed"],
                    "noise": case["noise"]["name"],
                    "pattern": case["pattern"],
                    "template_sensor_values": fingerprint(signal),
                    "template_power": fingerprint(power),
                    "total_tapered_template_energy": float(power.sum()),
                    "lower_octave_power_fraction": power_fraction(
                        power, (radius >= 1 / 32) & (radius < 1 / 16)
                    ),
                    "high_band_power_fraction": power_fraction(
                        power, (radius >= 1 / 16) & (radius <= 1 / 3)
                    ),
                    "below_lower_octave_power_fraction": power_fraction(power, radius < 1 / 32),
                    "nominal_fundamentals_below_high": sum(
                        p > 16 for p in case["source"]["recipe"]["periods_final_pixels"]
                    ),
                    "V185_raw_template_gain": responses[case["id"], "V185-spatial-context-raw"][
                        "template_gain"
                    ],
                    "V185_EMA_template_gain": responses[case["id"], "V185-spatial-context-EMA"][
                        "template_gain"
                    ],
                }
                local_radius = max(math.ceil(h / 65), math.ceil(w / 65))
                result["local_bandwidth_square_radius_bins"] = local_radius
                for method in METHODS:
                    bins = np.asarray(selection["bins"][method]).reshape(-1, 2)
                    for label, r in [("near1", 1), ("localwidth", local_radius)]:
                        result[method + "_" + label + "_template_fraction"] = power_fraction(
                            power, footprint((h, w), bins, r)
                        )
                scored.append(result)
                journal.write(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
            else:
                with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                    raw, variance, colors = [archive[k] for k in ["packed", "variance", "colors"]]
                regions = (
                    [{"name": case["id"], "ROI_xywh": case["ROI_xywh"]}]
                    if "ROI_xywh" in case
                    else case["source"]["cases"]
                )
                for region in regions:
                    x, y, width, height = region["ROI_xywh"]
                    center = np.array(
                        [[(y + height // 2) // 2, (x + width // 2) // 2]], dtype=np.int64
                    )
                    greens = np.flatnonzero(colors[0] == 1)
                    for method in METHODS:
                        values = []
                        for stat in selection["selected_stats"][method]:
                            a, b = [greens[q] for q in [(0, 1), (1, 0)][stat["direction"]]]
                            local = []
                            for phase in [a, b]:
                                item = local_phase_projection(
                                    raw[0, phase],
                                    variance[0, phase],
                                    stat["bin_yx"],
                                    window=65,
                                    centers_yx=center,
                                )
                                local.append(
                                    float(
                                        abs(item["coefficient"][0]) ** 2
                                        / max(float(item["noise_variance"][0]), (1 / 65535) ** 2)
                                    )
                                )
                            values.append(
                                {
                                    **stat,
                                    "ROI_center_local_selection_power": local[0],
                                    "ROI_center_local_other_power": local[1],
                                }
                            )
                        control.append(
                            {
                                "id": case["id"],
                                "kind": case["kind"],
                                "noise": selection["noise"],
                                "method": method,
                                "ROI_xywh": region["ROI_xywh"],
                                "center_packed_yx": center.tolist(),
                                "window_packed": 65,
                                "measurements": values,
                            }
                        )
    power_summary = []
    for (kind, present), items in _group_inputs(input_rows).items():
        for method in METHODS:
            maxima = [
                max(v["other_phase_power"] for v in r["selected_stats"][method]) for r in items
            ]
            power_summary.append(
                {
                    "kind": kind,
                    "present": present,
                    "method": method,
                    "cases": len(items),
                    "max_other_phase_power_median": float(np.median(maxima)),
                    "max_other_phase_power_p90": float(np.quantile(maxima, 0.9)),
                    "counts_at_predeclared_power": {
                        str(t): sum(v >= t for v in maxima) for t in plan["descriptive_power_bins"]
                    },
                }
            )
    save(
        ROOT / "control-ROI-measurements-v1.json",
        {
            "rows": control,
            "scope": "Input-only RAW measurements after selection at each fixed ROI center; real references never read and no real GT scored.",
        },
    )
    result = {
        "status": "completed-input-only-selection-and-postselection-template-coverage-not-new-model-quality",
        "owner": owner,
        "plan": ref(ROOT / "plan-v1.json"),
        "input_completion": ref(ROOT / "input-completion-v1.json"),
        "input_journal": ref(path),
        "template_journal": ref(ROOT / "postselection-template-v1.jsonl.gz"),
        "control_measurements": ref(ROOT / "control-ROI-measurements-v1.json"),
        "input_cases": 550,
        "constructed_template_cases": len(scored),
        "control_case_methods": len(control),
        "actual_vs_FP64_high4_case_mismatches": mismatch,
        "input_power_summary": power_summary,
        "template_summary_by_presence": summarize(scored, ["present"]),
        "template_summary_by_presence_and_nominal_band": summarize(
            scored, ["present", "nominal_fundamentals_below_high"]
        ),
        "rows": scored,
        "new_neural_forwards": 0,
        "new_RGB_restorations": 0,
        "new_checkpoint_loads": 0,
        "new_source_noise_draws": 0,
        "real_reference_reads": 0,
        "torch_imported": False,
        "rawpy_imported": False,
        "maximum_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "seconds": time.time() - started,
        "scope": plan["scope"],
    }
    assert (
        len(scored) == 512
        and len(control) == 160
        and "torch" not in sys.modules
        and "rawpy" not in sys.modules
    )
    guard(plan)
    save(ROOT / "result-v1.json", result)
    print(
        "PASS550inputselections/512postselectiontemplates/160controlmethods;no inference",
        flush=True,
    )


def _group_inputs(rows):
    result = defaultdict(list)
    for r in rows:
        result[r["kind"], r["present"]].append(r)
    return result


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "launch-v1.json").exists()
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "work/scripts"),
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    with (ROOT / "run-v1.log").open("xb") as log:
        process = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "run"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
    save(ROOT / "launch-v1.json", {"owner": owner, "plan": ref(ROOT / "plan-v1.json")})
    print(json.dumps(owner))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "run"])
    args = parser.parse_args()
    if args.phase == "run":
        try:
            run()
        except BaseException as exc:
            save(ROOT / "failure-v1.json", {"error": repr(exc), "created_unix_UTC": time.time()})
            raise
    else:
        {"prepare": prepare, "launch": launch}[args.phase]()
