"""Wait for the declared ADC training owners, audit on CPU, then hand off evaluation."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from evaluate_v43_quality_trial import monitor_child
from recover_v43_quality_trial import headroom, resource_snapshot, stop_owned_child
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
TERMINAL = "completed-matched-V95-ADC-training-awaiting-full-quality-and-native-review"
KEYS = {f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in ("V98", "V99")}
HELPERS = (
    "queue_v95_adc_quality.py",
    "audit_v43_quality_training.py",
    "evaluate_v43_quality_trial.py",
    "export_adc_cfa_projection.py",
    "train_v43_quality_trial.py",
    "train_directional_bank_trial.py",
    "recover_v43_quality_trial.py",
    "profile_raw_kernel_inference.py",
    "audit_fresh_dino_statistics.py",
    "evaluate_texture_candidates.py",
    "diagnose_texture_response.py",
    "report_raw_pair.py",
    "evaluate_color_grid_cuda.py",
    "prepare_color_grid.py",
    "audit_colored_flats.py",
)


def training_ready(state, plan_ref, controller_owner, *, is_live=live):
    """A completion label alone cannot release the independent evaluation."""
    assert state["plan"] == plan_ref, "Training plan changed"
    assert state["controller"] == controller_owner, "Training controller identity changed"
    assert not state["status"].startswith("failed"), state.get("error", state["status"])
    assert set(state["completed"]) <= KEYS, "Unexpected training phase"
    if state["status"] != TERMINAL:
        assert is_live(controller_owner), "Training controller exited before completion"
        return False
    assert set(state["completed"]) == KEYS, "Incomplete training coverage"
    return not is_live(controller_owner) and not is_live(state["child"])


def completed_results(state, plan_ref):
    for key in sorted(KEYS):
        item = state["completed"][key]
        assert ref(item["path"]) == item
        result = read(item["path"])
        phase, arm = key.split("-")
        assert result["plan"] == plan_ref and result["phase"] == phase and result["arm"] == arm
        assert result["engineering_only"] is (phase != "train")
        assert not live(result["owner"]), (key, result["owner"])


def prepare(training_root, root, evaluation_root, artifact_root):
    training_root, root = training_root.resolve(), root.resolve()
    evaluation_root, artifact_root = evaluation_root.resolve(), artifact_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert evaluation_root.is_relative_to(REPO / ".cache") and not evaluation_root.exists()
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    assert not artifact_root.exists() and os.path.ismount("/mnt/external")
    training_ref = ref(training_root / "plan.json")
    training = read(training_ref["path"])
    launch_ref = ref(training_root / "launch.json")
    launch = read(launch_ref["path"])
    assert launch["plan"] == training_ref
    assert training["arms"] == ["V98", "V99"] and training["planned_updates"] == 4000
    assert not training["engineering_only"]
    guard(training)
    training_ready(read(training_root / "status.json"), training_ref, launch["owner"])
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    files = list(trained.glob("src/demosaic/*.py"))
    assert len(files) == 47
    files += [trained / p for p in ("pyproject.toml", "uv.lock", "configs/evaluation.yaml")]
    files += [REPO / "scripts" / p for p in HELPERS]
    files += [REPO / p for p in ("LICENSE", "third_party/dinov3/LICENSE.md")]
    for source in files:
        relative = (
            source.relative_to(trained)
            if source.is_relative_to(trained)
            else source.relative_to(REPO)
        )
        destination = work / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    inputs = [training_ref, launch_ref]
    inputs += [
        ref(REPO / p)
        for p in (
            "docs/results/v43-curated-original20k-complete-review-v1.json",
            "configs/gfx-qualitative-20231231.json",
            "configs/gfx-qualitative-20231231-highlights.json",
        )
    ]
    plan = {
        "repository": str(REPO),
        "root": str(root),
        "work": str(work),
        "training_root": str(training_root),
        "training_plan": training_ref,
        "training_controller": launch["owner"],
        "evaluation_root": str(evaluation_root),
        "artifact_root": str(artifact_root),
        "python": training["python"],
        "cache_environment": training["cache_environment"],
        "disk_reserves": {"root_reserve_gib": 64, "external_reserve_gib": 384},
        "external_device": Path("/mnt/external").stat().st_dev,
        "stable_seconds": 60,
        "wait_seconds": 7200,
        "dependency_wait_seconds": 43200,
        "CPU_stage_timeout_seconds": 7200,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "CPU-only wait and independent audit of both fixed4k endpoints. After exact training owners exit, prepare the frozen full seven-panel common-policy comparison, launch its existing resource-managed controller and exit. No restart, retry, checkpoint selection, speed work or automatic promotion; independent numeric and native-crop review still required.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path, stage):
    plan = read(plan_path)
    guard(plan)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    repository, training_root = Path(plan["repository"]), Path(plan["training_root"])
    if stage.startswith("audit-"):
        import audit_v43_quality_training as auditor

        auditor.REPO = repository
        arm = stage.removeprefix("audit-")
        auditor.audit(
            training_root, arm, training_root / f"independent-{arm}-training-audit-v1.json"
        )
    else:
        assert stage == "prepare-evaluation"
        import evaluate_v43_quality_trial as evaluator

        evaluator.REPO = repository
        evaluator.prepare(
            training_root,
            Path(plan["evaluation_root"]),
            adc_training=True,
            artifact_root=Path(plan["artifact_root"]),
            source_repository=Path(plan["work"]),
        )
    guard(plan)


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child, identity = None, None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def observe():
        snapshot = resource_snapshot(root)
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(snapshot) + "\n")
        return snapshot

    try:
        record("waiting-for-exact-ADC-training-owners-to-complete-and-exit")
        deadline = time.monotonic() + plan["dependency_wait_seconds"]
        while True:
            assert time.monotonic() < deadline, "Training dependency wait bound"
            training_state = read(Path(plan["training_root"]) / "status.json")
            if training_ready(training_state, plan["training_plan"], plan["training_controller"]):
                break
            record(
                "waiting-for-exact-ADC-training-owners-to-complete-and-exit",
                observed_training_status=training_state["status"],
                observed_training_phase=training_state.get("phase"),
                observed_training_arm=training_state.get("arm"),
                resource_snapshot=observe(),
            )
            time.sleep(10)
        completed_results(training_state, plan["training_plan"])
        save(root / "completed-training-observation.json", training_state)
        env = dict(
            os.environ,
            CUDA_VISIBLE_DEVICES="",
            PYTHONPATH=f"{work}/src:{work}/scripts",
            PYTHONDONTWRITEBYTECODE="1",
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
        )
        env.update(plan["cache_environment"])
        for stage in ("audit-V98", "audit-V99", "prepare-evaluation"):
            guard(plan)
            record("waiting-for-CPU-audit-headroom", stage=stage)
            began, stable = time.monotonic(), None
            while True:
                assert time.monotonic() - began < plan["wait_seconds"]
                stable = (
                    (time.monotonic() if stable is None else stable)
                    if headroom(observe(), plan, 48)
                    else None
                )
                if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                    break
                time.sleep(2)
            with (root / (stage + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        str(work / "scripts/queue_v95_adc_quality.py"),
                        "worker",
                        str(plan_path),
                        "--stage",
                        stage,
                    ],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-CPU-only-ADC-audit-or-preparation", child=identity)
                monitor_child(
                    child,
                    identity,
                    plan=plan,
                    observe=observe,
                    record=record,
                    deadline=time.monotonic() + plan["CPU_stage_timeout_seconds"],
                )
                assert child.wait() == 0, (stage, child.returncode)
            output = (
                Path(plan["evaluation_root"]) / "plan.json"
                if stage == "prepare-evaluation"
                else Path(plan["training_root"])
                / f"independent-{stage.removeprefix('audit-')}-training-audit-v1.json"
            )
            state["completed"][stage] = ref(output)
            record("completed-CPU-only-ADC-queue-stage")
        evaluation_plan_path = Path(plan["evaluation_root"]) / "plan.json"
        evaluation = read(evaluation_plan_path)
        guard(plan)
        guard(evaluation)
        assert not (Path(plan["evaluation_root"]) / "controller.claim").exists()
        (root / "handoff.claim").open("x").close()
        evaluation_work = Path(evaluation["work"])
        env["PYTHONPATH"] = f"{evaluation_work}/src:{evaluation_work}/scripts"
        with (Path(plan["evaluation_root"]) / "controller.log").open("xb") as log:
            # The evaluator owns its separate-session workers and their resource policy.
            # This queue exits; it must never signal only that supervisor's process group.
            launched = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    str(evaluation_work / "scripts/evaluate_v43_quality_trial.py"),
                    "controller",
                    str(evaluation_plan_path),
                ],
                cwd=evaluation_work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        owner = {"pid": launched.pid, "created": psutil.Process(launched.pid).create_time()}
        receipt = {
            "plan": ref(evaluation_plan_path),
            "owner": owner,
            "queue_plan": ref(plan_path),
            "scope": "Handoff only; panel completion and review remain pending.",
        }
        save(Path(plan["evaluation_root"]) / "launch.json", receipt)
        save(root / "evaluation-launch.json", receipt)
        record(
            "handed-off-full-ADC-quality-evaluation-awaiting-panels-and-review",
            evaluation_controller=owner,
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, identity)
        record("failed-ADC-quality-queue-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evaluation-root", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--stage", choices=("audit-V98", "audit-V99", "prepare-evaluation"))
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output and args.evaluation_root and args.artifact_root
        prepare(args.path, args.output, args.evaluation_root, args.artifact_root)
    elif args.mode == "controller":
        controller(args.path)
    else:
        assert args.stage
        worker(args.path, args.stage)
