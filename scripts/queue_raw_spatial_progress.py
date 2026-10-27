"""Collect and independently score retained progress snapshots without stopping training."""

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
ARMS = ("V131", "V132")
HELPERS = (
    "collect_retained_checkpoint_pilot.py",
    "report_checkpoint_pilot.py",
    "audit_checkpoint_pilot.py",
    "frozen_backbone_identity.py",
    "profile_raw_kernel_inference.py",
    "train_directional_bank_trial.py",
    "train_v43_quality_trial.py",
)


def checked_collection(binding, expected):
    assert ref(binding["path"]) == binding
    result = read(binding["path"])
    execution = read(result["plan"]["path"])
    assert ref(result["plan"]["path"]) == result["plan"]
    guard(execution)
    assert result["counts"] == {"root": expected, "encoder": expected}
    assert len(result["observations"]) == len(execution["observations"]) == expected
    assert len({r["id"] for r in result["observations"]}) == expected
    return result, execution


def prepare(root, training_path, shadow_path, faint_path):
    root, training_path, shadow_path, faint_path = (
        Path(p).resolve() for p in (root, training_path, shadow_path, faint_path)
    )
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    training, shadow, faint = [read(p) for p in (training_path, shadow_path, faint_path)]
    for plan in (training, shadow, faint):
        guard(plan)
    assert training["training_format"] == "matched-raw-spatial-v1"
    assert list(training["arms"]) == list(ARMS)
    assert training["train_updates"] == 20000 and training["progress_steps"] == [1000]
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == ref(training_path) and live(status["controller"])
    assert not status["status"].startswith("failed")
    shadow_control = ref(Path(shadow["root"]) / "baseline-V120/collection-v1.json")
    old_shadow, shadow_execution = checked_collection(shadow_control, 64)
    faint_control = read(Path(faint["root"]) / "status.json")["completed"]["V120"]
    old_faint, faint_execution = checked_collection(faint_control, 16)
    assert len(shadow["shadow_observations"]) == 64
    assert len(shadow["retained_observations"]) == 22
    assert len(faint["observations"]) == 16
    for observations, execution in (
        (shadow["shadow_observations"], shadow_execution),
        (faint["observations"], faint_execution),
    ):
        assert [(o["id"], o["input_fingerprints"]) for o in observations] == [
            (o["id"], o["input_fingerprints"]) for o in execution["observations"]
        ]
        assert execution["checkpoint"]["sha256"] == training["parent"]["sha256"]
    shadow_rows = {r["id"]: r for r in old_shadow["observations"]}
    faint_rows = {r["id"]: r for r in old_faint["observations"]}
    cases = {c["id"]: c for c in faint["cases"]}
    observations, inputs = [], [ref(p) for p in (training_path, shadow_path, faint_path)]
    inputs += [shadow_control, faint_control, *shadow["inputs"], *faint["inputs"]]
    for source in shadow["shadow_observations"] + shadow["retained_observations"]:
        if source["kind"] == "shadow-material":
            controls = [
                {"model": {"label": "V120"}, "prediction": shadow_rows[source["id"]]["prediction"]}
            ]
        else:
            controls = [
                c
                for c in source["controls"]
                if c.get("label", c.get("model", {}).get("label")) in {"V120", "V120-profile3879"}
            ]
            assert len(controls) == 1
        observations.append({**source, "controls": controls})
    for source in faint["observations"]:
        case = cases[source["case_id"]]
        observations.append(
            {
                **source,
                "case": case,
                "original_case_id": case["original_case_id"],
                "controls": [
                    {
                        "model": {"label": "V120"},
                        "prediction": faint_rows[source["id"]]["prediction"],
                    }
                ],
            }
        )
    assert len(observations) == len({o["id"] for o in observations}) == 102
    for observation in observations:
        inputs.append(observation["arrays"])
        if "target" in observation:
            inputs.append(observation["target"])
        else:
            assert observation["kind"] == "mesh"
        inputs += [c["prediction"] for c in observation["controls"]]
    root.mkdir(parents=True)
    controller_source = root / "controller.py"
    shutil.copyfile(__file__, controller_source)
    for name in ("train_directional_bank_trial.py", "train_v43_quality_trial.py"):
        shutil.copyfile(REPO / "scripts" / name, root / name)
    for arm in ARMS:
        work = root / arm / "work"
        shutil.copytree(
            Path(training["work"]) / "src",
            work / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for name in HELPERS:
            target = work / "scripts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / "scripts" / name, target)
        shutil.copytree(Path(training["work"]) / "third_party", work / "third_party")
    original_root = training.get("output_worker_root", training["root"])
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_status": str(Path(training["root"]) / "status.json"),
        "training_owner": status["controller"],
        "worker_root": original_root,
        "controller_source": ref(controller_source),
        "python": sys.executable,
        "arms": list(ARMS),
        "step": 1000,
        "training_horizon": 20000,
        "observations": observations,
        "saved_V120_shadow": shadow_control,
        "saved_V120_faint_ADC": faint_control,
        "planned_new_root_forwards_per_model": 102,
        "planned_new_encoder_forwards_total": 204,
        "planned_new_root_forwards_total": 204,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "maximum_training_wait_seconds": 691200,
        "maximum_headroom_wait_seconds": 172800,
        "maximum_collector_seconds": 3600,
        "maximum_CPU_analysis_seconds": 1800,
        "launch_RAM_GiB": 52,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 12,
        "launch_internal_reserve_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "launch_external_reserve_GiB": 208,
        "runtime_external_reserve_GiB": 208,
        "inputs": list({(v["path"], v["sha256"]): v for v in inputs}.values()),
        "frozen_files": {
            **shadow["frozen_files"],
            **faint["frozen_files"],
            **{str(p): ref(p)["sha256"] for p in root.rglob("*") if p.is_file()},
        },
        "scope": (
            "V131/V132 step1000 progress within original20000-update horizons, never "
            "completed endpoints.102 new FP32 calls each:64 retained shadow,16 ordinary "
            "material,4 main-GFX512,2 extra-mesh768 fixed profiles,16 retained faint-ADC. "
            "Reuse all V120 predictions; V132 also compares saved V131 progress predictions. "
            "No new inputs/noise/RAW/reference/optimizer work or training signals/reset. "
            "Exact step/horizon/Adam/EMA/lineage checks precede model construction. "
            "Sequential collections with52GiB admission/12GiB CUDAcap/32GiB runtime floor; "
            "reports and independent FFT/native-pixel audits follow on CPU. Scores and "
            "actual native viewing remain pending; no automatic retry or promotion."
        ),
    }
    path = root / "queue-plan-v1.json"
    save(path, plan)
    guard(plan)
    return path


