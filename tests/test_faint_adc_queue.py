"""Owned subprocess protocol tests; fixture collectors perform no neural work."""

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import queue_faint_adc_precision as queue
from train_directional_bank_trial import read, ref, save


def fixture(tmp_path, monkeypatch, failure=None, changed_owner=False):
    root = tmp_path / "faint-ADC"
    root.mkdir()
    checkpoint = root / "fixture-checkpoint.txt"
    checkpoint.write_text("Protocol fixture; no model or tensors")
    dead = {"pid": os.getpid(), "created": 0.0}
    producer = root / "fixture-training"
    producer.mkdir()
    training_path = producer / "plan.json"
    save(training_path, {"root": str(producer)})
    result_path = producer / "train-V130-result.json"
    save(
        result_path,
        {
            "updates": 1000,
            "all_AdamW_steps": 1000,
            "model_EMA_Adam_finite": True,
            "all_observed_inputs_match_saved_control": True,
            "owner": dead,
            "checkpoint": ref(checkpoint),
        },
    )
    save(
        producer / "status.json",
        {
            "plan": ref(training_path),
            "controller": {**dead, "created": 1.0} if changed_owner else dead,
            "status": "completed-training-awaiting-model-comparisons",
            "child": None,
            "completed": {"train-V130": ref(result_path)},
        },
    )
    methods = {}
    frozen = {}
    for label in ("V120", "V129", "V130"):
        work = root / label / "work"
        scripts = work / "scripts"
        scripts.mkdir(parents=True)
        (work / "src").mkdir()
        collector = scripts / "collect_retained_checkpoint_pilot.py"
        collector.write_text(
            "import json,pathlib,sys\n"
            "p=json.loads(pathlib.Path(sys.argv[1]).read_text())\n"
            "r=pathlib.Path(p['root'])\n"
            "(r/'fixture-only-call').write_text('Zero neural work')\n"
            + ("raise RuntimeError('Declared fixture failure')\n" if label == failure else "")
            + "rows=[{'id':o['id'],'prediction':p['checkpoint']} for o in p['observations']]\n"
            "(r/'collection-v1.json').write_text(json.dumps({'plan':{'path':str(pathlib.Path(sys.argv[1]).resolve()),'sha256':__import__('hashlib').sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()},'counts':{'root':16,'encoder':16},'RNG_unchanged':True,'observations':rows}))\n"
        )
        frozen[str(collector)] = ref(collector)["sha256"]
        methods[label] = {"checkpoint": ref(checkpoint), "step": 20000 if label == "V120" else 1000}
    path = root / "plan-v1.json"
    save(
        path,
        {
            "root": str(root),
            "methods": methods,
            "python": sys.executable,
            "training_plan": ref(training_path),
            "training_owner": dead,
            "training_worker": dead,
            "absolute_training_deadline_unix": time.time() + 60,
            "observations": [{"id": f"fixture-{i}"} for i in range(16)],
            "inputs": [],
            "frozen_files": frozen,
            "launch_RAM_GiB": 48,
            "maximum_collector_seconds": 30,
        },
    )
    save(
        root / "input-audit-v1.json",
        {
            "plan": ref(path),
            "status": "passed-independent-faint-target-and-ADC-preparation-audit",
            "scope": "Protocol fixture only; no actual tensor audit",
        },
    )
    monkeypatch.setattr(
        queue.psutil, "virtual_memory", lambda: SimpleNamespace(available=80 * 2**30)
    )
    monkeypatch.setattr(
        queue,
        "time",
        SimpleNamespace(
            time=time.time, monotonic=time.monotonic, sleep=lambda unused: time.sleep(0.005)
        ),
    )
    return path


def test_three_methods_collected_once_and_saved_controls_wired(tmp_path, monkeypatch):
    path = fixture(tmp_path, monkeypatch)
    queue.controller(path)
    state = read(path.parent / "status.json")
    assert (
        state["status"] == "completed48-faint-ADC-forwards-awaiting-independent-and-native-review"
    )
    assert list(state["completed"]) == ["V120", "V129", "V130"]
    for label, expected in [("V120", []), ("V129", ["V120"]), ("V130", ["V120", "V129 1k EMA"])]:
        execution = read(path.parent / label / "plan-v1.json")
        assert [r["model"]["label"] for r in execution["observations"][0]["controls"]] == expected
    with pytest.raises(FileExistsError):
        queue.controller(path)
    assert len(list(path.parent.glob("*/fixture-only-call"))) == 3


def test_failed_method_preserves_completed_prefix_without_retry(tmp_path, monkeypatch):
    path = fixture(tmp_path, monkeypatch, failure="V129")
    with pytest.raises(AssertionError):
        queue.controller(path)
    state = read(path.parent / "status.json")
    assert state["status"] == "failed-preserved-no-automatic-retry" and list(
        state["completed"]
    ) == ["V120"]
    assert not (path.parent / "V130/fixture-only-call").exists()


def test_replaced_producer_cannot_supply_V130_endpoint(tmp_path, monkeypatch):
    path = fixture(tmp_path, monkeypatch, changed_owner=True)
    with pytest.raises(AssertionError):
        queue.controller(path)
    assert list(read(path.parent / "status.json")["completed"]) == ["V120", "V129"]
    assert not (path.parent / "V130/fixture-only-call").exists()
