"""Real owned subprocess protocol checks with collectors that do no neural work."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import queue_shadow_pilot_quality as queue
from train_directional_bank_trial import ref, save


def fixture(tmp_path, status_name="completed-training-awaiting-model-comparisons"):
    root, training_root = tmp_path / "queue", tmp_path / "training"
    root.mkdir()
    training_root.mkdir()
    checkpoint = tmp_path / "fixture-checkpoint.txt"
    checkpoint.write_text("Protocol fixture; never loaded as a model")
    parent = ref(checkpoint)
    training = {
        "root": str(training_root),
        "parent": parent,
        "parent_step": 20000,
        "backbones": {"V126": {}, "V127": {}},
    }
    training_path = training_root / "plan.json"
    save(training_path, training)
    # Deliberately nonmatching creation time marks these fixture handles exited.
    dead = {"pid": os.getpid(), "created": 0.0}
    completed, frozen = {}, {}
    for arm in ("V126", "V127"):
        path = training_root / f"train-{arm}-result.json"
        save(
            path,
            {
                "updates": 1000,
                "owner": dead,
                "model_EMA_Adam_finite": True,
                "all_AdamW_steps": 1000,
                "checkpoint": parent,
            },
        )
        completed[f"train-{arm}"] = ref(path)
        work = root / arm / "work"
        (work / "src").mkdir(parents=True)
        scripts = work / "scripts"
        scripts.mkdir()
        collector = scripts / "collect_retained_checkpoint_pilot.py"
        collector.write_text(
            "import json, pathlib, sys\n"
            "plan = json.loads(pathlib.Path(sys.argv[1]).read_text())\n"
            "root = pathlib.Path(plan['root'])\n"
            "(root / 'actual-fixture-call').write_text('No neural work')\n"
            "(root / 'collection-v1.json').write_text(json.dumps({'counts': {'root':86,'encoder':86}}))\n"
        )
        frozen[str(collector)] = ref(collector)["sha256"]
    save(
        training_root / "status.json",
        {
            "plan": ref(training_path),
            "controller": dead,
            "child": dead,
            "status": status_name,
            "completed": completed,
        },
    )
    inputs_path = tmp_path / "inputs.json"
    save(
        inputs_path,
        {
            "shadow_observations": [{"id": f"shadow-{i}"} for i in range(64)],
            "retained_observations": [{"id": f"retained-{i}"} for i in range(22)],
        },
    )
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_owner": dead,
        "input_plan": ref(inputs_path),
        "python": sys.executable,
        "maximum_training_wait_seconds": 30,
        "maximum_collector_seconds": 30,
        "launch_RAM_GiB": 48,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 12,
        "launch_internal_reserve_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "launch_external_reserve_GiB": 208,
        "runtime_external_reserve_GiB": 208,
        "inputs": [ref(training_path), ref(inputs_path)],
        "frozen_files": frozen,
        "scope": "Protocol fixture only; no actual NN calls or checkpoints",
    }
    path = root / "queue-plan-v1.json"
    save(path, plan)
    return path, training_root


def test_completed_training_collects_each_new_endpoint_once(tmp_path, monkeypatch):
    path, _ = fixture(tmp_path)
    monkeypatch.setattr(
        queue,
        "time",
        SimpleNamespace(
            time=time.time, monotonic=time.monotonic, sleep=lambda unused: time.sleep(0.005)
        ),
    )
    monkeypatch.setattr(
        queue.psutil, "virtual_memory", lambda: SimpleNamespace(available=80 * 2**30)
    )
    queue.controller(path)
    state = json.loads((path.parent / "status.json").read_text())
    assert state["status"] == "completed-pilot-predictions-awaiting-independent-and-native-review"
    assert set(state["completed"]) == {"V126", "V127"}
    assert len(list(path.parent.glob("*/actual-fixture-call"))) == 2
    with pytest.raises(FileExistsError):
        queue.controller(path)


@pytest.mark.parametrize("status", ["failed-fixture", "running-quality-training"])
def test_failed_or_prematurely_exited_training_never_collects(tmp_path, status):
    path, _ = fixture(tmp_path, status)
    with pytest.raises((RuntimeError, AssertionError)):
        queue.controller(path)
    assert not list(path.parent.glob("*/actual-fixture-call"))


def test_replaced_training_owner_is_rejected(tmp_path):
    path, training = fixture(tmp_path)
    status_path = training / "status.json"
    status = json.loads(status_path.read_text())
    status["controller"]["created"] = 1.0
    save(status_path, status)
    with pytest.raises(AssertionError):
        queue.controller(path)
    assert not list(path.parent.glob("*/actual-fixture-call"))


def test_frozen_entrypoint_runs_with_only_declared_helpers(tmp_path):
    path, _ = fixture(tmp_path)
    for name in (
        "queue_shadow_pilot_quality.py",
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
    ):
        destination = path.parent / ("controller.py" if name.startswith("queue_") else name)
        shutil.copyfile(Path(queue.__file__).with_name(name), destination)
    plan = json.loads(path.read_text())
    plan["launch_RAM_GiB"] = 0.001  # Model-free child fixture, never CUDA allocation.
    plan["frozen_files"].update({str(p): ref(p)["sha256"] for p in path.parent.glob("*.py")})
    save(path, plan)
    result = subprocess.run(
        [sys.executable, "-P", str(path.parent / "controller.py"), "controller", str(path)],
        cwd=path.parent,
        env={**os.environ, "PYTHONPATH": str(path.parent)},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    status = json.loads((path.parent / "status.json").read_text())
    assert status["status"] == "completed-pilot-predictions-awaiting-independent-and-native-review"
    assert len(list(path.parent.glob("*/actual-fixture-call"))) == 2
