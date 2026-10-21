"""Explicitly recover an early V95 resource failure while retaining completed arms."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import compare_pair, live, resources

REPO = Path(__file__).resolve().parents[1]


def resource_snapshot(root):
    result = {"unix": time.time(), "RAM_available_bytes": psutil.virtual_memory().available}
    for name, path in (("root", root), ("external", "/mnt/external")):
        try:
            result[name + "_free_bytes"] = shutil.disk_usage(path).free
        except OSError as error:
            result[name + "_free_bytes"] = None
            result[name + "_error"] = repr(error)
    result["external_is_mount"] = os.path.ismount("/mnt/external")
    try:
        result["external_device"] = Path("/mnt/external").stat().st_dev
    except OSError:
        result["external_device"] = None
    return result


def headroom(snapshot, plan, ram_gib=24):
    reserves = plan["disk_reserves"]
    return (
        snapshot["RAM_available_bytes"] >= ram_gib * 2**30
        and snapshot["root_free_bytes"] is not None
        and snapshot["root_free_bytes"] >= reserves["root_reserve_gib"] * 2**30
        and snapshot["external_free_bytes"] is not None
        and snapshot["external_free_bytes"] >= reserves["external_reserve_gib"] * 2**30
        and snapshot["external_is_mount"]
        and snapshot["external_device"] == plan["external_device"]
    )


def signal_owned_group(owner, sig):
    process = psutil.Process(owner["pid"])
    assert process.create_time() == owner["created"] and os.getsid(process.pid) == process.pid
    assert process.status() != psutil.STATUS_ZOMBIE
    os.killpg(process.pid, sig)


def stop_owned_child(child, owner):
    if child.poll() is not None:
        return
    try:
        stopped = psutil.Process(child.pid).status() == psutil.STATUS_STOPPED
        signal_owned_group(owner, signal.SIGTERM)
        if stopped:
            try:
                signal_owned_group(owner, signal.SIGCONT)
            except (psutil.NoSuchProcess, ProcessLookupError):
                pass
    except (psutil.NoSuchProcess, ProcessLookupError):
        pass
    try:
        child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        signal_owned_group(owner, signal.SIGKILL)
        child.wait(timeout=10)


def prepare(study, root, reclamation):
    original_path = study / "plan.json"
    original = read(original_path)
    guard(original)
    failure_path = study / "status.json"
    failure = read(failure_path)
    assert failure["status"] == "failed-V43-quality-stage-preserved-no-automatic-retry"
    assert failure["phase"] == "train" and failure["arm"] == "V95"
    assert failure["error"] == "AssertionError('Training resource floor')"
    assert failure["plan"] == ref(original_path)
    assert not live(failure["controller"]) and not live(failure["child"])
    expected = {f"{phase}-{arm}" for phase in ("CPU", "CUDA") for arm in ("V93", "V94", "V95")}
    assert set(failure["completed"]) == expected | {"train-V93", "train-V94"}
    for name, item in failure["completed"].items():
        assert ref(item["path"]) == item
        result = read(item["path"])
        assert not live(result["owner"]) and result["plan"] == ref(original_path)
        assert result["engineering_only"] == (not name.startswith("train-"))
        assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        assert ref(result["metrics"]["path"]) == result["metrics"]
    controls = {arm: read(failure["completed"][f"train-{arm}"]["path"]) for arm in ("V93", "V94")}
    matched = compare_pair(
        controls["V93"]["logged_training_observations"],
        controls["V94"]["logged_training_observations"],
        {"native-RAW-synthetic", "paired-RAW"},
        require_changes=True,
    )
    assert all(r["counts"]["optimizer_steps"] == 20000 for r in controls.values())
    assert len({r["source_sha256"] for r in controls.values()}) == 1
    assert (
        read(reclamation)["status"]
        == "owned-cold-checkpoints-relocated-with-original-paths-and-bytes-preserved"
    )
    assert resources(study, 48, **original["disk_reserves"])
    run = Path(original["artifact_root"]) / "train/V95"
    assert run.is_dir() and not list(run.glob("*.pt"))
    assert not (study / "train-V95-result.json").exists()
    assert (study / "train-V95.claim").exists()
    assert (study / "train-V95.log").exists()
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    failed = root / "failed-original"
    failed.mkdir()
    archived_status = failed / "status.json"
    shutil.copyfile(failure_path, archived_status)
    assert archived_status.read_bytes() == failure_path.read_bytes()
    archive_run = Path(original["artifact_root"]) / ("failed-train-V95-before-" + root.name)
    assert not archive_run.exists()
    trial_files = {str(p.relative_to(run)): ref(p) for p in run.rglob("*") if p.is_file()}
    run.rename(archive_run)
    archived = []
    for relative, old in trial_files.items():
        new = ref(archive_run / relative)
        assert new["sha256"] == old["sha256"]
        archived.append({"original": old, "archived": new})
    for name in ("train-V95.claim", "train-V95.log"):
        source, target = study / name, failed / name
        old = ref(source)
        source.rename(target)
        assert ref(target)["sha256"] == old["sha256"]
        archived.append({"original": old, "archived": ref(target)})
    save(
        root / "archive.json",
        {
            "status": "failed-V95-trial-archived-byte-exact-before-explicit-recovery",
            "failure": ref(archived_status),
            "files": archived,
            "scope": "Failed partial trial had no saved checkpoint. Preserve all its bytes and original-path mapping; completed arms, original frozen plan and original controller claim/log unchanged.",
        },
    )
    operator = root / "controller-executed-source.py"
    shutil.copyfile(__file__, operator)
    inputs = [
        ref(original_path),
        ref(archived_status),
        ref(root / "archive.json"),
        ref(reclamation),
    ]
    inputs += list(failure["completed"].values())
    inputs += [r["archived"] for r in archived]
    plan = {
        "root": str(root),
        "study": str(study),
        "work": original["work"],
        "original_plan": ref(original_path),
        "original_failure": ref(archived_status),
        "original_completed_results": failure["completed"],
        "completed_control_input_audit": matched,
        "operator": ref(operator),
        "python": original["python"],
        "cache_environment": original["cache_environment"],
        "disk_reserves": original["disk_reserves"],
        "wait_seconds": original["wait_seconds"],
        "stable_seconds": original["stable_seconds"],
        "timeout_seconds": original["timeouts_seconds"]["train"],
        "external_device": Path("/mnt/external").stat().st_dev,
        "resource_startup_observation": resource_snapshot(study),
        "resource_policy": "Capture exact readings every2s. RAM below24GiB terminates the owned worker. Disk reserve/mount breach with adequate RAM suspends only the owned process group; resume the same PID after original48GiB/disk floors are stable60s, verifying both input guards. Disk wait bounded7200s and original stage wall-time bound still applies. No retry or numerical-worker change.",
        "inputs": inputs,
        "frozen_files": {str(operator): ref(operator)["sha256"]},
        "scope": "Explicit manual recovery after an unsaved early V95 resource-guard stop. Previous guards did not record which resource crossed its floor. Reuse all passed preflights and completed V93/V94. Restart only V95 from original V43 step2000 with the exact original frozen numerical worker/config/20k schedule and unchanged resource thresholds. Preserve failed trial bytes. Add exact resource telemetry and same-worker disk suspension, with immediate termination for a RAM breach. No automatic retry or quality promotion.",
    }
    save(root / "plan.json", plan)
    guard(original)
    guard(plan)
    print(ref(root / "plan.json"))


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    original = read(plan["original_plan"]["path"])
    guard(original)
    root, study, work = Path(plan["root"]), Path(plan["study"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = read(plan["original_failure"]["path"])
    assert ref(study / "status.json") == {
        "path": str(study / "status.json"),
        "sha256": plan["original_failure"]["sha256"],
    }
    state.pop("error")
    state.pop("child")
    state["controller"] = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state["manual_recovery"] = {
        "plan": ref(plan_path),
        "original_failed_status": plan["original_failure"],
    }
    child, identity = None, None
    last_snapshot = None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(study / "status.json", state)
        save(root / "status.json", state)

    def observe():
        nonlocal last_snapshot
        snapshot = resource_snapshot(study)
        last_snapshot = snapshot
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(snapshot) + "\n")
        return snapshot

    try:
        began, stable = time.monotonic(), None
        record("waiting-for-stable-training-headroom", phase="train", arm="V95")
        while True:
            assert time.monotonic() - began < plan["wait_seconds"]
            stable = (
                (time.monotonic() if stable is None else stable)
                if headroom(observe(), plan, 48)
                else None
            )
            if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                break
            time.sleep(5)
        guard(plan)
        guard(original)
        assert not (study / "train-V95.claim").exists()
        env = dict(
            os.environ,
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            CUDA_VISIBLE_DEVICES="0",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OMP_NUM_THREADS="4",
            OPENBLAS_NUM_THREADS="2",
            PYTHONDONTWRITEBYTECODE="1",
        )
        env.update(plan["cache_environment"])
        with (study / "train-V95.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    str(work / "scripts/train_v43_quality_trial.py"),
                    "worker",
                    plan["original_plan"]["path"],
                    "--phase",
                    "train",
                    "--arm",
                    "V95",
                ],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-V43-quality-stage", phase="train", arm="V95", child=identity)
            deadline = time.monotonic() + plan["timeout_seconds"]
            while child.poll() is None:
                snapshot = observe()
                assert snapshot["RAM_available_bytes"] >= 24 * 2**30, snapshot
                if not headroom(snapshot, plan):
                    signal_owned_group(identity, signal.SIGSTOP)
                    record("paused-V43-training-disk-reserve", resource_snapshot=snapshot)
                    paused_at, stable = time.monotonic(), None
                    while True:
                        assert child.poll() is None, "Suspended worker exited"
                        assert time.monotonic() < deadline, "Training stage runtime bound"
                        assert time.monotonic() - paused_at < plan["wait_seconds"], (
                            "Disk reserve wait bound"
                        )
                        current = observe()
                        assert current["RAM_available_bytes"] >= 24 * 2**30, current
                        stable = (
                            (time.monotonic() if stable is None else stable)
                            if headroom(current, plan, 48)
                            else None
                        )
                        if (
                            stable is not None
                            and time.monotonic() - stable >= plan["stable_seconds"]
                        ):
                            guard(original)
                            guard(plan)
                            signal_owned_group(identity, signal.SIGCONT)
                            record(
                                "running-V43-quality-stage",
                                resumed_same_worker=True,
                                resource_snapshot=current,
                            )
                            break
                        time.sleep(2)
                assert time.monotonic() < deadline, "Training stage runtime bound"
                time.sleep(2)
            assert child.wait() == 0, child.returncode
        result_path = study / "train-V95-result.json"
        result = read(result_path)
        assert result["owner"] == identity and result["plan"] == plan["original_plan"]
        assert not result["engineering_only"] and result["counts"]["optimizer_steps"] == 20000
        state["completed"]["train-V95"] = ref(result_path)
        results = {
            arm: read(state["completed"][f"train-{arm}"]["path"]) for arm in ("V93", "V94", "V95")
        }
        assert len({r["source_sha256"] for r in results.values()}) == 1
        audit = {
            "larger_data_shared_domains": compare_pair(
                results["V93"]["logged_training_observations"],
                results["V94"]["logged_training_observations"],
                {"native-RAW-synthetic", "paired-RAW"},
                require_changes=True,
            ),
            "fine_detail_paired_domain": compare_pair(
                results["V94"]["logged_training_observations"],
                results["V95"]["logged_training_observations"],
                {"paired-RAW"},
                require_changes=True,
            ),
        }
        guard(original)
        guard(plan)
        record(
            "completed-matched-V43-training-awaiting-full-evaluation-and-native-review",
            observation_audit=audit,
        )
        save(
            root / "result.json",
            {
                "status": "explicit-V95-recovery-completed-all-three-original-plan-endpoints",
                "plan": ref(plan_path),
                "original_plan": plan["original_plan"],
                "original_failure": plan["original_failure"],
                "owner": state["controller"],
                "worker": identity,
                "completed": state["completed"],
                "observation_audit": audit,
                "final_status": ref(study / "status.json"),
                "scope": plan["scope"],
            },
        )
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, identity)
        record(
            "failed-V43-quality-stage-preserved-no-automatic-retry",
            error=repr(error),
            last_resource_snapshot=last_snapshot,
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reclamation", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output and args.reclamation
        prepare(args.path.resolve(), args.output, args.reclamation.resolve())
    else:
        controller(args.path.resolve())
