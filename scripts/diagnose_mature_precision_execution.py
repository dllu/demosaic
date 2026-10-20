"""Isolate a stopped precision preflight without changing its parity limits."""

import argparse
import contextlib
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from qualify_mature_precision import alive
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
ARMS = ("paired-autotune", "history-autotune", "paired-fixed", "history-inference-load")


def prepare(failed_path, root):
    failed = read(failed_path)
    guard(failed)
    terminal = Path(failed["root"]) / "controller-status.json"
    state = read(terminal)
    assert state["status"] == "failed-full-precision-quality-preserved-no-automatic-retry"
    assert state["completed"] == ["CPU"]
    assert not any(alive(state[k]) for k in ("controller", "child"))
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    # Reuse the exact stopped code, not a mutable checkout implementation.
    for folder in ("src", "scripts"):
        shutil.copytree(Path(failed["work"]) / folder, work / folder)
    target = work / "scripts" / Path(__file__).name
    shutil.copyfile(__file__, target)
    snapshots = root / "failure"
    snapshots.mkdir()
    for path in (terminal, Path(failed["root"]) / "GPU-preflight.log"):
        shutil.copyfile(path, snapshots / path.name)
    pilot = read(failed["pilot_GPU"]["path"])
    model = next(m for m in pilot["models"] if m["model"] == "V43")
    fixture = failed["pilot_preflight"][0]
    captures = {c["policy"]: c["RGB"] for c in model["captures"] if c["fixture"] == fixture["id"]}
    inputs = [ref(failed_path), failed["pilot_GPU"], failed["models"]["V43"], fixture["arrays"]]
    inputs += list(captures.values()) + [ref(p) for p in snapshots.iterdir()]
    plan = {
        "root": str(root),
        "work": str(work),
        "python": failed["python"],
        "HF_HOME": failed["HF_HOME"],
        "checkpoint": failed["models"]["V43"],
        "expected_model": model["model_sha256"],
        "expected_DINO": model["DINO_sha256"],
        "fixture": fixture,
        "pilot_RGB": captures,
        "blocking_owners": [state[k] for k in ("controller", "child")],
        "arms": list(ARMS),
        "worker": ref(target),
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Four fresh serial execution diagnostics on the failed V43 B4 GFX input only: paired autotune, original three-policy warmup history, fixed algorithms, and original inference-mode loading. Save every output, including mismatches, before comparisons. No threshold relaxation, full qualification, timing claim, production change or automatic retry.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path, arm):
    import numpy as np
    import torch
    from mature_precision_tools import precision_policy
    from mature_quality_pairs import KEYS, PairRunner, load_arrays, physical_rows
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.train import batch_fingerprint

    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"] and arm in plan["arms"]
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    device = torch.device("cuda", torch.cuda.current_device())
    torch.set_num_threads(4)
    previous = (
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.benchmark_limit,
        torch.cuda.get_per_process_memory_fraction(device),
    )
    torch.cuda.set_per_process_memory_fraction(
        min(previous[2], 16 * 2**30 / torch.cuda.get_device_properties(device).total_memory), device
    )
    torch.backends.cudnn.benchmark = arm != "paired-fixed"
    torch.backends.cudnn.benchmark_limit = 10
    output = Path(plan["root"]) / "outputs" / arm
    output.mkdir(parents=True, exist_ok=False)
    rows, arrays = [], {}
    try:
        loading = (
            torch.inference_mode() if arm == "history-inference-load" else contextlib.nullcontext()
        )
        with loading:
            model, state = load_checkpoint(plan["checkpoint"]["path"], device)
            assert state["loaded_sha256"] == plan["checkpoint"]["sha256"]
            del state
            model.eval().to(memory_format=torch.channels_last)
            assert model_hash(model) == plan["expected_model"]
            assert model_hash(model.context.backbone) == plan["expected_DINO"]
            runner = PairRunner(model, "V43", plan["checkpoint"], device)
            host = load_arrays(plan["fixture"]["arrays"])
            digest = batch_fingerprint(host)
            model.set_noise(
                plan["fixture"]["condition"]["shot"], plan["fixture"]["condition"]["read"]
            )

            def capture(label, policy, value):
                data = value.detach().cpu().numpy().copy()
                assert data.dtype == np.float32 and np.isfinite(data).all()
                path = output / (label + "-" + policy + ".npy")
                np.save(path, data, allow_pickle=False)
                # Preserve an unfavorable prediction before deriving any differences.
                entry = {"label": label, "policy": policy, "RGB": ref(path)}
                save(output / "captures.json", rows + [entry])
                prior = np.load(plan["pilot_RGB"][policy]["path"], allow_pickle=False)
                entry["versus_matching_pilot"] = physical_rows(
                    torch.from_numpy(prior), torch.from_numpy(data)
                )
                entry["pilot_parity_pass"] = all(
                    r["max_abs_DN16"] <= 1 and r["RMS_DN16"] <= 0.25
                    for r in entry["versus_matching_pilot"]
                )
                if policy in arrays:
                    entry["versus_first_same_process"] = physical_rows(
                        torch.from_numpy(arrays[policy]), torch.from_numpy(data)
                    )
                    entry["first_same_process_bytes_exact"] = (
                        arrays[policy].tobytes() == data.tobytes()
                    )
                else:
                    arrays[policy] = data
                rows.append(entry)
                save(output / "captures.json", rows)

            if arm.startswith("history"):
                actual = [host[k].to(device) for k in KEYS]
                actual = [
                    v.contiguous(memory_format=torch.channels_last) if v.ndim == 4 else v
                    for v in actual
                ]
                runner.expected_args = tuple(actual)
                with torch.inference_mode():
                    for policy in ("fp32", "fp16", "fp16-hidden"):
                        for repeat in range(3):
                            with precision_policy(model, policy, device):
                                result = model(*actual)
                            capture("history-" + str(repeat), policy, result)
                            runner.forwards += 1
                            runner.observations += len(result)
                del actual, result
            for repeat in range(2):
                predicted, _ = runner(host, plan["fixture"]["condition"])
                for policy, value in predicted.items():
                    capture("paired-" + str(repeat), policy, value)
            assert batch_fingerprint(host) == digest
            invariant = runner.finish()
            assert invariant["actual_forwards"] == (13 if arm.startswith("history") else 4)
    finally:
        torch.backends.cudnn.benchmark, torch.backends.cudnn.benchmark_limit = previous[:2]
        torch.cuda.set_per_process_memory_fraction(previous[2], device)
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "completed-execution-diagnostic-not-quality-qualification",
            "plan": ref(plan_path),
            "arm": arm,
            "invariants": invariant,
            "captures": rows,
            "backend_settings_restored": True,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


