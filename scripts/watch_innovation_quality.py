"""Follow registered training, run four endpoint predictions once, finish CPU artifacts."""

import argparse
import json
import os
import shutil
import subprocess
import time

import psutil
from directional_trial_protocol import guard, launch, read, ref, require_launch, save
from phase_admission_protocol import owner_live
from review_innovation_wave import launch_review, ready, review_plan, source_guard
from train_innovation_wave import REPO, ROOT

STAGE = ROOT / "quality-controller-v1"


def prepare():
    assert not STAGE.exists()
    plan = review_plan()
    seal = source_guard(plan)
    preflight = read(ROOT / "metric-preflight-v1.json")
    assert preflight["review_source"] == ref(ROOT / "review-source-v1.json")
    assert preflight["status"].startswith("pass36saved-V195-native-metrics")
    assert read(ROOT / "input-layout-preflight-v1.json")["status"].startswith(
        "pass-all822cached-layouts"
    )
    training = ROOT / "training-controller-v1/watch-launch-v1.json"
    STAGE.mkdir()
    runner = STAGE / "worker-v1.py"
    shutil.copyfile(__file__, runner)
    save(
        STAGE / "plan-v1.json",
        {
            "status": "prepared-one-four-endpoint-review-after-registered-training-audit",
            "created_unix_UTC": time.time(),
            "root": str(STAGE),
            "work": seal["work"],
            "runner": ref(runner),
            "frozen_files": {str(runner): ref(runner)["sha256"]},
            "inputs": [
                ref(ROOT / "plan-v1.json"),
                ref(ROOT / "review-source-v1.json"),
                ref(ROOT / "metric-preflight-v1.json"),
                ref(ROOT / "input-layout-preflight-v1.json"),
                ref(training),
            ],
            "training_launch": ref(training),
            "training_owner": read(training)["owner"],
            "minimum_GiB": {"local": 40, "RAM": 32},
            "launch_RAM_GiB": 52,
            "scope": "FollowactualtrainingcontrollerPIDpluscreationtimeuntilterminal;requireboth900updatearmsandindependentfullCPUstateaudit. Launchregisteredreviewexactlyonce,4x822,thenCPUqualityaudit,reduction,fourstrictexports,eightdirectionalprojections,72nativefigures/24triplets. Neverrestartscientificprefixonobservationtimeout. Nooriginal/dataz,newsource/noisedraws,parentDINOinference,RAWdecode orqualityclaimbeforeactualviewing/comparisons. Sourceguardall104neuralsandhelpers;zeroexternalwrites,existing2GiBtrialbudget.",
        },
    )
    print("Preparedsequentialtraining-to-review-audit-rendercontroller")


def progress(value):
    temporary = STAGE / "watch-status-v1.tmp"
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(STAGE / "watch-status-v1.json")


def watch():
    receipt = read(STAGE / "plan-v1.json")
    guard(receipt, __file__)
    owner = require_launch(STAGE, "watch")
    (STAGE / "watch.claim").open("x").close()
    try:
        while owner_live(receipt["training_owner"]):
            assert not (ROOT / "training-controller-v1/watch-failure-v1.json").exists()
            progress(
                {
                    "status": "waiting-for-original-training-controller",
                    "owner": owner,
                    "child": receipt["training_owner"],
                }
            )
            time.sleep(5)
        training = read(ROOT / "training-controller-v1/watch-result-v1.json")
        assert training["owner"] == receipt["training_owner"]
        assert (
            training["status"] == "completed-both-training-arms-and-CPU-audit-quality-not-yet-run"
        )
        plan = review_plan()
        seal = source_guard(plan)
        ready(plan)
        assert not (ROOT / "review-launch-v1.json").exists()
        launch_review()
        reviewer = read(ROOT / "review-launch-v1.json")["owner"]
        while owner_live(reviewer):
            assert not (ROOT / "review-failure-v1.json").exists()
            progress(
                {
                    "status": "waiting-for-original-four-endpoint-review",
                    "owner": owner,
                    "child": reviewer,
                }
            )
            time.sleep(5)
        assert not (ROOT / "review-failure-v1.json").exists()
        scores = read(ROOT / "scores-v1.json")
        assert scores["owner"] == reviewer and scores["status"].startswith(
            "completed-V197-four-endpoint"
        )
        stages = []
        for name, key in [
            ("quality-audit", "auditor"),
            ("reduction", "reducer"),
            ("exports", "exporter"),
            ("directional-breakdown", "breakdown"),
            ("rendering", "renderer"),
        ]:
            source_guard(plan)
            binding = seal[key]
            assert ref(binding["path"]) == binding
            assert not (STAGE / f"{name}-launch-v1.json").exists()
            env = dict(
                os.environ,
                PYTHONPATH=f"{seal['work']}/src:{seal['work']}/scripts",
                CUDA_VISIBLE_DEVICES="",
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
            )
            with (STAGE / f"{name}-v1.log").open("xb") as log:
                child = subprocess.Popen(
                    [str(REPO / ".venv/bin/python"), binding["path"]],
                    cwd=REPO,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            save(STAGE / f"{name}-launch-v1.json", {"owner": child_owner, "runner": binding})
            while child.poll() is None:
                progress({"status": "running-" + name, "owner": owner, "child": child_owner})
                time.sleep(2)
            assert child.returncode == 0, (name, child.returncode)
            stages.append({"name": name, "owner": child_owner, "runner": binding, "returncode": 0})
        assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V197-four-endpoint")
        assert read(ROOT / "figures-v1.json")["native_figures"] == 72
        result = {
            "status": "ready-for-actual-native-viewing-and-browser-checks-no-publication-yet",
            "created_unix_UTC": time.time(),
            "owner": owner,
            "review_owner": reviewer,
            "stages": stages,
            "scores": ref(ROOT / "scores-v1.json"),
            "quality_audit": ref(ROOT / "quality-audit-v1.json"),
            "figures": ref(ROOT / "figures-v1.json"),
            "exports": ref(ROOT / "exports-v1.json"),
            "directional_breakdown": ref(ROOT / "directional-breakdown-v1.json"),
        }
        save(STAGE / "watch-result-v1.json", result)
        progress(result)
    except BaseException as exc:
        save(
            STAGE / "watch-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        progress({"status": "failed-inspect-original-evidence", "owner": owner, "error": repr(exc)})
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
