import pytest
import yield_training_gpu as coordination

OWNER = {"pid": 10, "created": 20.0}


class Process:
    def __init__(self):
        self.created = 20.0
        self.current_status = "running"
        self.calls = []

    def create_time(self):
        return self.created

    def status(self):
        return self.current_status

    def suspend(self):
        self.calls.append("suspend")
        self.current_status = coordination.psutil.STATUS_STOPPED

    def resume(self):
        self.calls.append("resume")
        self.current_status = "running"


@pytest.fixture
def worker(monkeypatch):
    process = Process()
    monkeypatch.setattr(coordination.psutil, "Process", lambda pid: process)
    return process


def test_same_process_resumes_after_normal_yield(worker):
    with coordination.yielded(OWNER):
        assert worker.status() == coordination.psutil.STATUS_STOPPED
    assert worker.calls == ["suspend", "resume"]


def test_same_process_resumes_when_coordination_fails(worker):
    with pytest.raises(ValueError, match="failed while waiting"), coordination.yielded(OWNER):
        raise ValueError("failed while waiting")
    assert worker.calls == ["suspend", "resume"]


def test_exception_immediately_after_stop_still_resumes(worker, monkeypatch):
    stop = worker.suspend

    def interrupted_stop():
        stop()
        raise ValueError("interrupted immediately after stop")

    monkeypatch.setattr(worker, "suspend", interrupted_stop)
    with pytest.raises(ValueError, match="immediately after stop"), coordination.yielded(OWNER):
        pass
    assert worker.calls == ["suspend", "resume"]


def test_reused_pid_is_never_signaled(worker):
    worker.created += 1
    with pytest.raises(RuntimeError, match="no longer live"), coordination.yielded(OWNER):
        pass
    assert worker.calls == []


def test_preexisting_stop_is_not_taken_over(worker):
    worker.current_status = coordination.psutil.STATUS_STOPPED
    with pytest.raises(RuntimeError, match="already stopped"), coordination.yielded(OWNER):
        pass
    assert worker.calls == []


def test_pid_reused_during_yield_is_not_resumed(worker):
    with coordination.yielded(OWNER):
        worker.created += 1
    assert worker.calls == ["suspend"]


@pytest.mark.parametrize("damage", ["plan", "controller", "child", "arm", "phase"])
def test_changed_training_identity_is_rejected_before_any_signal(damage):
    declaration = {
        "plan": {"path": "plan.json", "sha256": "a"},
        "controller": {"pid": 1, "created": 2},
        "child": OWNER,
        "arm": "V122",
    }
    state = {**declaration, "phase": "train"}
    state[damage] = "different"
    with pytest.raises(ValueError):
        coordination.check_state(state, declaration, child=True)
