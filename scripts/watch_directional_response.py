"""One-shot V195 controller: terminal training -> CPU audit -> quality -> native boards."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import psutil
from directional_trial_protocol import MODES, REPO, guard, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from phase_admission_protocol import owner_live


def status(value):
    path = ROOT / "controller-status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


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


def launch():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert not (ROOT / "controller-launch-v1.json").exists()
    runner = ROOT / "controller-work-v1.py"
    with runner.open("x") as stream:
        stream.write(Path(__file__).read_text())
    with (ROOT / "controller-v1.log").open("xb") as log:
        child = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), str(runner), "run"],
            cwd=REPO,
            env=env(plan["work"]),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    save(
        ROOT / "controller-launch-v1.json",
        {
            "owner": owner,
            "runner": ref(runner),
            "plan": ref(ROOT / "plan-v1.json"),
            "review_source": ref(ROOT / "review-source-v1.json"),
        },
    )
    print(owner)


def run():
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        try:
            launch_record = read(ROOT / "controller-launch-v1.json")
            assert launch_record["owner"] == owner and launch_record["runner"] == ref(__file__)
            break
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.2)
    else:
        raise RuntimeError("Missing controller launch owner")
    (ROOT / "controller.claim").open("x").close()
    try:
        plan = read(ROOT / "plan-v1.json")
        guard(plan)
        seal = read(ROOT / "review-source-v1.json")
        for name, digest in seal["frozen_files"].items():
            assert ref(name)["sha256"] == digest
        owners = {mode: read(ROOT / f"{mode}-launch-v1.json")["owner"] for mode in MODES}
        while any(owner_live(value) for value in owners.values()):
            for mode in MODES:
                assert not (ROOT / f"{mode}-train-failure-v1.json").exists(), mode
            status(
                {
                    "owner": owner,
                    "status": "waiting-for-original-training-owners",
                    "training_owners": owners,
                }
            )
            time.sleep(2)
        for mode in MODES:
            result = read(ROOT / f"{mode}-train-result-v1.json")
            assert result["owner"] == owners[mode] and result["status"].startswith(
                "completed-V195-"
            )
        children = []

        def stage(name, runner, work, args=()):
            assert not (ROOT / f"{name}-launch-v1.json").exists()
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
            children.append(
                {"name": name, "owner": actual, "runner": runner, "returncode": child.returncode}
            )

        stage("training-audit", plan["auditor"], plan["work"])
        assert read(ROOT / "training-audit-v1.json")["status"].startswith("pass-V195-two-matched")
        stage("review-launcher", seal["reviewer"], seal["work"], ["launch"])
        review_owner = read(ROOT / "review-launch-v1.json")["owner"]
        while owner_live(review_owner):
            assert not (ROOT / "review-failure-v1.json").exists()
            status(
                {
                    "owner": owner,
                    "status": "waiting-for-original-review-owner",
                    "review_owner": review_owner,
                }
            )
            time.sleep(2)
        scores = read(ROOT / "scores-v1.json")
        assert scores["owner"] == review_owner and scores["status"].startswith(
            "completed-V195-four-endpoint"
        )
        stage("quality-audit", seal["auditor"], seal["work"])
        assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
        stage("reduction", seal["reducer"], seal["work"])
        stage("rendering", seal["renderer"], seal["work"])
        save(
            ROOT / "controller-result-v1.json",
            {
                "status": "ready-for-actual-native-viewing-not-publication",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "children": children,
                "training_owners": owners,
                "review_owner": review_owner,
                "scores": ref(ROOT / "scores-v1.json"),
                "training_audit": ref(ROOT / "training-audit-v1.json"),
                "quality_audit": ref(ROOT / "quality-audit-v1.json"),
                "figures": ref(ROOT / "figures-v1.json"),
                "scope": "No scientific worker restart or prefix replay. Actual native viewing,diagnostic interpretation,exports,report and publication remain pending.",
            },
        )
        status({"owner": owner, "status": "ready-for-actual-native-viewing-not-publication"})
    except BaseException as exc:
        save(
            ROOT / "controller-failure-v1.json",
            {"owner": owner, "error": repr(exc), "time_UTC": time.time()},
        )
        status({"owner": owner, "status": "failed-inspect-preserved-evidence", "error": repr(exc)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["launch", "run"])
    launch() if parser.parse_args().phase == "launch" else run()
