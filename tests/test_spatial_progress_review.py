"""Real queue protocol and checkpoint-contract checks without neural work."""

import copy
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import queue_raw_spatial_progress as queue
import torch
from collect_retained_checkpoint_pilot import verify_progress_checkpoint
from train_directional_bank_trial import read, ref, save


def progress(spatial=False):
    values = {f"common.{i}": torch.zeros(1) for i in range(91)}
    if spatial:
        values.update({f"pretrained_rgb.raw_spatial.{i}": torch.ones(1) for i in range(23)})
    lineage = {"path": "parent-fixture", "sha256": "a" * 64, "step": 20000}
    state = {
        "step": 1000,
        "config": {"steps": 20000, "initialized_from": lineage},
        "model_config": {"raw_spatial_features": spatial},
        "model": values,
        "ema": copy.deepcopy(values),
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(1000), "exp_avg": torch.zeros(1)}
                for i in range(112 if spatial else 89)
            }
        },
    }
    plan = {
        "step": 1000,
        "training_horizon": 20000,
        "raw_spatial_features": spatial,
        "EMA_tensors": len(values),
        "expected_lineage": lineage,
    }
    return state, plan


@pytest.mark.parametrize("spatial", [False, True])
def test_progress_state_verifier_constructs_no_neural_module(monkeypatch, spatial):
    def forbidden(*args, **kwargs):
        raise AssertionError("Progress validation must precede neural construction/calls")

    monkeypatch.setattr(torch.nn.Module, "__init__", forbidden)
    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)
    verify_progress_checkpoint(*progress(spatial))


@pytest.mark.parametrize(
    "change", ["step", "horizon", "lineage", "architecture", "tensors", "adam", "finite", "branch"]
)
def test_partial_changed_or_corrupt_checkpoint_is_rejected(change):
    state, plan = progress(True)
    if change == "step":
        state["step"] = 999
    elif change == "horizon":
        state["config"]["steps"] = 1000
    elif change == "lineage":
        state["config"]["initialized_from"] = {}
    elif change == "architecture":
        state["model_config"]["raw_spatial_features"] = False
    elif change == "tensors":
        del state["ema"]["common.90"]
    elif change == "adam":
        state["optimizer"]["state"][111]["step"] = torch.tensor(999)
    elif change == "finite":
        state["ema"]["common.90"].fill_(float("nan"))
    else:
        state["model"]["unknown.key"] = state["model"].pop("pretrained_rgb.raw_spatial.22")
        state["ema"] = copy.deepcopy(state["model"])
    with pytest.raises(ValueError):
        verify_progress_checkpoint(state, plan)


