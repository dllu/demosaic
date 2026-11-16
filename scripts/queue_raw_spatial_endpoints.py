"""Freeze retained-input endpoint reviews for the resumed matched attention trial."""

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

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())
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


def training_ready(plan, status):
    if status["plan"] != plan["training_plan"] or status["owner"] != plan["training_owner"]:
        raise ValueError("Training controller or plan identity changed")
    if status["status"].startswith("failed"):
        raise RuntimeError(
            "Original exact training controller failed; preserve review without retry"
        )
    if live(plan["training_owner"]):
        return False
    if status["status"] != "completed-both-arms-quality-review-pending":
        raise RuntimeError("Exact training owner exited without complete endpoints")
    bindings = status["results"]
    expected = {
        (Path(plan["training_status"]).parent / f"train-{a}-result.json").resolve() for a in ARMS
    }
    if len(bindings) != 2 or {Path(b["path"]).resolve() for b in bindings} != expected:
        raise ValueError("Training did not publish exactly the two declared endpoints")
    return True


def matched_results(results):
    """Compare every training observation directly, in addition to the worker checks."""
    a, b = [results[arm] for arm in ARMS]
    keys = ("step", "domain", "clean_sha256", "batch_sha256")
    if any(
        [r["step"] for r in result["observed_inputs"]] != list(range(1, 20001)) for result in (a, b)
    ):
        raise ValueError("Incomplete endpoint training input trace")
    if [[r[k] for k in keys] for r in a["observed_inputs"]] != [
        [r[k] for k in keys] for r in b["observed_inputs"]
    ]:
        raise ValueError("Endpoint training observations differ")
    return True


def attach_control(observations, execution, collection):
    """Add endpoint predictions only with identical input and display bindings."""
    if not (
        execution["step"] == execution["training_horizon"] == 20000
        and execution["model_label"] == "V131 endpoint20k"
        and execution["completed_training_checkpoint"] is True
        and collection["completed_training_checkpoint_verified"] is True
    ):
        raise ValueError("Comparison control is not the verified completed V131 endpoint")
    original = {row["id"]: row for row in execution["observations"]}
    actual = {row["id"]: row for row in collection["observations"]}
    if (
        not (
            len(original)
            == len(execution["observations"])
            == len(actual)
            == len(collection["observations"])
            == len(observations)
        )
        or set(original) != set(actual)
        or set(original) != {r["id"] for r in observations}
    ):
        raise ValueError("Missing or duplicate control observations")
    keys = (
        "arrays",
        "input_fingerprints",
        "target",
        "ROI_xywh",
        "display_exposure",
        "noise",
        "reference_role",
    )
    output = []
    for row in observations:
        if any(row.get(k) != original[row["id"]].get(k) for k in keys):
            raise ValueError("Control observation or display differs")
        prediction = actual[row["id"]]["prediction"]
        if ref(prediction["path"]) != prediction:
            raise ValueError("Control prediction changed")
        output.append(
            {
                **row,
                "controls": [
                    *row["controls"],
                    {"model": {"label": execution["model_label"]}, "prediction": prediction},
                ],
            }
        )
    return output


