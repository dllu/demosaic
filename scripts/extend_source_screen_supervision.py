"""Adopt the unchanged owned source-screen worker with an explicit eight-hour bound."""

import argparse
import os
import shutil
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def owned(identity):
    try:
        process = psutil.Process(identity["pid"])
        if (
            process.create_time() == identity["created"]
            and process.status() != psutil.STATUS_ZOMBIE
        ):
            return process
    except psutil.NoSuchProcess:
        pass
    return None


def prepare(screen_root, output):
    screen = read(screen_root / "plan.json")
    guard(screen)
    state = read(screen_root / "controller-status.json")
    assert state["status"] == "running-source-screen-GPU"
    controller, child = owned(state["controller"]), owned(state["child"])
    assert controller and child and child.ppid() == controller.pid
    assert os.getsid(child.pid) == child.pid
    assert controller.cmdline()[3] == "run" and child.cmdline()[3] == "worker"
    output = output.resolve()
    assert output.is_relative_to(REPO / ".cache")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(
        screen_root / "controller-status.json", output / "previous-controller-status.json"
    )
    shutil.copyfile(__file__, output / "supervisor.py")
    save(
        output / "plan.json",
        {
            "root": str(output),
            "screen_plan": ref(screen_root / "plan.json"),
            "previous_status": ref(output / "previous-controller-status.json"),
            "previous_controller": state["controller"],
            "child": state["child"],
            "controller_command": controller.cmdline(),
            "child_command": child.cmdline(),
            "previous_runtime_seconds": 21600,
            "runtime_seconds_from_original_worker_start": 28800,
            "minimum_available_RAM_GiB": 24,
            "root_reserve_GiB": 64,
            "external_reserve_GiB": 500,
            "operator": ref(output / "supervisor.py"),
            "scope": "Operational supervision handoff only: original worker/source/plan/checkpoint/scoring/inputs and resource floors remain unchanged. Terminate only the exact old supervisor, then supervise the same already-running independent-session worker. No restart, extra CUDA worker, retry, training, timing or quality comparison.",
        },
    )
    print(ref(output / "plan.json"))


def run(plan_path):
    plan = read(plan_path)
    assert ref(__file__) == plan["operator"]
    assert ref(plan["screen_plan"]["path"]) == plan["screen_plan"]
    assert ref(plan["previous_status"]["path"]) == plan["previous_status"]
    screen = read(plan["screen_plan"]["path"])
    guard(screen)
    root = Path(plan["root"])
    (root / "supervisor.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "supervisor": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "child": plan["child"],
    }

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def resources():
        return (
            psutil.virtual_memory().available >= 24 * 2**30
            and shutil.disk_usage(root).free >= 64 * 2**30
            and shutil.disk_usage("/mnt/external").free >= 500 * 2**30
        )

    def stop_worker():
        process = owned(plan["child"])
        if process is None:
            return
        identities = [
            {"pid": p.pid, "created": p.create_time()} for p in process.children(recursive=True)
        ] + [plan["child"]]
        processes = []
        for identity in identities:
            p = owned(identity)
            if p:
                p.terminate()
                processes.append(p)
        psutil.wait_procs(processes, timeout=5)
        for identity in identities:
            p = owned(identity)
            if p:
                p.kill()

    adopted = False
    try:
        controller, child = owned(plan["previous_controller"]), owned(plan["child"])
        assert controller and child and child.ppid() == controller.pid
        assert (
            controller.cmdline() == plan["controller_command"]
            and child.cmdline() == plan["child_command"]
        )
        assert os.getsid(child.pid) == child.pid and resources()
        record("ready-to-adopt-existing-worker")
        # SIGTERM uses the old supervisor's default handler; the child owns a
        # separate session, so this does not signal the worker or its loaders.
        controller.terminate()
        controller.wait(timeout=10)
        assert owned(plan["previous_controller"]) is None
        assert owned(plan["child"]) is not None
        adopted = True
        record("supervising-same-original-source-worker")
        while owned(plan["child"]) is not None:
            assert time.time() - plan["child"]["created"] < 28800, (
                "Eight-hour original-start runtime bound"
            )
            assert resources(), "Unchanged source-screen resource floor"
            time.sleep(2)
        receipt_path = Path(screen["work"]) / "source-scores/receipt.json"
        receipt = read(receipt_path)
        assert receipt["owner"] == plan["child"] and receipt["plan"] == plan["screen_plan"]
        assert receipt["sources_scored"] == 88508 and receipt["cases"] == 177016
        assert receipt["actual_forwards"] == receipt["DINO_calls"] == 22128
        assert (
            not receipt["engineering_only"]
            and receipt["state_config_parameters_RNG_inputs_preserved"]
        )
        assert ref(receipt["scores"]["path"]) == receipt["scores"]
        guard(screen)
        record(
            "completed-original-source-worker-awaiting-visual-curation", receipt=ref(receipt_path)
        )
    except BaseException as error:
        if adopted:
            stop_worker()
        record("failed-supervision-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output
        prepare(args.path.resolve(), args.output)
    else:
        run(args.path.resolve())
