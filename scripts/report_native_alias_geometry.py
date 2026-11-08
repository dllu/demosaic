"""Close saved input-only bins, then measure native RGB template geometry."""

import argparse
import gzip
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from green_phase_spectrum import tapered_spectrum
from native_alias_geometry import power_summary
from phase_admission_protocol import owner_live, read, ref
from report_frequency_coverage import fingerprint, summarize

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V190-native-alias-geometry-v2"
METHODS = {"V187_actual8": "V187-pooled-wave-raw", "V189_actual8": "V189-spaced-pooled-raw"}


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def lines(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def dependencies():
    dep = {}
    for version, stem in [(187, "pooled-wave"), (189, "spaced-pooled")]:
        index = REPO / f"docs/results/v{version}-{stem}-final-v1.json"
        proof = REPO / f"docs/results/v{version}-{stem}-publication-verification-v1.json"
        final, verified = read(index), read(proof)
        assert final["status"].startswith("completed-") and verified["status"].startswith("pass-")
        assert verified["publication"] == ref(index)
        for key in ["report", "figures", "notes", "publication_source"]:
            assert ref(final[key]["path"]) == final[key]
        trial = Path(final["plan"]["path"]).parent
        for name in ["wave-train", "review", "train-review-controller", "review-render-controller"]:
            assert not owner_live(read(trial / f"{name}-launch-v1.json")["owner"])
        dep[f"V{version}_publication"] = ref(index)
        dep[f"V{version}_verification"] = ref(proof)
        dep[f"V{version}_journal"] = ref(trial / "quality-observations-v1.jsonl.gz")
    diversity = ROOT.parent / "V188-selection-diversity-v1"
    assert read(diversity / "verification-v1.json")["status"].startswith("pass-")
    dep["diversity_inputs"] = ref(diversity / "input-selections-v1.jsonl.gz")
    dep["diversity_plan"] = ref(diversity / "plan-v1.json")
    dep["diversity_audit"] = ref(diversity / "verification-v1.json")
    return dep


def prepare():
    dep = dependencies()
    assert not ROOT.exists()
    assert shutil.disk_usage(REPO).free > 40.025 * 2**30
    assert psutil.virtual_memory().available > 32 * 2**30
    tests = REPO / ".cache/v190-native-alias-CPU-tests-v2.log"
    assert "20 passed" in tests.read_text()
    cases = read(dep["diversity_plan"]["path"])["cases"]
    assert len(cases) == 550 and sum(c["kind"] == "mesh" for c in cases) == 512
    ROOT.mkdir()
    names = [
        "scripts/" + name + ".py"
        for name in [
            "report_native_alias_geometry",
            "native_alias_geometry",
            "audit_native_alias_geometry",
            "green_phase_spectrum",
            "phase_admission_protocol",
            "report_frequency_coverage",
            "frequency_coverage",
            "frequency_coverage_reference",
            "local_phase_projection",
        ]
    ] + ["tests/test_native_alias_geometry.py"]
    for name in names:
        target = ROOT / "work" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    preflight = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            "-c",
            "import report_native_alias_geometry, audit_native_alias_geometry; print('PASS isolated frozen import closure')",
        ],
        cwd=REPO,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "work/scripts"), CUDA_VISIBLE_DEVICES=""),
        text=True,
        capture_output=True,
        check=True,
    )
    (ROOT / "import-preflight-v1.log").write_text(preflight.stdout)
    neural = {p.name: ref(p)["sha256"] for p in (REPO / "src/demosaic").glob("*.py")}
    assert len(neural) == 102
    plan = {
        "status": "fixed-native-template-geometry-after-closing-saved-input-only-bins-not-quality",
        "created_unix_UTC": time.time(),
        "runner": ref(ROOT / "work/scripts/report_native_alias_geometry.py"),
        "auditor": ref(ROOT / "work/scripts/audit_native_alias_geometry.py"),
        "sources": [
            dict(ref(ROOT / "work" / n), text=(ROOT / "work" / n).read_text()) for n in names
        ],
        "dependency": dep,
        "cases": cases,
        "methods": METHODS,
        "neural102_hashes": neural,
        "CPU_tests": ref(tests),
        "isolated_import_preflight": ref(ROOT / "import-preflight-v1.log"),
        "preserved_pre_main_import_failure": ref(
            ROOT.parent / "V190-native-alias-geometry-v1/launch-inspection-v1.json"
        ),
        "local_floor_GiB": 40,
        "RAM_floor_GiB": 32,
        "new_local_forecast_GiB": 0.025,
        "scope": "Completed V189 regresses mesh/quiet quality despite V188 weak-sector proximity gains. Measure exact native cameraRGB template spectra instead of folded CFA template spectra. All550 saved V187/V189 input selections and1650RAW/variance/CFA fingerprints close before target access; no new selection or parameter fitting. Bridge actual V189 bins to earlier V188spaced8 and V187bins to V188actual8. Then512 present/absent mesh records use exact clipped present-minus-empty templates,absent templates hypothetical. Sum three independent Hann/weighted-affine nativeRGB power planes. Compare native strict principal square,quarter-cycle boundary,outside closed square and radial band; two fixed square neighborhoods radius1 andceil(maxpackedaxis/65) around principal signed carriers or allfour aliases. Lift centers before native-torus neighborhood expansion; allmasks conjugate-closed,overlaps countedonce. Fouraliases cost more basis capacity and are not four independently measured signals. No footprint is achievable amplitude, a neural recovery bound, confidence, wire-family attribution or a quality/safety test: spatial mixing/modulation creates frequencies beyond these masks. Two green-phase relative signs distinguish only two classes among four lifts; analytic tests check this ambiguity for allfourCFAs. Case records share seeds/targets/noise and are not independent replications;report counts without significanceclaims. No real reference/ISO100/JPEG read,model/checkpoint load,neural inference,rendered restoration,newsource/noise draw,original/dataz access or neural-source change. All102older neural files/checkpoints/receipts remain unchanged. Allnew outputs local,externalread-only.",
    }
    save(ROOT / "plan-v1.json", plan)
    print("Prepared550saved-selections/512native-template-records;zero new model/quality")


