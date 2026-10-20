"""Freeze and verify genuine head-only updates, including a fresh-process restart."""

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
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save
from train_late_rgb_trial import resources_allow

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]
OLD = Path("/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-v1")
COMPLETE = "completed-genuine-head-only16-and-fresh-process8plus8"


def prepare(root, device, *, cpu=None, cuda=None, full=False):
    previous = read(OLD / "plan.json")
    guard(previous)
    assert not full or device == "cuda"
    proofs = []
    for supplied, expected in [(cpu, "cpu"), (cuda, "cuda")]:
        if supplied is None:
            continue
        status = read(supplied)
        assert status["status"] == COMPLETE
        assert not alive(status["controller"]) and not alive(status["child"])
        assert ref(status["plan"]["path"]) == status["plan"]
        proof = read(status["plan"]["path"])
        assert proof["device"] == expected and proof["engineering_only"]
        guard(proof)
        for folder in ["src/demosaic", "scripts"]:
            for source in (REPO / folder).glob("*.py"):
                assert ref(source)["sha256"] == ref(Path(proof["work"]) / folder / source.name)[
                    "sha256"
                ], source
        proofs.append(ref(supplied))
    assert device != "cuda" or cpu is not None
    assert not full or cuda is not None
    root = writable_path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    sources = [
        *sorted((REPO / "src/demosaic").glob("*.py")),
        *sorted((REPO / "scripts").glob("*.py")),
        *[
            REPO / name
            for name in [
                "pyproject.toml", "uv.lock", "configs/evaluation.yaml",
                "third_party/gaussian/Noise2VST-LICENSE",
                "third_party/gaussian/KAIR-LICENSE", "third_party/dinov3/LICENSE.md",
                "docs/late-rgb-head-only-v92.md", "tests/test_late_rgb.py",
            ]
        ],
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    modules = sorted(p.name for p in (work / "src/demosaic").glob("*.py"))
    old_modules = sorted(p.name for p in (Path(previous["work"]) / "src/demosaic").glob("*.py"))
    assert modules == old_modules and len(modules) == 47
    differences = [
        name for name in modules
        if ref(work / "src/demosaic" / name)["sha256"]
        != ref(Path(previous["work"]) / "src/demosaic" / name)["sha256"]
    ]
    assert differences == ["train.py"]
    config_source = REPO / "configs/dino-convnext-late-rgb-head-only-v92.yaml"
    cfg = yaml.safe_load(config_source.read_text())
    old_cfg = yaml.safe_load(Path(previous["arms"][0]["config"]).read_text())
    assert {
        k: v for k, v in cfg.items() if k not in ["late_rgb_only", "run", "experiment_notes"]
    } == {k: v for k, v in old_cfg.items() if k not in ["run", "experiment_notes", "validation_protocol"]} | {
        "validation_protocol": "configs/evaluation.yaml"
    }
    assert cfg["late_rgb_only"] is True and cfg["model"]["late_rgb_refinement"] == "global"
    cfg["run"] = str(work / "runs/control")
    cfg["validation_protocol"] = str(work / "configs/evaluation.yaml")
    if not full:
        cfg.update(log_every=1, checkpoint_every=16, val_batches=1, validation_images=1)
    if device == "cpu":
        cfg.update(
            device="cpu", batch_size=1, patch_size=64, validation_patch_size=64,
            precision="float32", amp=False, channels_last=False, cpu_threads=2,
            workers=0, paired_workers=0, raw_clean_workers=0,
        )
    config = work / "configs/control.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=True))
    old_preflight = OLD.with_name(f"late-rgb-v90-v91-{device.upper()}16-v1")
    historical = read(OLD / "control-result.json")
    old_reference = read(old_preflight / "control-result.json")
    extra_inputs = [
        ref(OLD / "plan.json"), ref(OLD / "control-result.json"), historical["checkpoint"],
        historical["observations"], historical["initializations"], historical["metrics"],
        ref(old_preflight / "control-result.json"), old_reference["checkpoint"],
        old_reference["observations"], ref(config_source), *proofs,
        ref(REPO / "docs/results/late-rgb-components-final-review-v1.json"),
        ref("/mnt/external/demosaic/late-rgb-only-unit-v1.xml"),
    ]
    plan = {
        "root": str(root), "work": str(work), "repository": str(REPO),
        "parent": previous["parent"], "DINO_sha256": previous["DINO_sha256"],
        "python": previous["python"], "cache_environment": previous["cache_environment"],
        "device": device, "boundary_updates": 4000 if full else 16,
        "planned_updates": 4000, "engineering_only": not full,
        "late_rgb_only": True, "training_manifest": previous["training_manifest"],
        "historical_control": ref(OLD / "control-result.json"),
        "historical_preflight": ref(old_preflight / "control-result.json"),
        "model_source_differences_from_historical_control": differences,
        "worker": ref(work / "scripts/train_late_rgb_trial.py"),
        "helper": ref(work / "scripts/preflight_late_rgb_only.py"),
        "arms": [{"name": "control", "late_rgb_mode": "global", "config": str(config), "run": cfg["run"]}],
        "inputs": [*previous["inputs"], *extra_inputs],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "stable_seconds": 60, "root_disk_reserve_gib": 64,
        "timeout_seconds": 14400 if full else 3600,
        "scope": "One exploratory head-only candidate; frozen V90 historical reference, no automatic retry/extension/promotion.",
    }
    guard(plan)
    save(root / "plan.json", plan)
    print(json.dumps({"plan": ref(root / "plan.json"), "device": device, "full": full}))


def restart_plan(plan, result, *, resume=False):
    root = Path(plan["root"]) / ("fresh8plus8" if resume else "first8")
    root.mkdir(exist_ok=False)
    cfg = yaml.safe_load(Path(plan["arms"][0]["config"]).read_text())
    cfg["run"] = str(root / "run")
    config = root / "config.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=True))
    child_plan = copy.deepcopy(plan)
    child_plan.update(
        root=str(root), boundary_updates=16 if resume else 8,
        arms=[{"name": "control", "late_rgb_mode": "global", "config": str(config), "run": cfg["run"]}],
    )
    child_plan["inputs"].append(ref(config))
    if resume:
        prior = read(result)
        assert prior["actual_step"] == 8
        run = Path(cfg["run"])
        run.mkdir()
        shutil.copyfile(prior["metrics"]["path"], run / "metrics.jsonl")
        child_plan["resume"] = {"control": {
            "checkpoint": prior["checkpoint"], "observations": prior["observations"], "step": 8,
        }}
        child_plan["inputs"] += [ref(result), prior["checkpoint"], prior["observations"]]
    path = root / "plan.json"
    guard(child_plan)
    save(path, child_plan)
    return path


def run(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["helper"]
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {"plan": ref(plan_path), "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()}}

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", status)
        print(json.dumps({"status": value, "stage": status.get("stage")}), flush=True)

    def resources():
        return (
            psutil.virtual_memory().available / 2**30,
            shutil.disk_usage(plan["repository"]).free / 2**30,
            shutil.disk_usage(root).free / 2**30,
        )

    child = None

    def launch(path, stage):
        nonlocal child
        current = read(path)
        guard(current)
        record("waiting-for-head-only-resources", stage=stage)
        since, deadline = None, time.monotonic() + plan["timeout_seconds"]
        while True:
            assert time.monotonic() < deadline, "Head-only resource wait exhausted; no retry"
            if resources_allow(plan, *resources(), launch=True):
                since = time.monotonic() if since is None else since
                if time.monotonic() - since >= plan["stable_seconds"]:
                    break
            else:
                since = None
            time.sleep(5)
        env = dict(os.environ, **plan["cache_environment"])
        env.update(
            PYTHONPATH=str(Path(plan["work"]) / "src") + ":" + str(Path(plan["work"]) / "scripts"),
            HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
            CUDA_VISIBLE_DEVICES="" if plan["device"] == "cpu" else "0",
            CUBLAS_WORKSPACE_CONFIG=":4096:8", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2",
        )
        with (Path(current["root"]) / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker"]["path"], "worker", str(path), "--arm", "control"],
                cwd=plan["work"], env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-source-frozen-head-only-worker", child=owner)
            deadline = time.monotonic() + plan["timeout_seconds"]
            while child.poll() is None:
                if time.monotonic() > deadline or not resources_allow(plan, *resources()):
                    raise RuntimeError("Head-only runtime/resource bound reached; no retry")
                time.sleep(5)
            assert child.wait() == 0, stage
        return Path(current["root"]) / "control-result.json"

    try:
        actual_result = launch(plan_path, "uninterrupted")
        if plan["engineering_only"]:
            first = launch(restart_plan(plan, None), "first-eight")
            fresh = launch(restart_plan(plan, first, resume=True), "fresh-process-eight-to-sixteen")
        import torch
        from audit_flat_palette import identical

        actual = read(actual_result)
        assert actual["common_model_and_EMA_exact_parent"] and actual["common_backward_absent"]
        state = torch.load(actual["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
        historical = read(plan["historical_preflight" if plan["engineering_only"] else "historical_control"]["path"])
        assert read(actual["observations"]["path"]) == read(historical["observations"]["path"])
        assert actual["captures"][0]["initial_model_sha256"] == historical["captures"][0]["initial_model_sha256"]
        for x, y in zip(actual["logged_observations"], historical["logged_observations"], strict=True):
            assert all(x[k] == y[k] for k in ["step", "domain", "lr", "batch_sha256"])
        old_state = torch.load(historical["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
        for key in ["python_rng", "torch_rng", "cuda_rng"]:
            identical(state[key], old_state[key])
        if plan["engineering_only"]:
            restarted = read(fresh)
            other = torch.load(restarted["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            keys = ["model", "ema", "optimizer", "python_rng", "torch_rng", "cuda_rng", "best", "step", "model_config"]
            for key in keys:
                identical(state[key], other[key])
            assert read(actual["observations"]["path"]) == read(restarted["observations"]["path"])
            assert actual["source_sha256"] == restarted["source_sha256"]
            assert restarted["common_model_and_EMA_exact_parent"]
            assert restarted["common_backward_absent"]
        guard(plan)
        record(
            COMPLETE if plan["engineering_only"] else "completed-original4000-head-only-awaiting-full-quality-and-native-review",
            result=ref(actual_result), fresh_process_result=ref(fresh) if plan["engineering_only"] else None,
            exact_common_model_and_EMA=True, matched_original_inputs_LRs_and_RNG=True,
            fresh_process_all_state_exact=True if plan["engineering_only"] else None,
            engineering_only=plan["engineering_only"],
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            assert alive(status["child"]) and os.getpgid(child.pid) == child.pid
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        record("failed-head-only-study-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("--device", choices=["cpu", "cuda"], required=True)
    p.add_argument("--cpu", type=Path)
    p.add_argument("--cuda", type=Path)
    p.add_argument("--full", action="store_true")
    p = commands.add_parser("run")
    p.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root, args.device, cpu=args.cpu, cuda=args.cuda, full=args.full)
    else:
        run(args.plan)
