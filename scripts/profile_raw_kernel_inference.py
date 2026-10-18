"""Attribute unchanged V67 inference costs on four retained GFX RAW contexts.

CUDA events measure inclusive branch intervals; the separate operator trace is
instrumented and is not an end-to-end or full-frame speed benchmark. CPU mode
exists only to verify real-model hooks, inputs and unchanged outputs beforehand.
"""

import argparse
import hashlib
import json
import os
import statistics
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def describe(value):
    if isinstance(value, torch.Tensor):
        return {
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "logical_bytes": value.numel() * value.element_size(),
            "contiguous": value.is_contiguous(),
            "channels_last": value.ndim == 4
            and value.is_contiguous(memory_format=torch.channels_last),
        }
    if isinstance(value, (tuple, list)):
        return [describe(v) for v in value]
    return None


def model_hash(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        # Singleton dimensions can be "contiguous" yet retain a non-unit last
        # stride (notably channels-last 1x1 weights). Byte reinterpretation
        # requires unit stride. Copy the logical values to a canonical vector;
        # this also supports scalars and BF16 without converting their values.
        flat = value.reshape(-1).clone(memory_format=torch.contiguous_format)
        digest.update(flat.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


@contextmanager
def instrument(model, device):
    modules = {
        "DINO-context-inclusive": model.context,
        "DINO-backbone-nested": model.context.backbone,
        "restoration-trunk": model.pretrained_rgb.network,
        "RAW-head-inclusive": model.pretrained_rgb.raw_kernel,
        "RAW-coefficients-nested": model.pretrained_rgb.raw_kernel.coefficients,
    }
    with instrument_modules(modules, device) as records:
        yield records


@contextmanager
def instrument_modules(modules, device):
    """Attach observational hooks; never return replacements or retain tensors."""
    assert modules and all(isinstance(module, torch.nn.Module) for module in modules.values())
    records, stacks, handles = {name: [] for name in modules}, {name: [] for name in modules}, []

    def begin(name):
        def hook(_module, args):
            region = torch.profiler.record_function("demosaic::" + name)
            region.__enter__()
            start = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
            if start is not None:
                start.record()
            stacks[name].append(
                {
                    "start_cpu": time.perf_counter(),
                    "start": start,
                    "region": region,
                    "inputs": describe(args),
                }
            )

        return hook

    def end(name):
        def hook(_module, _args, output):
            entry = stacks[name].pop()
            elapsed = (time.perf_counter() - entry["start_cpu"]) * 1000
            stop = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
            if stop is not None:
                stop.record()
            entry["region"].__exit__(None, None, None)
            records[name].append(
                {
                    "CPU_interval_ms": elapsed,
                    "start": entry["start"],
                    "end": stop,
                    "inputs": entry["inputs"],
                    "output": describe(output),
                }
            )

        return hook

    try:
        for name, module in modules.items():
            handles.append(module.register_forward_pre_hook(begin(name)))
            handles.append(module.register_forward_hook(end(name), always_call=True))
        yield records
    finally:
        for handle in handles:
            handle.remove()
        assert all(not value for value in stacks.values())


def collect(records, cuda):
    result = {}
    for name, entries in records.items():
        assert entries
        result[name] = {
            "calls": len(entries),
            "CPU_interval_ms": [entry["CPU_interval_ms"] for entry in entries],
            "CUDA_interval_ms": [entry["start"].elapsed_time(entry["end"]) for entry in entries]
            if cuda
            else None,
            "inputs": entries[0]["inputs"],
            "output": entries[0]["output"],
        }
    return result


def load_inputs(report, device, batch_size, native_size):
    source = json.loads(report.read_text())
    records = [r for r in source["float_contexts"] if r["role"] == "noisy-packed"]
    assert len(records) == 4 and batch_size in (1, 4) and native_size in (256, 512)
    packed, provenance = [], []
    for record in records[:batch_size]:
        path = report.parent / record["image"]
        assert sha(path) == record["sha256"]
        value = np.load(path, allow_pickle=False)
        assert (
            value.shape == (1, 4, 256, 256)
            and value.dtype == np.float32
            and np.isfinite(value).all()
        )
        packed.append(torch.from_numpy(value[..., : native_size // 2, : native_size // 2].copy()))
        provenance.append(
            {
                **record,
                "path": str(path),
                "profile_context_xywh": [*record["context_xywh"][:2], native_size, native_size],
            }
        )
    raw = torch.cat(packed).to(device)
    if device.type == "cuda":
        raw = raw.contiguous(memory_format=torch.channels_last)
    metadata = next(r["metadata"] for r in source["sources"] if r["role"] == "noisy")
    shot, read = source["conditioning"]["shot"], source["conditioning"]["read"]
    return [
        raw,
        raw.clamp_min(0) * shot + read,
        color_indices(metadata["pattern"], device=device)[None].expand(batch_size, -1),
        torch.tensor(metadata["white_balance"], device=device)[None].expand(batch_size, -1),
        torch.tensor(metadata["camera_to_srgb"], device=device)[None].expand(batch_size, -1, -1),
    ], {
        "report": str(report),
        "report_sha256": sha(report),
        "cases": provenance,
        "conditioning": source["conditioning"],
        "metadata": metadata,
    }


@torch.inference_mode()
def main(
    checkpoint,
    gfx_report,
    output,
    device="cuda",
    batch_size=4,
    native_size=512,
    warmup=3,
    samples=5,
):
    os.nice(5)
    torch.set_num_threads(2)
    device = torch.device(device)
    if device.type == "cpu":
        assert not torch.cuda.is_initialized() and batch_size == 1 and native_size == 256
    else:
        assert batch_size == 4 and native_size == 512
    assert warmup >= 1 and samples >= 2
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    batch, provenance = load_inputs(gfx_report, device, batch_size, native_size)
    model, state = load_checkpoint(checkpoint, device)
    assert state["loaded_sha256"] == sha(checkpoint)
    assert model.config.raw_kernel_reconstruction and model.config.raw_kernel_phase_conditioning
    model.eval()
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
    model.set_noise(provenance["conditioning"]["shot"], provenance["conditioning"]["read"])
    step, digest = state["step"], state["loaded_sha256"]
    del state
    before = model_hash(model)
    rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone() if device.type == "cuda" else None

    def synchronize():
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    def forward():
        with amp_context(device, dtype="float16" if device.type == "cuda" else "float32"):
            return model(*batch)

    for _ in range(warmup):
        reference = forward()
    synchronize()
    assert (
        reference.shape == (batch_size, 3, native_size, native_size)
        and reference.dtype == torch.float32
    )
    assert torch.isfinite(reference).all()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    unhooked_ms = []
    for _ in range(samples):
        started = time.perf_counter()
        actual = forward()
        synchronize()
        unhooked_ms.append((time.perf_counter() - started) * 1000)
        assert torch.equal(actual, reference)
    with instrument(model, device) as records:
        for _ in range(samples):
            actual = forward()
            synchronize()
            assert torch.equal(actual, reference)
    branches = collect(records, device.type == "cuda")
    assert all(row["calls"] == samples for row in branches.values())
    activities = [torch.profiler.ProfilerActivity.CPU]
    if device.type == "cuda":
        activities.append(torch.profiler.ProfilerActivity.CUDA)
    with (
        torch.profiler.profile(
            activities=activities, record_shapes=False, with_stack=False, profile_memory=True
        ) as profile,
        instrument(model, device) as trace_records,
    ):
        actual = forward()
        synchronize()
    assert torch.equal(actual, reference)
    trace_branches = collect(trace_records, device.type == "cuda")
    keys = profile.key_averages()
    operators = [
        {
            "name": row.key,
            "calls": row.count,
            "self_CPU_us": row.self_cpu_time_total,
            "inclusive_CPU_us": row.cpu_time_total,
            "self_device_us": row.self_device_time_total,
            "inclusive_device_us": row.device_time_total,
            "self_CPU_memory_bytes": row.self_cpu_memory_usage,
            "self_device_memory_bytes": row.self_device_memory_usage,
        }
        for row in keys
    ]
    assert {"demosaic::" + name for name in branches} <= {row["name"] for row in operators}
    cuda_events = sum(
        str(event.device_type) == "DeviceType.CUDA" and event.time_range.elapsed_us() > 0
        for event in profile.events()
    )
    if device.type == "cuda":
        assert cuda_events > 0, "No genuine CUDA events; profiler fallback is not GPU evidence"
    trace = output / "operator-trace.json"
    profile.export_chrome_trace(str(trace))
    assert model_hash(model) == before
    assert torch.equal(torch.get_rng_state(), rng)
    if cuda_rng is not None:
        assert torch.equal(torch.cuda.get_rng_state(), cuda_rng)
    assert sha(checkpoint) == digest
    np.save(output / "unchanged-reference-f32.npy", reference.cpu().numpy(), allow_pickle=False)
    archive = output / "source"
    archive.mkdir()
    sources = {str(path): sha(path) for path in Path("src/demosaic").glob("*.py")}
    for path in [Path(__file__), *map(Path, sources)]:
        (archive / path.name).write_bytes(path.read_bytes())
    result = {
        "status": "completed-real-V67-CPU-profiler-preflight-no-GPU-timing"
        if device.type == "cpu"
        else "completed-real-V67-bounded-CUDA-inference-profile",
        "checkpoint": {"path": str(checkpoint), "sha256": digest, "step": step},
        "inputs": provenance,
        "device": str(device),
        "torch": str(torch.__version__),
        "hardware": torch.cuda.get_device_name(device)
        if device.type == "cuda"
        else "CPU engineering preflight",
        "batch_size": batch_size,
        "native_size": native_size,
        "warmup": warmup,
        "samples": samples,
        "unhooked_forward_synchronized_ms": unhooked_ms,
        "unhooked_median_ms": statistics.median(unhooked_ms),
        "inclusive_branches": branches,
        "instrumented_trace_branches": trace_branches,
        "operator_statistics": sorted(
            operators,
            key=lambda row: row["self_device_us"] if device.type == "cuda" else row["self_CPU_us"],
            reverse=True,
        ),
        "genuine_CUDA_trace_events": cuda_events,
        "trace": {"path": str(trace), "sha256": sha(trace)},
        "all_hooked_unhooked_profiled_outputs_bitwise_reference": True,
        "model_and_actual_DINO_state_hash_before_after": before,
        "model_and_actual_DINO_state_unchanged": True,
        "CPU_and_CUDA_RNG_unchanged": True,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": torch.cuda.is_initialized(),
        "peak_CUDA_allocation_GB": torch.cuda.max_memory_allocated(device) / 1e9
        if device.type == "cuda"
        else None,
        "scope": "Unchanged checkpoint and fixed input batch; no optimization, compile, weight/precision/tile change, quality score or promotion. Branch intervals are inclusive and nested; never sum parent and child times. Profiler statistics/trace are instrumented, separate from synchronized unhooked forward samples. Excludes RAW decoding, input transfer, output transfer, tiling/blending and encoding; not a100MP speed result or throughput sweep. Shared-machine measurements do not establish idle hardware performance. CPU mode verifies hooks and identity only, never GPU bottlenecks.",
        "API_sources": [
            "https://docs.pytorch.org/docs/2.14/profiler.html",
            "https://docs.pytorch.org/docs/2.14/generated/torch.cuda.Event.html",
        ],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"result": str(output / "result.json"), "status": result["status"], "step": step}
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gfx-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    for name, default in [("batch-size", 4), ("native-size", 512), ("warmup", 3), ("samples", 5)]:
        parser.add_argument("--" + name, type=int, default=default)
    main(**vars(parser.parse_args()))
