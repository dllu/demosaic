"""Resource-bounded single GPU capture after genuine CPU parity; no retry."""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from queue_tf32x3_cuda import alive, read, ref, stop_owned


def save(path, value):
    import json

    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def main(path):
    path = Path(path).resolve()
    plan = read(path)
    assert ref(__file__) == plan["controller"]
    root = Path(plan["root"])
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(owner["pid"]))
    proof = ref(Path(plan["CPU_output"]) / "receipt.json")
    state = {"controller": owner, "plan": ref(path), "CPU_preflight": proof}

    def record(value, **details):
        state.update(status=value, updated_unix=time.time(), **details)
        save(root / "controller-status.json", state)

    def guard():
        for p, digest in plan["frozen_files"].items():
            assert ref(p)["sha256"] == digest, p
        for item in plan["inputs"] + [proof]:
            assert ref(item["path"]) == item
        cpu = read(proof["path"])
        assert cpu["all_full_tail_head_replays_exact"] and cpu["all_states_and_RNG_unchanged"]
        assert cpu["plan"] == ref(path) and not alive(cpu["owner"]) and not cpu["CUDA_initialized"]
        assert all(not alive(o) for o in plan["blocking_owners"])

    def resources(available):
        return (
            psutil.virtual_memory().available >= available * 2**30
            and shutil.disk_usage(root).free >= 500 * 2**30
            and shutil.disk_usage("/home/dllu/proj/demosaic").free >= 64 * 2**30
        )

    try:
        guard()
        assert not Path(plan["GPU_output"]).exists()
        record("waiting-for-stable-headroom-no-Torch-or-CUDA")
        started, stable = time.monotonic(), None
        while True:
            now = time.monotonic()
            if now - started > 3600:
                raise TimeoutError("Resource wait bound; no retry")
            stable = now if stable is None and resources(48) else stable if resources(48) else None
            if stable is not None and now - stable >= 60:
                break
            time.sleep(5)
        guard()
        work = Path(plan["work"])
        env = dict(
            os.environ,
            CUDA_VISIBLE_DEVICES="0",
            HF_HOME=plan["HF_HOME"],
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OMP_NUM_THREADS="4",
            OPENBLAS_NUM_THREADS="4",
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
        )
        with (root / "GPU-worker.log").open("xb") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker"]["path"], str(path)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-fixed-late-RGB-component-GPU-capture", child=child_owner)
            started = time.monotonic()
            try:
                while child.poll() is None:
                    if time.monotonic() - started > 900:
                        raise TimeoutError("Owned GPU worker bound")
                    if not resources(24):
                        raise MemoryError("Shared memory/disk floor")
                    time.sleep(2)
            except BaseException:
                stop_owned(child, child_owner)
                raise
            assert child.returncode == 0
        guard()
        result = read(Path(plan["GPU_output"]) / "receipt.json")
        assert result["owner"] == child_owner and result["all_full_tail_head_replays_exact"]
        assert result["common_trunk_and_DINO_forwards"] == 75
        record(
            "completed-fixed-component-GPU-arrays-awaiting-native-and-independent-scalar-review",
            receipt=ref(Path(plan["GPU_output"]) / "receipt.json"),
        )
    except BaseException as error:
        record("failed-late-RGB-component-controller-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    main(p.parse_args().plan)
