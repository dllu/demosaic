import importlib.util
import json
from pathlib import Path

import pytest
import torch


def load_script(name):
    path = Path("scripts") / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def worker():
    return load_script("benchmark_ema_updates")


@pytest.fixture(scope="module")
def queue():
    return load_script("queue_ema_measurement")


def scalar(model, ema, decay):
    for name, value in model.restoration_state_dict().items():
        ema[name].lerp_(value, 1 - decay)


def test_grouping_matches_original_names_and_preserves_source_bits_and_strides(worker):
    values = {
        "matrix": torch.arange(12, dtype=torch.float32).reshape(3, 4).T,
        "scalar": torch.tensor(-0.0),
        "weight": torch.arange(108, dtype=torch.float32)
        .reshape(4, 3, 3, 3)
        .to(memory_format=torch.channels_last),
    }
    ema = {name: torch.zeros_like(value) for name, value in reversed(values.items())}
    original, target = worker.state_hash(values), worker.state_hash(ema)
    worker.validate_states(values, ema)
    for decay in (0, 0.2, 0.996005996001, 1):
        result = worker.compare_case(values, ema, decay, scalar)
        assert result["passed"] and all(result["byte_identical_after_each_update"])
        assert result["reference_state_sha256"] == result["grouped_state_sha256"]
    assert worker.state_hash(values) == original and worker.state_hash(ema) == target


@pytest.mark.parametrize("problem", ["empty", "names", "shape", "dtype", "nonfinite"])
def test_invalid_named_state_is_rejected(worker, problem):
    source, ema = {"a": torch.ones(2)}, {"a": torch.zeros(2)}
    if problem == "empty":
        source, ema = {}, {}
    elif problem == "names":
        ema = {"b": torch.zeros(2)}
    elif problem == "shape":
        ema = {"a": torch.zeros(3)}
    elif problem == "dtype":
        ema["a"] = ema["a"].to(torch.float16)
    else:
        source["a"][0] = float("nan")
    with pytest.raises(ValueError):
        worker.validate_states(source, ema)


def test_hash_distinguishes_signed_zero(worker):
    assert worker.state_hash({"a": torch.tensor(0.0)}) != worker.state_hash(
        {"a": torch.tensor(-0.0)}
    )


def test_source_checksum_checked_before_execution(worker, tmp_path):
    path = tmp_path / "train.py"
    path.write_text('raise RuntimeError("must not execute")\n')
    with pytest.raises(ValueError, match="checksum"):
        worker.original_update(path, "0" * 64)


def test_failed_equivalence_never_enters_timing_or_profiling(worker, tmp_path, monkeypatch):
    source = tmp_path / "train.py"
    source.write_text(
        "def update_ema(model, ema, decay):\n"
        "    for name, value in model.restoration_state_dict().items():\n"
        "        ema[name].lerp_(value, 1 - decay)\n"
    )
    checkpoint = tmp_path / "state.pt"
    torch.save(
        {
            "model": {"a": torch.ones(2)},
            "ema": {"a": torch.zeros(2)},
            "config": {"steps": 40000, "ema_decay": 0.996005996001},
            "model_config": {"restoration_backbone": "packed-isotropic", "dino": False},
            "step": 2000,
            "example_draws": 32000,
        },
        checkpoint,
    )
    monkeypatch.setattr(worker.os, "nice", lambda _: None)
    monkeypatch.setattr(worker, "grouped_update", lambda *_: None)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Failed arithmetic must not reach measurement")

    monkeypatch.setattr(worker, "measure", forbidden)
    result = worker.main(
        checkpoint,
        source,
        worker.sha(source),
        tmp_path / "output",
        device="cpu",
        warmup=1,
        samples=2,
    )
    assert result["status"] == "rejected-EMA-state-difference-no-timing-or-adoption"
    assert not result["strict_state_equivalence_passed"] and result["measurements"] is None
    assert not result["CUDA_initialized"]


@pytest.mark.parametrize("status", ["waiting", "running", "failed"])
def test_both_queue_and_worker_reject_unfinished_profile(
    worker, queue, tmp_path, monkeypatch, status
):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"status": status}))
    monkeypatch.setattr(worker, "PROFILE_STATUS", path)
    with pytest.raises(RuntimeError, match="profile must finish"):
        worker.check_gpu_release()
    with pytest.raises(RuntimeError, match="Complete inference profiles"):
        queue.gate({"profile_status": str(path)})


