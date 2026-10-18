"""Freeze two FP32 GPU profiles behind the exact mixed16 quarter quality owner."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
ROOT = BASE / "benchmarks/mixed16-packed-profile-after-quarter-v1"
STATUS = BASE / "runs/mixed16-packed-profile-after-quarter-v1.json"
REVIEW = BASE / "runs/packed-isotropic-mixed16-quarter-review-workflow-v1.json"
TERMINAL = "completed-mixed16-quarter-panels-statistics-artifacts-hue-sensitivities-and-parent-progress-awaiting-native-quality-review"


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    with Path(path).open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(Path(path).resolve()), "sha256": sha}


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert ref(path)["sha256"] == digest, path


def gate(plan):
    status = read(plan["review_status"])
    if status["status"] != TERMINAL:
        raise RuntimeError("Complete quarter quality panels must finish before GPU profiling")
    assert status["controller"] == plan["review_owner"]
    assert all(not alive(status[k]) for k in ["controller", "child"])
    assert status["plan"] == plan["review_plan"] == ref(plan["review_plan"]["path"])
    review_plan = read(plan["review_plan"]["path"])
    for key in [
        "statistics",
        "hue",
        "artifacts",
        "supplementary",
        "source_sensitivity",
        "progress",
        "analytic",
    ]:
        assert status[key] == ref(status[key]["path"]), key
    # Run the frozen completed-boundary validator on CPU, with its exact source.
    sys.path[:0] = [review_plan["tools"], str(Path(review_plan["work"]) / "src")]
    import torch
    from review_mixed_packed_trial import completed

    torch.set_num_threads(2)
    _training, checkpoints, _evidence = completed(review_plan)
    assert checkpoints == status["checkpoints"]
    assert [c["path"] for c in checkpoints] == plan["checkpoints"]
    assert all(c["step"] == 10000 and c["example_draws"] == 160000 for c in checkpoints)
    assert not torch.cuda.is_initialized()
    return checkpoints


def prepare():
    assert not ROOT.exists() and not STATUS.exists()
    review = read(REVIEW)
    assert alive(review["controller"])
    assert review["plan"] == ref(review["plan"]["path"])
    previous = read(review["plan"]["path"])
    guard(previous)
    fixture = BASE / "benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    manifest = read(fixture)
    cpu_root = BASE / "benchmarks/mixed16-packed-profile-CPU-v1"
    cpu = [cpu_root / arm / "result.json" for arm in ["no-dino", "dino"]]
    for path, dino in zip(cpu, [False, True], strict=True):
        result = read(path)
        assert not result["CUDA_initialized"] and result["genuine_CUDA_trace_events"] == 0
        assert result["hooked_unhooked_traced_RGB_bitwise_equal"]
        assert (
            result["model_and_actual_DINO_state_unchanged"] and result["CPU_and_CUDA_RNG_unchanged"]
        )
        assert (
            result["checkpoint"]["step"] == 2000
            and result["checkpoint"]["model_config"]["dino"] is dino
        )
        assert len(result["inclusive_branches"]) == (15 if dino else 13)
        assert all(v["calls"] == 2 for v in result["inclusive_branches"].values())
        for source, digest in result["helpers"].items():
            assert ref(source)["sha256"] == digest
    ROOT.mkdir()
    work = ROOT / "work"
    shutil.copytree(previous["work"], work, symlinks=True)
    for path in cpu:
        for source, digest in read(path)["source_files"].items():
            assert ref(work / "src/demosaic" / Path(source).name)["sha256"] == digest
    tools = ROOT / "tools"
    tools.mkdir()
    for name in ["profile_packed_inference.py", "profile_raw_kernel_inference.py"]:
        shutil.copyfile(REPO / "scripts" / name, tools / name)
    shutil.copyfile(__file__, ROOT / "controller.py")
    files = [
        fixture,
        Path(manifest["serving_probes"][0]["observation"]["path"]),
        Path(review["plan"]["path"]),
        *cpu,
    ]
    checkpoints = previous["checkpoints_to_evaluate"][:2]
    plan = {
        "python": previous["python"],
        "work": str(work),
        "tools": str(tools),
        "review_status": str(REVIEW),
        "review_plan": review["plan"],
        "review_owner": review["controller"],
        "checkpoints": checkpoints,
        "fixture": ref(fixture),
        "CPU_preflights": [ref(p) for p in cpu],
        "outputs": [
            str(BASE / f"benchmarks/mixed16-quarter-FP32-profile-{arm}-v1")
            for arm in ["no-dino", "dino"]
        ],
        "inputs": {str(p): ref(p)["sha256"] for p in files},
        "guards": {
            str(p): ref(p)["sha256"]
            for p in ROOT.rglob("*")
            if p.is_file() and ".cache" not in p.parts
        },
        "scope": "Two unchanged actual10k/160k-example endpoints, serial IEEE FP32/native512/B4/channels-last. Three warmups, five synchronized unhooked samples, five hooked samples and one operator trace. Wait for exact complete numerical-quality controller/final child exit and independent completed training-boundary validator. CPU preflights verify instrumentation only. No optimization, compilation, new quality inference, training, production change or promotion; native manual review remains required. Inclusive ranges overlap; transfer/tiling/blending/decode/encode excluded. Never infer a GPU bottleneck from CPU timings or MAC counts.",
    }
    assert all(not Path(p).exists() for p in plan["outputs"])
    (ROOT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    guard(plan)
    try:
        gate(plan)
    except RuntimeError as error:
        assert "Complete quarter" in str(error)
    else:
        raise AssertionError("Live unfinished quality work was admitted")
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
        "previous_owner": plan["review_owner"],
        "completed": [],
    }

    def record(status, **values):
        info.update(status=status, updated_unix=time.time(), **values)
        temporary = STATUS.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(STATUS)

    record("waiting-for-exact-quarter-quality-owner-exit-no-GPU-profiling")
    try:
        while alive(plan["review_owner"]):
            time.sleep(15)
        guard(plan)
        checkpoints = gate(plan)
        env = {
            **os.environ,
            "PYTHONPATH": str(Path(plan["work"]) / "src") + ":" + plan["tools"],
            "HF_HUB_OFFLINE": "1",
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
        }
        for checkpoint, output in zip(checkpoints, plan["outputs"], strict=True):
            assert (
                psutil.virtual_memory().available > 32 * 2**30
                and shutil.disk_usage(BASE).free > 500 * 2**30
            )
            guard(plan)
            with (ROOT / (checkpoint["arm"] + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        str(Path(plan["tools"]) / "profile_packed_inference.py"),
                        "--checkpoint",
                        checkpoint["path"],
                        "--inputs",
                        plan["fixture"]["path"],
                        "--output",
                        output,
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("profiling-actual-quarter-FP32-CUDA", arm=checkpoint["arm"], child=owner)
                try:
                    code = child.wait(timeout=300)
                except subprocess.TimeoutExpired:
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
                result["status"] == "completed-packed-mixed16-bounded-FP32-CUDA-inference-profile"
            )
            assert (
                result["checkpoint"]["sha256"]
                == checkpoint["sha256"]
                == ref(checkpoint["path"])["sha256"]
            )
            assert result["checkpoint"]["step"] == 10000
            assert result["CUDA_initialized"] and result["genuine_CUDA_trace_events"] > 0
            assert result["hooked_unhooked_traced_RGB_bitwise_equal"]
            assert (
                result["model_and_actual_DINO_state_unchanged"]
                and result["CPU_and_CUDA_RNG_unchanged"]
            )
            info["completed"].append(ref(result_path))
        guard(plan)
        record(
            "completed-bounded-mixed16-quarter-FP32-CUDA-profiles-awaiting-trace-analysis",
            quality_review=ref(plan["review_status"]),
            no_optimization_or_promotion=True,
        )
    except BaseException as error:
        record("failed-no-automatic-restart-or-promotion", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        with (REPO / ".cache/mixed16-packed-profile-after-quarter-v1.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run()