def prepare(root, training_path, observations_path, zero_forward_handoff=None):
    training_path, observations_path = training_path.resolve(), observations_path.resolve()
    training, previous = read(training_path), read(observations_path)
    guard(training)
    guard(previous)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == ref(training_path) and live(status["owner"])
    assert not status["status"].startswith("failed")
    assert list(training["arms"]) == list(ARMS)
    assert training["train_updates"] == 20000
    assert training["restoration_tensors_by_arm"] == {"V131": 91, "V132": 114}
    observations = previous["observations"]
    assert len(observations) == len({r["id"] for r in observations}) == 102
    assert previous["training_horizon"] == 20000
    assert all(len(r["controls"]) == 1 for r in observations)
    jpeg_inputs = {
        (binding["path"], binding["sha256"]): binding
        for row in observations
        if row["kind"] == "mesh"
        for case in row["cases"]
        for item in case["camera_JPEGs"].values()
        for binding in (item["pixels"],)
    }
    assert len(jpeg_inputs) == 4
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    root.mkdir(parents=True)
    source = root / "controller.py"
    shutil.copyfile(__file__, source)
    for name in ("train_directional_bank_trial.py", "train_v43_quality_trial.py"):
        shutil.copyfile(REPO / "scripts" / name, root / name)
    copied_sources = {}
    for arm in ARMS:
        work = root / arm / "work"
        for name in ("src", "third_party"):
            shutil.copytree(Path(training["work"]) / name, work / name)
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copyfile(Path(training["work"]) / name, work / name)
        for name in HELPERS:
            target = work / "scripts" / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(REPO / "scripts" / name, target)
        copied_sources[arm] = {
            str(p.relative_to(work / "src")): ref(p)["sha256"] for p in (work / "src").rglob("*.py")
        }
    assert copied_sources["V131"] == copied_sources["V132"]
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_owner": status["owner"],
        "training_status": str(Path(training["root"]) / "status.json"),
        "observations_plan": ref(observations_path),
        "observations": observations,
        "include_camera_jpegs": True,
        "controller_source": ref(source),
        "python": sys.executable,
        "training_source_sha256": training["prefix_source_sha256"],
        "original_numerical_sources_exact": copied_sources,
        "launch_RAM_GiB": 52,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 12,
        "launch_internal_reserve_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "launch_external_reserve_GiB": 96,
        "runtime_external_reserve_GiB": 64,
        "training_wait_deadline_unix": status["owner"]["created"] + 7 * 86400,
        "maximum_headroom_wait_seconds": 48 * 3600,
        "maximum_collector_seconds": 3600,
        "maximum_CPU_analysis_seconds": 1800,
        "planned_root_forwards_per_model": 102,
        "planned_root_forwards_total": 204,
        "planned_encoder_forwards_total": 204,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "inputs": [
            ref(training_path),
            ref(observations_path),
            *training["inputs"],
            *previous["inputs"],
            *jpeg_inputs.values(),
        ],
        "frozen_files": {
            **training["frozen_files"],
            **previous["frozen_files"],
            **{str(p): ref(p)["sha256"] for p in root.rglob("*") if p.is_file()},
        },
        "scope": "New completed20k endpoints only, same original102 retained observations, original frozen numerical/data package. Wait for exact controller success and dead owners; verify both model/EMA/Adam/source/lineage/horizons/counts and every matched clean/noisy training hash before constructing models. Reuse V120 predictions; V132 also compares newly saved V131 endpoint predictions.204 total IEEEFP32 root/DINO calls, zero training/noise/source/RAW work. CPU metrics plus independent FFT/display/all-native-pixel audit. Both protected GFX families/ROIs/profiles/JPEGs retained; independent references not GT. Actual viewing and broad427-photo/full-resolution review remain separate.52GiB admission/12GiB CUDAcap/32GiB runtime floor; internal128/96GiB and external-readonly96/64GiB. No automatic retry, checkpoint selection or model promotion.",
    }
    if zero_forward_handoff is not None:
        handoff = read(zero_forward_handoff)
        assert handoff["training_plan"] == ref(training_path)
        assert handoff["new_neural_forwards"] == 0
        assert not live(handoff["old_owner"])
        assert read(handoff["preserved_status"]["path"])["completed"] == {}
        assert ref(handoff["preserved_status"]["path"]) == handoff["preserved_status"]
        plan["zero_forward_handoff"] = ref(zero_forward_handoff)
        plan["inputs"].extend([ref(zero_forward_handoff), handoff["preserved_status"]])
    path = root / "queue-plan.json"
    save(path, plan)
    guard(plan)
    return path


