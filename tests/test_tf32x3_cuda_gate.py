import importlib.util
import json
import os
import sys
from pathlib import Path

import psutil
import pytest
import torch

scripts = Path(__file__).parents[1] / "scripts"
original = list(sys.path)
try:
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("tf32x3_cuda_probe", scripts / "probe_tf32x3_cuda.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
finally:
    sys.path[:] = original


def test_current_exact_owner_prevents_any_future_state_reads_or_cuda():
    plan = {"blocking_owners": [{"pid": os.getpid(), "created": psutil.Process().create_time()}],
            "completed_dependencies": [{"path": "/does-not-exist"}]}
    with pytest.raises(RuntimeError, match="owners are live"):
        probe.require_idle(plan)
    assert not torch.cuda.is_initialized()


@pytest.fixture
def completed(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "alive", lambda owner: owner.get("live", False))
    source = tmp_path / "bound-plan.json"
    source.write_text('{}\n')
    owner = {"pid": 123, "created": 456.0}
    status = tmp_path / "status.json"
    payload = {"status": "completed-fixed-review", "controller": owner, "plan": probe.ref(source)}
    status.write_text(json.dumps(payload))
    dependency = {"path": str(status), "status": payload["status"], "controller": owner, "plan": probe.ref(source)}
    return {"blocking_owners": [], "completed_dependencies": [dependency]}, status, payload, source


def test_exact_successful_closed_dependency_is_accepted_without_cuda(completed):
    plan, _, _, _ = completed
    probe.require_idle(plan)
    assert not torch.cuda.is_initialized()


@pytest.mark.parametrize("change", ["status", "owner", "plan", "live_child"])
def test_failed_changed_or_unfinished_dependencies_are_rejected(completed, change):
    plan, path, status, source = completed
    if change == "status":
        status["status"] = "failed-previous-work"
    elif change == "owner":
        status["controller"] = {"pid": 124, "created": 456.0}
    elif change == "plan":
        source.write_text('{"changed":true}\n')
    else:
        status["child"] = {"live": True}
    path.write_text(json.dumps(status))
    with pytest.raises(RuntimeError):
        probe.require_idle(plan)
    assert not torch.cuda.is_initialized()


def test_hidden_wrapper_restores_after_operator_failure_without_modifying_weights(monkeypatch):
    network = torch.nn.Sequential(torch.nn.Conv2d(2, 2, 3, padding=1, bias=False)).eval()
    before = {k: v.clone() for k, v in network.state_dict().items()}

    def fail(*args, **kwargs):
        raise RuntimeError("sentinel operator failure")

    monkeypatch.setattr(probe, "convolution", fail)
    with torch.inference_mode():
        with pytest.raises(RuntimeError, match="sentinel"), probe.accelerated_hidden(network):
            network(torch.ones(1, 2, 3, 3))
        assert 'forward' not in network[0].__dict__
    assert all(torch.equal(v, before[k]) for k, v in network.state_dict().items())


def test_reference_board_failure_also_prevents_gpu_launch(completed, tmp_path):
    plan, _, _, _ = completed
    path = tmp_path / 'reference-result.json'
    path.write_text(json.dumps({'status': 'failed-reference-preparation'}))
    plan['required_completed_receipts'] = [{'path': str(path), 'status': 'prepared-references'}]
    with pytest.raises(RuntimeError, match='retained-reference'):
        probe.require_idle(plan)
    assert not torch.cuda.is_initialized()
