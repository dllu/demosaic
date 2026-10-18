"""Isolated full-state mixed16 continuation after its complete native quality review."""

import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import psutil
import yaml

BASE = Path("/mnt/external/demosaic")
REPO = Path("/home/dllu/proj/demosaic")
OLD = BASE / "benchmarks/packed-isotropic-mixed16-first32000-workflow-v1"
ROOT = BASE / "benchmarks/packed-isotropic-mixed16-quarter-workflow-v1"
STATUS = BASE / "runs/packed-isotropic-mixed16-quarter-workflow-v1.json"
DECISION = BASE / "benchmarks/mixed16-native-review-v1/next-budget-decision.json"
START, END = 2000, 10000
SOURCE = "fabd0b781938e156a6dcf89fb429a0a0c7c727e9c1acdb38c434dd201a81ebae"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def save(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


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
        assert sha(path) == digest, path


def resources():
    assert psutil.virtual_memory().available > 32 * 2**30
    # Completed exports leave~506GiB;500GiB still bounds this small checkpoint run.
    assert shutil.disk_usage(BASE).free > 500 * 2**30


def same_recipe(first, second):
    """Only output location and explanatory notes may differ from the original."""
    ignored = {"run", "experiment_notes"}
    assert {k: v for k, v in first.items() if k not in ignored} == {
        k: v for k, v in second.items() if k not in ignored
    }
    assert first["run"] != second["run"]


def release():
    decision = read(DECISION)
    assert (
        decision["status"]
        == "continue-isolated-original-mixed16-schedule-after-complete-quality-review"
    )
    assert (
        decision["start_optimizer_step"],
        decision["end_optimizer_step"],
        decision["original_horizon_optimizer_updates"],
    ) == (START, END, 40000)
    for key in ("quality_review", "review_workflow", "native_views"):
        assert decision[key] == ref(decision[key]["path"])
    workflow = read(decision["review_workflow"]["path"])
    assert (
        workflow["status"]
        == "completed-mixed16-panels-statistics-artifacts-hue-and-sensitivities-awaiting-native-quality-review"
    )
    assert not alive(workflow["controller"]) and not alive(workflow["child"])
    native = read(decision["native_views"]["path"])
    assert native["all_required_viewed"] and native["native_triplets"] == 146
    quality = read(decision["quality_review"]["path"])
    assert not quality["quality_decision"]["promoted"]
    assert quality["next_experiment"]["end_optimizer_step"] == END
    assert decision["parents"] == quality["checkpoints"] == workflow["checkpoints"]
    return decision


def prepare():
    import torch

    assert not torch.cuda.is_initialized() and not ROOT.exists() and not STATUS.exists()
    resources()
    decision = release()
    old = read(OLD / "plan.json")
    guard(old)
    review_plan = read(
        BASE / "benchmarks/packed-isotropic-mixed16-first32000-review-workflow-v1/plan.json"
    )
    guard(review_plan)
    cpu = REPO / "docs/results/mixed16-trained-state-restart-CPU-v1.json"
    assert all(a["full_four_equals_two_plus_two_bitwise"] for a in read(cpu)["arms"])
    paths = []
    for arm in old["arms"]:
        run = BASE / "runs" / (Path(arm["target"]).stem.removesuffix("-step2000") + "-quarter")
        targets = {
            str(step): str(
                Path(arm["target"]).with_name(
                    Path(arm["target"]).name.replace("step2000", f"step{step}")
                )
            )
            for step in (4000, 6000, 8000, END)
        }
        assert not run.exists() and all(not Path(p).exists() for p in targets.values())
        paths.append((run, targets))
    ROOT.mkdir()
    shutil.copyfile(__file__, ROOT / "controller.py")
    inputs = {
        **old["inputs"],
        str(OLD / "plan.json"): sha(OLD / "plan.json"),
        str(DECISION): sha(DECISION),
        str(cpu): sha(cpu),
    }
    for key in ("quality_review", "review_workflow", "native_views"):
        inputs[decision[key]["path"]] = decision[key]["sha256"]
    original_metrics = BASE / "runs/no-dino-packed-isotropic-b4-v71-quarter/metrics.jsonl"
    inputs[str(original_metrics)] = sha(original_metrics)
    arms = []
    for arm, (run, targets), parent in zip(old["arms"], paths, decision["parents"], strict=True):
        assert parent["arm"] == arm["arm"] and ref(arm["target"]) == {
            k: parent[k] for k in ("path", "sha256")
        }
        state = torch.load(arm["target"], map_location="cpu", weights_only=True)
        assert (state["step"], state["data_step"], state["example_draws"]) == (
            START,
            START * 4,
            START * 16,
        )
        assert state["config"]["steps"] == 40000 and state["config"]["source_sha256"] == SOURCE
        assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in state[key].values())
        assert all(int(row["step"]) == START for row in state["optimizer"]["state"].values())
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        log = Path(cfg["run"]) / "metrics.jsonl"
        inputs[str(log)] = sha(log)
        inputs[arm["target"]] = sha(arm["target"])
        run.mkdir()
        for filename in ("last.pt", "best.pt"):
            shutil.copyfile(arm["target"], run / filename)
            assert sha(run / filename) == parent["sha256"]
        shutil.copyfile(log, run / "metrics.jsonl")
        new = copy.deepcopy(cfg)
        new["run"] = str(run)
        new["experiment_notes"] += (
            " Isolated full-state continuation after complete2k review, to10000 optimizer/160000 examples. Original40000-update horizon, data, units, precision, LR and EMA unchanged. Preserve2k evidence; no promotion or extension beyond10k."
        )
        same_recipe(cfg, new)
        path = ROOT / (arm["arm"] + ".yaml")
        path.write_text(yaml.safe_dump(new, sort_keys=False))
        arms.append(
            {
                **arm,
                "config": str(path),
                "run": str(run),
                "prefix_checkpoint": arm["target"],
                "target": targets[str(END)],
                "targets": targets,
                "prefix_metrics": ref(log),
            }
        )
        del state
    plan = {
        **old,
        "root": str(ROOT),
        "status": str(STATUS),
        "driver": str(ROOT / "controller.py"),
        "legacy_worker": ref(OLD / "controller.py"),
        "prefix_updates": START,
        "quality_gate_updates": END,
        "quality_gate_examples": END * 16,
        "arms": arms,
        "inputs": inputs,
        "guards": {**old["guards"], **{str(p): sha(p) for p in ROOT.iterdir() if p.is_file()}},
        "quality_decision": ref(DECISION),
        "original_metrics": ref(original_metrics),
        "source_bundle_sha256": SOURCE,
        "scope": "Reuse frozen production worker for genuine full-state2k->10k, effective16 through4B4. Separate runs/archives preserve2k evidence. Original640k horizon, source/recipe/precision/LR/EMA unchanged. Actual model/Adam/global RNG and EMA/first16 input checks;403 logged groups compared across pair and original source observations. No new-source admission, protected-final scores, promotion or automatic extension beyond10k.",
    }
    save(ROOT / "plan.json", plan)
    guard(plan)
    print(
        json.dumps(
            {
                "prepared": ref(ROOT / "plan.json"),
                "inputs": len(inputs),
                "guards": len(plan["guards"]),
            }
        ),
        flush=True,
    )


