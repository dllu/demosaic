"""Check exact EMA arithmetic before measuring isolated update latency."""

import argparse
import ast
import hashlib
import json
import os
import random
import statistics
import time
from pathlib import Path

import psutil
import torch

from demosaic.safety import writable_path

SCHEDULE_POSITIONS = (1, 12, 13, 2000, 2001, 8000, 10000, 40000)
PROFILE_STATUS = Path("/mnt/external/demosaic/runs/mixed16-packed-profile-after-quarter-v1.json")
PROFILE_OWNER = {"pid": 2714232, "created": 1792306477.92}
PROFILE_TERMINAL = "completed-bounded-mixed16-quarter-FP32-CUDA-profiles-awaiting-trace-analysis"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def state_hash(values):
    digest = hashlib.sha256()
    for name, value in values.items():
        digest.update(name.encode() + b"\0")
        digest.update(
            value.detach().contiguous().cpu().reshape(-1).view(torch.uint8).numpy().tobytes()
        )
    return digest.hexdigest()


def validate_states(values, ema):
    if not values or set(values) != set(ema):
        raise ValueError("EMA and model must contain the same nonempty named state")
    devices = {value.device for value in values.values()}
    if len(devices) != 1:
        raise ValueError("This measurement requires one device")
    for name, value in values.items():
        target = ema[name]
        if value.dtype != torch.float32 or target.dtype != torch.float32:
            raise ValueError("This measurement supports FP32 state only")
        if value.shape != target.shape or value.device != target.device:
            raise ValueError("Named EMA shapes and devices must match")
        if not torch.isfinite(value).all() or not torch.isfinite(target).all():
            raise ValueError("EMA measurement requires finite state")


def original_update(path, expected_sha256):
    if sha(path) != expected_sha256:
        raise ValueError("Frozen training source checksum differs")
    tree = ast.parse(Path(path).read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "update_ema"]
    if len(functions) != 1:
        raise ValueError("Expected exactly one original EMA function")
    namespace = {"torch": torch}
    exec(  # noqa: S102 -- Execute only the caller's hash-checked own training function.
        compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace
    )
    return namespace["update_ema"]


class StateOnly:
    def __init__(self, values):
        self.values = values

    def restoration_state_dict(self):
        return self.values


@torch.no_grad()
def grouped_update(values, ema, decay):
    torch._foreach_lerp_([ema[name] for name in values], list(values.values()), 1 - decay)


def clone_state(values):
    return {name: value.clone() for name, value in values.items()}


def owner_alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def check_gpu_release():
    status = json.loads(PROFILE_STATUS.read_text())
    if status["status"] != PROFILE_TERMINAL:
        raise RuntimeError("The existing inference profile must finish before CUDA EMA work")
    if status["controller"] != PROFILE_OWNER or any(
        owner_alive(status[k]) for k in ("controller", "child")
    ):
        raise RuntimeError("The exact inference profile owner and child must have exited")
    return {"path": str(PROFILE_STATUS), "sha256": sha(PROFILE_STATUS)}


def compare_case(values, initial, decay, scalar, *, updates=5):
    reference, candidate = clone_state(initial), clone_state(initial)
    model = StateOnly(values)
    matches = []
    for _ in range(updates):
        scalar(model, reference, decay)
        grouped_update(values, candidate, decay)
        matches.append(state_hash(reference) == state_hash(candidate))
    strides = all(reference[n].stride() == candidate[n].stride() for n in values)
    return {
        "decay": decay,
        "byte_identical_after_each_update": matches,
        "identical_strides": strides,
        "reference_state_sha256": state_hash(reference),
        "grouped_state_sha256": state_hash(candidate),
        "passed": all(matches) and strides,
    }


def measure(values, initial, scalar, decay, output, device, warmup, samples):
    model = StateOnly(values)
    states = {method: clone_state(initial) for method in ("scalar", "grouped")}

    def sync():
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    def update(method):
        if method == "scalar":
            scalar(model, states[method], decay)
        else:
            grouped_update(values, states[method], decay)

    for _ in range(warmup):
        for method in states:
            update(method)
    sync()
    order = list(states) * samples
    random.Random(42).shuffle(order)
    timings = {method: [] for method in states}
    for method in order:
        sync()
        start_event = end_event = None
        if device.type == "cuda":
            start_event = torch.cuda.Event(enable_timing=True)
            end_event = torch.cuda.Event(enable_timing=True)
            start_event.record()
        started = time.perf_counter()
        update(method)
        if end_event is not None:
            end_event.record()
        sync()
        elapsed = (time.perf_counter() - started) * 1000
        event_ms = start_event.elapsed_time(end_event) if start_event is not None else None
        assert elapsed > 0 and (event_ms is None or event_ms > 0)
        timings[method].append({"synchronized_wall_ms": elapsed, "CUDA_event_ms": event_ms})
    assert state_hash(states["scalar"]) == state_hash(states["grouped"])
    profiles = {}
    activities = [torch.profiler.ProfilerActivity.CPU]
    if device.type == "cuda":
        activities.append(torch.profiler.ProfilerActivity.CUDA)
    for method in states:
        with (
            torch.profiler.profile(activities=activities) as profile,
            torch.profiler.record_function(f"demosaic::EMA-{method}"),
        ):
            update(method)
            sync()
        cuda_events = sum(
            str(event.device_type) == "DeviceType.CUDA" and event.time_range.elapsed_us() > 0
            for event in profile.events()
        )
        assert device.type != "cuda" or cuda_events > 0
        trace = output / f"EMA-{method}-trace.json"
        profile.export_chrome_trace(str(trace))
        profiles[method] = {
            "trace": {"path": str(trace), "sha256": sha(trace)},
            "genuine_CUDA_trace_events": cuda_events,
            "operator_calls": {event.key: event.count for event in profile.key_averages()},
        }
    assert state_hash(states["scalar"]) == state_hash(states["grouped"])
    return {
        "warmup": warmup,
        "samples_per_method": samples,
        "balanced_shuffled_order": order,
        "samples": timings,
        "synchronized_wall_median_ms": {
            method: statistics.median(row["synchronized_wall_ms"] for row in rows)
            for method, rows in timings.items()
        },
        "profiles": profiles,
        "post_timing_and_trace_states_byte_identical": True,
    }


