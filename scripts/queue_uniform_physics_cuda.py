"""Run one frozen uniform-profile probe after exact quality owners succeed.

This waiting process imports no Torch/CUDA. It never retries or changes the
training, quality protocol, model defaults or numerical acceptance limits.
"""

import argparse
import os
import subprocess
import time
from pathlib import Path

import psutil
from queue_tf32x3_cuda import (
    alive,
    dependencies_ready,
    read,
    ref,
    stop_owned,
)
from queue_tf32x3_cuda import (
    resource_ready as resource_headroom,
)
from train_directional_bank_trial import save

COMPLETE = "completed-uniform-physics-CUDA-array-gates-and-resident-timing-awaiting-review"
CPU_COMPLETE = "completed-uniform-physics-worker-CPU-switching-no-GPU-or-speed-result"
REJECTED = "rejected-uniform-physics-CUDA-array-gate-no-timing-or-integration"


def resource_ready(plan):
    return resource_headroom(dict(plan, root=plan["root_filesystem_path"]))


def guard(plan):
    gpu = read(plan["GPU_plan"]["path"])
    for item in [plan["controller"], plan["GPU_plan"], plan["CPU_preflight"], *gpu["inputs"]]:
        if ref(item["path"]) != item:
            raise ValueError("Frozen uniform-profile probe input changed: " + item["path"])
    proof = read(plan["CPU_preflight"]["path"])
    assert proof["status"] == CPU_COMPLETE and proof["CUDA_initialized"] is False
    assert proof["plan"] == plan["GPU_plan"] and proof["worker"] == gpu["worker"]
    assert not proof["resident_timings"] and len(proof["cases"]) == 8
    for case in proof["cases"]:
        assert case["difference"]["bytes_exact"]
        assert case["candidate_repeat_bytes_exact"] and case["restored_original_bytes_exact"]
        assert ref(case["arrays"]["path"]) == case["arrays"]
    return gpu


def main(path):
    os.nice(10)
    path = Path(path).resolve()
    plan = read(path)
    assert ref(__file__) == plan["controller"]
    gpu = guard(plan)
    root = Path(plan["root"])
    assert not Path(gpu["output"]).exists()
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"controller": owner, "plan": ref(path), "GPU_plan": plan["GPU_plan"]}

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        record("waiting-for-exact-training-review-closure-reference-package-exits-no-CUDA")
        started = time.monotonic()
        while not dependencies_ready(gpu):
            if time.monotonic() - started > plan["dependency_timeout_seconds"]:
                raise TimeoutError("Quality wait bound reached; no automatic retry")
            time.sleep(plan["poll_seconds"])
        guard(plan)
        record("waiting-for-stable-resource-headroom-no-CUDA")
        started, stable = time.monotonic(), None
        while True:
            now = time.monotonic()
            if now - started > plan["resource_timeout_seconds"]:
                raise TimeoutError("Resource wait bound reached; no automatic retry")
            if resource_ready(plan):
                stable = now if stable is None else stable
                if now - stable >= plan["stable_seconds"]:
                    break
            else:
                stable = None
            time.sleep(plan["poll_seconds"])
        assert dependencies_ready(gpu)
        guard(plan)
        with (root / "GPU-worker.log").open("xb") as log:
            child = subprocess.Popen(
                [gpu["python"], "-P", gpu["worker"]["path"], plan["GPU_plan"]["path"]],
                cwd=gpu["work"],
                env=dict(os.environ, **plan["worker_env"]),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-uniform-physics-CUDA-array-gates-before-timing", child=child_owner)
            started = time.monotonic()
            try:
                while child.poll() is None:
                    if time.monotonic() - started > plan["worker_timeout_seconds"]:
                        raise TimeoutError("Owned GPU probe exceeded runtime bound")
                    if not resource_ready(
                        dict(plan, launch_available_gib=plan["active_available_gib"])
                    ):
                        raise MemoryError("Shared memory/disk floor reached")
                    time.sleep(2)
            except BaseException:
                stop_owned(child, child_owner)
                raise
            assert child.returncode == 0 and not alive(child_owner)
        guard(plan)
        result = read(Path(gpu["output"]) / "status.json")
        assert result["owner"] == child_owner and result["plan"] == plan["GPU_plan"]
        if result["status"] == REJECTED:
            record(REJECTED, terminal=ref(Path(gpu["output"]) / "status.json"))
            return
        assert result["status"] == COMPLETE
        assert ref(result["receipt"]["path"]) == result["receipt"]
        receipt = read(result["receipt"]["path"])
        assert receipt["plan"] == plan["GPU_plan"] and receipt["owner"] == child_owner
        record(COMPLETE, receipt=result["receipt"])
    except BaseException as error:
        record("failed-uniform-physics-CUDA-queue-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    main(p.parse_args().plan)
