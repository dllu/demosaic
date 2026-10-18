"""Time real mixed-domain updates in an already frozen execution-preflight tree."""

import argparse
import json
import os
import shutil
import subprocess
import time
from decimal import Decimal
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import train_rows
from profile_raw_kernel_inference import model_hash
from train_directional_interval_trial import guard, read, ref, save

import demosaic.train as training
from demosaic.safety import writable_path


def worker(plan_path, case):
    plan = read(plan_path)
    guard(plan)
    assert psutil.virtual_memory().available > 40 * 2**30
    device = torch.device("cuda", torch.cuda.current_device())
    torch.cuda.set_per_process_memory_fraction(
        24 * 2**30 / torch.cuda.get_device_properties(device).total_memory, device
    )
    arm = next(a for a in plan["cases"] if a["name"] == case)
    original = training.JointDemosaic
    current = {}

    def instrument(options):
        model = original(options)
        current["model"] = model

        def first_forward(module, args):
            parent = torch.load(
                plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True
            )
            assert all(
                torch.equal(module.restoration_state_dict()[k].cpu(), v)
                for k, v in parent["ema"].items()
            )
            current["DINO_sha256"] = model_hash(module.context.backbone)
            hook.remove()

        hook = model.register_forward_pre_hook(first_forward)
        return model

    training.JointDemosaic = instrument
    try:
        checkpoint = training.train(arm["config"], initialize=plan["parent"]["path"], stop_after=60)
    finally:
        training.JointDemosaic = original
    model = current["model"]
    assert current["DINO_sha256"] == model_hash(model.context.backbone)
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == 60 and state["config"]["steps"] == 4000
    assert len(state["model"]) == len(state["ema"]) == 99 and len(state["optimizer"]["state"]) == 97
    for key in ("model", "ema"):
        assert all(torch.isfinite(v).all() for v in state[key].values())
    for values in state["optimizer"]["state"].values():
        assert int(values["step"]) == 60
        assert all(torch.isfinite(v).all() for v in values.values() if isinstance(v, torch.Tensor))
    guard(plan)
    save(
        Path(arm["config"]).parent / "worker-result.json",
        {
            "checkpoint": ref(checkpoint),
            "finite_states": {"model": 99, "EMA": 99, "AdamW": 97},
            "DINO_sha256_unchanged": current["DINO_sha256"],
            "source_sha256": state["config"]["source_sha256"],
            "runtime": state["config"]["training_execution_runtime"],
        },
    )


def controller(preflight_plan, output):
    prior = read(preflight_plan)
    guard(prior)
    preflight_root = Path(prior["root"])
    for device in ("cpu", "cuda"):
        assert (
            read(preflight_root / (device + "-audit.json"))["status"]
            == "passed-" + device.upper() + "-execution-preflight"
        )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    worker_path = output / Path(__file__).name
    shutil.copyfile(__file__, worker_path)
    template = yaml.safe_load(Path(prior["configs"]["cuda-strict-a"]).read_text())
    cases = []
    for name, policy in (
        ("throughput-0", "throughput-v1"),
        ("strict-0", "deterministic-v1"),
        ("strict-1", "deterministic-v1"),
        ("throughput-1", "throughput-v1"),
    ):
        case = output / name
        case.mkdir()
        config = {
            **template,
            "training_execution": policy,
            "run": str(case / "run"),
            "checkpoint_every": 4000,
            "trace_observations": False,
            "validation_protocol": None,
        }
        path = case / "config.yaml"
        path.write_text(yaml.safe_dump(config))
        cases.append({"name": name, "policy": policy, "config": str(path)})
    plan = {
        "parent": prior["parent"],
        "cases": cases,
        "inputs": [
            *prior["inputs"],
            ref(preflight_plan),
            ref(worker_path),
            ref(preflight_root / "cpu-audit.json"),
            ref(preflight_root / "cuda-audit.json"),
            *[ref(a["config"]) for a in cases],
        ],
        "frozen_files": prior["frozen_files"],
        "warmup_excluded": 15,
        "measured_updates": 45,
        "batch_size": 16,
        "scope": "Throughput only; four fresh serial processes in balanced ABBA order. Real selected-domain loading/augmentation/degradation, frozen DINO, forward/backward, clipping, AdamW and EMA; original4000 LR horizon. Exclude initialization, first15 updates, validation, serialization and post-run audit. No image-quality/default change.",
    }
    plan_path = output / "plan.json"
    save(plan_path, plan)
    results = []
    env = dict(
        os.environ,
        HF_HUB_OFFLINE="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
        PYTHONPATH=os.pathsep.join(str(Path(prior["work"]) / p) for p in ("src", "scripts")),
    )
    for arm in cases:
        guard(plan)
        assert psutil.virtual_memory().available > 40 * 2**30
        assert shutil.disk_usage(output).free > 128 * 2**30
        assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
        before = {
            "available_GiB": psutil.virtual_memory().available / 2**30,
            "load_average": list(os.getloadavg()),
        }
        started = time.monotonic()
        case = Path(arm["config"]).parent
        with (case / "process.log").open("xb") as log:
            subprocess.run(
                [
                    prior["python"],
                    "-P",
                    str(worker_path),
                    "worker",
                    str(plan_path),
                    "--case",
                    arm["name"],
                ],
                cwd=prior["work"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=900,
            )
        rows = train_rows(case / "run")
        assert [r["step"] for r in rows] == list(range(1, 61))
        elapsed = (
            Decimal(str(rows[59]["seconds_per_step"])) * 60
            - Decimal(str(rows[14]["seconds_per_step"])) * 15
        )
        assert elapsed > 0
        domains = {}
        for row in rows[15:]:
            domains[row["domain"]] = domains.get(row["domain"], 0) + 1
        result = {
            "name": arm["name"],
            "policy": arm["policy"],
            "measured_seconds": float(elapsed),
            "patches_per_second": float(Decimal(16 * 45) / elapsed),
            "peak_CUDA_bytes": round(rows[-1]["cuda_gb"] * 1e9),
            "domains": domains,
            "whole_process_seconds": time.monotonic() - started,
            "before": before,
            "available_GiB_after": psutil.virtual_memory().available / 2**30,
            "config": ref(arm["config"]),
            "metrics": ref(case / "run/metrics.jsonl"),
            "worker_result": ref(case / "worker-result.json"),
        }
        results.append(result)
        save(
            output / "summary.json",
            {"status": "running", "plan": ref(plan_path), "results": results},
        )
        print(
            json.dumps({k: result[k] for k in ("name", "patches_per_second", "domains")}),
            flush=True,
        )
    assert len({json.dumps(r["domains"], sort_keys=True) for r in results}) == 1
    assert len({read(r["worker_result"]["path"])["source_sha256"] for r in results}) == 1
    guard(plan)
    save(
        output / "summary.json",
        {"status": "complete", "plan": ref(plan_path), "results": results, "scope": plan["scope"]},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.plan, args.case)
    else:
        if args.output is None:
            parser.error("run requires --output")
        controller(args.plan, args.output)
