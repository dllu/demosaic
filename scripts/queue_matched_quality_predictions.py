"""Freeze and queue retained-prediction quality evaluation after matched training."""

import argparse
import ast
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
STAGES = {"photo": (3108, 12404), "known": (24, 72), "unseen": (30, 90),
          "texture": (112, 448), "color": (1176, 1176), "gfx": (4, 4),
          "gfx-highlights": (2, 2), "full-gfx": (130, 520)}
HELPERS = ["collect_quality_predictions.py", "queue_matched_quality_predictions.py",
           "frozen_backbone_identity.py", "train_directional_bank_trial.py",
           "train_v43_quality_trial.py", "profile_raw_kernel_inference.py",
           "evaluate_texture_candidates.py", "diagnose_texture_response.py",
           "evaluate_color_grid_cuda.py", "prepare_color_grid.py", "audit_colored_flats.py",
           "report_raw_pair.py"]


def function_ast(path, name):
    tree = ast.parse(Path(path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.dump(node, include_attributes=False)


def prepare(root, artifacts, training_root, witness_plan, gfx_selections, controls=()):
    root, artifacts, training_root = root.resolve(), artifacts.resolve(), training_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    internal_artifacts = artifacts.is_relative_to(root / "work")
    assert internal_artifacts or artifacts.is_relative_to(Path("/mnt/external/demosaic"))
    status = read(training_root / "status.json")
    execution = ref(training_root / "execution-plan-v1.json")
    training = read(execution["path"])
    guard(training)
    assert status["execution_plan"] == execution and live(status["owner"])
    assert not status["status"].startswith("failed")
    arm_names = [a["arm"] for a in training["arms"]]
    assert arm_names and len(arm_names) == len(set(arm_names))
    original = read(witness_plan)
    guard(original)
    assert function_ast(REPO / "src/demosaic/suite.py", "observation") == function_ast(original["historical_suite"]["path"], "observation")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py")) + [REPO / "scripts" / p for p in HELPERS]
    files += [REPO / p for p in ["pyproject.toml", "uv.lock", "third_party/dinov3/LICENSE.md"]]
    for source in files:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    protocol = work / "configs/evaluation.yaml"
    protocol.parent.mkdir(exist_ok=True)
    shutil.copyfile(original["stages"]["photo"]["protocol"]["path"], protocol)
    stages, inputs = {}, [execution, ref(witness_plan)]
    for stage, (calls, observations) in STAGES.items():
        spec = {"calls_per_model": calls, "observations_per_model": observations,
                "output": str(artifacts / stage)}
        if stage in {"photo", "known", "unseen"}:
            spec["manifest"] = original["stages"][stage]["manifest"]
            inputs.append(spec["manifest"])
        if stage == "photo":
            spec["protocol"] = ref(protocol)
        if stage in original["stages"]:
            spec["future_input_witness"] = str(Path(original["stages"][stage]["output"]) / "retained-means.jsonl")
            spec["future_original_result"] = str(Path(original["stages"][stage]["output"]) / "result.json")
        else:
            source = Path(gfx_selections[stage])
            selection = read(source)
            for key in ["noisy", "reference"]:
                p = Path(selection[key])
                if not p.is_absolute():
                    p = REPO / p
                assert p.resolve().is_relative_to(REPO / ".cache/gfx-qualitative-20231231")
                selection[key] = str(p.resolve())
                inputs.append(ref(p))
            target = work / "configs" / (stage+".json")
            save(target, selection)
            spec["selection"] = ref(target)
            inputs.append(ref(source))
        stages[stage] = spec
    inputs.append(original["color_inputs"])
    control_files = [ref(p) for p in controls]
    inputs.extend(control_files)
    # Evaluation-only callbacks/retention may change; the physical model and
    # observation generator must agree with the actually frozen training source.
    source_checks = []
    for arm in training["arms"]:
        plan = read(arm["training_plan"]["path"])
        guard(plan)
        changed = []
        for source in (Path(plan["work"])/"src/demosaic").glob("*.py"):
            if source.read_bytes() != (work / "src/demosaic" / source.name).read_bytes():
                changed.append(source.name)
        assert set(changed) <= {"suite.py", "real_suite.py"}, changed
        source_checks.append({"arm": arm["arm"], "training_plan": arm["training_plan"], "evaluation_only_changed_modules": changed})
    snapshot = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    plan = {"root": str(root), "work": str(work), "artifact_root": str(artifacts), "python": sys.executable,
            "training_execution": execution, "training_owner": status["owner"], "training_status": str(training_root / "status.json"),
            "expected_training_terminal": training.get("terminal_status", "completed-matched-V114-V115-training-awaiting-quality-comparisons"),
            "expected_training_phases": [f"{phase}-{arm}" for phase in ["CUDA", "train"] for arm in arm_names],
            "expected_model_count": len(arm_names),
            "original_witness_plan": ref(witness_plan), "stages": stages, "color_inputs": original["color_inputs"],
            "material_photo_ids": ["0ae232278265dabbdd54f52c34045a3d03323aa7", "14d8ea6cea4a27346a643e6d767f800729fb4693",
                                   "212ae12913effa23268af953b4c8f8e8b7ab4ef5", "2b5a51667b9906eecead8f82e08c7ba11750f8c6"],
            "shared_checkpoint_cache": str(artifacts / ".checkpoint-cache"),
            "existing_control_files": control_files, "estimated_retained_and_export_budget_GiB": 15 * len(arm_names),
            "collector_source": ref(work / "scripts/collect_quality_predictions.py"),
            "controller_source": ref(work / "scripts/queue_matched_quality_predictions.py"),
            "maximum_training_wait_seconds": 259200,
            "first_stage_external_free_GiB": 208 if internal_artifacts else 248,
            "phase_start_external_free_GiB": 208 if internal_artifacts else 216,
            "runtime_external_reserve_GiB": 208,
            "phase_start_internal_free_GiB": 128 if internal_artifacts else 32,
            "runtime_internal_reserve_GiB": 96 if internal_artifacts else 16,
            "core_training_sources_unchanged": source_checks, "photo_observation_AST_identical_to_original": True,
            "inputs": inputs, "frozen_files": snapshot,
            "scope": "Declared new endpoints only, eight single-view FP32 stages after exact training-owner success. Retain native predictions/exact supervision and compare all numerical-panel inputs to original completed eight-view witnesses. Existing controls are reused without neural reruns. Six full-frame native floats and two RGB16 exports per new model. No automatic model promotion or retry; numeric/native review follows."}
    save(root / "queue-plan-v1.json", plan)
    guard(plan)
    return root / "queue-plan-v1.json"


def endpoint_plan(plan, state):
    import torch

    from demosaic.checkpoint_cache import freeze_checkpoint

    execution = read(plan["training_execution"]["path"])
    assert len(execution["arms"]) == plan.get("expected_model_count", len(execution["arms"]))
    assert set(state["completed"]) == set(plan["expected_training_phases"])
    checkpoints, inputs = [], list(plan["inputs"])
    artifacts = Path(plan["artifact_root"])
    artifacts.mkdir(exist_ok=False)
    for arm in execution["arms"]:
        name = arm["arm"]
        accounting = state["completed"][f"train-{name}"]
        assert ref(accounting["path"]) == accounting
        actual = read(accounting["path"])
        assert not live(actual["owner"]) and actual["all_AdamW_steps"] == 20000
        assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 20000
        assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
        if name == "V115":
            assert actual["matched_logged_inputs_steps_domains_LRs"] == 801
        training = read(arm["training_plan"]["path"])
        assert ref(actual["checkpoint"]["path"]) == actual["checkpoint"]
        path, digest = freeze_checkpoint(actual["checkpoint"]["path"], artifacts / "weights", cache_dir=plan["shared_checkpoint_cache"])
        assert digest == actual["checkpoint"]["sha256"]
        snapshot = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        lineage = {**training["parent"], "step": 20000}
        assert snapshot["step"] == 20000 and snapshot["config"]["initialized_from"] == lineage
        checkpoints.append({"arm": name, **ref(path), "expected_lineage": {"step": 20000, "initialized_from": lineage},
                            "expected_backbone": training["backbones"][name]})
        inputs.extend([accounting, actual["checkpoint"], ref(path)])
    stages = {}
    for name, specification in plan["stages"].items():
        spec = dict(specification)
        if "future_input_witness" in spec:
            binding = ref(spec["future_input_witness"])
            result_binding = ref(spec["future_original_result"])
            result = read(result_binding["path"])
            assert result["averaged_observations"] == spec["observations_per_model"]
            assert result["retained_means"] == binding and result["all_streamed_numpy64_means_bit_exact"]
            assert len(Path(binding["path"]).read_text().splitlines()) == spec["calls_per_model"]
            spec["input_witness"] = binding
            inputs.extend([binding, result_binding])
        stages[name] = spec
    result = {**plan, "checkpoints": checkpoints, "stages": stages, "inputs": inputs}
    save(Path(plan["root"]) / "evaluation-plan-v1.json", result)
    return Path(plan["root"]) / "evaluation-plan-v1.json"


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["controller_source"]
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"owner": owner, "queue_plan": ref(path), "completed": {}}
    child = child_owner = None

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        record("waiting-for-exact-matched-training-owner", dependency=plan["training_owner"])
        began = time.monotonic()
        while live(plan["training_owner"]):
            observed = read(plan["training_status"])
            assert observed["owner"] == plan["training_owner"] and observed["execution_plan"] == plan["training_execution"]
            assert not observed["status"].startswith("failed"), observed["status"]
            assert time.monotonic()-began < plan["maximum_training_wait_seconds"]
            time.sleep(10)
        observed = read(plan["training_status"])
        assert observed["owner"] == plan["training_owner"] and observed["execution_plan"] == plan["training_execution"]
        assert observed["status"] == plan["expected_training_terminal"]
        assert observed.get("child") is None or not live(observed["child"])
        guard(plan)
        evaluation_path = endpoint_plan(plan, observed)
        evaluation = read(evaluation_path)
        for index, stage in enumerate(plan["stages"]):
            record("waiting-for-quality-headroom", stage=stage, child=None)
            began, stable = time.monotonic(), None
            while True:
                enough = (psutil.virtual_memory().available >= 48*2**30 and shutil.disk_usage(root).free >= plan.get("phase_start_internal_free_GiB", 32)*2**30
                          and shutil.disk_usage("/mnt/external").free >= plan["first_stage_external_free_GiB" if index == 0 else "phase_start_external_free_GiB"]*2**30)
                stable = (time.monotonic() if stable is None else stable) if enough else None
                if stable is not None and time.monotonic()-stable >= 15:
                    break
                assert time.monotonic()-began < 7200
                time.sleep(2)
            guard(evaluation)
            work = Path(plan["work"])
            env = dict(os.environ, PYTHONPATH=f"{work/'src'}:{work/'scripts'}", CUDA_VISIBLE_DEVICES="0",
                       HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="4")
            with (root / (stage+"-v1.log")).open("x") as log:
                child = subprocess.Popen([plan["python"], "-P", plan["collector_source"]["path"], str(evaluation_path), stage],
                                         cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-frozen-endpoint-quality-stage", stage=stage, child=child_owner)
                began = time.monotonic()
                while child.poll() is None:
                    assert time.monotonic()-began < 43200
                    assert psutil.virtual_memory().available >= 24*2**30
                    assert shutil.disk_usage(root).free >= plan.get("runtime_internal_reserve_GiB", 16)*2**30
                    assert shutil.disk_usage("/mnt/external").free >= plan["runtime_external_reserve_GiB"]*2**30
                    time.sleep(2)
                assert child.wait() == 0, (stage, child.returncode)
            result_path = Path(plan["stages"][stage]["output"]) / "result.json"
            result = read(result_path)
            assert result["owner"] == child_owner and not live(child_owner)
            state["completed"][stage] = ref(result_path)
            record("completed-quality-stage", child=None)
        record("completed-matched-endpoint-evaluation-awaiting-independent-and-native-review", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-quality-evaluation-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "controller"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--witness-plan", type=Path)
    parser.add_argument("--gfx", type=Path)
    parser.add_argument("--gfx-highlights", type=Path)
    parser.add_argument("--full-gfx", type=Path)
    parser.add_argument("--controls", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.root, args.artifacts, args.training_root, args.witness_plan,
                      {"gfx": args.gfx, "gfx-highlights": args.gfx_highlights, "full-gfx": args.full_gfx}, args.controls))
    else:
        controller(args.root)
