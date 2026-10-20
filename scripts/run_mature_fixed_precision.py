"""Freeze and run two serial original-weight, fixed-backend precision replicas."""

import argparse
import copy
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import psutil
from qualify_mature_precision import alive
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
EXECUTION = "mature-fixed-backends-v1"


def prepare(root):
    tests = Path("/mnt/external/demosaic/mature-fixed-execution-tests-v2.xml")
    x = ET.parse(tests).getroot().find("testsuite")
    assert x.attrib["tests"] == "26" and x.attrib["errors"] == x.attrib["failures"] == "0"
    pilot = REPO / ".cache/benchmarks/mature-mixed-precision-CUDA-v1"
    original_path = pilot / "plan.json"
    original = read(original_path)
    guard(original)
    failed_path = REPO / ".cache/benchmarks/mature-hidden-FP16-full-quality-v1/plan.json"
    failed = read(failed_path)
    guard(failed)
    replay = REPO / ".cache/benchmarks/mature-precision-original-worker-replay-v1"
    roots = [
        pilot,
        Path(failed["root"]),
        REPO / ".cache/benchmarks/mature-precision-execution-drift-v1",
        replay,
    ]
    owners, states = [], []
    for folder in roots:
        status = read(folder / "controller-status.json")
        assert status["status"].startswith(("completed-", "failed-full-precision-quality-"))
        assert not any(alive(status[k]) for k in ("controller", "child"))
        owners += [status[k] for k in ("controller", "child")]
        states.append(ref(folder / "controller-status.json"))
    assert read(replay / "outputs/receipt.json")["models"][0]["model"] == "V43"
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for folder in ("src/demosaic", "scripts"):
        for source in (REPO / folder).glob("*.py"):
            target = work / folder / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name in (
        "pyproject.toml",
        "uv.lock",
        "configs/evaluation.yaml",
        "docs/mature-fixed-execution-pilot.md",
        "tests/test_mature_precision_execution.py",
        "tests/test_mature_precision_tools.py",
        "tests/test_mature_quality_pairs.py",
    ):
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    files = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    inputs = (
        original["inputs"]
        + list(failed["models"].values())
        + [ref(original_path), ref(failed_path), ref(tests), ref(replay / "outputs/receipt.json")]
        + states
    )
    inputs += [
        c["RGB"]
        for m in read(pilot / "work/GPU-output/receipt.json")["models"]
        for c in m["captures"]
    ]
    replicas = []
    for index in range(2):
        folder = root / f"replica{index}"
        folder.mkdir()
        child = copy.deepcopy(original)
        child.update(
            root=str(folder),
            work=str(work),
            output=str(work / f"replica{index}-outputs"),
            models=failed["models"],
            worker=ref(work / "scripts/probe_mature_precision_cuda.py"),
            execution_policy=EXECUTION,
            inputs=inputs,
            frozen_files=files,
            scope="New fixed-backend finite precision replica; separate from the failed autotuned qualification. No automatic full-quality/full-frame continuation or adoption.",
        )
        save(folder / "plan.json", child)
        guard(child)
        replicas.append(ref(folder / "plan.json"))
    plan = {
        "root": str(root),
        "work": str(work),
        "python": original["python"],
        "HF_HOME": original["HF_HOME"],
        "execution_policy": EXECUTION,
        "replicas": replicas,
        "blocking_owners": owners,
        "inputs": inputs + replicas,
        "frozen_files": files,
        "controller": ref(work / "scripts/run_mature_fixed_precision.py"),
        "unit_tests": {"JUnit": ref(tests), "passed": 26},
        "CPU_proofs": [original["CPU_preflight"], ref(Path(failed["output"]) / "CPU-receipt.json")],
        "protocol": ref(work / "docs/mature-fixed-execution-pilot.md"),
        "scope": "Two fresh source-frozen fixed-backend replicas only. All first-replica FP32 outputs retain original1/.25DN16 parity; all348 capture files require pairwise SHA identity and all48 timed files require first-capture SHA identity in subsequent CPU audit. Then actual48 native cells and independent scalar review are required. No quality/speed interpretation here, no gate relaxation or automatic continuation.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def run(plan_path):
    from queue_tf32x3_cuda import stop_owned

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"plan": ref(plan_path), "controller": owner, "completed": []}
    child = None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "controller-status.json", state)

    def resources(gib):
        return (
            psutil.virtual_memory().available >= gib * 2**30
            and shutil.disk_usage(root).free >= 64 * 2**30
            and shutil.disk_usage("/mnt/external").free >= 500 * 2**30
        )

    try:
        assert ref(__file__) == plan["controller"]
        assert not any(alive(o) for o in plan["blocking_owners"])
        for index, item in enumerate(plan["replicas"]):
            began, stable = time.monotonic(), None
            record("waiting-for-stable-fixed-precision-headroom", replica=index)
            while True:
                assert time.monotonic() - began < 3600
                stable = (time.monotonic() if stable is None else stable) if resources(48) else None
                if stable is not None and time.monotonic() - stable >= 60:
                    break
                time.sleep(5)
            guard(plan)
            cp = read(item["path"])
            guard(cp)
            work = Path(plan["work"])
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
                HF_HOME=plan["HF_HOME"],
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OMP_NUM_THREADS="4",
                OPENBLAS_NUM_THREADS="4",
                PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            )
            with (root / f"replica{index}.log").open("xb") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", cp["worker"]["path"], item["path"]],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-fixed-precision-replica", child=child_owner)
                deadline = time.monotonic() + 900
                while child.poll() is None:
                    if time.monotonic() > deadline or not resources(24):
                        raise RuntimeError(
                            "Owned fixed-precision worker reached resource/runtime bound"
                        )
                    time.sleep(2)
                assert child.wait() == 0
            receipt = Path(cp["output"]) / "receipt.json"
            result = read(receipt)
            assert result["owner"] == child_owner and result["execution_policy"] == EXECUTION
            restoration = read(Path(cp["output"]) / "fixed-execution-restoration.json")
            assert (
                restoration["receipt"] == ref(receipt)
                and restoration["outer_backend_settings_restored_exact"]
            )
            save(
                Path(cp["root"]) / "controller-status.json",
                {
                    "controller": owner,
                    "child": child_owner,
                    "plan": item,
                    "receipt": ref(receipt),
                    "status": "completed-mature-precision-pilot-arrays-awaiting-native-and-independent-scalar-review",
                },
            )
            state["completed"].append(index)
            record("completed-fixed-precision-replica", receipt=ref(receipt))
        guard(plan)
        record("completed-fixed-precision-replicas-awaiting-execution-native-and-scalar-review")
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned(child, state["child"])
        record("failed-fixed-precision-replicas-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    prepare(args.path) if args.mode == "prepare" else run(args.path.resolve())
