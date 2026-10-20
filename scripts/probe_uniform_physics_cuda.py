"""Frozen unchanged-weight array gates before timing uniform-profile batching.

The explicit CPU mode checks the same forward switching on small cached
subcontexts; it cannot produce a CUDA success or a speed result.
"""

import argparse
import json
import os
import statistics
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import numpy as np
import psutil
import torch
from probe_uniform_physics_cpu import SOURCE_SHA, candidate_functions
from profile_raw_kernel_inference import model_hash
from queue_tf32x3_cuda import dependencies_ready
from train_directional_bank_trial import read, ref, save

import demosaic.pretrained_rgb as rgb_module
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context, cudnn_autotune
from demosaic.safety import writable_path

COMPLETE = "completed-uniform-physics-CUDA-array-gates-and-resident-timing-awaiting-review"
CPU_COMPLETE = "completed-uniform-physics-worker-CPU-switching-no-GPU-or-speed-result"
REJECTED = "rejected-uniform-physics-CUDA-array-gate-no-timing-or-integration"


def guard(plan):
    for item in [plan["worker"], *plan["inputs"]]:
        if ref(item["path"]) != item:
            raise ValueError("Frozen probe input changed: " + item["path"])


def require_idle(plan):
    if not dependencies_ready(plan):
        raise RuntimeError("Exact training/quality owners remain live; no CUDA initialization")


def difference(original, candidate):
    a, b = original.detach().cpu().numpy(), candidate.detach().cpu().numpy()
    assert a.dtype == b.dtype == np.float32 and a.shape == b.shape
    assert np.isfinite(a).all() and np.isfinite(b).all()
    delta = (b.astype(np.float64) - a.astype(np.float64)) * 65535
    return {
        "values": a.size,
        "shape": list(a.shape),
        "bytes_exact": a.tobytes() == b.tobytes(),
        "maximum_DN16": float(np.abs(delta).max()),
        "RMS_DN16": float(np.sqrt(np.mean(np.square(delta)))),
    }


def array_gate(result):
    return result["maximum_DN16"] <= 1 and result["RMS_DN16"] <= 0.25


