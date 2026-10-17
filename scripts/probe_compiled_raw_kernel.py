"""Isolated eager/compiled comparison after a genuine V67 inference profile.

Compile only seven pure neural blocks; retain weights, precision, physical code,
inputs and model configuration. CUDA mode needs the actual final10000 profile.
CPU mode is an engineering fixture, never CUDA timing or quality evidence.
"""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import load_inputs, model_hash, sha
from torch._dynamo.utils import counters
from torch._inductor import metrics

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path

BLOCKS = ("m_down1", "m_down2", "m_down3", "m_body", "m_up3", "m_up2", "m_up1")


def differences(actual, expected):
    delta = actual.double() - expected.double()
    return [
        {
            "image_index": i,
            "maximum_absolute_difference": float(row.abs().max()),
            "RMS_difference": float(row.square().mean().sqrt()),
            "bitwise_equal": torch.equal(actual[i], expected[i]),
        }
        for i, row in enumerate(delta)
    ]


@torch.inference_mode()
def main(profile_result, output, device="cuda", warmup=3, forwards=5, order="ABBABAAB"):
    os.nice(5)
    torch.set_num_threads(2)
    device = torch.device(device)
    cpu = device.type == "cpu"
    profile = json.loads(profile_result.read_text())
    if cpu:
        assert not torch.cuda.is_available() and not torch.cuda.is_initialized()
        assert profile["status"] == "completed-real-V67-CPU-profiler-preflight-no-GPU-timing"
        assert profile["checkpoint"]["step"] == 2000 and order == "AB"
    else:
        assert device.type == "cuda" and warmup == 3 and forwards == 5 and order == "ABBABAAB"
        assert profile["status"] == "completed-real-V67-bounded-CUDA-inference-profile"
        assert profile["checkpoint"]["step"] == 10000 and profile["genuine_CUDA_trace_events"] > 0
    assert warmup >= 1 and forwards >= 1
    assert profile["all_hooked_unhooked_profiled_outputs_bitwise_reference"]
    assert (
        profile["model_and_actual_DINO_state_unchanged"] and profile["CPU_and_CUDA_RNG_unchanged"]
    )
    available = psutil.virtual_memory().available / 1e9
    assert available > (32 if cpu else 40)
    memory_policy = {"available_GB": available, "allocator_cap_GB": None}
    if not cpu:
        total = torch.cuda.get_device_properties(0).total_memory
        fraction = min((available - 24) * 1e9 / total, 0.75)
        torch.cuda.memory.set_per_process_memory_fraction(fraction, 0)
        memory_policy.update(allocator_cap_GB=fraction * total / 1e9, reserve_GB=24)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = profile["checkpoint"]
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    batch, provenance = load_inputs(
        Path(profile["inputs"]["report"]), device, profile["batch_size"], profile["native_size"]
    )
    assert provenance == profile["inputs"]
    model, state = load_checkpoint(checkpoint["path"], device)
    assert state["loaded_sha256"] == checkpoint["sha256"] and state["step"] == checkpoint["step"]
    del state
    model.eval()
    if not cpu:
        model.to(memory_format=torch.channels_last)
    model.set_noise(provenance["conditioning"]["shot"], provenance["conditioning"]["read"])
    before = model_hash(model)
    assert before == profile["model_and_actual_DINO_state_hash_before_after"]
    original_config = model.config.to_dict()
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone() if not cpu else None
    reference_path = profile_result.parent / "unchanged-reference-f32.npy"
    reference = torch.from_numpy(np.load(reference_path, allow_pickle=False)).to(device)

    def synchronize():
        if not cpu:
            torch.cuda.synchronize(device)

    def forward():
        with amp_context(device, dtype="float32" if cpu else "float16"):
            return model(*batch)

    for _ in range(warmup):
        actual = forward()
        assert torch.equal(actual, reference), "Eager output differs from the genuine prior profile"
    synchronize()
    blocks = {name: getattr(model.pretrained_rgb.network, name) for name in BLOCKS}
    assert all(block._compiled_call_impl is None for block in blocks.values())
    counters.clear()
    metrics.reset()
    compile_started = time.monotonic()
    for block in blocks.values():
        block.compile(backend="inductor", fullgraph=True, dynamic=False)
    for _ in range(warmup):
        compiled = forward()
    synchronize()
    assert compiled.dtype == torch.float32 and torch.isfinite(compiled).all()
    assert torch.equal(forward(), compiled), "Compiled forward is not repeatable"
    compiled_calls = {name: block._compiled_call_impl for name, block in blocks.items()}
    assert all(call is not None for call in compiled_calls.values())
    assert {
        name for name, part in model.named_modules() if part._compiled_call_impl is not None
    } == {"pretrained_rgb.network." + name for name in BLOCKS}
    assert counters["stats"]["unique_graphs"] >= 7
    compile_seconds = time.monotonic() - compile_started
    errors = differences(compiled, reference)
    numerical_pass = all(
        row["maximum_absolute_difference"] <= 1e-5 and row["RMS_difference"] <= 1e-6
        for row in errors
    )
    np.save(output / "eager-reference-f32.npy", reference.cpu().numpy(), allow_pickle=False)
    np.save(output / "compiled-f32.npy", compiled.cpu().numpy(), allow_pickle=False)
    measured_cpu_rng = torch.get_rng_state().clone()
    measured_cuda_rng = torch.cuda.get_rng_state().clone() if not cpu else None
    records = []
    if numerical_pass:
        for index, policy in enumerate(order):
            for name, block in blocks.items():
                block._compiled_call_impl = compiled_calls[name] if policy == "B" else None
            # Exclude one policy-switch warmup from every timing block.
            actual = forward()
            assert torch.equal(actual, reference if policy == "A" else compiled)
            synchronize()
            if not cpu:
                torch.cuda.reset_peak_memory_stats(device)
            start = torch.cuda.Event(enable_timing=True) if not cpu else None
            end = torch.cuda.Event(enable_timing=True) if not cpu else None
            began = time.perf_counter()
            if start is not None:
                start.record()
            for _ in range(forwards):
                actual = forward()
            if end is not None:
                end.record()
            synchronize()
            wall_ms = (time.perf_counter() - began) * 1000 / forwards
            assert torch.equal(actual, reference if policy == "A" else compiled)
            row = {
                "block": index,
                "policy": "eager" if policy == "A" else "compiled-neural-blocks",
                "forwards": forwards,
                "synchronized_wall_ms_per_forward": wall_ms,
                "CUDA_ms_per_forward": start.elapsed_time(end) / forwards
                if start is not None
                else None,
                "peak_CUDA_GB": torch.cuda.max_memory_allocated(device) / 1e9 if not cpu else None,
            }
            records.append(row)
            print(json.dumps(row), flush=True)
    assert torch.equal(torch.get_rng_state(), measured_cpu_rng)
    if not cpu:
        assert torch.equal(torch.cuda.get_rng_state(), measured_cuda_rng)
    assert model_hash(model) == before and model.config.to_dict() == original_config
    assert sha(checkpoint["path"]) == checkpoint["sha256"]
    medians = (
        {
            policy: statistics.median(
                row["synchronized_wall_ms_per_forward"]
                for row in records
                if row["policy"] == policy
            )
            for policy in ["eager", "compiled-neural-blocks"]
        }
        if numerical_pass
        else None
    )
    result = {
        "status": "completed-CPU-compiled-trial-engineering-fixture"
        if cpu
        else "completed-bounded-CUDA-compiled-neural-block-trial",
        "profile_result": {"path": str(profile_result), "sha256": sha(profile_result)},
        "checkpoint": checkpoint,
        "inputs": provenance,
        "batch_size": profile["batch_size"],
        "native_size": profile["native_size"],
        "device": str(device),
        "neural_compute_precision": "float32" if cpu else "float16",
        "physical_compute_precision": "float32",
        "hardware": "CPU engineering fixture" if cpu else torch.cuda.get_device_name(device),
        "torch": str(torch.__version__),
        "compiled_blocks": list(BLOCKS),
        "only_seven_pure_neural_blocks_compiled": True,
        "actual_unique_graphs": counters["stats"]["unique_graphs"],
        "generated_kernels_including_cache_metadata": metrics.generated_kernel_count,
        "compilation_and_warmup_seconds_excluded": compile_seconds,
        "prespecified_numerical_thresholds": {
            "maximum_absolute_difference": 1e-5,
            "RMS_difference": 1e-6,
        },
        "per_image_numerical_differences": errors,
        "numerical_gate_pass": numerical_pass,
        "timing_skipped_for_numerical_failure": not numerical_pass,
        "warmup_per_policy": warmup,
        "excluded_switch_warmups": len(records),
        "order": order,
        "timing_blocks": records,
        "median_synchronized_wall_ms": medians,
        "eager_over_compiled_wall_ratio": medians["eager"] / medians["compiled-neural-blocks"]
        if medians
        else None,
        "baseline_bitwise_prior_profile_reference": True,
        "all_measured_outputs_bitwise_their_policy_reference": True if records else None,
        "all_model_and_actual_DINO_state_SHA256_unchanged": before,
        "model_config_and_checkpoint_unchanged": True,
        "all_measured_forward_RNG_unchanged": True if records else None,
        "compilation_and_warmup_CPU_RNG_unchanged": torch.equal(cpu_rng, measured_cpu_rng),
        "compilation_and_warmup_CUDA_RNG_unchanged": torch.equal(cuda_rng, measured_cuda_rng)
        if not cpu
        else None,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "memory_policy": memory_policy,
        "arrays": {
            name: sha(output / name) for name in ["eager-reference-f32.npy", "compiled-f32.npy"]
        },
        "driver_sha256": sha(__file__),
        "scope": "Isolated process-local seven neural blocks compiled with Inductor/fullgraph/static, original model/weights/FP16-neural physicalFP32 precision/inputs/defaults preserved. Exact eager equality to actual profile reference, per-image numerical gate before timing, excluded initial/compile and switch warmups, ABBA/BAAB block timing. Both timing policies retain compiled-cache allocations. Sum or median is not full-frame throughput or idle hardware performance; shared machine. Numerical acceptance is an engineering bound, not preserved image quality or promotion. CPU fixture uses original real2k B1/native256/FP32 and AB only; no CUDA timing or equivalence claim. No training/export/source/config/production batch or precision change. Full quality/native/full-frame checks remain necessary.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"result": str(output / "result.json"), "status": result["status"]}), flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--forwards", type=int, default=5)
    parser.add_argument("--order", default="ABBABAAB")
    main(**vars(parser.parse_args()))