def progress_ready(plan, state, arm, progress):
    """Allow a live immutable snapshot, or the same worker's completed prefix."""
    assert state["plan"] == plan["training_plan"]
    assert state["controller"] == plan["training_owner"]
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    if not live(plan["training_owner"]):
        assert state["status"] == "completed-training-awaiting-model-comparisons"
    if progress is None:
        if not live(plan["training_owner"]):
            raise RuntimeError("Training exited without the declared progress snapshot")
        return False
    assert progress["status"] == "immutable-progress-checkpoint-within-original-training-budget"
    assert progress["arm"] == arm and progress["step"] == plan["step"] == 1000
    assert progress["declared_training_horizon"] == plan["training_horizon"] == 20000
    counts = progress["counts_at_checkpoint"]
    assert all(
        counts[k] == 1000
        for k in ("training_forwards", "optimizer_steps", "prepared_training_batches")
    )
    assert counts["validation_forwards"] == 32 and counts["encoder_forwards"] == 1032
    assert counts["target_contexts"] == 16000
    rows = progress["observed_inputs"]
    assert len(rows) == 1000 and [r["step"] for r in rows] == list(range(1, 1001))
    if live(progress["owner"]):
        assert state.get("child") == progress["owner"]
        assert state.get("phase") == "train" and state.get("arm") == arm
        assert state["status"] == "running-quality-training"
    else:
        binding = state["completed"].get(f"train-{arm}")
        if binding is None:
            return False  # Exact worker exit and controller accounting can differ by one poll.
        assert ref(binding["path"]) == binding
        result = read(binding["path"])
        assert result["owner"] == progress["owner"] and result["updates"] == 20000
        assert result["observed_inputs"][:1000] == rows
    return True


