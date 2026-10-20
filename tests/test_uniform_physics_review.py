"""Unclipped arithmetic and exact completed-owner checks for saved-array review."""

import math

import numpy as np
import pytest
from audit_uniform_physics_arrays import check_pairs, check_timings, completed
from train_directional_bank_trial import ref, save


def fixture_case(tmp_path):
    checkpoint, observation = tmp_path / "weights", tmp_path / "input"
    checkpoint.write_bytes(b"unit fixture; not a trained checkpoint")
    observation.write_bytes(b"unit fixture; no inference")
    a = np.full((1, 3, 256, 256), -2.0, dtype=np.float32)
    b = a.copy()
    b[0, 0, 0, 0] = np.nextafter(np.float32(-2.0), np.float32(-np.inf))
    maximum = float(abs(float(b[0, 0, 0, 0]) + 2.0)) * 65535
    path = tmp_path / "arrays.npz"
    np.savez(path, original=a, candidate=b)
    return {
        "model": "unit",
        "checkpoint": ref(checkpoint),
        "fixture": {"label": "photo0-native256", "observation": ref(observation)},
        "arrays": ref(path),
        "difference": {
            "maximum_DN16": maximum,
            "RMS_DN16": maximum / math.sqrt(a.size),
            "bytes_exact": False,
            "values": a.size,
        },
    }


def test_saved_arrays_retain_negative_unclipped_values(tmp_path):
    case = fixture_case(tmp_path)
    result = check_pairs([case])[0]
    assert result["maximum_DN16"] == 2**-22 * 65535
    assert result["passes_original_limits"] is True
    assert result["bytes_exact"] is False and result["values"] == 196608


def test_changed_recorded_error_is_detected(tmp_path):
    case = fixture_case(tmp_path)
    case["difference"]["maximum_DN16"] = 0.0
    with pytest.raises(AssertionError):
        check_pairs([case])


def test_duplicate_saved_pairs_are_rejected(tmp_path):
    case = fixture_case(tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        check_pairs([case, case])


@pytest.mark.parametrize("shape,value", [((1, 3, 64, 80), 0.0), ((1, 3, 256, 256), np.nan)])
def test_small_CPU_or_nonfinite_arrays_cannot_pass_full_GPU_review(tmp_path, shape, value):
    case = fixture_case(tmp_path)
    path = tmp_path / "invalid.npz"
    a = np.full(shape, value, dtype=np.float32)
    np.savez(path, original=a, candidate=a)
    case["arrays"] = ref(path)
    with pytest.raises(AssertionError):
        check_pairs([case])


def test_no_speed_summary_from_wrong_order_or_nonpositive_time():
    flags = [False, True, True, False, True, False, False, True]
    item = {
        "model": "unit",
        "samples": [{"candidate": flag, "seconds": 1.0} for flag in flags],
        "median_seconds": {"original": 1.0, "candidate": 1.0},
    }
    assert check_timings([item], ["unit"])[0]["candidate_over_original_median"] == 1.0
    item["samples"][0]["seconds"] = 0.0
    with pytest.raises(AssertionError):
        check_timings([item], ["unit"])
    item["samples"][0] = {"candidate": True, "seconds": 1.0}
    with pytest.raises(AssertionError):
        check_timings([item], ["unit"])


@pytest.mark.parametrize(
    "live,changed,expected",
    [
        (True, False, "owners remain live"),
        (False, True, "plan changed"),
        (False, False, "no completed/rejected CUDA terminal"),
    ],
)
def test_exact_owner_and_terminal_are_required(tmp_path, monkeypatch, live, changed, expected):
    root = tmp_path
    plan_path = root / "controller-plan.json"
    save(plan_path, {"root": str(root)})
    plan = ref(plan_path)
    owner = {"pid": 123, "created": 1.0}
    save(root / "queue-launch.json", {"plan": plan, "owner": owner})
    save(root / "verified-queue.json", {"controller_plan": plan, "controller_owner": owner})
    save(
        root / "status.json",
        {
            "plan": plan,
            "controller": {"pid": 123, "created": 2.0} if changed else owner,
            "status": "still-waiting",
        },
    )
    monkeypatch.setattr("audit_uniform_physics_arrays.guard", lambda _plan: {"blocking_owners": []})
    monkeypatch.setattr("audit_uniform_physics_arrays.alive", lambda _owner: live)
    with pytest.raises((ValueError, RuntimeError), match=expected):
        completed(plan_path)


@pytest.mark.parametrize(
    "terminal",
    [
        "completed-uniform-physics-CUDA-array-gates-and-resident-timing-awaiting-review",
        "rejected-uniform-physics-CUDA-array-gate-no-timing-or-integration",
    ],
)
def test_watcher_waits_for_both_exact_controller_and_child(tmp_path, monkeypatch, terminal):
    from watch_uniform_physics_review import ready

    path = tmp_path / "controller-plan.json"
    save(path, {})
    owner, child = {"pid": 123, "created": 1.0}, {"pid": 234, "created": 2.0}
    status = tmp_path / "status.json"
    state = {"controller": owner, "plan": ref(path), "status": terminal, "child": child}
    save(status, state)
    plan = {"GPU_status": str(status), "GPU_owner": owner, "GPU_controller_plan": ref(path)}
    monkeypatch.setattr("watch_uniform_physics_review.alive", lambda o: o == owner)
    assert ready(plan) is False
    monkeypatch.setattr("watch_uniform_physics_review.alive", lambda o: o == child)
    with pytest.raises(RuntimeError, match="worker remains live"):
        ready(plan)
    monkeypatch.setattr("watch_uniform_physics_review.alive", lambda _o: False)
    assert ready(plan) is True
    state["controller"] = dict(owner, created=9.0)
    save(status, state)
    with pytest.raises(ValueError, match="identity/plan changed"):
        ready(plan)


def test_watcher_refuses_failed_or_incomplete_gpu_terminal(tmp_path, monkeypatch):
    from watch_uniform_physics_review import ready

    path = tmp_path / "controller-plan.json"
    save(path, {})
    owner = {"pid": 123, "created": 1.0}
    status = tmp_path / "status.json"
    plan = {"GPU_status": str(status), "GPU_owner": owner, "GPU_controller_plan": ref(path)}
    monkeypatch.setattr("watch_uniform_physics_review.alive", lambda _o: False)
    for terminal, message in [
        ("failed-probe", "dependency failed"),
        ("waiting", "without a completed/rejected terminal"),
    ]:
        save(status, {"controller": owner, "plan": ref(path), "status": terminal})
        with pytest.raises(RuntimeError, match=message):
            ready(plan)
