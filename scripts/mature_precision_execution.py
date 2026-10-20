"""Explicit research-only fixed backends for a new mature precision study."""

import os
from contextlib import contextmanager

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

FIXED_EXECUTION = "mature-fixed-backends-v1"


def execution_snapshot():
    return {
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "cudnn_benchmark_limit": torch.backends.cudnn.benchmark_limit,
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "deterministic_warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
        "convolution_fp32": torch.backends.cudnn.conv.fp32_precision,
        "matmul_fp32": torch.backends.cuda.matmul.fp32_precision,
        "fp16_reduced_precision_reduction": torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction,
        "bf16_reduced_precision_reduction": torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction,
        "fp16_accumulation": torch.backends.cuda.matmul.allow_fp16_accumulation,
        "math_SDPA_reduced_precision_reduction": torch.backends.cuda.fp16_bf16_reduction_math_sdp_allowed(),
        "SDPA_math": torch.backends.cuda.math_sdp_enabled(),
        "SDPA_flash": torch.backends.cuda.flash_sdp_enabled(),
        "SDPA_efficient": torch.backends.cuda.mem_efficient_sdp_enabled(),
        "SDPA_cudnn": torch.backends.cuda.cudnn_sdp_enabled(),
        "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }


@contextmanager
def fixed_execution():
    """Restore all settings even on failure; this alone executes no GPU work.

    The workspace environment must be supplied before process/CUDA startup.
    Model weights, config and precision-policy flags are outside this context.
    """
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise ValueError("Set CUBLAS_WORKSPACE_CONFIG=:4096:8 before starting the process")
    previous = execution_snapshot()
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True, warn_only=False)
        torch.backends.cudnn.conv.fp32_precision = "ieee"
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
        torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
        torch.backends.cuda.matmul.allow_fp16_accumulation = False
        torch.backends.cuda.allow_fp16_bf16_reduction_math_sdp(False)
        with sdpa_kernel(SDPBackend.MATH):
            yield execution_snapshot()
    finally:
        torch.backends.cudnn.benchmark = previous["cudnn_benchmark"]
        torch.backends.cudnn.deterministic = previous["cudnn_deterministic"]
        torch.use_deterministic_algorithms(
            previous["deterministic_algorithms"],
            warn_only=previous["deterministic_warn_only"],
        )
        torch.backends.cudnn.conv.fp32_precision = previous["convolution_fp32"]
        torch.backends.cuda.matmul.fp32_precision = previous["matmul_fp32"]
        torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = previous[
            "fp16_reduced_precision_reduction"
        ]
        torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = previous[
            "bf16_reduced_precision_reduction"
        ]
        torch.backends.cuda.matmul.allow_fp16_accumulation = previous["fp16_accumulation"]
        torch.backends.cuda.allow_fp16_bf16_reduction_math_sdp(
            previous["math_SDPA_reduced_precision_reduction"]
        )
