"""Freeze isolated CUDA EMA measurements after the existing inference profiler."""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
ROOT = BASE / "benchmarks/mixed16-EMA-after-profile-v1"
STATUS = BASE / "runs/mixed16-EMA-after-profile-v1.json"
PROFILE = BASE / "runs/mixed16-packed-profile-after-quarter-v1.json"
TERMINAL = "completed-bounded-mixed16-quarter-FP32-CUDA-profiles-awaiting-trace-analysis"


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(Path(path).resolve()), "sha256": digest}


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert ref(path)["sha256"] == digest, path


def profile_ready(plan):
    status = read(plan["profile_status"])
    if status["status"] != TERMINAL:
        raise RuntimeError("Complete inference profiles must finish before EMA measurement")
    assert status["controller"] == plan["profile_owner"]
    assert all(not alive(status[key]) for key in ("controller", "child"))
    assert status["plan"] == plan["profile_plan"] == ref(plan["profile_plan"]["path"])
    previous = read(plan["profile_plan"]["path"])
    expected = [ref(Path(p) / "result.json") for p in previous["outputs"]]
    assert status["completed"] == expected and len(expected) == 2
    for item, checkpoint in zip(expected, plan["checkpoints"], strict=True):
        result = read(item["path"])
        assert result["status"] == "completed-packed-mixed16-bounded-FP32-CUDA-inference-profile"
        assert result["checkpoint"]["path"] == str(Path(checkpoint).resolve())
        assert result["checkpoint"]["sha256"] == ref(checkpoint)["sha256"]
        assert result["checkpoint"]["step"] == 10000
        assert result["CUDA_initialized"] and result["genuine_CUDA_trace_events"] > 0
        assert result["hooked_unhooked_traced_RGB_bitwise_equal"]
        assert (
            result["model_and_actual_DINO_state_unchanged"] and result["CPU_and_CUDA_RNG_unchanged"]
        )
        assert result["trace"] == ref(result["trace"]["path"])
    return status


def gate(plan):
    profile_ready(plan)
    previous = read(plan["profile_plan"]["path"])
    guard(previous)
    controller = Path(plan["profile_plan"]["path"]).with_name("controller.py")
    assert ref(controller)["sha256"] == previous["guards"][str(controller)]
    spec = importlib.util.spec_from_file_location("frozen_prior_profile_controller", controller)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # This exact frozen gate reruns the completed10k training validator on CPU.
    checkpoints = module.gate(previous)
    assert [item["path"] for item in checkpoints] == plan["checkpoints"]
    assert all(item["step"] == 10000 and item["example_draws"] == 160000 for item in checkpoints)
    return checkpoints


