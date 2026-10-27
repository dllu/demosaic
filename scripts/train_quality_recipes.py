"""Run source-frozen quality recipes with short discarded smokes and bounded jobs."""

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from frozen_backbone_identity import (
    CONVNEXT_TINY_SHA256,
    backbone_identity,
    verify_backbone_identity,
)
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def storage_policy(root, artifact_root):
    """Allow frozen-workspace outputs while retaining legacy external limits."""
    root, artifact_root = Path(root).resolve(), Path(artifact_root).resolve()
    if not root.is_relative_to(REPO / ".cache"):
        raise ValueError("Training workspace must be inside the repository cache")
    internal = artifact_root.is_relative_to(root / "work")
    if not internal and not artifact_root.is_relative_to(Path("/mnt/external/demosaic")):
        raise ValueError("Training artifacts need the frozen workspace or external scratch")
    return {
        "internal_artifacts": internal,
        "phase_start_internal_free_GiB": 128 if internal else 32,
        "runtime_internal_reserve_GiB": 96 if internal else 16,
        "phase_start_external_free_GiB": 208 if internal else 256,
        "runtime_external_reserve_GiB": 208 if internal else 128,
    }


def prepare(root, artifact_root, recipes, after_run_root=None):
    policy = storage_policy(root, artifact_root)
    import torch
    import yaml

    configs = [yaml.safe_load(recipe.read_text()) for recipe in recipes]
    lineage = configs[0]["initialize_parent"]
    assert all(config["initialize_parent"] == lineage for config in configs)
    parent = {key: lineage[key] for key in ("path", "sha256")}
    assert ref(parent["path"]) == parent
    parent_hash = configs[0].get("parent_dino_sha256", CONVNEXT_TINY_SHA256)
    assert all(c.get("parent_dino_sha256", CONVNEXT_TINY_SHA256) == parent_hash for c in configs)
    parent_state = torch.load(parent["path"], map_location="cpu", weights_only=True, mmap=True)
    parent_backbone = backbone_identity(parent_state["model_config"], parent_hash)
    del parent_state
    updates = configs[0]["steps"]
    assert isinstance(updates, int) and updates >= 8
    assert all(config["steps"] == updates for config in configs)
    root, artifact_root = root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    artifact_root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / name
        for name in (
            "scripts/train_quality_recipes.py",
            "scripts/frozen_backbone_identity.py",
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
    # Recipes explicitly select their parent. Never pin the mutable recommendation
    # file: documentation/model selection must be able to advance during a run.
    parent_selection = work / "configs/parent-selection.json"
    save(parent_selection, {"checkpoint": parent, "step": lineage["step"]})
    inputs = [parent]
    dependency = None
    if after_run_root is not None:
        after_run_root = after_run_root.resolve()
        assert after_run_root.is_relative_to(REPO / ".cache")
        status = read(after_run_root / "status.json")
        dependency_plan = ref(after_run_root / "plan.json")
        guard(read(dependency_plan["path"]))
        assert status["plan"] == dependency_plan
        terminal = "completed-GFX-fullframe-exports-awaiting-image-review"
        assert status["status"] in ("running-GFX-fullframe-exports", terminal)
        dependency_child = (
            status["child"]
            if status["status"] != terminal
            else read(status["result"]["path"])["owner"]
        )
        dependency = {
            "root": str(after_run_root),
            "plan": dependency_plan,
            "controller": status["controller"],
            "child": dependency_child,
            "terminal_status": terminal,
        }
        inputs.append(dependency_plan)
    arms, backbones = {}, {}
    for recipe, config in zip(recipes, configs, strict=True):
        match = re.search(r"(?:^|-)(v\d+)$", recipe.stem, re.IGNORECASE)
        assert match is not None, "Recipe filename must end in its explicit model version"
        name = match[1].upper()
        assert name not in arms
        assert config["initialize_parent"]["sha256"] == parent["sha256"]
        assert config["batch_size"] == 16 and config["patch_size"] == 256
        assert config["model"]["dino_feature_fusion"] == "convnext-pyramid"
        backbones[name] = backbone_identity(
            config["model"], config.get("expected_dino_sha256", CONVNEXT_TINY_SHA256)
        )
        inputs.append(ref(recipe))
        for key in (
            "manifest",
            "validation_manifest",
            "raw_clean_manifest",
            "paired_manifest",
            "reviewed_roi_catalogue",
        ):
            inputs.append(ref(config[key]))
        if config.get("photo_sampling_reference_manifest") is not None:
            inputs.append(ref(config["photo_sampling_reference_manifest"]))
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
        "parent_step": lineage["step"],
        "parent_backbone": parent_backbone,
        "backbones": backbones,
        "parent_selection": ref(parent_selection),
        "after_run": dependency,
        "arms": arms,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "python": sys.executable,
        "smoke_updates": 8,
        "train_updates": updates,
        **policy,
        "scope": f"Matched explicit-parent V84-family quality recipes, {updates} updates. CPU64/B1 and CUDA256/B16 eight-update smokes are discarded; production arms start freshly from the same parent EMA. Recipe files record the intended experimental difference.",
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
    assert parent["step"] == plan["parent_step"]
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
            verify_backbone_identity(
                module.config.to_dict(),
                captured["DINO_sha256"],
                {"expected_backbone": plan.get("backbones", {}).get(arm)},
                legacy_sha256=CONVNEXT_TINY_SHA256,
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
        "completed": dict(plan.get("adopted_phase_results", {})),
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        if plan.get("replaced_controller"):
            assert not live(plan["replaced_controller"])
        if dependency := plan.get("after_run"):
            record("waiting-for-owned-fullframe-export", dependency=dependency)
            started = time.monotonic()
            while True:
                assert time.monotonic() - started < 43200
                guard(plan)
                status = read(Path(dependency["root"]) / "status.json")
                assert status["plan"] == dependency["plan"]
                assert status["controller"] == dependency["controller"]
                if status["status"] == dependency["terminal_status"]:
                    result = read(status["result"]["path"])
                    assert ref(status["result"]["path"]) == status["result"]
                    assert result["owner"] == dependency["child"]
                    if not live(dependency["controller"]) and not live(dependency["child"]):
                        break
                else:
                    assert status["status"] == "running-GFX-fullframe-exports", status["status"]
                    assert live(dependency["controller"])
                time.sleep(15)
        for phase in ("CPU", "CUDA", "train"):
            if phase == "train" and (dependency := plan.get("before_train_admission")):
                began = time.monotonic()
                while True:
                    guard(plan)
                    observed = read(dependency["status"])
                    if training_admission_ready(observed, dependency):
                        break
                    record("waiting-for-existing-training-admission", dependency=dependency)
                    assert time.monotonic() - began < dependency["maximum_wait_seconds"]
                    time.sleep(15)
            for arm in plan["arms"]:
                guard(plan)
                if binding := state["completed"].get(f"{phase}-{arm}"):
                    assert ref(binding["path"]) == binding
                    assert not live(read(binding["path"])["owner"])
                    record("adopted-completed-quality-check", phase=phase, arm=arm)
                    continue
                record("waiting-for-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    deadline = plan.get("adopted_headroom_deadline", {})
                    if (phase, arm) == (deadline.get("phase"), deadline.get("arm")):
                        assert time.time() < deadline["unix"]
                    else:
                        assert time.monotonic() - began < 7200
                    enough = (
                        psutil.virtual_memory().available
                        >= plan.get("launch_available_RAM_GiB", 48) * 2**30
                        and shutil.disk_usage(root).free
                        >= plan.get("phase_start_internal_free_GiB", 32) * 2**30
                        and shutil.disk_usage("/mnt/external").free
                        >= plan.get("phase_start_external_free_GiB", 256) * 2**30
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
                            plan.get("worker_script", {}).get(
                                "path", str(work / "scripts/train_quality_recipes.py")
                            ),
                            "worker",
                            plan.get("adopted_worker_plan", {"path": str(path)})["path"],
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
                        assert time.monotonic() - started < plan.get(
                            "maximum_train_worker_seconds"
                            if phase == "train"
                            else "maximum_smoke_worker_seconds",
                            43200 if phase == "train" else 1200,
                        )
                        assert (
                            shutil.disk_usage(root).free
                            > plan.get("runtime_internal_reserve_GiB", 16) * 2**30
                        )
                        assert (
                            shutil.disk_usage("/mnt/external").free
                            > plan.get("runtime_external_reserve_GiB", 128) * 2**30
                        )
                        time.sleep(2)
                    assert child.wait() == 0, (phase, arm, child.returncode)
                result = Path(plan.get("output_worker_root", root)) / f"{phase}-{arm}-result.json"
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


def training_admission_ready(state, dependency):
    """Protect an existing job's startup headroom without changing its owner."""
    assert state["plan"] == dependency["plan"]
    assert state["controller"] == dependency["controller"]
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    if state["status"] == "completed-training-awaiting-model-comparisons":
        assert set(state["completed"]) == set(dependency["completed_phases"])
        return not live(state["controller"]) and (
            state.get("child") is None or not live(state["child"])
        )
    assert live(state["controller"]), "Existing training controller exited before admission"
    return (
        state.get("phase") == "train"
        and state.get("arm") == dependency["arm"]
        and state["status"] == dependency["running_status"]
        and state.get("child") is not None
        and live(state["child"])
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--recipes", type=Path, nargs="+")
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm")
    parser.add_argument("--after-run-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.artifacts, args.recipes, args.after_run_root))
    elif args.mode == "controller":
        controller(args.path)
    else:
        worker(args.path, args.phase, args.arm)