def queue_fixture(tmp_path):
    root, training_root = tmp_path / "queue", tmp_path / "training"
    root.mkdir()
    training_root.mkdir()
    checkpoint = tmp_path / "fixture-checkpoint.txt"
    checkpoint.write_text("Protocol fixture only; not a neural checkpoint\n")
    dead = {"pid": os.getpid(), "created": 0.0}
    training_path = training_root / "plan.json"
    save(
        training_path,
        {
            "root": str(training_root),
            "parent": ref(checkpoint),
            "parent_step": 20000,
            "backbones": {arm: {} for arm in queue.ARMS},
            "restoration_tensors_by_arm": {"V131": 91, "V132": 114},
        },
    )
    inputs = [
        {"step": i, "domain": "fixture", "clean_sha256": "c", "batch_sha256": "d"}
        for i in range(1, 1001)
    ]
    completed, frozen = {}, {}
    for arm in queue.ARMS:
        result = training_root / f"train-{arm}-result.json"
        save(result, {"owner": dead, "updates": 20000, "observed_inputs": inputs})
        completed[f"train-{arm}"] = ref(result)
        save(
            training_root / f"train-{arm}-progress1000.json",
            {
                "status": "immutable-progress-checkpoint-within-original-training-budget",
                "owner": dead,
                "arm": arm,
                "step": 1000,
                "declared_training_horizon": 20000,
                "checkpoint": ref(checkpoint),
                "observed_inputs": inputs,
                "counts_at_checkpoint": {
                    "training_forwards": 1000,
                    "optimizer_steps": 1000,
                    "prepared_training_batches": 1000,
                    "validation_forwards": 32,
                    "encoder_forwards": 1032,
                    "target_contexts": 16000,
                },
            },
        )
        work = root / arm / "work"
        (work / "src").mkdir(parents=True)
        scripts = work / "scripts"
        scripts.mkdir()
        collector = scripts / "collect_retained_checkpoint_pilot.py"
        collector.write_text(
            "import json,pathlib,sys\n"
            "p=pathlib.Path(sys.argv[1]);v=json.loads(p.read_text());r=pathlib.Path(v['root'])\n"
            "(r/'fixture-collect.claim').open('x').close()\n"
            "rows=[]\n"
            "for i,o in enumerate(v['observations']):\n"
            " q=r/f'fixture-prediction-{i}.txt';q.write_text('Zero neural calls')\n"
            " rows.append({'id':o['id'],'prediction':ref(q)})\n"
            "save(r/'collection-v1.json',{'plan':ref(p),'counts':{'root':102,'encoder':102},'observations':rows,'progress_checkpoint_verified':True,'training_horizon':20000,'fixture_actual_neural_calls':0})\n".replace(
                "import json,pathlib,sys\n",
                "import json,pathlib,sys\nfrom train_directional_bank_trial import ref,save\n",
            )
        )
        reporter = scripts / "report_checkpoint_pilot.py"
        reporter.write_text(
            "import json,pathlib,sys\n"
            "p=pathlib.Path(sys.argv[1]);v=json.loads(p.read_text());r=pathlib.Path(v['root'])\n"
            "(r/'report-v1').mkdir()\n"
            "(r/'report-v1/report.json').write_text(json.dumps({'fixture_actual_neural_calls':0,'control_counts':[len(o['controls']) for o in v['observations']]}))\n"
        )
        auditor = scripts / "audit_checkpoint_pilot.py"
        auditor.write_text(
            "import json,pathlib,sys\n"
            "r=pathlib.Path(sys.argv[1])\n"
            "(r/'independent-audit-v1.json').write_text(json.dumps({'status':'passed-independent-FFT-metric-and-native-pixel-audit','fixture_actual_neural_calls':0}))\n"
        )
        shutil.copyfile(
            Path(queue.__file__).with_name("train_directional_bank_trial.py"),
            scripts / "train_directional_bank_trial.py",
        )
        frozen.update({str(p): ref(p)["sha256"] for p in scripts.glob("*.py")})
    status_path = training_root / "status.json"
    save(
        status_path,
        {
            "plan": ref(training_path),
            "controller": dead,
            "child": None,
            "status": "completed-training-awaiting-model-comparisons",
            "completed": completed,
        },
    )
    controller = root / "controller.py"
    shutil.copyfile(queue.__file__, controller)
    for name in ("train_directional_bank_trial.py", "train_v43_quality_trial.py"):
        shutil.copyfile(Path(queue.__file__).with_name(name), root / name)
    frozen.update({str(p): ref(p)["sha256"] for p in root.glob("*.py")})
    plan = {
        "root": str(root),
        "worker_root": str(training_root),
        "training_plan": ref(training_path),
        "training_status": str(status_path),
        "training_owner": dead,
        "controller_source": ref(controller),
        "python": sys.executable,
        "arms": list(queue.ARMS),
        "step": 1000,
        "training_horizon": 20000,
        "observations": [
            {"id": f"fixture-{i}", "controls": [{"model": {"label": "V120"}}]} for i in range(102)
        ],
        "launch_RAM_GiB": 0.001,
        "runtime_RAM_GiB": 0.001,
        "CUDA_quota_GiB": 0,
        "launch_internal_reserve_GiB": 0,
        "launch_external_reserve_GiB": 0,
        "runtime_internal_reserve_GiB": 0,
        "runtime_external_reserve_GiB": 0,
        "maximum_training_wait_seconds": 20,
        "maximum_headroom_wait_seconds": 20,
        "maximum_collector_seconds": 20,
        "maximum_CPU_analysis_seconds": 20,
        "stable_headroom_seconds": 0,
        "inputs": [ref(training_path)],
        "frozen_files": frozen,
        "scope": "Owned subprocess protocol fixture; simulated coverage counters, zero actual neural/model/noise/RAW work.",
    }
    path = root / "queue-plan-v1.json"
    save(path, plan)
    return path, training_root


