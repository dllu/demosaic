"""Collect new pilot checkpoints on fixed shadow and retained qualitative inputs."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live


def prepare(root, inputs_path, training_path, arms=None, matched_control_collection=None):
    inputs, training = read(inputs_path), read(training_path)
    arms = list(arms or ("V126", "V127"))
    assert arms and len(arms) == len(set(arms)) and set(arms) <= set(training["arms"])
    guard(inputs)
    guard(training)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == ref(training_path) and live(status["controller"])
    assert len(inputs["shadow_observations"]) == 64
    assert len(inputs["retained_observations"]) == 22
    baseline_path = Path(inputs["root"]) / "baseline-V120/collection-v1.json"
    baseline = read(baseline_path)
    assert baseline["counts"] == {"root": 64, "encoder": 64}
    root.mkdir(parents=True, exist_ok=False)
    controller = root / "controller.py"
    shutil.copyfile(__file__, controller)
    for helper in ("train_directional_bank_trial.py", "train_v43_quality_trial.py"):
        shutil.copyfile(Path(__file__).with_name(helper), root / helper)
    source = Path(inputs["work"])
    for arm in arms:
        work = root / arm / "work"
        for name in ("src", "scripts", "third_party"):
            shutil.copytree(source / name, work / name)
    plan = {
        "root": str(root),
        "input_plan": ref(inputs_path),
        "training_plan": ref(training_path),
        "training_owner": status["controller"],
        "arms": arms,
        "baseline_collection": ref(baseline_path),
        "controller": ref(controller),
        "python": training["python"],
        "maximum_training_wait_seconds": 64800,
        "maximum_collector_seconds": 3600,
        "launch_RAM_GiB": 48,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 12,
        "launch_internal_reserve_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "launch_external_reserve_GiB": 208,
        "runtime_external_reserve_GiB": 208,
        "inputs": [ref(inputs_path), ref(training_path), ref(baseline_path), *inputs["inputs"]],
        "frozen_files": {
            **inputs["frozen_files"],
            **{str(p): ref(p)["sha256"] for p in root.rglob("*") if p.is_file()},
        },
        "scope": "Both fresh1000 endpoints only:86 new calls each on64 fixed new shadow observations plus22 retained material/GFX inputs. Existing V120 shadow64 already complete; all old material/GFX controls reused. Total236 calls across3 models,64 new noise observations, zero RAW/reference/optimizer work. Independent metrics and actual native review follow collection.",
    }
    if matched_control_collection is not None:
        binding = ref(matched_control_collection)
        control = read(binding["path"])
        assert control["counts"] == {"root": 86, "encoder": 86}
        assert len(control["observations"]) == 86
        plan["matched_control_collection"] = binding
        plan["inputs"].append(binding)
        plan["scope"] = (
            f"Only new candidate endpoints {arms}:86 new calls each on the64 retained shadow "
            "and22 material/GFX inputs. Reuse completed V1261000-update control predictions "
            "and V120 baseline predictions. Zero new noise/RAW/reference/optimizer work. "
            "No repeated control inference; independent metrics and actual native review "
            "follow collection. A1000-update pilot is not a completed20k quality result."
        )
    save(root / "queue-plan-v1.json", plan)
    guard(plan)
    return root / "queue-plan-v1.json"


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        began = time.monotonic()
        record("waiting-for-original1000-pilot-training")
        training = read(plan["training_plan"]["path"])
        while True:
            assert time.monotonic() - began < plan["maximum_training_wait_seconds"]
            if deadline := plan.get("absolute_training_wait_deadline_unix"):
                assert time.time() < deadline
            guard(plan)
            status = read(Path(training["root"]) / "status.json")
            assert status["plan"] == plan["training_plan"]
            assert status["controller"] == plan["training_owner"]
            if status["status"].startswith("failed"):
                raise RuntimeError("Original pilot training failed; preserve all work")
            if not live(plan["training_owner"]):
                assert status["status"] == "completed-training-awaiting-model-comparisons"
                assert not live(status["child"])
                break
            time.sleep(15)
        inputs = read(plan["input_plan"]["path"])
        for arm in plan.get("arms", ("V126", "V127")):
            result_binding = status["completed"][f"train-{arm}"]
            assert ref(result_binding["path"]) == result_binding
            result = read(result_binding["path"])
            assert result["updates"] == 1000 and not live(result["owner"])
            assert result["model_EMA_Adam_finite"] and result["all_AdamW_steps"] == 1000
            assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
            endpoint = root / arm
            work = endpoint / "work"
            execution = {
                **inputs,
                **{
                    key: plan[key]
                    for key in (
                        "launch_RAM_GiB",
                        "runtime_RAM_GiB",
                        "CUDA_quota_GiB",
                        "launch_internal_reserve_GiB",
                        "runtime_internal_reserve_GiB",
                        "launch_external_reserve_GiB",
                        "runtime_external_reserve_GiB",
                    )
                },
                "root": str(endpoint),
                "work": str(work),
                "step": 1000,
                "checkpoint": result["checkpoint"],
                "EMA_tensors": 91,
                "raw_frequency_features": False,
                "expected_lineage": {**training["parent"], "step": training["parent_step"]},
                "expected_backbone": training["backbones"][arm],
                "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
                "observations": inputs["shadow_observations"] + inputs["retained_observations"],
                "planned_new_root_forwards": 86,
                "planned_new_encoder_forwards": 86,
                "inputs": [*plan["inputs"], result_binding, result["checkpoint"]],
                "frozen_files": plan["frozen_files"],
                "scope": plan["scope"],
            }
            execution_path = endpoint / "plan-v1.json"
            save(execution_path, execution)
            guard(execution)
            record("waiting-for-pilot-quality-headroom", arm=arm)
            began = time.monotonic()
            while psutil.virtual_memory().available < plan["launch_RAM_GiB"] * 2**30:
                assert time.monotonic() - began < 7200
                time.sleep(5)
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OPENBLAS_NUM_THREADS="1",
                PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            )
            with (endpoint / "collect.log").open("xb") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", execution["collector"]["path"], str(execution_path)],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-new-pilot-endpoint-collection", arm=arm, child=owner)
                began = time.monotonic()
                while child.poll() is None:
                    assert time.monotonic() - began < plan["maximum_collector_seconds"]
                    time.sleep(2)
                assert child.wait() == 0
            result_path = endpoint / "collection-v1.json"
            assert read(result_path)["counts"] == {"root": 86, "encoder": 86}
            state["completed"][arm] = ref(result_path)
            record("completed-new-pilot-endpoint-collection")
        record("completed-pilot-predictions-awaiting-independent-and-native-review")
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-pilot-quality-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--input-plan", type=Path)
    parser.add_argument("--training-plan", type=Path)
    parser.add_argument("--arms", nargs="+")
    parser.add_argument("--matched-control-collection", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.path.resolve(),
                args.input_plan.resolve(),
                args.training_plan.resolve(),
                args.arms,
                args.matched_control_collection,
            )
        )
    else:
        controller(args.path.resolve())
