"""Protect exact dependency identities and leave unrelated retained controls untouched."""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rebind_unstarted_quality_queue as repair
from rebind_unstarted_quality_queue import replace_dependencies
from train_directional_bank_trial import guard, read, ref, save


def test_rebind_updates_hashes_owners_and_output_paths_together():
    old = {"path": "/cache/old-producer/plan.json", "sha256": "old"}
    new = {"path": "/cache/new-producer/plan.json", "sha256": "new"}
    owners = ({"pid": 3, "created": 1.0}, {"pid": 4, "created": 2.0})
    mapping = [
        {
            "old_root": "/cache/old-producer",
            "new_root": "/cache/new-producer",
            "old_plan": old,
            "new_plan": new,
            "old_owner": owners[0],
            "new_owner": owners[1],
        }
    ]
    value = {
        "input": old,
        "owner": owners[0],
        "status": "/cache/old-producer/status.json",
        "output": "/cache/old-queue/work/arrays",
        "frozen_files": {"/cache/old-queue/work/x.py": "retained"},
        "control": {"path": "/cache/old-producer-sibling/output", "sha256": "fixed"},
        "description": "Uses /cache/old-producer historically",
    }
    updated = replace_dependencies(value, mapping, "/cache/old-queue", "/cache/new-queue")
    assert updated["input"] == new and updated["owner"] == owners[1]
    assert updated["status"] == "/cache/new-producer/status.json"
    assert updated["output"] == "/cache/new-queue/work/arrays"
    assert updated["frozen_files"] == {"/cache/new-queue/work/x.py": "retained"}
    assert updated["control"] == value["control"] and updated["description"] == value["description"]
    assert value["input"] == old and value["owner"] == owners[0]


@pytest.mark.parametrize("started", [False, True])
@pytest.mark.parametrize("controller_field", ["controller_source", "controller_script"])
def test_actual_frozen_stub_is_rebound_once_or_started_work_is_rejected(
    tmp_path, monkeypatch, started, controller_field
):
    monkeypatch.setattr(repair, "REPO", tmp_path)
    old = tmp_path / ".cache/old"
    work = old / "work/scripts"
    work.mkdir(parents=True)
    script = work / "stub.py"
    script.write_text(
        "import json, os, sys, pathlib, psutil\n"
        "p = json.loads(pathlib.Path(sys.argv[2]).read_text())\n"
        "r = pathlib.Path(p['root'])\n"
        "(r / 'actual.claim').open('x').close()\n"
        "(r / 'status.json').write_text(json.dumps({'owner': {'pid': os.getpid(), 'created': psutil.Process().create_time()}, 'status': 'finished-stub'}))\n"
    )
    (old / "controller.claim").touch()
    if started:
        (old / "photo.claim").touch()
    old_owner = {"pid": 99999999, "created": time.time() - 50}
    save(old / "status.json", {"owner": old_owner, "status": "failed-dependency", "completed": {}})
    historical = old / "adopted-status.json"
    save(historical, {"original": "immutable receipt"})
    plan = {
        "root": str(old),
        "work": str(old / "work"),
        controller_field: ref(script),
        "python": sys.executable,
        "inputs": [ref(historical)],
        "frozen_files": {str(script): ref(script)["sha256"]},
        "maximum_wait_seconds": 300,
    }
    wrong_worker = work / "worker.py"
    wrong_worker.write_text(
        "raise AssertionError('Worker entrypoint must not replace controller')\n"
    )
    plan["worker_script"] = ref(wrong_worker)
    plan["frozen_files"][str(wrong_worker)] = ref(wrong_worker)["sha256"]
    save(old / "queue-plan.json", plan)
    new = tmp_path / ".cache/new"
    if started:
        with pytest.raises(AssertionError):
            repair.rebind(old / "queue-plan.json", new, [])
        assert not new.exists()
        return
    binding = ref(old / "status.json")
    result = repair.rebind(old / "queue-plan.json", new, [])
    assert ref(old / "status.json") == binding
    assert (new / "actual.claim").exists()
    assert (new / "work/scripts/stub.py").read_bytes() == script.read_bytes()
    assert (new / "adopted-status.json").read_bytes() == historical.read_bytes()
    derived = json.loads((new / "queue-plan.json").read_text())
    assert 240 < derived["maximum_wait_seconds"] < 250
    assert result["old_owner"] == old_owner and result["new_owner"]["pid"] != old_owner["pid"]


def test_second_rebind_preserves_prior_receipts_helpers_and_absolute_deadline(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(repair, "REPO", tmp_path)
    original = tmp_path / ".cache/original"
    scripts = original / "work/scripts"
    scripts.mkdir(parents=True)
    controller = scripts / "stub.py"
    controller.write_text(
        "import json,os,pathlib,sys,psutil\n"
        "p=json.loads(pathlib.Path(sys.argv[2]).read_text());r=pathlib.Path(p['root'])\n"
        "(r/'controller.claim').open('x').close()\n"
        "(r/'status.json').write_text(json.dumps({'owner':{'pid':os.getpid(),'created':psutil.Process().create_time()},'status':'waiting-fixture','completed':{}}))\n"
    )
    (original / "controller.claim").touch()
    old_owner = {"pid": 99999999, "created": time.time() - 10}
    save(
        original / "status.json", {"owner": old_owner, "status": "failed-fixture", "completed": {}}
    )
    path = original / "plan.json"
    save(
        path,
        {
            "root": str(original),
            "work": str(original / "work"),
            "controller_source": ref(controller),
            "python": sys.executable,
            "inputs": [],
            "frozen_files": {str(controller): ref(controller)["sha256"]},
            "maximum_wait_seconds": 300,
        },
    )
    first = tmp_path / ".cache/first"
    first_result = repair.rebind(path, first, [])
    first_plan = read(first / "plan.json")
    receipt, helper = first / "rebind-declaration-v1.json", first / "rebind-helper.py"
    receipt_bytes, helper_bytes = receipt.read_bytes(), helper.read_bytes()
    until = time.monotonic() + 5
    while repair.live(first_result["new_owner"]):
        assert time.monotonic() < until
        time.sleep(0.01)
    state = read(first / "status.json")
    state["status"] = "failed-fixture"
    save(first / "status.json", state)
    second = tmp_path / ".cache/second"
    repair.rebind(first / "plan.json", second, [], reason="protocol fixture")
    second_plan = read(second / "plan.json")
    guard(first_plan)
    guard(second_plan)
    assert (second / receipt.name).read_bytes() == receipt_bytes
    assert (second / helper.name).read_bytes() == helper_bytes
    assert (second / "rebind-declaration-v2.json").exists()
    assert (second / "rebind-helper-v2.py").exists()
    assert (
        second_plan["absolute_dependency_wait_deadlines"]
        == first_plan["absolute_dependency_wait_deadlines"]
    )