def run_child(plan, record, command, work, log_path, *, cuda, timeout):
    env = dict(
        os.environ,
        CUDA_VISIBLE_DEVICES="0" if cuda else "",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        PYTHONPATH=f"{work}/src:{work}/scripts",
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
            record(
                "collecting-completed-endpoint" if cuda else "analyzing-endpoint-on-CPU",
                child=owner,
            )
            deadline = owner["created"] + timeout
            while child.poll() is None:
                assert time.time() < deadline, "Declared collector/analysis deadline exceeded"
                assert (
                    shutil.disk_usage(plan["root"]).free
                    >= plan["runtime_internal_reserve_GiB"] * 2**30
                )
                assert (
                    shutil.disk_usage("/mnt/external").free
                    >= plan["runtime_external_reserve_GiB"] * 2**30
                )
                time.sleep(5)
            assert child.returncode == 0, (
                f"Child failed; preserve prefix without retry: {child.returncode}"
            )
    except BaseException:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
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

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    try:
        record("waiting-for-exact-completed-training", child=None)
        while not training_ready(plan, read(plan["training_status"])):
            assert time.time() < plan["training_wait_deadline_unix"]
            time.sleep(15)
        guard(plan)
        training = read(plan["training_plan"]["path"])
        completed = read(plan["training_status"])
        results = {read(b["path"])["arm"]: read(b["path"]) for b in completed["results"]}
        assert set(results) == set(ARMS)
        for binding in completed["results"]:
            assert ref(binding["path"]) == binding
        matched_results(results)
        for arm in ARMS:
            result = results[arm]
            assert not live(result["owner"])
            assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        save(
            root / "matched-training.json",
            {
                "status": "all20000-training-observations-exact-between-arms",
                "results": completed["results"],
                "keys": ["step", "domain", "clean_sha256", "batch_sha256"],
                "new_neural_forwards": 0,
            },
        )
        prior_execution = prior_collection = None
        for arm in ARMS:
            record("preparing-completed-endpoint", arm=arm, child=None)
            work = root / arm / "work"
            observations = plan["observations"]
            extras = []
            if prior_collection is not None:
                observations = attach_control(observations, prior_execution, prior_collection)
                extras = [
                    state["completed"]["V131"],
                    *[row["prediction"] for row in prior_collection["observations"]],
                ]
            result = results[arm]
            result_binding = next(b for b in completed["results"] if read(b["path"])["arm"] == arm)
            execution = {
                **{k: v for k, v in plan.items() if k.startswith(("launch_", "runtime_"))},
                "root": str(root / arm),
                "work": str(work),
                "step": 20000,
                "training_horizon": 20000,
                "completed_training_checkpoint": True,
                "include_camera_jpegs": plan["include_camera_jpegs"],
                "training_source_sha256": plan["training_source_sha256"],
                "training_result": result_binding,
                "raw_spatial_features": arm == "V132",
                "raw_frequency_features": False,
                "model_label": f"{arm} endpoint20k",
                "checkpoint": result["checkpoint"],
                "EMA_tensors": training["restoration_tensors_by_arm"][arm],
                "expected_lineage": {**training["parent"], "step": training["parent_step"]},
                "expected_backbone": training["backbones"][arm],
                "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
                "observations": observations,
                "CUDA_quota_GiB": plan["CUDA_quota_GiB"],
                "planned_new_root_forwards": 102,
                "planned_new_encoder_forwards": 102,
                "inputs": [
                    *plan["inputs"],
                    ref(path),
                    result_binding,
                    result["checkpoint"],
                    *extras,
                ],
                "frozen_files": plan["frozen_files"],
                "scope": plan["scope"],
            }
            execution_path = root / arm / "plan-v1.json"
            save(execution_path, execution)
            record("waiting-for-endpoint-review-headroom", child=None)
            deadline = time.time() + plan["maximum_headroom_wait_seconds"]
            while not (
                psutil.virtual_memory().available >= plan["launch_RAM_GiB"] * 2**30
                and shutil.disk_usage(root).free >= plan["launch_internal_reserve_GiB"] * 2**30
                and shutil.disk_usage("/mnt/external").free
                >= plan["launch_external_reserve_GiB"] * 2**30
            ):
                assert time.time() < deadline
                time.sleep(15)
            run_child(
                plan,
                record,
                [plan["python"], "-P", execution["collector"]["path"], str(execution_path)],
                work,
                root / arm / "collect.log",
                cuda=True,
                timeout=plan["maximum_collector_seconds"],
            )
            collection_path = root / arm / "collection-v1.json"
            collection = read(collection_path)
            assert collection["plan"] == ref(execution_path)
            assert collection["counts"] == {"root": 102, "encoder": 102}
            assert (
                collection["completed_training_checkpoint_verified"] and collection["RNG_unchanged"]
            )
            state["completed"][arm] = ref(collection_path)
            for name, arguments in [
                ("report_checkpoint_pilot.py", [str(execution_path), str(collection_path)]),
                ("audit_checkpoint_pilot.py", [str(root / arm)]),
            ]:
                run_child(
                    plan,
                    record,
                    [plan["python"], "-P", str(work / "scripts" / name), *arguments],
                    work,
                    root / arm / (name + ".log"),
                    cuda=False,
                    timeout=plan["maximum_CPU_analysis_seconds"],
                )
            audit = root / arm / "independent-audit-v1.json"
            assert read(audit)["status"] == "passed-independent-FFT-metric-and-native-pixel-audit"
            state["reports"][arm] = {
                "report": ref(root / arm / "report-v1/report.json"),
                "independent_audit": ref(audit),
            }
            prior_execution, prior_collection = execution, collection
            record("completed-endpoint-report-and-independent-audit", child=None)
        record("completed-both-endpoint-reviews-awaiting-actual-viewing", child=None)
    except BaseException as error:
        record("failed-endpoint-review-preserved-no-automatic-retry", error=repr(error), child=None)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--training-plan", type=Path)
    parser.add_argument("--observations-plan", type=Path)
    parser.add_argument("--zero-forward-handoff", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(
                args.path.resolve(),
                args.training_plan,
                args.observations_plan,
                args.zero_forward_handoff,
            )
        )
    else:
        controller(args.path.resolve())