def main(
    checkpoint,
    train_source,
    train_sha256,
    output,
    device="cuda",
    warmup=3,
    samples=10,
    expected_torch=None,
):
    os.nice(10)
    torch.set_num_threads(2)
    if expected_torch is not None and str(torch.__version__) != expected_torch:
        raise ValueError("Torch version differs from CPU preflight")
    if warmup < 1 or samples < 2:
        raise ValueError("Use at least one warmup and two samples")
    device = torch.device(device)
    if device.type not in ("cpu", "cuda"):
        raise ValueError("Use CPU or CUDA")
    release = check_gpu_release() if device.type == "cuda" else None
    source_digest = sha(__file__)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    checkpoint_digest = sha(checkpoint)
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    assert (
        state["config"]["steps"] == 40000
        and state["model_config"]["restoration_backbone"] == "packed-isotropic"
    )
    if device.type == "cuda":
        assert state["step"] == 10000 and state["example_draws"] == 160000
    scalar = original_update(train_source, train_sha256)
    identity = {
        "path": str(checkpoint.resolve()),
        "sha256": checkpoint_digest,
        "step": state["step"],
        "example_draws": state["example_draws"],
        "DINO": state["model_config"]["dino"],
    }
    values = {name: value.to(device) for name, value in state["model"].items()}
    initial = {name: value.to(device) for name, value in state["ema"].items()}
    validate_states(values, initial)
    source_hash, initial_hash = state_hash(values), state_hash(initial)
    cpu_rng, python_rng = torch.get_rng_state(), random.getstate()
    cuda_rng = torch.cuda.get_rng_state(device) if device.type == "cuda" else None
    cases = []
    for position in SCHEDULE_POSITIONS:
        decay = min(state["config"]["ema_decay"], (position + 1) / (position + 10))
        cases.append(
            {"decay_schedule_step": position, **compare_case(values, initial, decay, scalar)}
        )
    passed = all(case["passed"] for case in cases)
    measurements = (
        measure(
            values, initial, scalar, state["config"]["ema_decay"], output, device, warmup, samples
        )
        if passed
        else None
    )
    assert state_hash(values) == source_hash and state_hash(initial) == initial_hash
    assert torch.equal(torch.get_rng_state(), cpu_rng) and random.getstate() == python_rng
    if cuda_rng is not None:
        assert torch.equal(torch.cuda.get_rng_state(device), cuda_rng)
    assert torch.cuda.is_initialized() is (device.type == "cuda")
    assert sha(checkpoint) == checkpoint_digest and sha(train_source) == train_sha256
    assert sha(__file__) == source_digest
    if release is not None:
        assert sha(release["path"]) == release["sha256"]
    archive = output / "source"
    archive.mkdir()
    for path in (Path(__file__), train_source):
        (archive / path.name).write_bytes(path.read_bytes())
    result = {
        "status": (
            "completed-EMA-CPU-instrumentation-preflight-no-GPU-timing"
            if device.type == "cpu"
            else "completed-EMA-CUDA-state-and-latency-measurement"
        )
        if passed
        else "rejected-EMA-state-difference-no-timing-or-adoption",
        "checkpoint": identity,
        "source": {"path": str(Path(__file__)), "sha256": sha(__file__)},
        "frozen_train": {"path": str(train_source), "sha256": train_sha256},
        "torch": str(torch.__version__),
        "device": str(device),
        "state_tensors": len(values),
        "strict_state_equivalence_passed": passed,
        "cases": cases,
        "measurements": measurements,
        "source_and_initial_EMA_values_unchanged": True,
        "CPU_Python_CUDA_RNG_unchanged": True,
        "checkpoint_bytes_unchanged": True,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "previous_profile_release": release,
        "scope": "Isolated EMA updates on cloned actual FP32 checkpoint state. Eight original "
        "schedule positions/five updates each; strict byte equality before any timings. "
        "Model values stay fixed. Timings exclude source loading and state transfer; "
        "not whole-step training, I/O, network inference or 100MP timing. CPU mode "
        "checks wiring only. No optimizer update, learned weights, production change "
        "or automatic adoption. Shared-machine observations are not an idle hardware optimum.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "result": str(output / "result.json")}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("checkpoint", "train-source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--train-sha256", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--expected-torch")
    main(**vars(parser.parse_args()))