def arguments(fixture, device, *, cpu):
    with np.load(fixture["observation"]["path"], allow_pickle=False) as data:
        batch = {
            k: torch.from_numpy(data[k].copy())
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
    roi = None
    if cpu:
        height, width = batch["packed"].shape[-2:]
        y, x = height // 2 - 16, width // 2 - 20
        assert min(y, x) >= 0
        for key in ["packed", "variance"]:
            batch[key] = batch[key][..., y : y + 32, x : x + 40]
        roi = [x * 2, y * 2, 80, 64]
    args = [
        batch[k].to(device).contiguous(memory_format=torch.channels_last)
        if k in ("packed", "variance")
        else batch[k].to(device)
        for k in ["packed", "variance", "colors", "wb", "matrix"]
    ]
    return args, roi


@torch.inference_mode()
def main(plan_path, *, cpu=False):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    assert ref(rgb_module.__file__)["sha256"] == SOURCE_SHA
    if cpu:
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    else:
        require_idle(plan)
    assert psutil.virtual_memory().available >= (40 if cpu else 48) * 2**30
    device = torch.device("cpu" if cpu else "cuda")
    output = writable_path(plan["CPU_output"] if cpu else plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    cases, timings = [], []
    functions, old, new, _parts, _namespace = candidate_functions()
    (output / "original-forward.py").write_text(old + "\n")
    (output / "candidate-forward.py").write_text(new + "\n")

    def record(status, **fields):
        save(
            output / "status.json",
            {
                "status": status,
                "owner": owner,
                "plan": ref(plan_path),
                **fields,
            },
        )

    def policy(candidate):
        return (
            patch.object(rgb_module.PretrainedRgbDemosaic, "forward", functions["forward"])
            if candidate
            else nullcontext()
        )

    record("starting-CPU-worker-switching-preflight" if cpu else "starting-CUDA-output-array-gates")
    try:
        if not cpu:
            total = torch.cuda.get_device_properties(0).total_memory
            torch.cuda.set_per_process_memory_fraction(
                min(
                    torch.cuda.get_per_process_memory_fraction(0),
                    16 * 2**30 / total,
                ),
                0,
            )
        for label, checkpoint in plan["checkpoints"].items():
            model, saved = load_checkpoint(checkpoint["path"], device)
            step = saved["step"]
            del saved
            model.eval().to(memory_format=torch.channels_last)
            before = model_hash(model)
            parameter_ids = {k: id(p) for k, p in model.named_parameters()}
            for fixture in plan["fixtures"]:
                args, roi = arguments(fixture, device, cpu=cpu)
                model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
                rng = torch.get_rng_state().clone()
                cuda_rng = None if cpu else torch.cuda.get_rng_state().clone()
                with cudnn_autotune(device, enabled=not cpu), amp_context(device, dtype="float32"):
                    original = model(*args)
                    with policy(True):
                        candidate = model(*args)
                        repeated = model(*args)
                    restored = model(*args)
                error = difference(original, candidate)
                assert difference(candidate, repeated)["bytes_exact"]
                assert difference(original, restored)["bytes_exact"]
                assert torch.equal(rng, torch.get_rng_state())
                assert cpu or torch.equal(cuda_rng, torch.cuda.get_rng_state())
                assert before == model_hash(model)
                assert parameter_ids == {k: id(p) for k, p in model.named_parameters()}
                path = output / f"{label}-{fixture['label']}-RGB-f32.npz"
                np.savez(path, original=original.cpu().numpy(), candidate=candidate.cpu().numpy())
                case = {
                    "model": label,
                    "checkpoint": checkpoint,
                    "step": step,
                    "fixture": fixture,
                    "CPU_relative_native_xywh": roi,
                    "arrays": ref(path),
                    "difference": error,
                    "candidate_repeat_bytes_exact": True,
                    "restored_original_bytes_exact": True,
                    "model_DINO_state_parameter_identities_and_RNG_unchanged": True,
                }
                cases.append(case)
                save(output / "cases.json", cases)
                print(
                    json.dumps({"model": label, "fixture": fixture["label"], **error}), flush=True
                )
                if not array_gate(error):
                    record("rejected-CPU-switching-preflight" if cpu else REJECTED, cases=cases)
                    return
                del args, original, candidate, repeated, restored
            del model
        # Never time a policy before all unchanged-weight output gates pass.
        assert len(cases) == 8
        if not cpu:
            require_idle(plan)
            serving = next(f for f in plan["fixtures"] if f["label"] == "GFX-four-native512")
            for label, checkpoint in plan["checkpoints"].items():
                model, saved = load_checkpoint(checkpoint["path"], device)
                del saved
                model.eval().to(memory_format=torch.channels_last)
                args, _roi = arguments(serving, device, cpu=False)
                model.set_noise(serving["conditioning"]["shot"], serving["conditioning"]["read"])
                before = model_hash(model)
                parameter_ids = {k: id(p) for k, p in model.named_parameters()}
                rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
                samples = []
                with cudnn_autotune(device, enabled=True), amp_context(device, dtype="float32"):
                    for _ in range(3):
                        for candidate in [False, True]:
                            with policy(candidate):
                                model(*args)
                    for candidate in [False, True, True, False, True, False, False, True]:
                        with policy(candidate):
                            torch.cuda.synchronize()
                            started = time.perf_counter()
                            model(*args)
                            torch.cuda.synchronize()
                            samples.append(
                                {"candidate": candidate, "seconds": time.perf_counter() - started}
                            )
                assert before == model_hash(model)
                assert parameter_ids == {k: id(p) for k, p in model.named_parameters()}
                assert torch.equal(rng, torch.get_rng_state())
                assert torch.equal(cuda_rng, torch.cuda.get_rng_state())
                timings.append(
                    {
                        "model": label,
                        "samples": samples,
                        "median_seconds": {
                            name: statistics.median(
                                s["seconds"] for s in samples if s["candidate"] == flag
                            )
                            for name, flag in [("original", False), ("candidate", True)]
                        },
                    }
                )
                del model, args
        guard(plan)
        assert not cpu or not torch.cuda.is_initialized()
        result = {
            "status": CPU_COMPLETE if cpu else COMPLETE,
            "plan": ref(plan_path),
            "owner": owner,
            "worker": ref(__file__),
            "cases": cases,
            "resident_timings": timings,
            "original_forward": ref(output / "original-forward.py"),
            "candidate_forward": ref(output / "candidate-forward.py"),
            "CUDA_initialized": torch.cuda.is_initialized(),
            "scope": "CPU/native64x80/channels-last switching only; no GPU/speed result"
            if cpu
            else plan["scope"],
        }
        save(output / "receipt.json", result)
        record(result["status"], receipt=ref(output / "receipt.json"))
    except BaseException as error:
        record("failed-uniform-physics-probe-no-automatic-retry", error=repr(error), cases=cases)
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("--cpu-preflight", action="store_true")
    a = p.parse_args()
    main(a.plan, cpu=a.cpu_preflight)
