"""Finish the already-running corrected V195 review; never launch/replay inference."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import psutil
from directional_trial_protocol import REPO, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from phase_admission_protocol import owner_live
from review_directional_response import source_guard

TAG = "review-finisher-v2"


def env(work):
    return dict(
        os.environ,
        PYTHONPATH=f"{work}/src:{work}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )


def status(value):
    path = ROOT / f"{TAG}-status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


def launch():
    plan = read(ROOT / "plan-v1.json")
    seal = source_guard(plan)
    review = read(ROOT / "review-v2-launch-v1.json")
    assert owner_live(review["owner"])
    assert not (ROOT / f"{TAG}-launch-v1.json").exists()
    runner = ROOT / f"{TAG}-worker-v1.py"
    with runner.open("x") as stream:
        stream.write(Path(__file__).read_text())
    with (ROOT / f"{TAG}-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), str(runner), "run"],
            cwd=REPO,
            env=env(seal["work"]),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / f"{TAG}-launch-v1.json",
        {
            "owner": owner,
            "runner": ref(runner),
            "review_launch": ref(ROOT / "review-v2-launch-v1.json"),
            "review_owner": review["owner"],
            "review_source": ref(ROOT / "review-source-v2.json"),
            "plan": ref(ROOT / "plan-v1.json"),
        },
    )
    print(owner)


def run():
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        try:
            launch_record = read(ROOT / f"{TAG}-launch-v1.json")
            assert launch_record["owner"] == owner and launch_record["runner"] == ref(__file__)
            break
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.2)
    else:
        raise RuntimeError("Missing finisher launch owner")
    (ROOT / f"{TAG}.claim").open("x").close()
    try:
        plan = read(ROOT / "plan-v1.json")
        seal = source_guard(plan)
        assert ref(ROOT / "review-source-v2.json") == launch_record["review_source"]
        review_owner = launch_record["review_owner"]
        while owner_live(review_owner):
            assert not (ROOT / "review-v2-failure-v1.json").exists()
            status(
                {
                    "owner": owner,
                    "status": "waiting-for-original-corrected-review-owner",
                    "review_owner": review_owner,
                }
            )
            time.sleep(2)
        assert not (ROOT / "review-v2-failure-v1.json").exists()
        scores = read(ROOT / "scores-v1.json")
        assert scores["owner"] == review_owner and scores["status"].startswith(
            "completed-V195-four-endpoint"
        )
        stages = []

        def stage(name, runner, work, args=()):
            assert not (ROOT / f"{name}-launch-v1.json").exists()
            assert ref(runner["path"]) == runner
            with (ROOT / f"{name}-v1.log").open("xb") as log:
                child = subprocess.Popen(
                    [str(REPO / ".venv/bin/python"), runner["path"], *args],
                    cwd=REPO,
                    env=env(work),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            actual = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            save(ROOT / f"{name}-launch-v1.json", {"owner": actual, "runner": runner})
            status({"owner": owner, "status": "running-" + name, "child_owner": actual})
            while child.poll() is None:
                time.sleep(1)
            assert child.returncode == 0, (name, child.returncode)
            stages.append({"name": name, "owner": actual, "runner": runner, "returncode": 0})

        stage("quality-audit", seal["auditor"], seal["work"])
        assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
        stage("reduction", seal["reducer"], seal["work"])
        stage("rendering", seal["renderer"], seal["work"])
        breakdown = read(ROOT / "directional-breakdown-v2/plan-v1.json")
        breakdown_work = str(Path(breakdown["runner"]["path"]).parents[1])
        stage("directional-breakdown", breakdown["runner"], breakdown_work, ["run"])
        exporter = read(ROOT / "export-source-v2.json")
        stage("exports", exporter["runner"], seal["work"], ["export"])
        save(
            ROOT / f"{TAG}-result-v1.json",
            {
                "status": "ready-for-actual-native-viewing-and-browser-verification-not-publication",
                "owner": owner,
                "review_owner": review_owner,
                "stages": stages,
                "scores": ref(ROOT / "scores-v1.json"),
                "quality_audit": ref(ROOT / "quality-audit-v1.json"),
                "figures": ref(ROOT / "figures-v1.json"),
                "exports": ref(ROOT / "exports-v1.json"),
                "directional_breakdown": ref(ROOT / "directional-breakdown-v2/result-v1.json"),
                "scope": "Follow original corrected review only; no inference launch or scientific prefix replay. Actual native viewing,browser pixel checks,interpretation/report and publication remain pending.",
            },
        )
        status(
            {"owner": owner, "status": "ready-for-actual-native-viewing-and-browser-verification"}
        )
    except BaseException as exc:
        save(
            ROOT / f"{TAG}-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        status({"owner": owner, "status": "failed-inspect-preserved-evidence", "error": repr(exc)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["launch", "run"])
    launch() if parser.parse_args().phase == "launch" else run()