def guard(plan):
    for binding in plan["sources"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
    for binding in plan["dependency"].values():
        assert ref(binding["path"]) == binding
    for name, digest in plan["neural102_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest


def resources(plan):
    while (
        shutil.disk_usage(REPO).free <= plan["local_floor_GiB"] * 2**30
        or psutil.virtual_memory().available <= plan["RAM_floor_GiB"] * 2**30
    ):
        print("Waiting before next CPU case for recorded resource floors", flush=True)
        time.sleep(5)


def run():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["runner"]
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        if (ROOT / "launch-v1.json").exists() and read(ROOT / "launch-v1.json")["owner"] == owner:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Missing original owner binding")
    (ROOT / "run.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    started = time.time()
    source = {}
    ids = {c["id"] for c in plan["cases"]}
    for method, label in METHODS.items():
        version = method.split("_")[0]
        source[method] = {
            r["id"]: r
            for r in lines(plan["dependency"][version + "_journal"]["path"])
            if r["method"] == label and r["id"] in ids
        }
        assert len(source[method]) == 550
    prior = {r["id"]: r for r in lines(plan["dependency"]["diversity_inputs"]["path"])}
    inputs = []
    with gzip.open(ROOT / "input-bindings-v1.jsonl.gz", "xt", compresslevel=6) as f:
        for n, case in enumerate(plan["cases"]):
            resources(plan)
            assert ref(case["arrays"]["path"]) == case["arrays"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as a:
                raw = {key: a[key] for key in ["packed", "variance", "colors"]}
            hashes = {key: fingerprint(value) for key, value in raw.items()}
            bins = {}
            for method in METHODS:
                q = source[method][case["id"]]
                assert all(
                    value == q["inputs"][key] == prior[case["id"]]["inputs"][key]
                    for key, value in hashes.items()
                )
                s = q["pooled"]["selection"]
                assert np.asarray(s["valid"]).all()
                bins[method] = np.asarray(s["bin_yx"])[0].transpose(1, 0, 2).reshape(-1, 2).tolist()
                bridge = "V187_actual8" if method == "V187_actual8" else "spaced8"
                assert bins[method] == prior[case["id"]]["bins"][bridge]
            row = {
                "index": n,
                "id": case["id"],
                "arrays": case["arrays"],
                "inputs": hashes,
                "shape": list(raw["packed"].shape[-2:]),
                "bins": bins,
            }
            inputs.append(row)
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
            if (n + 1) % 100 == 0:
                print("bound-inputs", n + 1, flush=True)
    save(
        ROOT / "input-completion-v1.json",
        {
            "status": "closed550saved-input-only-selections-before-native-target-reads",
            "journal": ref(ROOT / "input-bindings-v1.jsonl.gz"),
            "target_reads_before_close": 0,
            "input_contexts": 550,
            "input_fingerprints": 1650,
            "saved_selection_bridges": 1100,
            "owner": owner,
        },
    )
    rows, cache = [], {}
    with gzip.open(ROOT / "native-template-v1.jsonl.gz", "xt", compresslevel=6) as f:
        for case, selection in zip(plan["cases"], inputs, strict=True):
            if case["kind"] != "mesh":
                continue
            resources(plan)
            with np.load(case["arrays"]["path"], allow_pickle=False) as a:
                signal = np.maximum(a["target_present"], np.float32(0)).astype(
                    np.float64
                ) - np.maximum(a["target_empty"], np.float32(0)).astype(np.float64)
            signal_hash = fingerprint(signal)
            digest = signal_hash["sha256"]
            if digest not in cache:
                assert signal.shape == (1, 3, 512, 512)
                power = sum(abs(tapered_spectrum(plane)["spectrum"]) ** 2 for plane in signal[0])
                cache[digest] = (power, fingerprint(power))
            power, power_hash = cache[digest]
            shape = tuple(selection["shape"])
            for method in METHODS:
                for neighborhood, radius in [
                    ("near1", 1),
                    ("localwidth", math.ceil(max(shape) / 65)),
                ]:
                    row = {
                        "id": case["id"],
                        "present": case["present"],
                        "method": method,
                        "neighborhood": neighborhood,
                        "radius": radius,
                        "template_native_values": signal_hash,
                        "native_power": power_hash,
                        **power_summary(
                            power, shape, np.asarray(selection["bins"][method]), radius
                        ),
                    }
                    rows.append(row)
                    f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            if len(rows) % 400 == 0:
                print("native-template-rows", len(rows), flush=True)
    summary_rows = [
        {
            k: v
            for k, v in row.items()
            if k not in ["id", "radius", "template_native_values", "native_power"]
        }
        for row in rows
    ]
    result = {
        "status": "completed-closed-input-native-template-alias-geometry-not-quality",
        "owner": owner,
        "plan": ref(ROOT / "plan-v1.json"),
        "input_completion": ref(ROOT / "input-completion-v1.json"),
        "input_journal": ref(ROOT / "input-bindings-v1.jsonl.gz"),
        "template_journal": ref(ROOT / "native-template-v1.jsonl.gz"),
        "input_contexts": len(inputs),
        "native_template_case_records": 512,
        "rows": len(rows),
        "unique_template_values": len(cache),
        "summary": summarize(summary_rows, ["present", "method", "neighborhood"]),
        "elapsed_seconds": time.time() - started,
        "maximum_RSS_KiB": __import__("resource")
        .getrusage(__import__("resource").RUSAGE_SELF)
        .ru_maxrss,
        "new_neural_forwards": 0,
        "new_source_noise_draws": 0,
        "scope": plan["scope"],
    }
    assert len(rows) == 2048 and len(result["summary"]) == 8
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    guard(plan)
    save(ROOT / "result-v1.json", result)
    print("PASS550closed-inputs/512native-templates/2048rows;no new quality", flush=True)


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
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
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "run"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / "launch-v1.json",
        {"owner": owner, "runner": plan["runner"], "plan": ref(ROOT / "plan-v1.json")},
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
