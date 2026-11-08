"""No CUDA import;exercise active owners,incomplete receipts and observation errors."""

import json

import psutil
import pytest
from phase_admission_protocol import dependency_readiness, owner_live


def write(path, value):
    path.write_text(json.dumps(value))


def completed(root):
    for i, (phase, result) in enumerate(
        [
            ("train", "train-result-v1.json"),
            ("review", "scores-v1.json"),
            ("completion-watch", "completion-watch-result-v1.json"),
        ]
    ):
        owner = {"pid": 10 + i, "created": 100 + i}
        write(root / f"{phase}-launch-v1.json", {"owner": owner})
        write(root / result, {"status": "completed-test", "owner": owner})
    write(
        root / "completion-watch-status-v1.json",
        {"status": "ready-for-actual-native-viewing", "owner": {"pid": 12, "created": 102}},
    )
    for name in [
        "training-audit-v1.json",
        "quality-audit-v1.json",
        "offset-audit-v1.json",
        "paired-comparisons-v1.json",
        "figures-v1.json",
    ]:
        write(root / name, {"status": "pass-test"})


def test_only_full_completed_pipeline_is_ready(tmp_path):
    completed(tmp_path)
    result = dependency_readiness(tmp_path, is_live=lambda _: False)
    assert result["ready"] and len(result["bindings"]) == 12
    assert len(result["owners"]) == 3


def test_actual_offset_writer_status_without_hyphen_is_completed(tmp_path):
    completed(tmp_path)
    write(
        tmp_path / "offset-audit-v1.json",
        {
            "status": "pass30-offset-arrays-six-primary-EMA-quality-bindings-and-independent-position-reduction"
        },
    )
    assert dependency_readiness(tmp_path, is_live=lambda _: False)["ready"]


@pytest.mark.parametrize("pid", [10, 11, 12])
def test_completed_record_cannot_override_live_owner(tmp_path, pid):
    completed(tmp_path)
    result = dependency_readiness(tmp_path, is_live=lambda o: o["pid"] == pid)
    assert not result["ready"] and result["owner"]["pid"] == pid


def test_missing_owner_without_complete_result_is_not_success(tmp_path):
    completed(tmp_path)
    (tmp_path / "scores-v1.json").unlink()
    result = dependency_readiness(tmp_path, is_live=lambda _: False)
    assert not result["ready"] and result["reason"] == "waiting-for-review-completed-result"


def test_missing_launch_is_not_success(tmp_path):
    assert not dependency_readiness(tmp_path, is_live=lambda _: False)["ready"]


@pytest.mark.parametrize(
    "damage", ["wrong-owner", "failed-result", "incomplete-render", "watch-status", "failure-file"]
)
def test_bad_dependency_evidence_rejects(tmp_path, damage):
    completed(tmp_path)
    if damage == "wrong-owner":
        write(
            tmp_path / "scores-v1.json",
            {"status": "completed-test", "owner": {"pid": 11, "created": 999}},
        )
    elif damage == "failed-result":
        write(
            tmp_path / "scores-v1.json", {"status": "failed", "owner": {"pid": 11, "created": 101}}
        )
    elif damage == "incomplete-render":
        write(tmp_path / "figures-v1.json", {"status": "running"})
    elif damage == "watch-status":
        write(
            tmp_path / "completion-watch-status-v1.json",
            {"status": "running-native-render", "owner": {"pid": 12, "created": 102}},
        )
    else:
        write(tmp_path / "train-failure-v1.json", {"error": "test"})
    with pytest.raises(RuntimeError):
        dependency_readiness(tmp_path, is_live=lambda _: False)


def test_transient_observation_is_not_completion(tmp_path):
    completed(tmp_path)

    def denied(_):
        raise psutil.AccessDenied(10)

    with pytest.raises(psutil.AccessDenied):
        dependency_readiness(tmp_path, is_live=denied)


@pytest.mark.parametrize("kind", ["live", "reused", "missing", "zombie", "denied"])
def test_owner_identity_and_errors(monkeypatch, kind):
    class Process:
        def __init__(self, _):
            if kind == "missing":
                raise psutil.NoSuchProcess(10)
            if kind == "denied":
                raise psutil.AccessDenied(10)

        def create_time(self):
            return 101 if kind == "reused" else 100

        def status(self):
            return psutil.STATUS_ZOMBIE if kind == "zombie" else psutil.STATUS_RUNNING

    monkeypatch.setattr(psutil, "Process", Process)
    if kind == "denied":
        with pytest.raises(psutil.AccessDenied):
            owner_live({"pid": 10, "created": 100})
    else:
        assert owner_live({"pid": 10, "created": 100}) == (kind == "live")
