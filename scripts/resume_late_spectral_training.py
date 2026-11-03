"""Adopt the exact suspended V147 worker after a user-requested pause."""

import argparse
import os
import shutil
import signal
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live


def main(root):
    point = root / "resume-v1"
    path = point / "plan-v1.json"
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["runner"]
    training = read(plan["training_plan"]["path"])
    guard(training)
    worker = plan["adopted_worker"]
    assert live(worker) and psutil.Process(worker["pid"]).status() == psutil.STATUS_STOPPED
    assert all(not live(row["owner"]) for row in plan["replaced_controllers"])
    assert psutil.virtual_memory().available > 52 * 2**30
    assert (
        shutil.disk_usage(root).free > 96 * 2**30
        and shutil.disk_usage("/mnt/external").free > 208 * 2**30
    )
    (point / "training-controller.claim").open("x").close()
    state = {
        "plan": ref(root / "plan-v1.json"),
        "resume_plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {"smoke": ref(root / "smoke-result-v1.json")},
        "phase": "train",
        "child": worker,
    }
    resumed = False
    try:
        save(root / "status-v1.json", {**state, "status": "running-declared-phase"})
        began = time.monotonic()
        os.kill(worker["pid"], signal.SIGCONT)
        resumed = True
        save(
            point / "continued-v1.json",
            {
                "status": "continued-original-worker-without-replay",
                "owner": worker,
                "controller": state["owner"],
                "recorded_unix_UTC": time.time(),
                "last_reported_progress": read(root / "train-progress-v1.json"),
                "new_worker_launches": 0,
                "new_noise_draws_by_controller": 0,
                "new_model_forwards_by_controller": 0,
            },
        )
        while live(worker):
            assert time.monotonic() - began < 7200, "Adopted worker timeout"
            assert psutil.Process(worker["pid"]).status() != psutil.STATUS_STOPPED, (
                "Worker unexpectedly suspended"
            )
            time.sleep(2)
        result = read(root / "train-result-v1.json")
        assert result["owner"] == worker and result["steps"] == 1000
        assert result["plan"] == ref(root / "plan-v1.json")
        assert result["counts"] == {
            "parent_root": 990,
            "DINO": 990,
            "module_training": 1000,
            "optimizer_updates": 1000,
            "adopted_parent_batches": 10,
        }
        assert result["parent_model_before"] == result["parent_model_after"]
        assert result["DINO_before"] == result["DINO_after"]
        guard(training)
        guard(plan)
        state["completed"]["train"] = ref(root / "train-result-v1.json")
        save(
            point / "completion-v1.json",
            {
                "status": "completed-adopted-original-worker",
                "plan": ref(path),
                "result": ref(root / "train-result-v1.json"),
                "worker_owner": worker,
                "worker_exited": True,
                "worker_exit_code": None,
                "scope": "Reparented worker is not this controller's child; terminal state and its complete verified result are observed, no exit code inferred. Exact in-memory training continued without checkpoint reload or replay.",
            },
        )
        save(
            root / "status-v1.json",
            {**state, "status": "completed-training-awaiting-quality-review"},
        )
    except BaseException as error:
        if resumed and live(worker):
            os.kill(worker["pid"], signal.SIGSTOP)
        save(
            root / "status-v1.json",
            {
                **state,
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "worker_suspended_if_live": resumed and live(worker),
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
