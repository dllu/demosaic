"""Yield one owned live training process until another original controller exits."""

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil


def read(path):
    return json.loads(Path(path).read_text())


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def matching_process(owner):
    try:
        process = psutil.Process(owner["pid"])
        if process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE:
            return process
    except psutil.NoSuchProcess:
        pass
    return None


def check_state(state, declaration, *, child=False):
    if state["plan"] != declaration["plan"] or state["controller"] != declaration["controller"]:
        raise ValueError("Training controller or source plan differs")
    if child and (
        state.get("phase") != "train"
        or state.get("arm") != declaration["arm"]
        or state.get("child") != declaration["child"]
    ):
        raise ValueError("Yield target is not the declared original training worker")


@contextlib.contextmanager
def yielded(owner):
    process = matching_process(owner)
    if process is None:
        raise RuntimeError("Owned training worker is no longer live")
    if process.status() == psutil.STATUS_STOPPED:
        raise RuntimeError("Worker was already stopped; this coordinator does not own that stop")
    suspended_here = False
    try:
        suspended_here = True
        process.suspend()
        began = time.monotonic()
        while process.status() != psutil.STATUS_STOPPED:
            if time.monotonic() - began > 2:
                raise RuntimeError("Worker stop could not be confirmed")
            time.sleep(0.05)
        yield process
    finally:
        if suspended_here and (current := matching_process(owner)) is not None:
            current.resume()
            began = time.monotonic()
            while (
                current := matching_process(owner)
            ) is not None and current.status() == psutil.STATUS_STOPPED:
                if time.monotonic() - began > 2:
                    raise RuntimeError("Owned worker resume could not be confirmed")
                time.sleep(0.05)


def log_snapshot(path):
    value = Path(path).read_bytes()
    complete = value[: value.rfind(b"\n") + 1]
    rows = [json.loads(row) for row in complete.splitlines()]
    train = [row for row in rows if row.get("event") == "train"]
    return {
        "path": str(Path(path).absolute()),
        "bytes": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
        "last_logged_step": train[-1]["step"],
    }


def main(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Coordination must not initialize CUDA or import Torch")
    plan = read(path)
    root = Path(path).absolute().parent
    (root / "coordinator.claim").open("x").close()
    for item in plan["inputs"]:
        if binding(item["path"]) != item:
            raise ValueError("Coordination source binding differs")
    if binding(__file__) != plan["source"]:
        raise ValueError("Coordinator code differs")
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    owner = {"pid": os.getpid(), "created": process.create_time()}
    state = {"owner": owner, "plan": binding(path)}

    def record(status, **details):
        state.update(
            status=status,
            recorded_local=datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            **details,
        )
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
        temporary.replace(root / "status.json")

    def interrupted(signum, frame):
        raise SystemExit(f"Coordinator interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    target, priority = plan["yield_training"], plan["priority_training"]
    began = None
    try:
        target_state = read(target["status"])
        check_state(target_state, target, child=True)
        check_state(read(priority["status"]), priority)
        if matching_process(target["controller"]) is None:
            raise RuntimeError("Yielded worker's original controller is not live")
        if matching_process(priority["controller"]) is None:
            record("completed-yield-unnecessary-priority-controller-already-exited")
            return
        worker = matching_process(target["child"])
        if worker is None or worker.cmdline() != plan["expected_worker_command"]:
            raise RuntimeError("Exact owned training-worker command differs")
        remaining = plan["yield_training_wall_limit_seconds"] - (
            time.time() - target["child"]["created"]
        )
        maximum = min(
            plan["maximum_yield_seconds"], remaining - plan["reserved_remaining_training_seconds"]
        )
        if maximum <= 0:
            raise RuntimeError("Insufficient remaining wall-time margin for a temporary yield")
        record(
            "confirming-owned-training-yield",
            yielded_worker=target["child"],
            priority_controller=priority["controller"],
        )
        with yielded(target["child"]):
            began = time.monotonic()
            externally_resumed = False
            before = log_snapshot(target["log"])
            record(
                "yielded-training-until-original-priority-controller-exits",
                stopped_log=before,
                maximum_yield_seconds=maximum,
                held_RSS_bytes=worker.memory_info().rss,
            )
            while matching_process(priority["controller"]) is not None:
                check_state(read(priority["status"]), priority)
                current = matching_process(target["child"])
                if current is None:
                    raise RuntimeError("Yielded training worker disappeared; no restart attempted")
                if current.status() != psutil.STATUS_STOPPED:
                    externally_resumed = True
                    record("yield-ended-externally", observed_worker_status=current.status())
                    break
                if time.monotonic() - began >= maximum:
                    record("yield-time-bound-reached-resuming-same-worker")
                    break
                time.sleep(10)
            after = log_snapshot(target["log"])
            if before != after and not externally_resumed:
                raise RuntimeError("Training log changed while its worker was confirmed stopped")
            final_priority = read(priority["status"])
            check_state(final_priority, priority)
            record(
                "resuming-original-training-worker",
                priority_terminal_status=final_priority["status"],
                log_unchanged_during_yield=before == after,
                externally_resumed=externally_resumed,
                yielded_seconds=time.monotonic() - began,
            )
        current = matching_process(target["child"])
        record(
            "completed-yield-original-training-worker-resumed",
            worker_live=current is not None,
            observed_worker_status=current.status() if current else None,
            yielded_seconds=time.monotonic() - began,
            new_model_constructions=0,
            new_neural_forwards=0,
            optimizer_restarts=0,
            RAW_decodes=0,
        )
    except BaseException as error:
        record(
            "failed-coordination-original-worker-resume-attempted",
            error=repr(error),
            worker_live=matching_process(target["child"]) is not None,
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan.resolve())
