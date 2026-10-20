"""Resume an existing discarded step8 checkpoint in a genuinely new worker."""

import argparse
import copy
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_late_rgb_trial import alive, resources_allow

from demosaic.safety import writable_path


def metric_prefix(text, step=8):
    prefix, steps, found_resume = [], [], False
    for line in text.splitlines():
        row = json.loads(line)
        if row.get("event") == "train":
            if row["step"] > step:
                assert row["step"] == step + 1
                found_resume = True
                break
            steps.append(row["step"])
        prefix.append(line)
    assert found_resume and steps == list(range(1, step + 1))
    return "\n".join(prefix) + "\n"


def prepare(status_path, root):
    status = read(status_path)
    assert status["status"] == "completed-late-rgb-engineering-preflight"
    assert not alive(status["controller"]) and not alive(status["child"])
    previous = read(status["plan"]["path"])
    assert ref(status["plan"]["path"]) == status["plan"]
    guard(previous)
    root = writable_path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work, old_work = root / "work", Path(previous["work"])
    for source, digest in previous["frozen_files"].items():
        source = Path(source)
        assert ref(source)["sha256"] == digest
        target = work / source.relative_to(old_work)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    helper = work / "scripts" / Path(__file__).name
    shutil.copyfile(__file__, helper)
    restart = read(status["completed"]["restart"]["path"])
    uninterrupted = read(status["completed"]["spatial"]["path"])
    checkpoint = Path(previous["root"]) / "restart-step8.pt"
    observations = read(restart["observations"]["path"])
    assert [row["step"] for row in observations] == list(range(1, 17))
    prefix_file = root / "seed-metrics-step8.jsonl"
    prefix_file.write_text(metric_prefix(Path(restart["metrics"]["path"]).read_text()))
    prior_observations = root / "observations-step8.json"
    save(prior_observations, observations[:8])
    original_arm = next(a for a in previous["arms"] if a["name"] == "restart")
    cfg = yaml.safe_load(Path(original_arm["config"]).read_text())
    cfg["run"] = str(work / "runs/control")
    cfg["validation_protocol"] = str(work / "configs/evaluation.yaml")
    config = work / "configs/control.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=True))
    run = Path(cfg["run"])
    run.mkdir(parents=True)
    shutil.copyfile(prefix_file, run / "metrics.jsonl")
    plan = copy.deepcopy(previous)
    plan.update(
        status="frozen-additional-fresh-process-step8-to16-engineering-replay",
        root=str(root),
        work=str(work),
        worker=ref(work / "scripts/train_late_rgb_trial.py"),
        helper=ref(helper),
        arms=[
            {"name": "control", "late_rgb_mode": "spatial", "config": str(config), "run": str(run)}
        ],
        resume={
            "control": {
                "checkpoint": ref(checkpoint),
                "observations": ref(prior_observations),
                "step": 8,
            }
        },
        fresh_process_reference={
            "preflight_status": ref(status_path),
            "uninterrupted": ref(status["completed"]["spatial"]["path"]),
            "checkpoint": uninterrupted["checkpoint"],
            "observations": uninterrupted["observations"],
        },
    )
    plan["inputs"] += [
        ref(status_path),
        status["plan"],
        ref(checkpoint),
        ref(prior_observations),
        ref(prefix_file),
        ref(status["completed"]["restart"]["path"]),
        ref(status["completed"]["spatial"]["path"]),
        uninterrupted["checkpoint"],
        uninterrupted["observations"],
    ]
    plan["frozen_files"] = {
        str(p): ref(p)["sha256"]
        for p in work.rglob("*")
        if p.is_file() and not p.is_relative_to(run)
    }
    guard(plan)
    save(root / "plan.json", plan)
    print(
        {"plan": ref(root / "plan.json"), "device": plan["device"], "additional_updates": 8},
        flush=True,
    )


def run(plan_path):
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["helper"]
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
    }

    def record(state, **extra):
        status.update(status=state, updated_unix=time.time(), **extra)
        save(root / "status.json", status)
        print({"status": state}, flush=True)

    def resources():
        return (
            psutil.virtual_memory().available / 2**30,
            shutil.disk_usage(plan["repository"]).free / 2**30,
            shutil.disk_usage(root).free / 2**30,
        )

    child = None
    try:
        assert resources_allow(plan, *resources(), launch=True)
        env = dict(os.environ, **plan["cache_environment"])
        env.update(
            PYTHONPATH=str(Path(plan["work"]) / "src") + ":" + str(Path(plan["work"]) / "scripts"),
            HF_HUB_OFFLINE="1",
            CUDA_VISIBLE_DEVICES="" if plan["device"] == "cpu" else "0",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
        )
        with (root / "fresh-worker.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    plan["worker"]["path"],
                    "worker",
                    str(plan_path),
                    "--arm",
                    "control",
                ],
                cwd=plan["work"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-extra-fresh-process-step8-resume", child=owner)
            deadline = time.monotonic() + 3600
            while child.poll() is None:
                if time.monotonic() > deadline or not resources_allow(plan, *resources()):
                    assert alive(owner) and os.getpgid(child.pid) == child.pid
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise RuntimeError(
                        "Owned fresh-restart worker reached resource/runtime bound; no retry"
                    )
                time.sleep(5)
            assert child.wait() == 0
        import torch
        from audit_flat_palette import identical, train_rows

        actual = read(root / "control-result.json")
        reference = read(plan["fresh_process_reference"]["uninterrupted"]["path"])
        states = [
            torch.load(item["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for item in [actual, reference]
        ]
        keys = [
            "model",
            "ema",
            "optimizer",
            "python_rng",
            "torch_rng",
            "cuda_rng",
            "best",
            "step",
            "model_config",
        ]
        for key in keys:
            identical(states[0][key], states[1][key])
        assert actual["actual_step"] == 16 and actual["source_sha256"] == reference["source_sha256"]
        assert read(actual["observations"]["path"]) == read(reference["observations"]["path"])
        fresh_rows = train_rows(Path(actual["checkpoint"]["path"]).parent)
        for a, b in zip(fresh_rows, reference["logged_observations"], strict=True):
            assert all(a[k] == b[k] for k in ["step", "domain", "lr", "batch_sha256"])
        guard(plan)
        record(
            "completed-genuine-fresh-process-late-RGB-restart-audit",
            compared_state_keys=keys,
            matched_all16_observations=True,
            exact_final_model_EMA_AdamW_RNG=True,
            actual=ref(root / "control-result.json"),
            reference=plan["fresh_process_reference"],
            additional_training_updates=8,
            engineering_only=True,
        )
    except BaseException as error:
        record("failed-fresh-process-late-RGB-restart-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("status", type=Path)
    p.add_argument("root", type=Path)
    p = sub.add_parser("run")
    p.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.status, args.root)
    else:
        run(args.plan)
