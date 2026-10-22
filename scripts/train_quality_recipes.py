"""Run source-frozen quality recipes with short discarded smokes and bounded jobs."""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def prepare(root, artifact_root, recipes):
    import yaml

    selection = read(REPO / "configs/current-model.json")
    parent = selection["checkpoint"]
    assert ref(parent["path"]) == parent
    root, artifact_root = root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    root.mkdir(parents=True, exist_ok=False)
    artifact_root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / name
        for name in (
            "scripts/train_quality_recipes.py",
            "scripts/train_directional_bank_trial.py",
            "scripts/train_v43_quality_trial.py",
            "scripts/profile_raw_kernel_inference.py",
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/dinov3/LICENSE.md",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
        )
    ]
    for source in files:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    inputs = [parent, ref(REPO / "configs/current-model.json")]
    arms = {}
    for recipe in recipes:
        config = yaml.safe_load(recipe.read_text())
        name = "V100" if recipe.stem.endswith("v100") else "V101"
        assert name not in arms
        assert config["initialize_parent"]["sha256"] == parent["sha256"]
        assert config["steps"] == 10000 and config["batch_size"] == 16
        assert config["model"]["dino_feature_fusion"] == "convnext-pyramid"
        inputs.append(ref(recipe))
        for key in (
            "manifest",
            "validation_manifest",
            "raw_clean_manifest",
            "paired_manifest",
            "reviewed_roi_catalogue",
        ):
            inputs.append(ref(config[key]))
        arms[name] = {}
        for phase in ("CPU", "CUDA", "train"):
            actual = dict(config, run=str(artifact_root / phase / name))
            actual["validation_protocol"] = str(work / "configs/evaluation.yaml")
            if phase == "CPU":
                actual.update(
                    device="cpu",
                    precision="float32",
                    amp=False,
                    batch_size=1,
                    patch_size=64,
                    workers=0,
                    paired_workers=0,
                    raw_clean_workers=0,
                    cpu_threads=2,
                    log_every=1,
                )
            elif phase == "CUDA":
                actual["log_every"] = 1
            path = work / "configs" / f"{phase}-{name}.yaml"
            path.write_text(yaml.safe_dump(actual, sort_keys=False))
            arms[name][phase] = str(path)
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifact_root),
        "parent": parent,
        "arms": arms,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "python": sys.executable,
        "smoke_updates": 8,
        "train_updates": 10000,
        "scope": "V84 architecture on curated Commons; original augmentation versus fine-detail package. CPU64/B1 and CUDA256/B16 eight-update smokes are discarded; both production arms start freshly from the same V84 final EMA.",
    }
    save(root / "plan.json", plan)
    return root / "plan.json"


def worker(path, phase, arm):
    import torch
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(path)
    guard(plan)
    if phase != "CPU":
        torch.cuda.set_per_process_memory_fraction(
            24 * 2**30 / torch.cuda.get_device_properties(0).total_memory
        )
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    constructor, captured = training.JointDemosaic, {}

    def instrument(config):
        model = constructor(config)
        captured["model"] = model

        def check_initial(module, args):
            actual = module.restoration_state_dict()
            assert actual.keys() == parent["ema"].keys()
            assert all(torch.equal(actual[k].cpu(), value) for k, value in parent["ema"].items())
            captured["initial_EMA_exact"] = True
            captured["DINO_sha256"] = model_hash(module.context.backbone)
            assert (
                captured["DINO_sha256"]
                == "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd"
            )
            hook.remove()

        hook = model.register_forward_pre_hook(check_initial)
        return model

    training.JointDemosaic = instrument
    expected = plan["train_updates"] if phase == "train" else plan["smoke_updates"]
    try:
        checkpoint = training.train(
            plan["arms"][arm][phase], initialize=plan["parent"]["path"], stop_after=expected
        )
    finally:
        training.JointDemosaic = constructor
    model = captured.pop("model")
    assert model_hash(model.context.backbone) == captured["DINO_sha256"]
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == expected
    assert all(
        torch.isfinite(value).all() for field in ("model", "ema") for value in state[field].values()
    )
    assert all(
        torch.isfinite(value).all()
        for group in state["optimizer"]["state"].values()
        for value in group.values()
        if isinstance(value, torch.Tensor)
    )
    guard(plan)
    save(
        Path(plan["root"]) / f"{phase}-{arm}-result.json",
        {
            "status": "completed-quality-training-phase",
            "phase": phase,
            "arm": arm,
            "updates": expected,
            "checkpoint": ref(checkpoint),
            "initialization": captured,
            "source_sha256": state["config"]["source_sha256"],
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": "Discarded implementation smoke"
            if phase != "train"
            else "Trained endpoint awaiting current quality/image comparison",
        },
    )


def controller(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        for phase in ("CPU", "CUDA", "train"):
            for arm in plan["arms"]:
                guard(plan)
                record("waiting-for-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    assert time.monotonic() - began < 7200
                    enough = (
                        psutil.virtual_memory().available >= 48 * 2**30
                        and shutil.disk_usage(root).free >= 32 * 2**30
                        and shutil.disk_usage(plan["artifact_root"]).free >= 256 * 2**30
                    )
                    stable = (time.monotonic() if stable is None else stable) if enough else None
                    if stable is not None and time.monotonic() - stable >= 15:
                        break
                    time.sleep(2)
                work = Path(plan["work"])
                env = dict(
                    os.environ,
                    PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
                    CUDA_VISIBLE_DEVICES="" if phase == "CPU" else "0",
                    HF_HUB_OFFLINE="1",
                    TRANSFORMERS_OFFLINE="1",
                    OMP_NUM_THREADS="2" if phase == "CPU" else "4",
                    OPENBLAS_NUM_THREADS="1",
                    CUBLAS_WORKSPACE_CONFIG=":4096:8",
                )
                with (root / f"{phase}-{arm}.log").open("x") as log:
                    child = subprocess.Popen(
                        [
                            plan["python"],
                            "-P",
                            str(work / "scripts/train_quality_recipes.py"),
                            "worker",
                            str(path),
                            "--phase",
                            phase,
                            "--arm",
                            arm,
                        ],
                        cwd=work,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                    record("running-quality-training", phase=phase, arm=arm, child=owner)
                    started = time.monotonic()
                    while child.poll() is None:
                        assert time.monotonic() - started < (43200 if phase == "train" else 1200)
                        assert shutil.disk_usage(root).free > 16 * 2**30
                        assert shutil.disk_usage(plan["artifact_root"]).free > 128 * 2**30
                        time.sleep(2)
                    assert child.wait() == 0, (phase, arm, child.returncode)
                result = root / f"{phase}-{arm}-result.json"
                assert read(result)["owner"] == owner and not live(owner)
                state["completed"][f"{phase}-{arm}"] = ref(result)
                record("completed-quality-training-phase")
        record("completed-training-awaiting-model-comparisons")
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-training-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--recipes", type=Path, nargs="+")
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm")
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.artifacts, args.recipes))
    elif args.mode == "controller":
        controller(args.path)
    else:
        worker(args.path, args.phase, args.arm)
