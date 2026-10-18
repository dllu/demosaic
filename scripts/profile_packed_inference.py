"""Measure unchanged packed-RAW branch costs; CPU mode checks instrumentation only."""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import numpy as np
import torch
from profile_raw_kernel_inference import collect, instrument_modules, model_hash, sha

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def modules_for(model):
    core = model.packed_isotropic
    modules = {
        "RAW-core-inclusive": core,
        "RAW-local-stem-nested": core.local_stem,
        "RAW-quarter-stem-nested": core.stem,
        "RAW-local-blocks-nested": core.local_blocks,
        **{f"RAW-group{i}-nested": group for i, group in enumerate(core.groups)},
        "RAW-upsample-nested": core.up,
        "RAW-decoder-nested": core.decoder,
        "RAW-head-nested": core.head,
    }
    if model.context is not None:
        modules.update(
            {"DINO-context-nested": model.context, "DINO-backbone-nested": model.context.backbone}
        )
    return modules


def load_inputs(manifest, device, batch_size, native_size):
    fixture = json.loads(manifest.read_text())
    observation = fixture["serving_probes"][0]["observation"]
    path = Path(observation["path"])
    assert sha(path) == observation["sha256"]
    with np.load(path, allow_pickle=False) as arrays:
        values = {
            k: torch.from_numpy(arrays[k][:batch_size].copy())
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
    assert values["packed"].shape == values["variance"].shape == (batch_size, 4, 256, 256)
    assert batch_size in (1, 4) and native_size in (256, 512)
    for key in ["packed", "variance"]:
        values[key] = values[key][..., : native_size // 2, : native_size // 2].contiguous()
    for key, value in values.items():
        assert torch.isfinite(value).all()
        values[key] = value.to(device)
        if device.type == "cuda" and value.ndim == 4:
            values[key] = values[key].contiguous(memory_format=torch.channels_last)
    return list(values.values()), {
        "manifest": {"path": str(manifest), "sha256": sha(manifest)},
        "observation": observation,
        "conditioning": fixture["conditioning"],
        "regions": fixture["gfx_regions"][:batch_size],
        "native_size": native_size,
        "CPU_subregion": "Top-left native256 of first fixed512 GFX context; engineering input, not the report ROI"
        if native_size == 256
        else None,
    }


@torch.inference_mode()
def main(checkpoint, inputs, output, device="cuda", warmup=3, samples=5):
    os.nice(10)
    torch.set_num_threads(2)
    device = torch.device(device)
    assert warmup >= 1 and samples >= 2
    if device.type == "cpu":
        assert not torch.cuda.is_initialized()
    batch_size, native_size = (1, 256) if device.type == "cpu" else (4, 512)
    source_files = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    helpers = {
        str(p): sha(p)
        for p in [Path(__file__), Path(__file__).with_name("profile_raw_kernel_inference.py")]
    }
    assert source_files, "Run from the frozen or repository package working directory"
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    batch, provenance = load_inputs(inputs, device, batch_size, native_size)
    model, state = load_checkpoint(checkpoint, device)
    assert model.config.restoration_backbone == "packed-isotropic"
    assert model.config.isotropic_raw_gain == 32 and model.config.isotropic_residual_scale == 1 / 32
    identity = {
        "path": str(checkpoint.resolve()),
        "sha256": state["loaded_sha256"],
        "step": state["step"],
        "model_config": model.config.to_dict(),
        "weights": "EMA",
    }
    del state
    model.eval()
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
    model.set_noise(provenance["conditioning"]["shot"], provenance["conditioning"]["read"])
    before = model_hash(model)
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone() if device.type == "cuda" else None

    def sync():
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    def forward():
        with amp_context(device, dtype="float32"):
            return model(*batch)

    for _ in range(warmup):
        reference = forward()
    sync()
    assert reference.shape == (batch_size, 3, native_size, native_size)
    assert reference.dtype == torch.float32 and torch.isfinite(reference).all()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    unhooked = []
    for _ in range(samples):
        start = time.perf_counter()
        actual = forward()
        sync()
        unhooked.append((time.perf_counter() - start) * 1000)
        assert torch.equal(actual, reference)
    modules = modules_for(model)
    with instrument_modules(modules, device) as records:
        for _ in range(samples):
            actual = forward()
            sync()
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
        instrument_modules(modules, device) as trace_records,
    ):
        actual = forward()
        sync()
    assert torch.equal(actual, reference)
    traced_branches = collect(trace_records, device.type == "cuda")
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
        for row in profile.key_averages()
    ]
    assert {"demosaic::" + name for name in branches} <= {row["name"] for row in operators}
    cuda_events = sum(
        str(e.device_type) == "DeviceType.CUDA" and e.time_range.elapsed_us() > 0
        for e in profile.events()
    )
    assert device.type != "cuda" or cuda_events > 0, "Genuine device events required"
    trace = output / "operator-trace.json"
    profile.export_chrome_trace(str(trace))
    reference_path = output / "unchanged-reference-f32.npy"
    np.save(reference_path, reference.cpu().numpy(), allow_pickle=False)
    assert model_hash(model) == before and torch.equal(torch.get_rng_state(), cpu_rng)
    if cuda_rng is not None:
        assert torch.equal(torch.cuda.get_rng_state(), cuda_rng)
    assert sha(checkpoint) == identity["sha256"]
    for path, digest in {**source_files, **helpers}.items():
        assert sha(path) == digest, path
    archive = output / "source"
    archive.mkdir()
    for path in map(Path, {**source_files, **helpers}):
        (archive / path.name).write_bytes(path.read_bytes())
    result = {
        "status": "completed-packed-mixed16-CPU-instrumentation-preflight-no-GPU-timing"
        if device.type == "cpu"
        else "completed-packed-mixed16-bounded-FP32-CUDA-inference-profile",
        "checkpoint": identity,
        "inputs": provenance,
        "precision": "IEEE float32; no AMP/TF32",
        "device": str(device),
        "torch": str(torch.__version__),
        "hardware": torch.cuda.get_device_name(device)
        if device.type == "cuda"
        else "CPU engineering preflight",
        "batch_size": batch_size,
        "native_size": native_size,
        "warmup": warmup,
        "samples": samples,
        "unhooked_forward_synchronized_ms": unhooked,
        "unhooked_median_ms": statistics.median(unhooked),
        "inclusive_branches": branches,
        "instrumented_trace_branches": traced_branches,
        "operator_statistics": sorted(
            operators,
            key=lambda row: row["self_device_us"] if device.type == "cuda" else row["self_CPU_us"],
            reverse=True,
        ),
        "genuine_CUDA_trace_events": cuda_events,
        "trace": {"path": str(trace), "sha256": sha(trace)},
        "reference": {"path": str(reference_path), "sha256": sha(reference_path)},
        "hooked_unhooked_traced_RGB_bitwise_equal": True,
        "model_and_actual_DINO_state_unchanged": True,
        "model_state_sha256": before,
        "CPU_and_CUDA_RNG_unchanged": True,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "peak_CUDA_allocation_GB": torch.cuda.max_memory_allocated(device) / 1e9
        if device.type == "cuda"
        else None,
        "source_files": source_files,
        "helpers": helpers,
        "scope": "Unchanged actual checkpoint and fixed input batch, matching the full-review IEEE FP32 policy. Inclusive ranges overlap: RAW core contains stems/groups/DINO; context contains backbone. Never sum nested intervals. Unhooked synchronized samples exclude input/output transfer, decoding, tiling/blending and encoding; not100MP timing. Traced allocation/operator costs are instrumented. CPU mode checks hooks and identity only. No optimization, compilation, precision change, quality score, training or promotion; shared-machine times do not establish an idle hardware optimum.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "result": str(output / "result.json"),
                "status": result["status"],
                "step": identity["step"],
                "DINO": model.config.dino,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["checkpoint", "inputs", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--samples", type=int, default=5)
    main(**vars(parser.parse_args()))
