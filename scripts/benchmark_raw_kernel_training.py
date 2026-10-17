"""Bounded, isolated training-throughput sweep for the current joint RAW head.

All cases initialize fresh from the same frozen EMA and discard their updates.
The production schedule/model/data remain fixed. CPU mode is an engineering
fixture only. Run CUDA mode after other owned GPU jobs have completed and exited.
"""

import argparse
import hashlib
import json
import math
import os
import random
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import psutil
import yaml

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def worker(config, initialize, updates, cap_gb):
    import torch

    from demosaic import train as module

    recipe = yaml.safe_load(config.read_text())
    policy = {"device": recipe["device"], "available_GB": psutil.virtual_memory().available / 1e9}
    if torch.device(recipe["device"]).type == "cuda":
        # This limits PyTorch's caching allocator, not other processes or all
        # non-PyTorch allocations. The parent also screens expected headroom.
        total = torch.cuda.get_device_properties(0).total_memory
        fraction = min(cap_gb * 1e9 / total, 0.75)
        assert 0 < fraction < 1
        torch.cuda.memory.set_per_process_memory_fraction(fraction, 0)
        policy.update(
            allocator_cap_GB=fraction * total / 1e9,
            fraction=fraction,
            CUDA_visible_total_GB=total / 1e9,
        )
    else:
        assert not torch.cuda.is_initialized()
        policy["allocator_cap_GB"] = None
    write(config.parent / "memory-policy.json", policy)
    initial = torch.load(initialize, map_location="cpu", weights_only=True, mmap=True)
    captured = {}
    original = module.make_optimizer

    def backbone_hash(model):
        digest = hashlib.sha256()
        for name, value in model.context.backbone.state_dict().items():
            digest.update(name.encode() + value.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def checked_optimizer(model, options):
        optimizer = original(model, options)
        restored = model.restoration_state_dict()
        assert restored.keys() == initial["ema"].keys()
        assert all(torch.equal(v.detach().cpu(), initial["ema"][n]) for n, v in restored.items())
        trainable = [p for p in model.parameters() if p.requires_grad]
        assert len(trainable) == 92 and sum(p.numel() for p in trainable) == 32931920
        assert all(not p.requires_grad for p in model.context.backbone.parameters())
        captured.update(model=model, DINO_sha256=backbone_hash(model))
        return optimizer

    module.make_optimizer = checked_optimizer
    try:
        checkpoint = module.train(config, initialize=initialize, stop_after=updates)
    finally:
        module.make_optimizer = original
    model = captured.pop("model")
    assert backbone_hash(model) == captured["DINO_sha256"]
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == updates and state["config"]["steps"] == recipe["steps"]
    assert len(state["model"]) == len(state["ema"]) == 94
    assert len(state["optimizer"]["state"]) == 92
    assert {int(v["step"]) for v in state["optimizer"]["state"].values()} == {updates}
    assert all(torch.isfinite(v).all() for k in ["model", "ema"] for v in state[k].values())
    assert all(
        torch.isfinite(v).all()
        for item in state["optimizer"]["state"].values()
        for v in item.values()
        if isinstance(v, torch.Tensor)
    )
    for key in ["model", "ema"]:
        for name in ["context.mean", "context.std"]:
            assert torch.equal(state[key][name], initial["ema"][name])
    write(
        config.parent / "state-checks.json",
        {
            **captured,
            "all94_initial_restoration_tensors_equal_frozen_EMA": True,
            "trainable_tensors": 92,
            "trainable_parameters": 32931920,
            "DINO_unchanged_frozen_and_gradient_free": True,
            "finite94model94EMA92Adam": True,
            "fresh_Adam_steps": updates,
            "normalization_buffers_unchanged": True,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "checkpoint_sha256": sha(checkpoint),
        },
    )


def main(
    config,
    initialize,
    output,
    batch_sizes,
    warmup,
    measure,
    repeats,
    reference_peak_gb=21.34,
    reference_batch=16,
    reserve_gb=24,
    timeout_seconds=1200,
):
    if (
        not batch_sizes
        or min([*batch_sizes, warmup, measure, repeats, reference_batch, timeout_seconds]) < 1
    ):
        raise ValueError("Positive batch/update/repeat/reference counts required")
    if len(batch_sizes) != len(set(batch_sizes)) or not all(
        math.isfinite(v) and v > 0 for v in [reference_peak_gb, reserve_gb]
    ):
        raise ValueError("Unique batches and finite positive memory policy required")
    recipe = yaml.safe_load(config.read_text())
    assert recipe["raw_kernel_only"] is False
    assert (
        recipe["model"]["raw_kernel_reconstruction"]
        and recipe["model"]["raw_kernel_phase_conditioning"]
    )
    cpu = recipe["device"] == "cpu"
    if not cpu:
        assert (
            recipe["device"] == "cuda"
            and recipe["patch_size"] == 256
            and recipe["precision"] == "bfloat16"
        )
    updates = warmup + measure
    assert updates < recipe["steps"]
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases = [(repeat, batch) for repeat in range(repeats) for batch in batch_sizes]
    random.Random(20261017).shuffle(cases)
    digest = sha(initialize)
    plan = {
        "status": "running-isolated-RAW-training-throughput-fixtures",
        "config": str(config),
        "config_sha256": sha(config),
        "initialize": str(initialize),
        "initialization_sha256": digest,
        "device": recipe["device"],
        "cases": cases,
        "warmup_excluded": warmup,
        "measured_updates": measure,
        "original_schedule_steps": recipe["steps"],
        "original_lr": recipe["lr"],
        "original_warmup": recipe["warmup_steps"],
        "per_case_timeout_seconds": timeout_seconds,
        "memory_policy": {
            "reference_peak_GB": reference_peak_gb,
            "reference_batch": reference_batch,
            "required_GB_formula": "1.2*reference_peak*batch/reference_batch+4GB scratch+reserve",
            "reserve_GB": reserve_gb,
            "allocator_cap": "min(available-reserve,75% CUDA visible memory)",
        },
        "driver_sha256": sha(__file__),
        "results": [],
        "scope": "Training throughput only. Fresh EMA initialization/scope/AdamW per case, discarded short updates. Original model/data/loss/seed/LR/warmup/10000 horizon fixed except run/batch/logging/checkpoint/validation-monitor settings and notes. Per-step logs with no observation hashing. Includes selected-domain loading/augmentation/degradation, frozen DINO, forward/backward/AdamW/EMA; excludes startup, first warmup updates, final checkpoint serialization and monitor validation. Different image counts/short trajectories are not quality/convergence evidence. CPU fixtures are not GPU throughput. Shared machine; memory bounds are conservative estimates, allocator cap does not bound all allocations. No automatic production batch/LR/model change or promotion.",
    }
    summary = output / "summary.json"
    write(summary, plan)
    source_hash = None
    for repeat, batch in cases:
        available = psutil.virtual_memory().available / 1e9
        expected = 1.2 * reference_peak_gb * batch / reference_batch + 4
        if not cpu and available < expected + reserve_gb:
            plan["results"].append(
                {
                    "batch": batch,
                    "repeat": repeat,
                    "status": "skipped-insufficient-predicted-headroom",
                    "available_GB": available,
                    "predicted_peak_GB": expected,
                    "reserve_GB": reserve_gb,
                }
            )
            write(summary, plan)
            continue
        assert available > reserve_gb
        case = output / f"batch{batch}-repeat{repeat}"
        case.mkdir()
        modified = {
            **recipe,
            "run": str(case / "run"),
            "batch_size": batch,
            "log_every": 1,
            "trace_observations": False,
            "checkpoint_every": recipe["steps"] + 1,
            "validation_protocol": None,
            "experiment_notes": "Discarded isolated throughput fixture; fixed initializer/model/data/seed/LR/warmup/original horizon. No production continuation or quality result.",
        }
        path = case / "config.yaml"
        path.write_text(yaml.safe_dump(modified, sort_keys=False))
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-case",
            str(path),
            "--initialize",
            str(initialize),
            "--updates",
            str(updates),
            "--cap-gb",
            str(available - reserve_gb),
        ]
        before = {"available_GB": available, "load_average": list(psutil.getloadavg())}
        started = time.monotonic()
        with (case / "console.log").open("xb") as log:
            child = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                code = child.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                # The session contains only this owned fixture and its workers.
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                code = "timeout"
        if code:
            plan["results"].append(
                {
                    "batch": batch,
                    "repeat": repeat,
                    "status": "failed-no-automatic-retry",
                    "returncode": code,
                    "case": str(case),
                }
            )
            plan["status"] = "failed-no-automatic-retry"
            write(summary, plan)
            raise RuntimeError(f"Owned throughput fixture failed: {case}/console.log")
        rows = [
            v
            for line in (case / "run/metrics.jsonl").read_text().splitlines()
            if (v := json.loads(line)).get("event") == "train"
        ]
        assert [v["step"] for v in rows] == list(range(1, updates + 1))
        assert all(
            math.isfinite(v) for row in rows for v in row.values() if isinstance(v, (int, float))
        )
        first, last = rows[warmup - 1], rows[-1]
        elapsed = last["seconds_per_step"] * updates - first["seconds_per_step"] * warmup
        assert elapsed > 0
        runtime = yaml.safe_load((case / "run/config.yaml").read_text())
        assert runtime["initialized_from"]["sha256"] == digest == sha(initialize)
        assert runtime["batch_size"] == batch
        skip = {
            "run",
            "batch_size",
            "log_every",
            "trace_observations",
            "checkpoint_every",
            "validation_protocol",
            "experiment_notes",
        }
        assert all(runtime[key] == value for key, value in recipe.items() if key not in skip)
        source_hash = runtime["source_sha256"] if source_hash is None else source_hash
        assert runtime["source_sha256"] == source_hash
        record = {
            "batch": batch,
            "repeat": repeat,
            "status": "completed-discarded-throughput-fixture",
            "patches_per_second": batch * measure / elapsed,
            "measured_seconds": elapsed,
            "seconds_per_update": elapsed / measure,
            "peak_CUDA_GB": last["cuda_gb"],
            "measured_domains": dict(Counter(row["domain"] for row in rows[warmup:])),
            "source_sha256": source_hash,
            "runtime_config_sha256": sha(case / "run/config.yaml"),
            "metrics_sha256": sha(case / "run/metrics.jsonl"),
            "case": str(case),
            "before": before,
            "available_GB_after": psutil.virtual_memory().available / 1e9,
            "whole_process_seconds": time.monotonic() - started,
            "memory_policy": json.loads((case / "memory-policy.json").read_text()),
            "state_checks": json.loads((case / "state-checks.json").read_text()),
        }
        plan["results"].append(record)
        write(summary, plan)
        print(json.dumps(record), flush=True)
    plan["status"] = "completed-RAW-training-throughput-fixtures-with-explicit-memory-skips"
    plan["source_sha256"] = source_hash
    write(summary, plan)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, nargs="?")
    parser.add_argument("--initialize", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=[4, 8, 16, 32, 48, 64])
    parser.add_argument("--warmup", type=int, default=15)
    parser.add_argument("--measure", type=int, default=45)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--reference-peak-gb", type=float, default=21.34)
    parser.add_argument("--reference-batch", type=int, default=16)
    parser.add_argument("--reserve-gb", type=float, default=24)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--worker-case", type=Path)
    parser.add_argument("--updates", type=int)
    parser.add_argument("--cap-gb", type=float)
    args = vars(parser.parse_args())
    if args["worker_case"] is not None:
        worker(args["worker_case"], args["initialize"], args["updates"], args["cap_gb"])
    else:
        if args["config"] is None or args["output"] is None:
            parser.error("config and --output are required for a sweep")
        for name in ["worker_case", "updates", "cap_gb"]:
            args.pop(name)
        main(**args)
