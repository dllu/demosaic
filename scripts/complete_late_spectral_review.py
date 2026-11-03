"""Queue a frozen late-spectral review after its fixed training horizon."""

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


def prepare(root):
    training = read(root / "plan-v1.json")
    guard(training)
    work = root / "postprocess-v1/scripts"
    work.mkdir(parents=True, exist_ok=False)
    names = [
        "score_late_spectral_trial.py",
        "audit_late_spectral_trial.py",
        "render_late_spectral_trial.py",
        "audit_late_spectral_figures.py",
        "report_late_spectral_mixed_quiet.py",
        "report_checkpoint_pilot.py",
        "review_v146_window_transfer.py",
    ]
    for name in names:
        shutil.copyfile(REPO / "scripts" / name, work / name)
    runner = work / Path(__file__).name
    runner.write_text(relocated_controller_source(Path(__file__).read_text(), REPO))
    stages = [
        {
            "name": "review",
            "argv": [str(root / "review-source-v1.py"), "worker", str(root)],
            "result": str(root / "review-result-v1.json"),
        },
        *(
            {"name": name, "argv": [str(work / filename), str(root)], "result": str(root / result)}
            for name, filename, result in [
                ("scores", "score_late_spectral_trial.py", "scores-v1.json"),
                (
                    "metric-audit",
                    "audit_late_spectral_trial.py",
                    "independent-metrics-audit-v1.json",
                ),
                ("render", "render_late_spectral_trial.py", "figures-v1.json"),
                (
                    "pixel-audit",
                    "audit_late_spectral_figures.py",
                    "independent-figures-audit-v1.json",
                ),
            ]
        ),
        {
            "name": "mixed-controls",
            "argv": [str(root / "mixed-quiet-v1/operator-v1.py"), "worker", str(root)],
            "result": str(root / "mixed-quiet-v1/result-v1.json"),
        },
        {
            "name": "mixed-report",
            "argv": [str(work / "report_late_spectral_mixed_quiet.py"), str(root)],
            "result": str(root / "mixed-quiet-v1/report-v1.json"),
        },
    ]
    save(
        root / "postprocess-plan-v1.json",
        {
            "root": str(root),
            "work": str(work),
            "runner": ref(runner),
            "python": str(REPO / ".venv/bin/python"),
            "training_plan": ref(root / "plan-v1.json"),
            "stages": stages,
            "inputs": [
                ref(root / p)
                for p in (
                    "plan-v1.json",
                    "review-plan-v1.json",
                    "mixed-quiet-v1/plan-v1.json",
                    "mixed-quiet-v1/scope-clarification-v1.json",
                )
            ]
            + [ref(root / "review-source-v1.py"), ref(root / "mixed-quiet-v1/operator-v1.py")],
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.glob("*.py")},
            "new_parent_DINO_forwards": 32,
            "new_module_forwards": 1596,
            "new_noise_draws_in_postprocess": 0,
            "scope": "Wait for fixed1000; execute both endpoints, audits, native figures and32 prepared mixed controls. No retraining, endpoint selection or automatic retries. Actual human native viewing and interpretation remain required after completion.",
        },
    )


def controller(root):
    path = root / "postprocess-plan-v1.json"
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["runner"]
    (root / "postprocess.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = child_owner = None
    try:
        start = time.monotonic()
        while True:
            training_status = read(root / "status-v1.json")
            if training_status["status"] == "completed-training-awaiting-quality-review":
                break
            assert training_status["status"] != "failed-preserved-no-automatic-retry", (
                training_status
            )
            assert live(training_status["owner"]) and time.monotonic() - start < 10800
            save(
                root / "postprocess-status-v1.json",
                {**state, "status": "waiting-for-fixed-training-horizon"},
            )
            time.sleep(5)
        training = read(plan["training_plan"]["path"])
        for stage in plan["stages"]:
            guard(plan)
            guard(training)
            start = time.monotonic()
            while psutil.virtual_memory().available < 52 * 2**30:
                assert time.monotonic() - start < 7200
                save(
                    root / "postprocess-status-v1.json",
                    {**state, "status": "waiting-for-headroom", "stage": stage["name"]},
                )
                time.sleep(5)
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
            with (root / f"postprocess-{stage['name']}-v1.log").open("x") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", *stage["argv"]],
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "postprocess-status-v1.json",
                    {
                        **state,
                        "status": "running-frozen-stage",
                        "stage": stage["name"],
                        "child": child_owner,
                    },
                )
                assert child.wait(timeout=1800) == 0, stage["name"]
            assert not live(child_owner)
            state["completed"][stage["name"]] = {
                "result": ref(stage["result"]),
                "owner": child_owner,
                "owner_exited": True,
            }
        save(
            root / "postprocess-status-v1.json",
            {**state, "status": "completed-audited-arrays-awaiting-human-native-viewing"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
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
    args = parser.parse_args()
    (prepare if args.mode == "prepare" else controller)(args.root.resolve())
