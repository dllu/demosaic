"""Prevent overlap with live children, stale terminals or a changed predecessor."""

import json

import pytest
import queue_mature_precision as queue
from train_directional_bank_trial import ref


def fixture(tmp_path):
    owners = [{"pid": i, "created": float(i)} for i in range(1, 7)]
    names = ["training", "training_child", "review", "closure", "reference", "package"]
    mapping = dict(zip(names, owners, strict=True))
    plans = {
        k: {"path": k + ".json", "sha256": k} for k in ["training", "review", "closure", "package"]
    }
    package = tmp_path / "index.json"
    package.write_text(
        json.dumps(
            {
                "native_cells_verified": 125,
                "source_triplets_verified": 81,
                "selected_triplets": [None] * 12,
                "all_boards": [None] * 8,
            }
        )
    )
    statuses = [
        {
            "status": "completed-directional-bank-inference-awaiting-statistical-and-manual-native-closure",
            "completed": [
                "boundary",
                "known",
                "unseen",
                "full427",
                "statistics",
                "sensitivity",
                "gfx",
                "analytic",
                "hue",
                "highlights",
            ],
        },
        {"status": "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review"},
        {
            "status": "prepared-native-report-assets-awaiting-manual-inspection",
            "result": ref(package),
        },
    ]
    for status, role, name in zip(
        statuses,
        ["review", "closure", "package"],
        ["status.json", "closure-status.json", "report-assets-status.json"],
        strict=True,
    ):
        status.update(controller=mapping[role], plan=plans[role])
        (tmp_path / name).write_text(json.dumps(status))
    training = tmp_path / "training.json"
    training.write_text(
        json.dumps(
            {
                "status": "completed-original4000-head-only-awaiting-full-quality-and-native-review",
                "controller": mapping["training"],
                "child": mapping["training_child"],
                "plan": plans["training"],
            }
        )
    )
    return {
        "predecessor_root": str(tmp_path),
        "predecessor_training_status": str(training),
        "blocking_owners": owners,
        "predecessor_owners": mapping,
        "predecessor_plans": plans,
    }


def change(path, **fields):
    value = json.loads(path.read_text())
    value.update(fields)
    path.write_text(json.dumps(value))


def test_terminal_files_cannot_override_a_live_predecessor(tmp_path, monkeypatch):
    plan = fixture(tmp_path)
    monkeypatch.setattr(queue, "alive", lambda owner: owner["pid"] == 1)
    assert queue.predecessor_ready(plan) is False


def test_dynamic_live_child_is_not_lost_when_controllers_exit(tmp_path, monkeypatch):
    plan = fixture(tmp_path)
    change(tmp_path / "status.json", child={"pid": 99, "created": 99.0})
    monkeypatch.setattr(queue, "alive", lambda owner: owner["pid"] == 99)
    assert queue.predecessor_ready(plan) is False


def test_dead_owner_with_incomplete_state_is_not_success(tmp_path, monkeypatch):
    plan = fixture(tmp_path)
    change(tmp_path / "training.json", status="running-source-frozen-head-only-worker")
    monkeypatch.setattr(queue, "alive", lambda _: False)
    with pytest.raises(AssertionError):
        queue.predecessor_ready(plan)


def test_failed_predecessor_is_not_an_indefinite_wait_or_GPU_start(tmp_path, monkeypatch):
    plan = fixture(tmp_path)
    change(tmp_path / "closure-status.json", status="failed-CPU-review")
    monkeypatch.setattr(queue, "alive", lambda _: True)
    with pytest.raises(RuntimeError, match="preceding V92 job failed"):
        queue.predecessor_ready(plan)


@pytest.mark.parametrize(
    "field,value",
    [
        ("controller", {"pid": 99, "created": 99.0}),
        ("plan", {"path": "different.json", "sha256": "different"}),
    ],
)
def test_a_different_owner_or_plan_cannot_satisfy_the_queue(tmp_path, monkeypatch, field, value):
    plan = fixture(tmp_path)
    change(tmp_path / "status.json", **{field: value})
    monkeypatch.setattr(queue, "alive", lambda _: False)
    with pytest.raises(AssertionError):
        queue.predecessor_ready(plan)


def test_all_exact_owners_exited_and_all_stages_complete(tmp_path, monkeypatch):
    plan = fixture(tmp_path)
    monkeypatch.setattr(queue, "alive", lambda _: False)
    assert queue.predecessor_ready(plan) is True
