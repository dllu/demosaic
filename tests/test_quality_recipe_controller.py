"""Exercise delegated training control with real, owned subprocesses (no model)."""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import train_quality_recipes as runner
from train_directional_bank_trial import ref, save


def fixture_plan(tmp_path, *, child_exit=0):
    work = tmp_path / "work"
    work.mkdir()
    worker = work / "delegated.py"
    worker.write_text(
        "import json, os, pathlib, sys, psutil\n"
        "plan = json.loads(pathlib.Path(sys.argv[2]).read_text())\n"
        "phase = sys.argv[sys.argv.index('--phase') + 1]\n"
        "arm = sys.argv[sys.argv.index('--arm') + 1]\n"
        "root = pathlib.Path(plan['root'])\n"
        "(root / (phase + '-' + arm + '.actual')).write_text(str(os.getpid()))\n"
        f"if {child_exit}: sys.exit({child_exit})\n"
        "result = {'owner': {'pid': os.getpid(), 'created': psutil.Process().create_time()}}\n"
        "(root / (phase + '-' + arm + '-result.json')).write_text(json.dumps(result))\n"
    )
    plan = {
        "root": str(tmp_path),
        "work": str(work),
        "python": sys.executable,
        "arms": {"V126": {}, "V127": {}},
        "worker_script": ref(worker),
        "inputs": [],
        "frozen_files": {str(worker): ref(worker)["sha256"]},
        "launch_available_RAM_GiB": 64,
        "maximum_train_worker_seconds": 30,
        "maximum_smoke_worker_seconds": 30,
    }
    path = tmp_path / "plan.json"
    save(path, plan)
    return path


def environment(monkeypatch, available, *, increment=1):
    clock = [0.0]

    def now():
        clock[0] += increment
        return clock[0]

    monkeypatch.setattr(
        runner,
        "time",
        SimpleNamespace(monotonic=now, time=time.time, sleep=lambda unused: time.sleep(0.005)),
    )
    monkeypatch.setattr(
        runner.psutil, "virtual_memory", lambda: SimpleNamespace(available=available * 2**30)
    )
    monkeypatch.setattr(
        runner.shutil, "disk_usage", lambda unused: SimpleNamespace(free=1000 * 2**30)
    )


def test_delegated_worker_completes_all_phases(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path)
    environment(monkeypatch, 80)
    runner.controller(path)
    state = json.loads((tmp_path / "status.json").read_text())
    assert state["status"] == "completed-training-awaiting-model-comparisons"
    assert set(state["completed"]) == {
        f"{phase}-{arm}" for phase in ("CPU", "CUDA", "train") for arm in ("V126", "V127")
    }
    assert len(list(tmp_path.glob("*.actual"))) == 6
    assert all(ref(v["path"]) == v for v in state["completed"].values())


def test_failed_delegate_is_not_retried(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path, child_exit=7)
    environment(monkeypatch, 80)
    with pytest.raises(AssertionError):
        runner.controller(path)
    state = json.loads((tmp_path / "status.json").read_text())
    assert state["status"] == "failed-training-preserved-no-automatic-retry"
    assert len(list(tmp_path.glob("*.actual"))) == 1


def test_declared_headroom_blocks_worker_launch(tmp_path, monkeypatch):
    path = fixture_plan(tmp_path)
    environment(monkeypatch, 63, increment=500)

    def forbidden(*args, **kwargs):
        pytest.fail("Worker launched below the plan's64GiB headroom")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    with pytest.raises(AssertionError):
        runner.controller(path)
    assert not list(tmp_path.glob("*.actual"))


def test_adoption_keeps_completed_checks_and_original_worker_plan(tmp_path, monkeypatch):
    old = tmp_path / "old"
    old.mkdir()
    previous = fixture_plan(old)
    original = json.loads(previous.read_text())
    dead = {"pid": __import__("os").getpid(), "created": 0.0}
    completed = {}
    for phase, arm in [("CPU", "V126"), ("CPU", "V127"), ("CUDA", "V126")]:
        result = old / f"{phase}-{arm}-result.json"
        save(result, {"owner": dead, "updates": 18})
        completed[f"{phase}-{arm}"] = ref(result)
    root = tmp_path / "adopted"
    root.mkdir()
    plan = {
        **original,
        "root": str(root),
        "output_worker_root": str(old),
        "adopted_worker_plan": ref(previous),
        "adopted_phase_results": completed,
        "replaced_controller": dead,
        "launch_available_RAM_GiB": 52,
        "inputs": [ref(previous), *completed.values()],
        "adopted_headroom_deadline": {"phase": "CUDA", "arm": "V127", "unix": time.time() + 60},
    }
    path = root / "plan.json"
    save(path, plan)
    environment(monkeypatch, 56)
    runner.controller(path)
    state = json.loads((root / "status.json").read_text())
    assert state["status"] == "completed-training-awaiting-model-comparisons"
    assert len(state["completed"]) == 6
    assert len(list(old.glob("*.actual"))) == 3
    assert not list(root.glob("*.actual"))
    assert all(ref(v["path"]) == v for v in completed.values())
