"""Finish only V186 controls after the closed 550/512 scientific prefix.

Original v1 failed on a cab case with two ROIs. No input selection or clean
spectral measurement is repeated. Controls had no durable output before failure;
this successor journals every completed case/ROI/method and reads no references.
"""

import argparse
import gzip
import importlib.util
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from local_phase_projection import local_phase_projection
from phase_admission_protocol import owner_live, read, ref

ROOT = Path("/home/dllu/proj/demosaic/.cache/quality-20261107/V186-frequency-coverage-v1")
_spec = importlib.util.spec_from_file_location(
    "v186_frozen_coverage_driver", ROOT / "work/scripts/report_frequency_coverage.py"
)
_driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_driver)
METHODS, REPO = _driver.METHODS, _driver.REPO
_group_inputs, guard, save, summarize = (
    _driver._group_inputs,
    _driver.guard,
    _driver.save,
    _driver.summarize,
)


def regions(case):
    if "ROI_xywh" in case:
        return [{"name": case["id"], "ROI_xywh": case["ROI_xywh"]}]
    result = [{"name": c["name"], "ROI_xywh": c["ROI_xywh"]} for c in case["source"]["cases"]]
    if not result or any(len(r["ROI_xywh"]) != 4 for r in result):
        raise ValueError("Missing fixed native ROIs")
    return result


def prepare():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert (
        not owner_live(read(ROOT / "launch-v1.json")["owner"])
        and (ROOT / "failure-v1.json").exists()
    )
    completion = read(ROOT / "input-completion-v1.json")
    assert completion["cases"] == 550
    assert completion["target_array_reads_before_close"] == 0
    with gzip.open(ROOT / "postselection-template-v1.jsonl.gz", "rt") as stream:
        count = sum(1 for _ in stream)
    assert count == 512 and not (ROOT / "result-v1.json").exists()
    prefix = [
        ref(ROOT / n)
        for n in [
            "plan-v1.json",
            "launch-v1.json",
            "failure-v1.json",
            "run-v1.log",
            "input-completion-v1.json",
            "input-selections-v1.jsonl.gz",
            "postselection-template-v1.jsonl.gz",
        ]
    ]
    work = ROOT / "control-resume-work-v1/scripts"
    work.mkdir(parents=True)
    for n in [
        "finish_frequency_coverage.py",
        "report_frequency_coverage.py",
        "frequency_coverage.py",
        "green_phase_spectrum.py",
        "local_phase_projection.py",
        "phase_admission_protocol.py",
    ]:
        source = (
            Path(__file__) if n == "finish_frequency_coverage.py" else ROOT / "work/scripts" / n
        )
        shutil.copyfile(source, work / n)
    output = {
        "status": "prepared-controls-only-resume-of-retained550input512template-prefix",
        "runner": ref(work / "finish_frequency_coverage.py"),
        "sources": [ref(p) for p in work.glob("*.py")],
        "original_prefix": prefix,
        "control_regions": sum(len(regions(c)) for c in plan["cases"] if c["kind"] != "mesh"),
        "methods_per_region": 4,
        "scope": "Original case selections and all512 constructed-template rows are closed and retained byte-exact. Original control computations were only in memory when the single-ROI assumption failed; there was no durable control prefix. Successor reads existing selection journal and only packed/variance/colors for 32quiet+6real contexts, visiting both cab ROIs (40regions/160region-methods). No input selection, clean template calculation, model/RGB inference, source/noise render or reference read is repeated.",
    }
    assert output["control_regions"] == 40
    save(ROOT / "control-resume-plan-v1.json", output)
    print("Prepared controls-only resume;550/512 durableprefix unchanged")


def guard_resume(plan):
    assert ref(__file__) == plan["runner"]
    for binding in plan["sources"] + plan["original_prefix"]:
        assert ref(binding["path"]) == binding
    assert not owner_live(read(ROOT / "launch-v1.json")["owner"])


