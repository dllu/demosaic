"""Frozen matching-only and multiharmonic RAW-wave pilots on identical inputs."""

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())


def prepare(root):
    from pilot_local_validated_waves import prepare as prepare_pilot

    from demosaic.local_validated_waves import LocalWaveConfig

    old = REPO / ".cache/experiments/local-validated-wave-pilot-v1"
    controls = {
        key: reference(old / name)
        for key, name in [
            ("plan", "plan.json"),
            ("collection", "collection.json"),
            ("model", "analytic-model-v2.json"),
            ("scores", "finite-scores-v2.json"),
        ]
    }
    study = {
        "primary_threshold": 2,
        "controls": controls,
        "question": "Separate valid-partial-fold matching from a richer thin-line waveform. H1/cardinality changes only matching; H3/cardinality permits up to three harmonics per family, with counts fixed before refinement and all harmonic columns jointly withheld-validated. All other settings/inputs remain fixed. This reused development pilot is not an independent test population.",
    }
    root.mkdir(parents=True, exist_ok=False)
    arms = {}
    for name, harmonics in [("matching", 1), ("harmonics", 3)]:
        path = prepare_pilot(
            root / name,
            config=replace(LocalWaveConfig(), harmonics=harmonics),
            study=study,
        )
        arms[name] = reference(path)
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "study_local_wave_shapes.py",
            "report_local_validated_waves.py",
            "audit_local_wave_pilot.py",
        ),
    )
    plan = {
        "arms": arms,
        "controls": controls,
        "study": study,
        "python": sys.executable,
        "work": str(work),
        "script": reference(work / "scripts/study_local_wave_shapes.py"),
        "equivalence_cases": ["source1-far-role2", "main-building-detail", "mesh-profile3879"],
        "inputs": [*controls.values(), *arms.values()],
        "frozen_files": files,
        "scope": "Check legacy H1 pixel equivalence first. Close both 24-image input-only arms before any new GT/reference analysis, then score/render/audit each. No NN/DINO/RAW/source/noise/optimizer work. Fixed original thresholds0/2/4, primary2; all protected main/cab contexts and both JPEGs retained. Existing full three-prior H1/legacy run and full V132 training remain independent and unchanged.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def equivalence(root):
    from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
    from demosaic.prediction_archive import fingerprint

    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    old = read_json(checked(plan["controls"]["plan"]))
    collection = read_json(checked(plan["controls"]["collection"]))
    rows = {r["id"]: r for r in collection["rows"]}
    results = []
    for name in plan["equivalence_cases"]:
        row = next(r for r in old["rows"] if r["id"] == name)
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            packed, colors = z["packed"][row["sample"]], z["colors"][row["sample"]]
        parent = np.load(checked(row["parent"]), allow_pickle=False)[row["sample"]]
        values, aux = restore_local_waves(
            parent,
            packed,
            colors,
            shot=row["noise"]["shot"],
            read=row["noise"]["read"],
            config=LocalWaveConfig(**old["config"], matching="legacy"),
            thresholds=tuple(old["thresholds"]),
        )
        checks = []
        for (mode, threshold), value in values.items():
            binding = rows[name]["predictions"][f"{mode}-t{threshold:g}"]
            saved = np.load(checked(binding), allow_pickle=False)
            if value.dtype != saved.dtype or value.tobytes() != saved.tobytes():
                raise ValueError(f"Legacy pixels changed: {name}/{mode}/{threshold}")
            checks.append({"saved": binding, "values": fingerprint(value), "channels": value.size})
        results.append({"case": name, "patches": aux["patches"], "checks": checks})
    write_json(
        root / "legacy-equivalence.json",
        {
            "plan": reference(root / "plan.json"),
            "cases": results,
            "all_pixel_bytes_exact": True,
            "target_or_reference_arrays_loaded": 0,
            "Torch_imported": "torch" in sys.modules,
        },
    )


def run(root):
    import psutil

    from demosaic.experiments.runtime import owner_identity

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    if reference(__file__) != plan["script"] or "torch" in sys.modules:
        raise RuntimeError("Require frozen NumPy-only controller")
    (root / "run.claim").open("x").close()
    state = {"owner": owner_identity(), "plan": reference(root / "plan.json")}
    child, identity = None, None

    def save(status, **fields):
        state.update(status=status, UTC_unix=time.time(), **fields)
        write_json(root / "status.json", state, replace=True)

    def execute(name, script, args, work, limit):
        nonlocal child, identity
        env = {
            **os.environ,
            "PYTHONPATH": str(work / "src") + ":" + str(work / "scripts"),
            "CUDA_VISIBLE_DEVICES": "",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "2",
        }
        with (root / (name + ".log")).open("x") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", str(script), *map(str, args)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            save("running-" + name, child=identity, deadline_UTC_unix=time.time() + limit)
            if child.wait(timeout=limit):
                raise RuntimeError(f"Owned {name} exited {child.returncode}")
        save("completed-" + name, child=None)

    try:
        work = Path(plan["work"])
        execute("legacy-equivalence", plan["script"]["path"], ["equivalence", root], work, 300)
        for name, binding in plan["arms"].items():
            arm = read_json(checked(binding))
            execute(
                name + "-predict",
                arm["script"]["path"],
                ["predict", arm["root"]],
                Path(arm["work"]),
                1920,
            )
        closed = [
            reference(Path(b["path"]).parent / "collection.json") for b in plan["arms"].values()
        ]
        write_json(
            root / "both-arms-closed-before-GT.json", {"collections": closed, "plan": state["plan"]}
        )
        for name, binding in plan["arms"].items():
            arm = read_json(checked(binding))
            execute(
                name + "-score",
                arm["script"]["path"],
                ["score", arm["root"]],
                Path(arm["work"]),
                300,
            )
            for phase, script in [
                ("report", "report_local_validated_waves.py"),
                ("audit", "audit_local_wave_pilot.py"),
            ]:
                execute(name + "-" + phase, work / "scripts" / script, [arm["root"]], work, 300)
        verify_plan(plan)
        save("completed-numerical-pilots-awaiting-native-review", collections=closed, child=None)
    except BaseException as error:
        if child is not None and child.poll() is None:
            try:
                current = psutil.Process(identity["pid"])
                if current.create_time() == identity["created"]:
                    os.killpg(child.pid, signal.SIGINT)
                    child.wait(timeout=30)
            except psutil.Error:
                pass
        save("failed-owned-study-preserved-no-automatic-retry", error=repr(error), child=None)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run", "equivalence"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "equivalence": equivalence}[args.mode](args.root.resolve())