def worker(label):
    import torch

    import demosaic.train as training

    plan = read(ROOT / "plan.json")
    guard(plan)
    assert Path(training.__file__).resolve() == Path(plan["work"]) / "src/demosaic/train.py"
    arm = next(a for a in plan["arms"] if a["arm"] == label)
    prior = torch.load(arm["prefix_checkpoint"], map_location="cpu", weights_only=True)
    spec = importlib.util.spec_from_file_location(
        "frozen_mixed16_worker", plan["legacy_worker"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    expected = read(plan["portable_fixtures"]["path"])
    assert [r["production_step"] for r in expected] == list(range(8001, 8017))
    checks = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "parent": ref(arm["prefix_checkpoint"]),
        "first16": [],
    }
    capture = {}
    original = {
        name: getattr(training, name)
        for name in (
            "make_optimizer",
            "set_learning_rate",
            "prepare_training_batch",
            "update_ema",
            "save_checkpoint",
        )
    }

    def record():
        save(ROOT / (label + "-actual-restoration.json"), checks)

    def optimizer(model, cfg):
        result = original["make_optimizer"](model, cfg)
        capture.update(model=model, optimizer=result)
        return result

    def learning_rate(opt, lr):
        if "model_Adam_global_RNG_restored_before_first_update" not in checks:
            model = capture["model"]
            assert legacy.digest(model.restoration_state_dict().items()) == legacy.digest(
                prior["model"].items()
            )
            assert legacy.optimizer_hash(opt.state_dict()) == legacy.optimizer_hash(
                prior["optimizer"]
            )
            assert opt.state_dict()["param_groups"] == prior["optimizer"]["param_groups"]
            assert (
                torch.equal(torch.get_rng_state(), prior["torch_rng"])
                and random.getstate() == prior["python_rng"]
            )
            assert all(
                torch.equal(a, b)
                for a, b in zip(torch.cuda.get_rng_state_all(), prior["cuda_rng"], strict=True)
            )
            checks["model_Adam_global_RNG_restored_before_first_update"] = True
            checks["Adam_param_groups_restored"] = True
            checks["first_optimizer_step"] = START + 1
            record()
        return original["set_learning_rate"](opt, lr)

    def prepare_batch(*args, **kwargs):
        result = original["prepare_training_batch"](*args, **kwargs)
        step, domain = args[:2]
        if len(checks["first16"]) < 16:
            witness = expected[len(checks["first16"])]
            fingerprint = training.batch_fingerprint(result)
            assert (
                step == witness["production_step"]
                and domain == witness["domain"]
                and fingerprint == witness["batch_fingerprint"]
            )
            checks["first16"].append(
                {"data_step": step, "domain": domain, "batch_sha256": fingerprint}
            )
            checks["first16_original_training_inputs_verified"] = len(checks["first16"]) == 16
            record()
        return result

    def ema(model, values, decay):
        if "EMA_restored_before_first_EMA_update" not in checks:
            assert values.keys() == prior["ema"].keys()
            assert all(torch.equal(v.detach().cpu(), prior["ema"][k]) for k, v in values.items())
            checks["EMA_restored_before_first_EMA_update"] = True
            record()
        return original["update_ema"](model, values, decay)

    def checkpoint(path, model, opt, values, step, cfg, best):
        result = original["save_checkpoint"](path, model, opt, values, step, cfg, best)
        if Path(path).name == "last.pt" and str(step) in arm["targets"] and step != END:
            target = Path(arm["targets"][str(step)])
            if not target.exists():
                shutil.copyfile(path, target)
                assert sha(target) == sha(path)
                save(
                    ROOT / f"{label}-step{step}-saved.json",
                    {"checkpoint": ref(target), "step": step},
                )
        return result

    for name, function in zip(
        original, (optimizer, learning_rate, prepare_batch, ema, checkpoint), strict=True
    ):
        setattr(training, name, function)
    try:
        legacy.worker(ROOT / "plan.json", label, "finish")
    finally:
        for name, function in original.items():
            setattr(training, name, function)
    assert (
        checks["first16_original_training_inputs_verified"]
        and checks["EMA_restored_before_first_EMA_update"]
    )
    checks["completed_continuation"] = True
    record()


def audit_logs(plan):
    logs = []
    original = {
        r["step"]: r
        for line in Path(plan["original_metrics"]["path"]).read_text().splitlines()
        if (r := json.loads(line)).get("event") == "train"
    }
    overlaps = []
    expected = [1, 13, *range(25, START + 1, 25), START + 1, *range(START + 25, END + 1, 25)]
    for arm in plan["arms"]:
        path = Path(arm["run"]) / "metrics.jsonl"
        assert path.read_bytes().startswith(Path(arm["prefix_metrics"]["path"]).read_bytes())
        rows = [
            r
            for line in path.read_text().splitlines()
            if (r := json.loads(line)).get("event") == "train"
        ]
        assert [r["step"] for r in rows] == expected and len(rows) == 403
        count = 0
        for row in rows:
            step = row["step"]
            progress = max(0, step - 500) / 39500
            lr = 2e-4 * min(1, step / 500) * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            assert row["lr"] == lr and row["example_draws"] == step * 16
            for group in row["source_groups"]:
                if group["data_step"] in original:
                    old = original[group["data_step"]]
                    domain = {
                        "synthetic": "commons",
                        "native-RAW-synthetic": "native",
                        "paired-RAW": "paired",
                    }[old["domain"]]
                    assert (
                        group["domain"] == domain and group["batch_sha256"] == old["batch_sha256"]
                    )
                    count += 1
        assert count == 403
        overlaps.append(count)
        logs.append(rows)
    for a, b in zip(*logs, strict=True):
        assert all(
            a[k] == b[k] for k in ("step", "lr", "batch_sha256", "source_groups", "example_draws")
        )
    return {
        "logged_macro_rows_per_arm": 403,
        "all_logged_pair_observations_equal": True,
        "original_source_overlaps_per_arm": overlaps,
    }


def controller():
    assert not STATUS.exists()
    plan = read(ROOT / "plan.json")
    guard(plan)
    release()
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(ROOT / "plan.json"),
        "completed": {},
    }

    def record(stage, **values):
        info.update(status=stage, updated_unix=time.time(), **values)
        save(STATUS, info)
        print(json.dumps({"status": stage, **values}), flush=True)

    with (ROOT / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        for arm in plan["arms"]:
            guard(plan)
            resources()
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(plan["work"]) / "src")
                + ":"
                + str(Path(plan["work"]) / "tools"),
                "HF_HUB_OFFLINE": "1",
            }
            with (ROOT / (arm["arm"] + ".log")).open("xb") as log:
                process = subprocess.Popen(
                    [plan["python"], "-P", plan["driver"], "worker", "--arm", arm["arm"]],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
                record("training-mixed16-quarter", arm=arm["arm"], child=owner)
                assert process.wait() == 0, arm["arm"]
            assert not alive(owner)
            result_path = ROOT / f"finish-{arm['arm']}-result.json"
            result = read(result_path)
            assert (
                result["end_optimizer_step"] == END
                and result["actual_prepared_source_groups"] == (END - START) * 4
            )
            assert result["source_bundle_SHA256"] == SOURCE
            target = Path(arm["target"])
            assert not target.exists()
            shutil.copyfile(result["checkpoint"]["path"], target)
            assert ref(target)["sha256"] == result["checkpoint"]["sha256"]
            info["completed"][arm["arm"]] = {
                "checkpoint": ref(target),
                "result": ref(result_path),
                "actual_restoration": ref(ROOT / (arm["arm"] + "-actual-restoration.json")),
            }
            record("completed-mixed16-quarter-arm", child=owner)
        verification = audit_logs(plan)
        guard(plan)
        record(
            "completed-matched-mixed16-quarter160000-examples-awaiting-full-quality-review",
            verification=verification,
        )
    except BaseException as error:
        record("failed-no-automatic-restart-or-promotion", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("--arm", choices=("no-dino", "dino"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "worker":
        worker(args.arm)
    else:
        with (REPO / ".cache/mixed16-quarter-v1.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            controller()