def run():
    resume = read(ROOT / "control-resume-plan-v1.json")
    guard_resume(resume)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "control-resume-launch-v1.json").exists() and read(
            ROOT / "control-resume-launch-v1.json"
        )["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing successor actual owner")
    (ROOT / "control-resume.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [6, 7])
    start = time.time()
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    with gzip.open(ROOT / "input-selections-v1.jsonl.gz", "rt") as stream:
        inputs = [json.loads(line) for line in stream]
    with gzip.open(ROOT / "postselection-template-v1.jsonl.gz", "rt") as stream:
        scored = [json.loads(line) for line in stream]
    assert len(inputs) == 550 and len(scored) == 512
    controls = []
    with gzip.open(ROOT / "control-ROI-journal-v1.jsonl.gz", "xt", compresslevel=6) as journal:
        for case, selection in zip(plan["cases"], inputs, strict=True):
            if case["kind"] == "mesh":
                continue
            assert case["id"] == selection["id"] and ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
                raw, variance, colors = [archive[k] for k in ["packed", "variance", "colors"]]
            greens = np.flatnonzero(colors[0] == 1)
            for region in regions(case):
                x, y, width, height = region["ROI_xywh"]
                center = np.array([[(y + height // 2) // 2, (x + width // 2) // 2]], dtype=np.int64)
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
                    record = {
                        "id": case["id"],
                        "region": region["name"],
                        "kind": case["kind"],
                        "noise": selection["noise"],
                        "method": method,
                        "ROI_xywh": region["ROI_xywh"],
                        "center_packed_yx": center.tolist(),
                        "window_packed": 65,
                        "measurements": values,
                    }
                    controls.append(record)
                    journal.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
                    journal.flush()
    power_summary = []
    for (kind, present), items in _group_inputs(inputs).items():
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
    save(ROOT / "control-ROI-measurements-v1.json", {"rows": controls, "scope": resume["scope"]})
    result = {
        "status": "completed-input-only-selection-and-postselection-template-coverage-not-new-model-quality",
        "owner": owner,
        "original_owner": read(ROOT / "launch-v1.json")["owner"],
        "control_resume_plan": ref(ROOT / "control-resume-plan-v1.json"),
        "plan": ref(ROOT / "plan-v1.json"),
        "input_completion": ref(ROOT / "input-completion-v1.json"),
        "input_journal": ref(ROOT / "input-selections-v1.jsonl.gz"),
        "template_journal": ref(ROOT / "postselection-template-v1.jsonl.gz"),
        "control_measurements": ref(ROOT / "control-ROI-measurements-v1.json"),
        "control_journal": ref(ROOT / "control-ROI-journal-v1.jsonl.gz"),
        "input_cases": 550,
        "constructed_template_cases": 512,
        "control_case_methods": len(controls),
        "actual_vs_FP64_high4_case_mismatches": read(ROOT / "input-completion-v1.json")[
            "actual_vs_FP64_case_mismatches"
        ],
        "input_power_summary": power_summary,
        "template_summary_by_presence": summarize(scored, ["present"]),
        "template_summary_by_presence_and_nominal_band": summarize(
            scored, ["present", "nominal_fundamentals_below_high"]
        ),
        "rows": scored,
        "retained_input_selection_replays": 0,
        "retained_clean_template_replays": 0,
        "new_neural_forwards": 0,
        "new_RGB_restorations": 0,
        "new_checkpoint_loads": 0,
        "new_source_noise_draws": 0,
        "real_reference_reads": 0,
        "torch_imported": False,
        "rawpy_imported": False,
        "maximum_resume_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "resume_seconds": time.time() - start,
        "scope": plan["scope"]
        + " Controls successor uses40fixedROIs/160methodrecords, including both cab regions; all550/512completedinput/GT prefixes retained without replay.",
    }
    assert len(controls) == 160 and "torch" not in sys.modules and "rawpy" not in sys.modules
    guard_resume(resume)
    guard(plan)
    save(ROOT / "result-v1.json", result)
    print(
        "PASS550inputselections/512templates/160controlROI-methods;durableprefix retained/no inference"
    )


def launch():
    plan = read(ROOT / "control-resume-plan-v1.json")
    guard_resume(plan)
    assert not (ROOT / "control-resume-launch-v1.json").exists()
    env = dict(
        os.environ,
        PYTHONPATH=str(Path(plan["runner"]["path"]).parent),
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    with (ROOT / "control-resume-v1.log").open("xb") as log:
        process = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "run"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    save(
        ROOT / "control-resume-launch-v1.json",
        {
            "owner": {"pid": process.pid, "created": psutil.Process(process.pid).create_time()},
            "plan": ref(ROOT / "control-resume-plan-v1.json"),
        },
    )
    print(process.pid)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["prepare", "launch", "run"])
    a = p.parse_args()
    {"prepare": prepare, "launch": launch, "run": run}[a.phase]()
