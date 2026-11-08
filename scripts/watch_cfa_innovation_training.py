"""Run the registered CFA training owner once, then its CPU state audit."""

import argparse
import os
import subprocess
import time

import psutil
from directional_trial_protocol import freeze, guard, launch, read, ref, require_launch, save
from phase_admission_protocol import owner_live
from train_cfa_innovation_wave import MODES, REPO, ROOT, ready

STAGE = ROOT / "training-controller-v1"


def prepare():
    ready()
    assert not STAGE.exists()
    trial = read(ROOT / "plan-v1.json")
    guard(trial)
    STAGE.mkdir()
    work, sources = freeze(STAGE, ["watch_cfa_innovation_training.py"])
    save(
        STAGE / "plan-v1.json",
        {
            "status": "prepared-registered-CFA-training-and-audit",
            "created_unix_UTC": time.time(),
            "root": str(STAGE),
            "work": str(work),
            "runner": ref(work / "scripts/watch_cfa_innovation_training.py"),
            "trial_plan": ref(ROOT / "plan-v1.json"),
            "inputs": [ref(ROOT / "plan-v1.json")],
            "frozen_files": sources,
            "minimum_GiB": {"local": 40, "RAM": 32},
            "launch_RAM_GiB": 52,
            "scope": "RunCFAexactlyonce,usingboundtrainingrunner. PollactualPIDpluscreationtime;liveworkerwithoutresultcontinueswaiting. Neverrestartonobservationtimeout. RequirecorrectterminalresultbeforeCPUaudit. Runfrozentrainingauditonceaftertrainingterminal. Noquality/inference/promotionclaim.",
        },
    )
    print("Preparedsequentialregisteredtrainingcontroller")


def progress(value):
    temporary = STAGE / "watch-status-v1.tmp"
    import json

    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(STAGE / "watch-status-v1.json")


def watch():
    plan = read(STAGE / "plan-v1.json")
    guard(plan, __file__)
    owner = require_launch(STAGE, "watch")
    (STAGE / "watch.claim").open("x").close()
    try:
        workers = {}
        for mode in MODES:
            path = ROOT / f"{mode}-launch-v1.json"
            if not path.exists():
                launch(ROOT, "train", mode=mode)
            child = read(path)["owner"]
            workers[mode] = child
            while owner_live(child):
                progress(
                    {
                        "status": "waiting-for-specific-training-owner",
                        "owner": owner,
                        "mode": mode,
                        "child": child,
                    }
                )
                time.sleep(5)
            assert not (ROOT / f"{mode}-train-failure-v1.json").exists()
            completed = read(ROOT / f"{mode}-train-result-v1.json")
            assert completed["owner"] == child and completed["mode"] == mode
            assert completed["status"] == "completed-V198-CFA-wave-head-above-frozen-V195-WholeEMA"
            assert completed["updates"] == 900
        trial = read(ROOT / "plan-v1.json")
        guard(trial)
        assert (
            not (STAGE / "audit-launch-v1.json").exists()
            and not (ROOT / "training-audit-v1.json").exists()
        )
        with (STAGE / "audit-v1.log").open("xb") as log:
            process = subprocess.Popen(
                [str(REPO / ".venv/bin/python"), trial["auditor"]["path"]],
                cwd=REPO,
                env=dict(
                    os.environ,
                    CUDA_VISIBLE_DEVICES="",
                    OPENBLAS_NUM_THREADS="1",
                    OMP_NUM_THREADS="1",
                    PYTHONPATH=f"{trial['work']}/src:{trial['work']}/scripts",
                ),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        auditor = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
        save(STAGE / "audit-launch-v1.json", {"owner": auditor, "auditor": trial["auditor"]})
        while owner_live(auditor):
            progress(
                {"status": "waiting-for-specific-CPU-audit-owner", "owner": owner, "child": auditor}
            )
            time.sleep(2)
        assert process.wait() == 0
        audit = read(ROOT / "training-audit-v1.json")
        assert audit["status"].startswith("pass-V198-full-CFA-trace")
        result = {
            "status": "completed-CFA-training-and-CPU-audit-quality-not-yet-run",
            "created_unix_UTC": time.time(),
            "owner": owner,
            "workers": workers,
            "auditor_owner": auditor,
            "training_audit": ref(ROOT / "training-audit-v1.json"),
        }
        save(STAGE / "watch-result-v1.json", result)
        progress(result)
    except BaseException as exc:
        save(
            STAGE / "watch-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "watch"])
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "launch":
        print(launch(STAGE, "watch"))
    else:
        watch()
