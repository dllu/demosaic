"""Keep numerical image operations in IEEE FP32 without disabling cuDNN."""

from contextlib import contextmanager, nullcontext

import torch

COMPUTE_DTYPES = ("bfloat16", "float16", "float32")
REFINEMENT_DTYPES = ("float32", "float16")


@contextmanager
def amp_context(device, enabled=True, *, dtype="bfloat16"):
    """Choose neural compute precision; physical operations keep their own FP32 guard.

    BF16 remains the training and historical inference default. Explicit FP32
    disables both autocast and TF32, including when nested in another AMP scope.
    CPU calls do not enable half-precision autocast.
    """
    if dtype not in COMPUTE_DTYPES:
        raise ValueError(f"Unknown compute precision {dtype!r}; choose from {COMPUTE_DTYPES}")
    device = torch.device(device)
    if enabled and dtype == "float32":
        with torch.autocast(device.type, enabled=False), ieee_fp32():
            yield
    else:
        context = (
            torch.autocast("cuda", dtype=getattr(torch, dtype))
            if enabled and device.type == "cuda"
            else nullcontext()
        )
        with context:
            yield


@contextmanager
def ieee_fp32():
    convolution = torch.backends.cudnn.conv.fp32_precision
    matmul = torch.backends.cuda.matmul.fp32_precision
    try:
        torch.backends.cudnn.conv.fp32_precision = "ieee"
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        yield
    finally:
        torch.backends.cudnn.conv.fp32_precision = convolution
        torch.backends.cuda.matmul.fp32_precision = matmul


@contextmanager
def cudnn_autotune(device, *, enabled=False, precision="float32"):
    """Bound an opt-in CUDA FP32 search and restore backend settings/quota."""
    if not enabled:
        yield {"enabled": False}
        return
    device = torch.device(device)
    if device.type != "cuda" or precision != "float32":
        raise ValueError("cuDNN autotuning requires CUDA and float32 precision")
    if device.index is None:
        device = torch.device("cuda", torch.cuda.current_device())
    previous_benchmark = torch.backends.cudnn.benchmark
    previous_limit = torch.backends.cudnn.benchmark_limit
    previous_fraction = torch.cuda.get_per_process_memory_fraction(device)
    total = torch.cuda.get_device_properties(device).total_memory
    fraction = min(previous_fraction, 16 * 2**30 / total)
    torch.cuda.set_per_process_memory_fraction(fraction, device)
    try:
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.benchmark_limit = 10
        with amp_context(device, dtype="float32"):
            yield {
                "enabled": True,
                "benchmark_limit": 10,
                "allocator_limit_bytes": int(total * fraction),
                "precision": "IEEE float32; no AMP/TF32",
            }
    finally:
        torch.backends.cudnn.benchmark = previous_benchmark
        torch.backends.cudnn.benchmark_limit = previous_limit
        torch.cuda.set_per_process_memory_fraction(previous_fraction, device)
