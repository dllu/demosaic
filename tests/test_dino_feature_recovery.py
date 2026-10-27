"""Check spent-budget accounting and actual single-launch recovery ownership without a model."""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resume_dino_feature_training as recovery
from train_directional_bank_trial import ref, save


def saved_prefix():
    state = {"step": 399, "optimizer": {"state": {k: {"step": 399.0} for k in range(89)}}}
    failure = {
        "counts": {
            "optimizer_steps": 399,
            "training_forwards": 399,
            "prepared_training_batches": 399,
            "validation_forwards": 0,
            "encoder_forwards": 399,
        }
    }
    return state, failure


def test_emergency_checkpoint_spends_only_remaining_original_updates():
    state, failure = saved_prefix()
    assert recovery.remaining_budget(state, failure, 1000) == 601


@pytest.mark.parametrize("fault", ["lost_updates", "optimizer", "encoder"])
def test_partial_or_mismatched_emergency_state_is_rejected(fault):
    state, failure = saved_prefix()
    if fault == "lost_updates":
        state["step"] = 300
    elif fault == "optimizer":
        state["optimizer"]["state"][0]["step"] = 300.0
    else:
        failure["counts"]["encoder_forwards"] += 1
    with pytest.raises(ValueError):
        recovery.remaining_budget(state, failure, 1000)


def fixture_plan(tmp_path, monkeypatch, exit_code=0):
    worker = tmp_path / "stub.py"
    worker.write_text(
        "import os, pathlib, sys, psutil, json\n"
        "p = json.loads(pathlib.Path(sys.argv[2]).read_text())\n"
        "assert os.environ['CUBLAS_WORKSPACE_CONFIG'] == ':4096:8'\n"
        "r = pathlib.Path(p['root'])\n"
        "(r / 'actual-launch.claim').open('x').close()\n"
        f"if {exit_code}: sys.exit({exit_code})\n"
        "(r / 'train-V128-result.json').write_text(json.dumps({'owner': {'pid':os.getpid(), 'created':psutil.Process().create_time()}}))\n"
    )
    plan = {
        "root": str(tmp_path),
        "work": str(tmp_path),
        "python": sys.executable,
        "controller_source": ref(worker),
        "adopted_phase_results": {"CPU-V128": {"saved": True}, "CUDA-V128": {"saved": True}},
        "absolute_worker_deadline_unix": time.time() + 30,
        "headroom_deadline_unix": time.time() + 30,
        "launch_available_RAM_GiB": 56,
        "phase_start_internal_free_GiB": 128,
        "phase_start_external_free_GiB": 208,
        "runtime_internal_reserve_GiB": 96,
        "runtime_external_reserve_GiB": 208,
        "inputs": [],
        "frozen_files": {str(worker): ref(worker)["sha256"]},
    }
    path = tmp_path / "plan.json"
    save(path, plan)
    monkeypatch.setattr(recovery, "__file__", str(worker))
    clock = [0.0]

    def monotonic():
        clock[0] += 20
        return clock[0]

    monkeypatch.setattr(
        recovery,
        "time",
        SimpleNamespace(
            time=time.time, monotonic=monotonic, sleep=lambda unused: time.sleep(0.005)
        ),
    )
    monkeypatch.setattr(
        recovery.psutil, "virtual_memory", lambda: SimpleNamespace(available=80 * 2**30)
    )
    monkeypatch.setattr(
        recovery.shutil, "disk_usage", lambda unused: SimpleNamespace(free=1000 * 2**30)
    )
    return path


def test_one_real_owned_worker_adopts_both_completed_checks(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path, monkeypatch)
    recovery.controller(path)
    state = json.loads((tmp_path / "status.json").read_text())
    assert state["status"] == "completed-training-awaiting-model-comparisons"
    assert state["completed"]["CPU-V128"] == state["completed"]["CUDA-V128"] == {"saved": True}
    assert set(state["completed"]) == {"CPU-V128", "CUDA-V128", "train-V128"}
    assert (tmp_path / "actual-launch.claim").exists()


def test_failed_continuation_gets_no_second_worker(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path, monkeypatch, exit_code=7)
    with pytest.raises(AssertionError):
        recovery.controller(path)
    state = json.loads((tmp_path / "status.json").read_text())
    assert state["status"] == "failed-feature-continuation-preserved-no-automatic-retry"
    assert set(state["completed"]) == {"CPU-V128", "CUDA-V128"}
    assert (tmp_path / "actual-launch.claim").exists()


def test_original_deadline_is_not_reset_on_continuation(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path, monkeypatch)
    plan = json.loads(path.read_text())
    plan["absolute_worker_deadline_unix"] = time.time() - 1
    save(path, plan)
    with pytest.raises(AssertionError):
        recovery.controller(path)
    assert not (tmp_path / "actual-launch.claim").exists()