def controller(plan_path):
    from queue_tf32x3_cuda import stop_owned

    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": [],
    }
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
        assert not any(alive(o) for o in plan["blocking_owners"])
        for arm in plan["arms"]:
            record("waiting-for-diagnostic-headroom", arm=arm)
            began, stable = time.monotonic(), None
            while True:
                assert time.monotonic() - began < 1800
                stable = (time.monotonic() if stable is None else stable) if resources(48) else None
                if stable is not None and time.monotonic() - stable >= 60:
                    break
                time.sleep(5)
            guard(plan)
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
            with (root / (arm + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["worker"]["path"],
                        "worker",
                        str(plan_path),
                        "--arm",
                        arm,
                    ],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-execution-diagnostic", child=owner)
                deadline = time.monotonic() + 600
                while child.poll() is None:
                    if time.monotonic() > deadline or not resources(24):
                        raise RuntimeError("Owned diagnostic reached resource/runtime limit")
                    time.sleep(2)
                assert child.wait() == 0
            receipt = root / "outputs" / arm / "receipt.json"
            assert read(receipt)["owner"] == owner
            state["completed"].append(arm)
            record("completed-diagnostic-arm", receipt=ref(receipt))
        guard(plan)
        record("completed-execution-diagnostics-awaiting-review")
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned(child, state["child"])
        record("failed-execution-diagnostic-preserved-no-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--failed-plan", type=Path)
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.failed_plan.resolve(), args.path)
    elif args.mode == "run":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.arm)
