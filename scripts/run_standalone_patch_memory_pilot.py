"""Run the checked V140 recipe independently of the failed October job chain.

Old plans, failures and checks stay immutable. This is a new, explicitly bound
1k run from V120, using the original trained source and all V137 batch witnesses.
"""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_patch_memory_pilot import require_checked_result
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/current-quality-20261023-v1"
ORIGINAL = BASE / "raw-patch-memory-training-v1/run"


def prepare(root):
    original = read(ORIGINAL / "plan.json")
    guard(original)
    status = read(ORIGINAL / "status.json")
    assert status["status"].startswith("failed-") and not live(status["controller"])
    assert not list((Path(original["work"]) / "artifacts/train/V140").glob("*.pt"))
    assert not (ORIGINAL / "train-V140-result.json").exists()
    assert original["train_updates"] == 1000
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for directory in ("src", "scripts", "configs"):
        shutil.copytree(
            Path(original["work"]) / directory,
            work / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    # The trainer preserves dependency files and third-party license notices.
    # The older unlaunched V140 work directory omitted these required assets.
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(REPO / name, work / name)
    shutil.copytree(REPO / "third_party", work / "third_party")
    config = yaml.safe_load(Path(original["arms"]["V140"]["train"]).read_text())
    config["run"] = str(work / "artifacts/train/V140")
    config["validation_protocol"] = str(work / "configs/evaluation.yaml")
    train_path = work / "configs/standalone-V140.yaml"
    train_path.write_text(yaml.safe_dump(config, sort_keys=False))
    adopted = []
    for phase in ("CPU", "CUDA"):
        source = ORIGINAL / f"{phase}-V140-result.json"
        result = read(source)
        require_checked_result(result)
        assert not live(result["owner"])
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        destination = root / source.name
        shutil.copyfile(source, destination)
        adopted.extend([ref(source), ref(destination)])
    scope = (
        "Standalone V140 fresh1000 from V120 EMA, original checked recipe/source, "
        "90782/27, seed70, quota.5, zeroPSF, B16/native256/BF16, frozen91 parent "
        "tensors, 16 trainable patch-memory tensors, LR1e-3/warm100. "
        "All1000 clean/noisy batches must match saved V137. Adopt existing CPU/CUDA16+2 "
        "checks. The old V125 memory-reserve failure and dependent queues stay unchanged. "
        "This explicitly separate run removes their execution dependency, without claiming "
        "V139 comparison or an isolated descriptor ablation. 12GiB CUDA cap, 50GiB "
        "launch RAM, 32GB runtime floor, original8h timeout, no automatic retries. "
        "Quality requires subsequent matched native/faint/GFX review."
    )
    plan = {
        **original,
        "root": str(root),
        "work": str(work),
        "artifact_root": str(work / "artifacts"),
        "arms": {"V140": {**original["arms"]["V140"], "train": str(train_path)}},
        "worker_script": ref(work / "scripts/train_patch_memory_pilot.py"),
        "core_worker_script": ref(work / "scripts/train_reviewed_shadow_trial.py"),
        "inputs": [
            *original["inputs"],
            ref(ORIGINAL / "plan.json"),
            ref(ORIGINAL / "status.json"),
            *adopted,
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": scope,
        "execution_dependency_removed": original["quality_dependency"],
        "quality_dependency": None,
        "production_launched": False,
    }
    path = root / "plan.json"
    save(path, plan)
    guard(plan)
    return path


def run(path):
    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    assert psutil.virtual_memory().available >= 50 * 2**30
    assert shutil.disk_usage(root).free >= 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free >= 208 * 2**30
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
        "status": "starting-standalone-V140",
    }

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "standalone-status.json", state)

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
    child = None
    try:
        with (root / "train-V140.log").open("x") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["worker_script"]["path"], "worker", str(path)],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            record(
                "running-standalone-V140",
                child={"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
            )
            code = child.wait(timeout=plan["maximum_train_worker_seconds"])
            assert code == 0, ("worker exit", code)
        result = read(root / "train-V140-result.json")
        assert result["updates"] == 1000 and not live(result["owner"])
        record(
            "completed-standalone-V140-awaiting-quality-review",
            child=None,
            result=ref(root / "train-V140-result.json"),
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
            child.wait(timeout=30)
        record("failed-standalone-V140-no-automatic-retry", child=None, error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    else:
        run(args.path.resolve())
