"""Wait for matched training, then run all six fixed endpoint reviews."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from review_v146_window_transfer import relocated_controller_source
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def prepare(root, revision=1):
    training = read(root / "plan-v1.json")
    guard(training)
    work = root / f"postprocess-v{revision}/scripts"
    work.mkdir(parents=True, exist_ok=False)
    for name in (
        "score_delivered_objective_trial.py",
        "audit_delivered_objective_trial.py",
        "render_delivered_objective_trial.py",
        "report_checkpoint_pilot.py",
        "report_late_spectral_mixed_quiet.py",
        "review_v146_window_transfer.py",
        "audit_delivered_objective_training.py",
    ):
        shutil.copyfile(REPO / "scripts" / name, work / name)
    runner = work / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    stages = [
        {
            "name": "training-state-audit",
            "argv": [
                str(work / "audit_delivered_objective_training.py"),
                str(root),
                "--states-only",
            ],
            "result": str(root / "independent-training-state-audit-v1.json"),
        },
        {
            "name": "review",
            "argv": [str(root / "review-source-v1.py"), "worker", str(root)],
            "result": str(root / "review-result-v1.json"),
        },
    ]
    stages += [
        {"name": name, "argv": [str(work / script), str(root)], "result": str(root / result)}
        for name, script, result in (
            (
                "training-audit",
                "audit_delivered_objective_training.py",
                "independent-training-audit-v1.json",
            ),
            ("scores", "score_delivered_objective_trial.py", "scores-v1.json"),
            (
                "metric-audit",
                "audit_delivered_objective_trial.py",
                "independent-metrics-audit-v1.json",
            ),
            ("render", "render_delivered_objective_trial.py", "figures-v1.json"),
        )
    ]
    inputs = [
        ref(root / p)
        for p in (
            "plan-v1.json",
            "review-plan-v1.json",
            "quality-design-v1.json",
            "review-source-v1.py",
        )
    ]
    inputs += [
        ref(root.parent / p)
        for p in (
            "collaborative-detail-v1/transfer-v1.py",
            "V144-V145-photo-supplement-v1/operator-v2.py",
            "collaborative-detail-v1/audit-transfer-v1.py",
        )
    ]
    save(
        root / f"postprocess-plan-v{revision}.json",
        {
            "root": str(root),
            "runner": ref(runner),
            "work": str(work),
            "python": str(REPO / ".venv/bin/python"),
            "training_plan": ref(root / "plan-v1.json"),
            "stages": stages,
            "inputs": inputs,
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.glob("*.py")},
            "new_component_forwards": 4932,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Six fixed final paired endpoints; retained798 plus24 ADC controls, independent array reductions and84 native figures with independent pixel checks. Actual native viewing remains required. Observed polling-time budget caps intervals at5s so suspended controllers do not charge a whole user pause.",
        },
    )


def controller(root, revision=1):
    path = root / f"postprocess-plan-v{revision}.json"
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["runner"]
    (root / f"postprocess-v{revision}.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None
    try:
        observed, last = 0.0, time.monotonic()
        while True:
            status = read(root / "status-v1.json")
            if status["status"] == "completed-matched-training-awaiting-fixed-quality-review":
                break
            assert status["status"] != "failed-preserved-no-automatic-retry", status
            assert live(status["owner"])
            save(
                root / "postprocess-status-v1.json",
                {**state, "status": "waiting-for-fixed-matched-training"},
            )
            time.sleep(2)
            now = time.monotonic()
            paused = (
                status.get("child")
                and live(status["child"])
                and psutil.Process(status["child"]["pid"]).status() == psutil.STATUS_STOPPED
            )
            if not paused:
                observed += min(now - last, 5.0)
            last = now
            assert observed < 14400
        training = read(plan["training_plan"]["path"])
        for stage in plan["stages"]:
            guard(plan)
            guard(training)
            while psutil.virtual_memory().available < 52 * 2**30:
                save(
                    root / "postprocess-status-v1.json",
                    {**state, "status": "waiting-for-headroom", "stage": stage["name"]},
                )
                time.sleep(2)
            env = dict(
                os.environ,
                PYTHONPATH=f"{training['work']}/src:{plan['work']}:{training['work']}/scripts",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
            )
            with (root / f"postprocess-{stage['name']}-v{revision}.log").open("x") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", *stage["argv"]],
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "postprocess-status-v1.json",
                    {
                        **state,
                        "status": "running-fixed-stage",
                        "stage": stage["name"],
                        "child": owner,
                    },
                )
                observed, last = 0.0, time.monotonic()
                while child.poll() is None:
                    time.sleep(2)
                    now = time.monotonic()
                    if live(owner) and psutil.Process(child.pid).status() != psutil.STATUS_STOPPED:
                        observed += min(now - last, 5.0)
                    last = now
                    assert observed < 1800, stage["name"]
                assert child.returncode == 0, stage["name"]
            assert not live(owner)
            state["completed"][stage["name"]] = {
                "result": ref(stage["result"]),
                "owner": owner,
                "owner_exited": True,
            }
        save(
            root / "postprocess-status-v1.json",
            {**state, "status": "completed-audited-paired-arrays-awaiting-human-native-viewing"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "postprocess-status-v1.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else controller)(args.root.resolve(), args.revision)
