"""Protect exact dependency identities and leave unrelated retained controls untouched."""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rebind_unstarted_quality_queue as repair
from rebind_unstarted_quality_queue import replace_dependencies
from train_directional_bank_trial import ref, save


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
