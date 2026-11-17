"""Start bound CPU reviews after the existing20k training phase completes."""

import argparse
import copy
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil
import torch

from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json


def live(identity):
    try:
        process = psutil.Process(identity["pid"])
        return (
            process.create_time() == identity["create_time"]
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def run(path):
    plan = read_json(path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    os.nice(10)
    os.sched_setaffinity(0, [8, 9, 10, 11])
    root = Path(plan["root"])
    (root / "queue.claim").open("x").close()
    owner = {"pid": os.getpid(), "create_time": psutil.Process().create_time()}

    def status(state, **details):
        write_json(
            root / "status.json",
            {
                "owner": owner,
                "status": state,
                "observed_unix": time.time(),
                "plan": reference(path),
                **details,
            },
            replace=True,
        )

    stage_result = Path(plan["training_stage_result"])
    missing = 0
    while not stage_result.exists():
        controller_alive = live(plan["training_controller_owner"])
        worker_alive = live(plan["training_worker_owner"])
        missing = 0 if controller_alive or worker_alive else missing + 1
        if missing >= 3:
            status("stopped-without-training-completion-receipt")
            return
        status(
            "waiting-for-existing20k-training",
            controller_alive=controller_alive,
            worker_alive=worker_alive,
        )
        time.sleep(10)
    stage = read_json(stage_result)
    assert stage["production_plan"] == plan["training_plan"]
    if stage["returncode"]:
        status("training-stage-failed-no-retry", terminal_stage=reference(stage_result))
        return
    trained = read_json(Path(plan["training_run"]) / "completed.json")
    phase = read_json(checked(trained["phase"]))
    assert phase["production_plan"] == plan["training_plan"]
    assert trained["steps"] == phase["to_step"] == phase["LR_horizon"] == 20000
    assert phase["from_step"] == 13000 and phase["training_updates"] == 7000
    assert phase["optimizer_EMA_RNG_preserved_on_resume"] and phase["DINO_unchanged"]
    binding = trained["checkpoint"]
    assert phase["last"] == binding
    retained = read_json(Path(plan["training_run"]) / "step020000-receipt.json")
    assert retained["checkpoint"]["sha256"] == binding["sha256"]
    assert retained["global_step"] == retained["LR_horizon"] == 20000
    checkpoint = torch.load(checked(binding), map_location="cpu", weights_only=True)
    assert checkpoint["step"] == checkpoint["config"]["steps"] == 20000
    assert len(checkpoint["model"]) == len(checkpoint["ema"]) == 91
    assert len(checkpoint["optimizer"]["state"]) == 89
    assert all(s["step"] == 20000 for s in checkpoint["optimizer"]["state"].values())
    assert all(
        torch.isfinite(v).all() for group in ["model", "ema"] for v in checkpoint[group].values()
    )
    assert all(
        torch.isfinite(v).all()
        for s in checkpoint["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )
    assert checkpoint["python_rng"] and checkpoint["cuda_rng"] and checkpoint["torch_rng"].numel()
    del checkpoint
    write_json(
        root / "endpoint-admission.json",
        {
            "queue_plan": reference(path),
            "training_stage": reference(stage_result),
            "training_completion": reference(Path(plan["training_run"]) / "completed.json"),
            "phase_completion": trained["phase"],
            "checkpoint": binding,
            "raw_EMA_Adam_RNG_finite_and_complete": True,
            "scope": "Actual completed20k/320k-example trajectory with original horizon; previous failed/replayed work remains separate. Numerical/native review begins after this receipt; no quality/promotion claim.",
        },
    )
    work = root / "review-work"
    shutil.copytree(
        Path(plan["qualified_work"]), work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    native_template = read_json(checked(plan["native_template"]))
    native_work = Path(native_template["work"])
    for source, digest in native_template["frozen_files"].items():
        relative = Path(source).relative_to(native_work)
        if relative.parts[0] == "scripts" and not (work / relative).exists():
            target = work / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checked({"path": source, "sha256": digest}), target)
    for source in plan["review_scripts"]:
        shutil.copyfile(checked(source), work / "scripts" / Path(source["path"]).name)
    frozen = {str(p): reference(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    template = read_json(checked(plan["primary_template"]))
    models = {
        "V120": dict(template["models"]["V120"], weights="EMA", display_label="V120 EMA"),
        "scale-control20k": {
            "checkpoint": binding,
            "step": 20000,
            "weights": "EMA",
            "display_label": "Corpus20k EMA",
            "retained_progress": True,
            "training_horizon": 20000,
        },
    }
    common = {
        "work": str(work),
        "frozen_files": frozen,
        "models": models,
        "inputs": [
            reference(path),
            reference(root / "endpoint-admission.json"),
            *[s["checkpoint"] for s in models.values()],
        ],
        "parent_label": "V120",
    }
    native_root = root / "native20k"
    native_root.mkdir()
    native = {
        **copy.deepcopy(native_template),
        **common,
        "root": str(native_root),
        "collector": reference(work / "scripts/collect_full_corpus_checkpoint_review.py"),
        "triplet_model": "scale-control20k",
        "maximum_seconds": 10800,
        "training_plan": plan["training_plan"],
        "retained_checkpoint_receipt": reference(
            Path(plan["training_run"]) / "step020000-receipt.json"
        ),
        "scope": "Completed20k EMA with fresh matched V120 on all110 fixed material/flat/standing-GFX inputs. No new GPU/RAW/noise/optimizer work. Native viewing and full primary scores remain separate.",
    }
    write_json(native_root / "plan.json", native)
    preflight_root = root / "primary20k-preflight"
    preflight_root.mkdir()
    preflight = {
        **copy.deepcopy(template),
        **common,
        "root": str(preflight_root),
        "driver": reference(work / "scripts/collect_local_primary.py"),
        "kind": "preflight",
        "maximum_seconds": 3600,
    }
    write_json(preflight_root / "plan.json", preflight)
    children = []

    def launch(script, child_plan, threads, label):
        env = dict(
            os.environ,
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            CUDA_VISIBLE_DEVICES="",
            OMP_NUM_THREADS=str(threads),
            OPENBLAS_NUM_THREADS=str(threads),
            MKL_NUM_THREADS=str(threads),
            PYTHONUNBUFFERED="1",
        )
        command = [sys.executable, str(script), str(child_plan)]
        with (root / (label + ".log")).open("x") as stream:
            process = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
        identity = {
            "pid": process.pid,
            "create_time": psutil.Process(process.pid).create_time(),
            "plan": reference(child_plan / "plan.json" if child_plan.is_dir() else child_plan),
            "command": command,
            "label": label,
        }
        write_json(root / (label + "-launch.json"), identity)
        children.append((process, identity))
        return process

    launch(
        work / "scripts/collect_full_corpus_checkpoint_review.py",
        native_root / "plan.json",
        2,
        "native20k",
    )
    preflight_child = launch(
        work / "scripts/collect_local_primary.py",
        preflight_root / "plan.json",
        4,
        "primary20k-preflight",
    )
    status(
        "reviewing-native-and-primary-preflight", children=[identity for _, identity in children]
    )
    while preflight_child.poll() is None:
        time.sleep(10)
    write_json(
        root / "primary20k-preflight-returncode.json", {"returncode": preflight_child.returncode}
    )
    if preflight_child.returncode == 0:
        qualification = read_json(preflight_root / "collection/result.json")
        assert qualification["all_complete"] and qualification["cases"] == 3
        primary_root = root / "primary20k"
        primary_root.mkdir()
        primary = {
            **preflight,
            "root": str(primary_root),
            "kind": "full",
            "maximum_seconds": 172800,
            "preflight": reference(preflight_root / "collection/result.json"),
            "scope": "All3162 exact canonical primary cases:427 photos plus16 separate synthetic sources across7 conditions/4 CFAs,24 known and30 unseen camera batches. Fresh matched CPU EMA V120/control20k, B4/4threads/IEEE FP32,0 GPU/RAW/new corruption/optimizer calls. Original metric formulas/reference SSIM; exact canonical inputs unchanged. Source-bound history and actual native review follow completed results, never preflight means.",
        }
        primary["inputs"] = [*primary["inputs"], primary["preflight"]]
        write_json(primary_root / "plan.json", primary)
        launch(
            work / "scripts/collect_local_primary.py", primary_root / "plan.json", 4, "primary20k"
        )
    status("CPU-reviews-running", children=[identity for _, identity in children])
    results = []
    for process, identity in children:
        while process.poll() is None:
            status("CPU-reviews-running", children=[v for _, v in children])
            time.sleep(10)
        result = {"child": identity, "returncode": process.returncode}
        if identity["label"] == "native20k" and process.returncode == 0:
            reporter = launch(
                work / "scripts/report_full_corpus_checkpoint_review.py",
                native_root,
                2,
                "native20k-report",
            )
            while reporter.poll() is None:
                time.sleep(10)
            result["NumPy_report_returncode"] = reporter.returncode
        results.append(result)
    write_json(
        root / "result.json",
        {
            "plan": reference(path),
            "results": results,
            "scope": "Declared20k CPU reviews completed or explicitly failed; no retry/reset/promotion. Native viewing, full-independent audits and documentation/history publication remain separate.",
        },
    )
    status("CPU-review-jobs-terminal", results=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
