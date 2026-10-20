"""CPU array/native preparation after the exact frozen CUDA controller exits."""

import argparse
import os
import subprocess
import time
from pathlib import Path

import psutil
from queue_tf32x3_cuda import alive, stop_owned
from queue_uniform_physics_cuda import COMPLETE, REJECTED, resource_ready
from train_directional_bank_trial import read, ref, save


def ready(plan):
    state = read(plan["GPU_status"])
    if state["controller"] != plan["GPU_owner"] or state["plan"] != plan["GPU_controller_plan"]:
        raise ValueError("Exact GPU controller identity/plan changed")
    if ref(state["plan"]["path"]) != state["plan"]:
        raise ValueError("GPU controller plan bytes changed")
    if state["status"].startswith("failed-"):
        raise RuntimeError("GPU dependency failed; no review retry")
    if alive(plan["GPU_owner"]):
        return False
    if state["status"] not in (COMPLETE, REJECTED):
        raise RuntimeError("GPU owner exited without a completed/rejected terminal")
    if state.get("child") and alive(state["child"]):
        raise RuntimeError("Exact GPU worker remains live")
    return True


def guard(plan):
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    proof = read(plan["CPU_preflight"]["path"])
    assert (
        proof["status"]
        == "completed-uniform-physics-review-historical-CPU-integration-no-current-GPU-result"
    )
    assert proof["historical_RGB_values_independently_reduced"] == 7077888
    assert proof["live_current_GPU_refused_before_output"]
    assert proof["native_panels_match_historical_pixels"] == 72
    assert proof["native_board_cells"] == 48 and proof["native_triplets"] == 24
    assert proof["manual_review_completed"] is False and proof["CUDA_initialized"] is False


def main(path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    os.nice(10)
    path = Path(path).resolve()
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["driver"]
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    state = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
    }

    def record(status, **values):
        state.update(status=status, updated_unix=time.time(), **values)
        save(root / "status.json", state)

    try:
        record("waiting-for-exact-uniform-physics-CUDA-controller-exit-no-Torch-CUDA")
        started = time.monotonic()
        while not ready(plan):
            if time.monotonic() - started > plan["dependency_timeout_seconds"]:
                raise TimeoutError("GPU wait bound reached; no review retry")
            time.sleep(5)
        started = time.monotonic()
        while not resource_ready(plan):
            if time.monotonic() - started > plan["resource_timeout_seconds"]:
                raise TimeoutError("CPU review resource wait bound reached")
            time.sleep(5)
        for stage, script, arguments in [
            (
                "arrays",
                plan["array_driver"],
                [plan["GPU_controller_plan"]["path"], plan["array_output"]],
            ),
            (
                "native",
                plan["native_driver"],
                [str(Path(plan["array_output"]) / "array-audit.json"), plan["native_output"]],
            ),
        ]:
            assert ready(plan)
            guard(plan)
            if stage == "native" and read(plan["GPU_status"])["status"] == REJECTED:
                record(
                    "audited-CUDA-array-rejection-no-native-package-or-integration",
                    arrays=ref(Path(plan["array_output"]) / "array-audit.json"),
                )
                return
            with (root / f"{stage}.log").open("xb") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", script["path"], *arguments],
                    cwd=plan["work"],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=dict(os.environ, **plan["worker_env"]),
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-CPU-uniform-physics-review", stage=stage, child=owner)
                started = time.monotonic()
                try:
                    while child.poll() is None:
                        if time.monotonic() - started > plan["worker_timeout_seconds"]:
                            raise TimeoutError("Owned CPU review runtime bound reached")
                        if not resource_ready(
                            dict(plan, launch_available_gib=plan["active_available_gib"])
                        ):
                            raise MemoryError("Shared CPU review memory/disk floor reached")
                        time.sleep(2)
                except BaseException:
                    stop_owned(child, owner)
                    raise
                assert child.returncode == 0 and not alive(owner)
        guard(plan)
        native = Path(plan["native_output"]) / "report.json"
        result = read(native)
        assert result["manual_review_completed"] is False and result["CUDA_initialized"] is False
        assert result["native_source_triplets"] == 24 and result["displayed_board_cells"] == 48
        record(
            "prepared-uniform-physics-native-views-awaiting-actual-inspection-no-promotion",
            arrays=ref(Path(plan["array_output"]) / "array-audit.json"),
            native_report=ref(native),
        )
    except BaseException as error:
        record("failed-uniform-physics-CPU-review-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    main(p.parse_args().plan)