def prepare():
    assert not ROOT.exists() and not STATUS.exists()
    profile = read(PROFILE)
    assert alive(profile["controller"]) and profile["plan"] == ref(profile["plan"]["path"])
    previous = read(profile["plan"]["path"])
    guard(previous)
    cpu_root = BASE / "benchmarks/mixed16-EMA-benchmark-CPU-v1"
    proofs = [cpu_root / arm / "result.json" for arm in ("no-dino8k", "dino2k")]
    worker = REPO / "scripts/benchmark_ema_updates.py"
    audit_path = cpu_root / "audit.json"
    audit = read(audit_path)
    assert audit["worker"] == ref(worker) and not audit["CUDA_initialized"]
    assert audit["matched_cases"] == 16 and audit["matched_final_state_hashes"] == 32
    assert audit["actual_unfinished_profile_rejected_before_input_load_or_output_creation"]
    assert audit["prior_independent_replay"] == ref(audit["prior_independent_replay"]["path"])
    inputs = [
        Path(profile["plan"]["path"]),
        *proofs,
        audit_path,
        Path(audit["prior_independent_replay"]["path"]),
    ]
    versions = set()
    reference = None
    for proof in proofs:
        result = read(proof)
        assert result["status"] == "completed-EMA-CPU-instrumentation-preflight-no-GPU-timing"
        assert result["strict_state_equivalence_passed"] and not result["CUDA_initialized"]
        assert result["source"]["sha256"] == ref(worker)["sha256"]
        assert result["checkpoint"]["sha256"] == ref(result["checkpoint"]["path"])["sha256"]
        inputs.append(Path(result["checkpoint"]["path"]))
        assert len(result["cases"]) == 8 and all(case["passed"] for case in result["cases"])
        assert (
            result["source_and_initial_EMA_values_unchanged"]
            and result["CPU_Python_CUDA_RNG_unchanged"]
        )
        versions.add(result["torch"])
        assert reference is None or reference == result["frozen_train"]
        reference = result["frozen_train"]
        assert reference == ref(reference["path"])
        for measurement in result["measurements"]["profiles"].values():
            assert measurement["genuine_CUDA_trace_events"] == 0
            assert measurement["trace"] == ref(measurement["trace"]["path"])
            inputs.append(Path(measurement["trace"]["path"]))
    assert len(versions) == 1
    ROOT.mkdir()
    tools, work = ROOT / "tools", ROOT / "work"
    tools.mkdir()
    package = work / "src/demosaic"
    package.mkdir(parents=True)
    for name in ("__init__.py", "safety.py"):
        shutil.copyfile(Path(previous["work"]) / "src/demosaic" / name, package / name)
    shutil.copyfile(worker, tools / worker.name)
    shutil.copyfile(reference["path"], ROOT / "original-train.py")
    shutil.copyfile(__file__, ROOT / "controller.py")
    plan = {
        "python": previous["python"],
        "work": str(work),
        "tools": str(tools),
        "profile_status": str(PROFILE),
        "profile_plan": profile["plan"],
        "profile_owner": profile["controller"],
        "checkpoints": previous["checkpoints"],
        "frozen_train": ref(ROOT / "original-train.py"),
        "torch_version": versions.pop(),
        "CPU_preflights": [ref(p) for p in proofs],
        "outputs": [
            str(BASE / f"benchmarks/mixed16-quarter-EMA-CUDA-{arm}-v1")
            for arm in ("no-dino", "dino")
        ],
        "inputs": {str(p): ref(p)["sha256"] for p in inputs},
        "guards": {str(p): ref(p)["sha256"] for p in ROOT.rglob("*") if p.is_file()},
        "warmup": 3,
        "samples": 10,
        "scope": "After exact complete inference-profile owner/child exit and independent "
        "completed10k training revalidation: two serial actual10k FP32 EMA comparisons. "
        "Eight original decay positions/five updates each, strict byte equality before "
        "timings. Three warmups/ten balanced synchronized samples per method and two "
        "genuine CUDA traces per arm.300s own-child limit;32GiB RAM/500GiB disk reserves. "
        "Source/EMA input and RNG unchanged. No network inference, backward, optimizer "
        "update, learned checkpoint, production change or automatic adoption. "
        "An arithmetic mismatch is retained as a rejection without timings. "
        "Isolated EMA latency does not establish whole-step training throughput.",
    }
    assert all(not Path(p).exists() for p in plan["outputs"])
    (ROOT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    guard(plan)
    try:
        gate(plan)
    except RuntimeError as error:
        assert "Complete inference profiles" in str(error)
    else:
        raise AssertionError("A live unfinished profile was admitted")
    print(
        json.dumps(
            {
                "prepared": ref(ROOT / "plan.json"),
                "inputs": len(plan["inputs"]),
                "guards": len(plan["guards"]),
            }
        )
    )


def run():
    assert not STATUS.exists()
    plan = read(ROOT / "plan.json")
    guard(plan)
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(ROOT / "plan.json"),
        "previous_owner": plan["profile_owner"],
        "completed": [],
    }

    def record(status, **values):
        info.update(status=status, updated_unix=time.time(), **values)
        temporary = STATUS.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(STATUS)

    record("waiting-for-exact-inference-profile-owner-exit-no-CUDA-EMA-work")
    try:
        while alive(plan["profile_owner"]):
            time.sleep(15)
        guard(plan)
        checkpoints = gate(plan)
        env = {
            **os.environ,
            "PYTHONPATH": str(Path(plan["work"]) / "src"),
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "HF_HUB_OFFLINE": "1",
        }
        for checkpoint, output in zip(checkpoints, plan["outputs"], strict=True):
            assert psutil.virtual_memory().available > 32 * 2**30
            assert shutil.disk_usage(BASE).free > 500 * 2**30
            guard(plan)
            with (ROOT / (checkpoint["arm"] + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        str(Path(plan["tools"]) / "benchmark_ema_updates.py"),
                        "--checkpoint",
                        checkpoint["path"],
                        "--train-source",
                        plan["frozen_train"]["path"],
                        "--train-sha256",
                        plan["frozen_train"]["sha256"],
                        "--output",
                        output,
                        "--expected-torch",
                        plan["torch_version"],
                        "--device",
                        "cuda",
                        "--warmup",
                        str(plan["warmup"]),
                        "--samples",
                        str(plan["samples"]),
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record(
                    "measuring-isolated-EMA-on-actual10k-CUDA-state",
                    arm=checkpoint["arm"],
                    child=owner,
                )
                try:
                    code = child.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    assert alive(owner)
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                    raise
                assert code == 0 and not alive(owner)
            result_path = Path(output) / "result.json"
            result = read(result_path)
            assert (
                result["checkpoint"]["sha256"]
                == checkpoint["sha256"]
                == ref(checkpoint["path"])["sha256"]
            )
            assert result["CUDA_initialized"] and result["CPU_Python_CUDA_RNG_unchanged"]
            assert (
                result["source_and_initial_EMA_values_unchanged"]
                and result["checkpoint_bytes_unchanged"]
            )
            assert (
                result["source"]["sha256"]
                == ref(Path(plan["tools"]) / "benchmark_ema_updates.py")["sha256"]
            )
            if result["strict_state_equivalence_passed"]:
                assert result["status"] == "completed-EMA-CUDA-state-and-latency-measurement"
                assert all(
                    p["genuine_CUDA_trace_events"] > 0
                    for p in result["measurements"]["profiles"].values()
                )
            else:
                assert result["status"] == "rejected-EMA-state-difference-no-timing-or-adoption"
                assert result["measurements"] is None
            info["completed"].append(ref(result_path))
        guard(plan)
        record(
            "completed-bounded-CUDA-EMA-comparisons-awaiting-analysis", no_automatic_adoption=True
        )
    except BaseException as error:
        record("failed-no-automatic-restart-or-adoption", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        with (REPO / ".cache/mixed16-EMA-after-profile-v1.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run()