def run_child(plan, state, record, command, work, log_path, *, cuda, timeout):
    env = dict(
        os.environ,
        CUDA_VISIBLE_DEVICES="0" if cuda else "",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
    )
    child = owner = None
    try:
        with log_path.open("x") as log:
            child = subprocess.Popen(
                command,
                cwd=work,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("collecting-progress" if cuda else "analyzing-progress-on-CPU", child=owner)
            began = time.monotonic()
            while child.poll() is None:
                assert time.monotonic() - began < timeout
                assert (
                    shutil.disk_usage(Path(plan["root"])).free
                    > plan["runtime_internal_reserve_GiB"] * 2**30
                )
                assert (
                    shutil.disk_usage("/mnt/external").free
                    > plan["runtime_external_reserve_GiB"] * 2**30
                )
                time.sleep(2)
            assert child.wait() == 0, (command, child.returncode)
    except BaseException:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        raise


def controller(path):
    plan = read(path)
    guard(plan)
    assert ref(__file__) == plan["controller_source"]
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
        "reports": {},
    }

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    began = time.monotonic()
    try:
        training = read(plan["training_plan"]["path"])
        prior = None
        for arm in plan["arms"]:
            record("waiting-for-immutable-training-progress", arm=arm, child=None)
            snapshot_path = Path(plan["worker_root"]) / f"train-{arm}-progress1000.json"
            while True:
                if deadline := plan.get("absolute_training_wait_deadline_unix"):
                    assert time.time() < deadline
                observed = read(plan["training_status"])
                progress = read(snapshot_path) if snapshot_path.exists() else None
                if progress_ready(plan, observed, arm, progress):
                    break
                assert time.monotonic() - began < plan["maximum_training_wait_seconds"]
                time.sleep(15)
            guard(plan)
            assert ref(progress["checkpoint"]["path"]) == progress["checkpoint"]
            if prior is not None:
                keys = ("step", "domain", "clean_sha256", "batch_sha256")
                assert [[r[k] for k in keys] for r in progress["observed_inputs"]] == [
                    [r[k] for k in keys] for r in prior["observed_inputs"]
                ]
            endpoint, work = root / arm, root / arm / "work"
            execution = {
                **{k: v for k, v in plan.items() if k.startswith(("launch_", "runtime_"))},
                "root": str(endpoint),
                "work": str(work),
                "step": 1000,
                "training_horizon": 20000,
                "progress_checkpoint": True,
                "raw_spatial_features": arm == "V132",
                "raw_frequency_features": False,
                "model_label": f"{arm} progress1k/20k",
                "checkpoint": progress["checkpoint"],
                "EMA_tensors": training["restoration_tensors_by_arm"][arm],
                "expected_lineage": {**training["parent"], "step": training["parent_step"]},
                "expected_backbone": training["backbones"][arm],
                "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
                "observations": plan["observations"],
                "CUDA_quota_GiB": plan["CUDA_quota_GiB"],
                "planned_new_root_forwards": 102,
                "planned_new_encoder_forwards": 102,
                "inputs": [*plan["inputs"], ref(path), ref(snapshot_path), progress["checkpoint"]],
                "frozen_files": plan["frozen_files"],
                "scope": plan["scope"],
            }
            execution_path = endpoint / "plan-v1.json"
            save(execution_path, execution)
            record("waiting-for-progress-collection-headroom", child=None)
            waited, stable = time.monotonic(), None
            while True:
                if deadline := plan.get("absolute_training_wait_deadline_unix"):
                    assert time.time() < deadline
                enough = psutil.virtual_memory().available >= plan["launch_RAM_GiB"] * 2**30
                stable = (time.monotonic() if stable is None else stable) if enough else None
                if stable is not None and time.monotonic() - stable >= plan.get(
                    "stable_headroom_seconds", 15
                ):
                    break
                assert time.monotonic() - waited < plan["maximum_headroom_wait_seconds"]
                time.sleep(2)
            run_child(
                plan,
                state,
                record,
                [plan["python"], "-P", execution["collector"]["path"], str(execution_path)],
                work,
                endpoint / "collect.log",
                cuda=True,
                timeout=plan["maximum_collector_seconds"],
            )
            collection_path = endpoint / "collection-v1.json"
            collection = read(collection_path)
            assert collection["plan"] == ref(execution_path)
            assert collection["counts"] == {"root": 102, "encoder": 102}
            assert collection["progress_checkpoint_verified"]
            assert collection["training_horizon"] == 20000
            state["completed"][arm] = ref(collection_path)
            record("completed-progress-collection", child=None)
            analysis_root = root / f"analysis-{arm}"
            analysis_root.mkdir()
            observations = plan["observations"]
            extra = []
            if prior is not None:
                control = read(state["completed"]["V131"]["path"])
                rows = {r["id"]: r for r in control["observations"]}
                observations = [
                    {
                        **o,
                        "controls": [
                            *o["controls"],
                            {
                                "model": {"label": "V131 progress1k/20k"},
                                "prediction": rows[o["id"]]["prediction"],
                            },
                        ],
                    }
                    for o in observations
                ]
                extra = [state["completed"]["V131"], *[r["prediction"] for r in rows.values()]]
            analysis = {
                **execution,
                "root": str(analysis_root),
                "observations": observations,
                "actual_neural_execution": ref(execution_path),
                "inputs": [*execution["inputs"], ref(collection_path), *extra],
            }
            analysis_path = analysis_root / "plan-v1.json"
            save(analysis_path, analysis)
            derived_collection = analysis_root / "collection-v1.json"
            save(
                derived_collection,
                {
                    **collection,
                    "plan": ref(analysis_path),
                    "actual_neural_collection": ref(collection_path),
                    "new_forwards_in_this_derivation": 0,
                },
            )
            for helper, arguments in (
                ("report_checkpoint_pilot.py", [str(analysis_path), str(derived_collection)]),
                ("audit_checkpoint_pilot.py", [str(analysis_root)]),
            ):
                run_child(
                    plan,
                    state,
                    record,
                    [plan["python"], "-P", str(work / "scripts" / helper), *arguments],
                    work,
                    analysis_root / (helper + ".log"),
                    cuda=False,
                    timeout=plan["maximum_CPU_analysis_seconds"],
                )
            audit = analysis_root / "independent-audit-v1.json"
            assert read(audit)["status"] == "passed-independent-FFT-metric-and-native-pixel-audit"
            state["reports"][arm] = {
                "report": ref(analysis_root / "report-v1/report.json"),
                "independent_audit": ref(audit),
            }
            record("completed-progress-report-and-independent-audit", child=None)
            prior = progress
        record("completed-progress-comparisons-awaiting-actual-native-viewing", child=None)
    except BaseException as error:
        record("failed-progress-review-preserved-no-automatic-retry", error=repr(error), child=None)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--training", type=Path)
    parser.add_argument("--shadow-inputs", type=Path)
    parser.add_argument("--faint-inputs", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.training, args.shadow_inputs, args.faint_inputs))
    else:
        controller(args.path.resolve())