def test_real_owned_queue_collects_each_progress_once_and_reuses_control(tmp_path, monkeypatch):
    path, _ = queue_fixture(tmp_path)
    monkeypatch.setattr(queue, "__file__", str(path.parent / "controller.py"))
    monkeypatch.setattr(
        queue,
        "time",
        SimpleNamespace(
            time=time.time, monotonic=time.monotonic, sleep=lambda _: time.sleep(0.005)
        ),
    )
    queue.controller(path)
    state = read(path.parent / "status.json")
    assert state["status"] == "completed-progress-comparisons-awaiting-actual-native-viewing"
    assert set(state["completed"]) == set(queue.ARMS)
    for arm, expected in (("V131", 1), ("V132", 2)):
        report = read(state["reports"][arm]["report"]["path"])
        assert report["control_counts"] == [expected] * 102
        assert read(state["completed"][arm]["path"])["fixture_actual_neural_calls"] == 0
    with pytest.raises(FileExistsError):
        queue.controller(path)


def test_frozen_controller_entrypoint_uses_only_declared_helpers(tmp_path):
    path, _ = queue_fixture(tmp_path)
    result = subprocess.run(
        [sys.executable, "-P", str(path.parent / "controller.py"), "controller", str(path)],
        cwd=path.parent,
        env={**os.environ, "PYTHONPATH": str(path.parent)},
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, result.stderr
    state = read(path.parent / "status.json")
    assert state["status"] == "completed-progress-comparisons-awaiting-actual-native-viewing"
    assert len(list(path.parent.glob("*/fixture-collect.claim"))) == 2


@pytest.mark.parametrize("change", ["failed", "owner", "horizon", "missing", "input"])
def test_invalid_progress_or_training_never_launches_any_collector(tmp_path, monkeypatch, change):
    path, training = queue_fixture(tmp_path)
    monkeypatch.setattr(queue, "__file__", str(path.parent / "controller.py"))
    if change in ("failed", "owner"):
        state = read(training / "status.json")
        if change == "failed":
            state["status"] = "failed-fixture"
        else:
            state["controller"]["created"] = 1
        save(training / "status.json", state)
    else:
        p = training / "train-V131-progress1000.json"
        if change == "missing":
            p.unlink()
        else:
            receipt = read(p)
            if change == "horizon":
                receipt["declared_training_horizon"] = 1000
            else:
                receipt["observed_inputs"][-1]["clean_sha256"] = "changed"
            save(p, receipt)
    with pytest.raises((AssertionError, RuntimeError)):
        queue.controller(path)
    assert not list(path.parent.glob("*/fixture-collect.claim"))


def test_live_snapshot_accepts_only_the_exact_running_worker(monkeypatch):
    dependency = {
        "training_plan": {},
        "training_owner": {"live": True},
        "step": 1000,
        "training_horizon": 20000,
    }
    monkeypatch.setattr(queue, "live", lambda owner: owner["live"])
    owner = {"live": True, "identity": "worker"}
    receipt = {
        "status": "immutable-progress-checkpoint-within-original-training-budget",
        "owner": owner,
        "arm": "V131",
        "step": 1000,
        "declared_training_horizon": 20000,
        "counts_at_checkpoint": {
            "training_forwards": 1000,
            "optimizer_steps": 1000,
            "prepared_training_batches": 1000,
            "validation_forwards": 32,
            "encoder_forwards": 1032,
            "target_contexts": 16000,
        },
        "observed_inputs": [{"step": i} for i in range(1, 1001)],
    }
    state = {
        "plan": {},
        "controller": dependency["training_owner"],
        "child": owner,
        "phase": "train",
        "arm": "V131",
        "status": "running-quality-training",
    }
    assert queue.progress_ready(dependency, state, "V131", receipt)
    state["child"] = {"live": True, "identity": "replacement"}
    with pytest.raises(AssertionError):
        queue.progress_ready(dependency, state, "V131", receipt)


def test_preserved_absolute_wait_deadline_rejects_even_an_available_snapshot(tmp_path, monkeypatch):
    path, _ = queue_fixture(tmp_path)
    monkeypatch.setattr(queue, "__file__", str(path.parent / "controller.py"))
    plan = read(path)
    plan["absolute_training_wait_deadline_unix"] = time.time() - 1
    save(path, plan)
    with pytest.raises(AssertionError):
        queue.controller(path)
    assert not list(path.parent.glob("*/fixture-collect.claim"))
