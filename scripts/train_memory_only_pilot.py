"""Adopt V139's checked prefixes and run one fresh, bounded1000-update pilot."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

CHECKS = REPO / ".cache/current-quality-20261023-v1/raw-global-memory-only-pilot-v1/run"
BASE = CHECKS.parents[1]


def require_checked_result(result):
    """Adopt only the original completed16+2 implementation check."""
    assert result["status"] == "completed-memory-only-global-implementation-check"
    assert result["arm"] == "V139" and result["phase"] in ("CPU", "CUDA")
    assert result["updates"] == result["all_AdamW_steps"] == 18
    assert result["model_EMA_tensor_count"] == 106 and result["optimizer_state_count"] == 15
    assert result["raw_global_only"] and result["frozen_parent91_model_and_EMA_exact"]
    assert result["model_EMA_Adam_finite"] and result["frozen_encoder_no_gradients"]
    assert result["all_observed_inputs_match_saved_control"]
    assert all(
        result["counts"][k] == 18
        for k in (
            "training_forwards",
            "encoder_forwards",
            "optimizer_steps",
            "prepared_training_batches",
        )
    )
    assert len(result["changed_global_resume_rejections"]) == 7


def memory_dependency_ready(state, owner, owner_live):
    """Completion and exact-owner exit, without a score/promotion threshold."""
    assert state["owner"] == owner
    assert not state["status"].startswith("failed"), state
    completed = state["status"] == "completed-V138-memory-diagnostic-awaiting-review"
    if not owner_live:
        assert completed, "Dependency owner exited without its completed receipt"
    return completed and not owner_live


def prepare(root):
    import yaml

    original = read(CHECKS / "plan.json")
    guard(original)
    audit = read(CHECKS / "independent-audit-v1.json")
    assert audit["status"].startswith("passed-independent-memory-only")
    memory = BASE / "V138-trained-memory-mechanism-v1"
    memory_launch = read(memory / "launch-v1.json")
    assert live(memory_launch["owner"])
    assert read(memory / "status.json")["owner"] == memory_launch["owner"]
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    old_work = Path(original["work"])
    for directory in ("src", "scripts", "configs"):
        shutil.copytree(
            old_work / directory, work / directory, ignore=shutil.ignore_patterns("__pycache__")
        )
    script = work / "scripts" / Path(__file__).name
    shutil.copyfile(__file__, script)
    config = yaml.safe_load(Path(original["arms"]["V139"]["train"]).read_text())
    assert config["steps"] == 1000 and config["raw_global_only"] is True
    assert config["model"]["raw_global_conditioning"] == "memory-only-v3"
    config["run"] = str(work / "artifacts/train/V139")
    config["validation_protocol"] = str(work / "configs/evaluation.yaml")
    train = work / "configs/train-V139.yaml"
    train.write_text(yaml.safe_dump(config, sort_keys=False))
    plan = {
        **original,
        "root": str(root),
        "work": str(work),
        "artifact_root": str(work / "artifacts"),
        "worker_script": ref(script),
        "core_worker_script": ref(work / "scripts/train_reviewed_shadow_trial.py"),
        "parent_selection": ref(work / "configs/parent-selection.json"),
        "arms": {"V139": {**original["arms"]["V139"], "train": str(train)}},
        "phase_result_status": "completed-memory-only-global-pilot-training-phase",
        "maximum_train_worker_seconds": 28800,
        "gradient_observation_steps": sorted({*range(1, 17), *range(25, 1001, 25)}),
        "adopted_phase_results": {},
        "production_launched": False,
        "memory_dependency": {
            "status": str(memory / "status.json"),
            "owner": memory_launch["owner"],
            "policy": ref(memory / "queue-policy-v1.json"),
            "absolute_deadline_unix": read(memory / "queue-policy-v1.json")[
                "original_absolute_deadline_unix"
            ],
        },
        "headroom_wait_seconds": 7200,
    }
    # Exact receipt copies retain their original checkpoint/input/source paths.
    adopted = []
    for phase in ("CPU", "CUDA"):
        src = CHECKS / f"{phase}-V139-result.json"
        result = read(src)
        require_checked_result(result)
        assert (
            not live(result["owner"]) and ref(result["checkpoint"]["path"]) == result["checkpoint"]
        )
        dest = root / src.name
        shutil.copyfile(src, dest)
        assert dest.read_bytes() == src.read_bytes()
        plan["adopted_phase_results"][f"{phase}-V139"] = ref(dest)
        adopted.extend((ref(src), ref(dest)))
    control = read(BASE / "raw-global-only-pilot-v1/run/plan.json")
    plan["prospective_domain_batches"] = control["prospective_domain_batches"]
    plan["inputs"] = [
        *original["inputs"],
        ref(CHECKS / "plan.json"),
        ref(CHECKS / "independent-audit-v1.json"),
        *adopted,
        plan["memory_dependency"]["policy"],
        ref(BASE / "raw-global-only-pilot-v1/run/plan.json"),
    ]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan["scope"] = (
        "Original V139 fresh1000-update memory-only pilot, never resume a discarded18-update check. "
        "Adopt exact completed CPU/CUDA16+2 receipts without rerunning checks. Same68 neural modules, "
        "V12020k parent,90782/27,seed70/quota.5/zeroPSF/native256B16BF16/15trainable tensors/LR1e-3/warm100. "
        "Every clean/noisy batch matches savedV137; later endpoint also compares actualV138 hashes. "
        "Wait originalV138 primary/faint/memory chain to complete and exact memory owner exit, within its "
        "original absolute dependency deadline. Then52GiB/128GiB internal/208GiB external admission stable15s; "
        "2h headroom limit,16GiB CUDAcap,32GB runtime floor,8h worker. No existing queue/guard/data change, "
        "old inference, retry, schedule reset or extension. Train1000 plus64 validation/1064encoder calls. "
        "Quality review is separately frozen; trained quality remains unmeasured."
    )
    save(root / "plan.json", plan)
    guard(plan)
    return root / "plan.json"


def controller(path):
    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {
        "controller": owner,
        "plan": ref(path),
        "completed": dict(plan["adopted_phase_results"]),
    }
    child = child_owner = None

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        dependency = plan["memory_dependency"]
        record("waiting-for-original-V138-memory-review", child=None)
        while True:
            guard(plan)
            assert time.time() < dependency["absolute_deadline_unix"]
            observed = read(dependency["status"])
            if memory_dependency_ready(observed, dependency["owner"], live(dependency["owner"])):
                for key in ("result", "independent_audit", "comparison"):
                    assert ref(observed[key]["path"]) == observed[key]
                assert read(observed["independent_audit"]["path"])["status"].startswith("passed")
                break
            time.sleep(15)
        deadline, stable = time.time() + plan["headroom_wait_seconds"], None
        record(
            "waiting-for-training-headroom",
            phase="train",
            arm="V139",
            headroom_deadline_unix=deadline,
        )
        while True:
            assert time.time() < deadline
            enough = (
                psutil.virtual_memory().available >= 52 * 2**30
                and shutil.disk_usage(root).free >= 128 * 2**30
                and shutil.disk_usage("/mnt/external").free >= 208 * 2**30
            )
            stable = (time.monotonic() if stable is None else stable) if enough else None
            if stable is not None and time.monotonic() - stable >= 15:
                break
            time.sleep(2)
        guard(plan)
        env = dict(
            os.environ,
            CUDA_VISIBLE_DEVICES="0",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
        )
        with (root / "train-V139-v1.log").open("x") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker_script"]["path"], "worker", str(path)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-memory-only-training", child=child_owner)
            assert child.wait(timeout=plan["maximum_train_worker_seconds"]) == 0
        binding = ref(root / "train-V139-result.json")
        result = read(binding["path"])
        assert result["updates"] == 1000 and not live(result["owner"])
        state["completed"]["train-V139"] = binding
        record("completed-training-awaiting-model-comparisons", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-training-preserved-no-automatic-retry", child=None, error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), "train", "V139")
