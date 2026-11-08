"""Fixed analytical window/taper/carrier-grid calculation; no model quality."""

import argparse, gzip, json, os, shutil, subprocess, sys, time
from pathlib import Path
from collections import defaultdict
import numpy as np
import psutil
from dense_measurement_support import cases, measure, ratios
from phase_admission_protocol import read, ref, owner_live

R = Path("/home/dllu/proj/demosaic")
ROOT = R / ".cache/quality-20261107/V192-dense-support-v1"


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def dependencies():
    index = R / "docs/results/v191-dense-spectrum-final-v1.json"
    proof = R / "docs/results/v191-dense-spectrum-publication-verification-v1.json"
    completion = R / "docs/results/v191-completed-execution-v1.json"
    p, v, c = read(index), read(proof), read(completion)
    assert (
        v["publication"] == ref(index)
        and v["status"].startswith("pass-")
        and c["status"].startswith("pass-terminal-")
    )
    for o in c["all_terminal_owners"].values():
        assert not owner_live(o)
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(p[key]["path"]) == p[key]
    neural = dict(c["previous102_neural_hashes_unchanged"])
    neural["late_dense_local_spectrum.py"] = c["new_neural_source"]["sha256"]
    assert len(neural) == 103
    for name, digest in neural.items():
        assert ref(R / "src/demosaic" / name)["sha256"] == digest
    return {
        "publication": ref(index),
        "verification": ref(proof),
        "completion": ref(completion),
        "neural103_hashes": neural,
    }


def prepare():
    dep = dependencies()
    assert not ROOT.exists()
    assert (
        shutil.disk_usage(R).free > 40.02 * 2**30 and psutil.virtual_memory().available > 32 * 2**30
    )
    log = R / ".cache/v192-support-CPU-tests-v1.log"
    assert "15 passed" in log.read_text()
    ROOT.mkdir()
    work = ROOT / "work/scripts"
    work.mkdir(parents=True)
    files = [
        "report_dense_measurement_support.py",
        "dense_measurement_support.py",
        "dense_support_reference.py",
        "audit_dense_measurement_support.py",
        "phase_admission_protocol.py",
    ]
    for name in files:
        shutil.copyfile(R / "scripts" / name, work / name)
    p = {
        "status": "fixed-analytical-tone-support-and-carrier-quantization-not-quality",
        "created_unix_UTC": time.time(),
        "runner": ref(work / files[0]),
        "auditor": ref(work / files[3]),
        "sources": [dict(ref(work / name), text=(work / name).read_text()) for name in files],
        "dependency": dep,
        "CPU_tests": ref(log),
        "cases": cases(),
        "local_floor_GiB": 40,
        "RAM_floor_GiB": 32,
        "forecast_GiB": 0.020,
        "scope": "V191 changes dense/local representation,taper,coefficientunits andsynthesis together and regresses mesh. Isolate linearmeasurement effects with48fixedanalytic nativefrequencies(12base65gridbins x4subbinoffsets),unit-amplitude cosine/sinequadratures,uniform/graded independentvariance,interior/corner of256packedcontext. Compare rectangular65/global256carriergrid,Hann65/local65grid,Hann129/local129grid. Exact-frequency mode isolates support/taper; nearest-available-carrier mode separately includes deterministic quantization,not inputselection. Both use weightedaffine detrending;signalpower averaged over two quadratures,not randomphase/noise draws. Pure one-phase lattice linearmeasurement,not trainedRGB,fullCFArecovery,confidence orstatisticalreplications. Rectangular256grid is only an available-frequency comparator,not V187actual8binselection. Nearest carrier uses known analytic frequency,not a deployable noisy selector. No realimage,target/reference,checkpoint/model load,oldNN/parent/DINO/RAWdecode,source/noisedraw,original/dataz access orneural-sourcechange. All103sources/earlierreceipts/checkpoints remainunchanged. Newoutputs localforecast.020GiB above40GiBfloor,externalread-only.",
    }
    save(ROOT / "plan-v1.json", p)
    print("Prepared1152deterministiclinear cases;no image/model/noise draws")


def guard(p):
    for b in p["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for key, b in p["dependency"].items():
        if key == "neural103_hashes":
            for name, digest in b.items():
                assert ref(R / "src/demosaic" / name)["sha256"] == digest
        else:
            assert ref(b["path"]) == b


def summaries(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in ["position", "noise", "mode", "method"])].append(
            row["ratio_to_rect65"]
        )
    return [
        dict(
            zip(["position", "noise", "mode", "method"], key, strict=True),
            cases=len(values),
            mean=float(np.mean(values)),
            median=float(np.median(values)),
            minimum=min(values),
            maximum=max(values),
            above_one=sum(v > 1 for v in values),
            below_one=sum(v < 1 for v in values),
        )
        for key, values in groups.items()
    ]


def run():
    p = read(ROOT / "plan-v1.json")
    guard(p)
    assert ref(__file__) == p["runner"]
    o = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "launch-v1.json").exists() and read(ROOT / "launch-v1.json")["owner"] == o:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing actual owner")
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    start = time.time()
    rows = []
    with gzip.open(ROOT / "measurements-v1.jsonl.gz", "xt", compresslevel=6) as f:
        for case in p["cases"]:
            while (
                shutil.disk_usage(R).free <= 40 * 2**30
                or psutil.virtual_memory().available <= 32 * 2**30
            ):
                time.sleep(5)
            row = measure(case)
            rows.append(row)
            f.write(json.dumps(row, allow_nan=False) + "\n")
    paired = ratios(rows, p["cases"])
    assert len(rows) == 1152 and len(paired) == 768
    result = {
        "status": "completed1152analyticmeasurements-no-image-or-model-quality",
        "owner": o,
        "plan": ref(ROOT / "plan-v1.json"),
        "measurements": ref(ROOT / "measurements-v1.jsonl.gz"),
        "ratios": paired,
        "summary": summaries(paired),
        "elapsed_seconds": time.time() - start,
        "new_neural_forwards": 0,
        "new_source_noise_draws": 0,
        "scope": p["scope"],
    }
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    guard(p)
    save(ROOT / "result-v1.json", result)
    print("PASS1152analyticmeasurements/768pairedratios/16summarygroups", flush=True)


def launch():
    p = read(ROOT / "plan-v1.json")
    guard(p)
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
        child = subprocess.Popen(
            [str(R / ".venv/bin/python"), p["runner"]["path"], "run"],
            cwd=R,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    o = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(ROOT / "launch-v1.json", {"owner": o, "plan": ref(ROOT / "plan-v1.json")})
    print(json.dumps(o))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "run"])
    args = parser.parse_args()
    {"prepare": prepare, "launch": launch, "run": run}[args.phase]()