@pytest.mark.parametrize("live_key", ["controller", "child"])
def test_terminal_text_cannot_release_live_profile_owner(
    worker, queue, tmp_path, monkeypatch, live_key
):
    controller, child = worker.PROFILE_OWNER, {"pid": 123, "created": 456}
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps({"status": worker.PROFILE_TERMINAL, "controller": controller, "child": child})
    )
    monkeypatch.setattr(worker, "PROFILE_STATUS", path)
    monkeypatch.setattr(
        worker,
        "owner_alive",
        lambda owner: owner == (controller if live_key == "controller" else child),
    )
    monkeypatch.setattr(
        queue, "alive", lambda owner: owner == (controller if live_key == "controller" else child)
    )
    with pytest.raises(RuntimeError, match="must have exited"):
        worker.check_gpu_release()
    with pytest.raises(AssertionError):
        queue.profile_ready({"profile_status": str(path), "profile_owner": controller})


def test_worker_rejects_different_completed_profile_identity(worker, tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "status": worker.PROFILE_TERMINAL,
                "controller": {"pid": 123, "created": 456},
                "child": {},
            }
        )
    )
    monkeypatch.setattr(worker, "PROFILE_STATUS", path)
    with pytest.raises(RuntimeError, match="exact inference profile"):
        worker.check_gpu_release()


@pytest.fixture
def completed_profile(queue, tmp_path, monkeypatch):
    owner = {"pid": 123, "created": 456}
    plan_path = tmp_path / "profile-plan.json"
    folders, checkpoints, results = [], [], []
    for index in range(2):
        folder = tmp_path / f"output-{index}"
        folder.mkdir()
        checkpoint, trace = tmp_path / f"weights-{index}.pt", folder / "trace.json"
        checkpoint.write_bytes(bytes([index]))
        trace.write_text("{}\n")
        result = {
            "status": "completed-packed-mixed16-bounded-FP32-CUDA-inference-profile",
            "checkpoint": {**queue.ref(checkpoint), "step": 10000},
            "CUDA_initialized": True,
            "genuine_CUDA_trace_events": 1,
            "hooked_unhooked_traced_RGB_bitwise_equal": True,
            "model_and_actual_DINO_state_unchanged": True,
            "CPU_and_CUDA_RNG_unchanged": True,
            "trace": queue.ref(trace),
        }
        report = folder / "result.json"
        report.write_text(json.dumps(result))
        folders.append(str(folder))
        checkpoints.append(str(checkpoint))
        results.append(queue.ref(report))
    plan_path.write_text(json.dumps({"outputs": folders}))
    path = tmp_path / "profile-status.json"
    path.write_text(
        json.dumps(
            {
                "status": queue.TERMINAL,
                "controller": owner,
                "child": owner,
                "plan": queue.ref(plan_path),
                "completed": results,
            }
        )
    )
    monkeypatch.setattr(queue, "alive", lambda _: False)
    return {
        "profile_status": str(path),
        "profile_owner": owner,
        "profile_plan": queue.ref(plan_path),
        "checkpoints": checkpoints,
    }, folders


def test_complete_profile_artifacts_are_required(queue, completed_profile):
    plan, _ = completed_profile
    assert queue.profile_ready(plan)["status"] == queue.TERMINAL


@pytest.mark.parametrize("invalid", ["trace", "checkpoint", "coverage", "device_events"])
def test_completed_profile_with_invalid_evidence_is_rejected(queue, completed_profile, invalid):
    plan, folders = completed_profile
    status = Path(plan["profile_status"])
    if invalid == "trace":
        (Path(folders[0]) / "trace.json").write_text("changed")
    elif invalid == "checkpoint":
        Path(plan["checkpoints"][0]).write_bytes(b"changed")
    elif invalid == "coverage":
        value = queue.read(status)
        value["completed"].pop()
        status.write_text(json.dumps(value))
    else:
        report = Path(folders[0]) / "result.json"
        value = queue.read(report)
        value["genuine_CUDA_trace_events"] = 0
        report.write_text(json.dumps(value))
        value = queue.read(status)
        value["completed"][0] = queue.ref(report)
        status.write_text(json.dumps(value))
    with pytest.raises(AssertionError):
        queue.profile_ready(plan)
