"""Acceptance and ownership guards for the isolated uniform-profile probe."""

import json

import numpy as np
import pytest
import torch
from probe_uniform_physics_cuda import array_gate, difference, require_idle
from queue_uniform_physics_cuda import resource_ready


@pytest.mark.parametrize(
    "maximum,rms,expected",
    [
        (1.0, 0.25, True),
        (0.0, 0.0, True),
        (1.000000001, 0.25, False),
        (1.0, 0.250000001, False),
        (float("nan"), 0.0, False),
        (0.0, float("nan"), False),
        (float("inf"), 0.0, False),
        (0.0, float("inf"), False),
    ],
)
def test_original_numerical_limits(maximum, rms, expected):
    assert array_gate({"maximum_DN16": maximum, "RMS_DN16": rms}) is expected


def test_difference_keeps_unclipped_negative_values():
    a = torch.tensor([-2.0, 2.0, 0.0], dtype=torch.float32)
    b = a.clone()
    b[0] = torch.nextafter(a[0], torch.tensor(float("-inf")))
    result = difference(a, b)
    delta = (b.numpy().astype(np.float64) - a.numpy().astype(np.float64)) * 65535
    assert not result["bytes_exact"]
    assert result["maximum_DN16"] == np.abs(delta).max()
    assert result["RMS_DN16"] == np.sqrt(np.square(delta).mean())


def test_live_owner_blocks_worker(monkeypatch):
    monkeypatch.setattr("probe_uniform_physics_cuda.dependencies_ready", lambda _plan: False)
    with pytest.raises(RuntimeError, match="owners remain live; no CUDA initialization"):
        require_idle({})


def test_resource_gate_checks_system_disk_separately(monkeypatch):
    observed = []
    monkeypatch.setattr(
        "queue_uniform_physics_cuda.resource_headroom", lambda plan: observed.append(plan) or False
    )
    plan = {
        "root": "/mnt/external/study",
        "root_filesystem_path": "/home/dllu/proj/demosaic",
        "root_reserve_gib": 64,
        "external_reserve_gib": 500,
    }
    assert resource_ready(plan) is False
    assert observed[0]["root"] == "/home/dllu/proj/demosaic"
    assert observed[0]["external_reserve_gib"] == 500
    assert plan["root"] == "/mnt/external/study"


def test_real_dependency_reader_checks_exact_owner_and_plan(tmp_path, monkeypatch):
    from queue_tf32x3_cuda import dependencies_ready, ref

    owner = {"pid": 1234, "created": 55.0}
    frozen = tmp_path / "plan.json"
    frozen.write_text("{}\n")
    status = tmp_path / "status.json"
    state = {"controller": owner, "plan": ref(frozen), "status": "working"}
    status.write_text(json.dumps(state))
    plan = {
        "blocking_owners": [owner],
        "completed_dependencies": [
            {
                "path": str(status),
                "controller": owner,
                "plan": ref(frozen),
                "status": "complete",
            }
        ],
    }
    monkeypatch.setattr("queue_tf32x3_cuda.alive", lambda _owner: True)
    assert dependencies_ready(plan) is False
    state["controller"] = {"pid": owner["pid"], "created": 66.0}
    status.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="identity changed"):
        dependencies_ready(plan)


def test_dead_owner_requires_success_and_dead_child(tmp_path, monkeypatch):
    from queue_tf32x3_cuda import dependencies_ready, ref

    owner = {"pid": 1234, "created": 55.0}
    child = {"pid": 5678, "created": 77.0}
    frozen = tmp_path / "plan.json"
    frozen.write_text("{}\n")
    status = tmp_path / "status.json"
    state = {"controller": owner, "plan": ref(frozen), "status": "working", "child": child}
    plan = {
        "blocking_owners": [owner],
        "completed_dependencies": [
            {
                "path": str(status),
                "controller": owner,
                "plan": ref(frozen),
                "status": "complete",
            }
        ],
    }
    monkeypatch.setattr("queue_tf32x3_cuda.alive", lambda _owner: _owner == child)
    status.write_text(json.dumps(state))
    with pytest.raises(RuntimeError, match="successful terminal"):
        dependencies_ready(plan)
    state["status"] = "complete"
    status.write_text(json.dumps(state))
    with pytest.raises(RuntimeError, match="child remains live"):
        dependencies_ready(plan)
    monkeypatch.setattr("queue_tf32x3_cuda.alive", lambda _owner: False)
    assert dependencies_ready(plan) is True
    frozen.write_text('{"changed": true}\n')
    with pytest.raises(ValueError, match="plan bytes changed"):
        dependencies_ready(plan)


def test_failed_predecessor_refuses_while_other_work_is_live(tmp_path, monkeypatch):
    from queue_tf32x3_cuda import dependencies_ready, ref

    owner = {"pid": 1234, "created": 55.0}
    frozen = tmp_path / "plan.json"
    frozen.write_text("{}\n")
    status = tmp_path / "status.json"
    status.write_text(
        json.dumps(
            {"controller": owner, "plan": ref(frozen), "status": "failed-original-quality-work"}
        )
    )
    plan = {
        "blocking_owners": [owner],
        "completed_dependencies": [
            {
                "path": str(status),
                "controller": owner,
                "plan": ref(frozen),
                "status": "complete",
            }
        ],
    }
    monkeypatch.setattr("queue_tf32x3_cuda.alive", lambda _owner: True)
    with pytest.raises(RuntimeError, match="dependency failed"):
        dependencies_ready(plan)
