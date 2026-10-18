"""Explicit training execution profiles, scoped to one training invocation."""

import os
from contextlib import contextmanager

import torch

POLICIES = ("throughput-v1", "deterministic-v1")


def validate_training_execution(value):
    if not isinstance(value, str) or value not in POLICIES:
        raise ValueError(f"Training execution must be one of {POLICIES}")
    return value


def require_resume_execution(previous, policy, runtime):
    prior = validate_training_execution(previous.get("training_execution", "throughput-v1"))
    if prior != policy:
        raise ValueError("Resume training execution differs; initialize a new run")
    if policy == "deterministic-v1" and previous.get("training_execution_runtime") != runtime:
        raise ValueError("Resume strict execution environment differs; initialize a new run")


@contextmanager
def training_execution(policy, device):
    """Select tested backend settings and restore the caller on every exit.

    The strict profile is opt-in and never downgrades unsupported operations.
    Matching these recorded settings is not a cross-platform/long-run guarantee.
    """
    policy = validate_training_execution(policy)
    device = torch.device(device)
    strict = policy == "deterministic-v1"
    workspace = os.environ.get("CUBLAS_WORKSPACE_CONFIG") if device.type == "cuda" else None
    if strict and device.type == "cuda" and workspace != ":4096:8":
        raise ValueError(
            "deterministic-v1 CUDA training requires CUBLAS_WORKSPACE_CONFIG=:4096:8 "
            "in the environment before starting the process"
        )
    previous = {
        "matmul_fp32": torch.backends.cuda.matmul.fp32_precision,
        "conv_fp32": torch.backends.cudnn.conv.fp32_precision,
        "benchmark": torch.backends.cudnn.benchmark,
        "deterministic": torch.backends.cudnn.deterministic,
        "algorithms": torch.are_deterministic_algorithms_enabled(),
        "warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
    }
    try:
        # Use the same backend API as ieee_fp32; mixing the legacy precision
        # getter with an explicit backend setting raises in current PyTorch.
        torch.backends.cuda.matmul.fp32_precision = "tf32"
        torch.backends.cudnn.benchmark = not strict
        torch.backends.cudnn.deterministic = strict
        torch.use_deterministic_algorithms(strict, warn_only=False)
        yield {
            "policy": policy,
            "device_type": device.type,
            "torch_version": str(torch.__version__),
            "matmul_fp32_precision": torch.backends.cuda.matmul.fp32_precision,
            "convolution_fp32_precision": torch.backends.cudnn.conv.fp32_precision,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "deterministic_warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
            "cublas_workspace_config": workspace,
        }
    finally:
        torch.backends.cuda.matmul.fp32_precision = previous["matmul_fp32"]
        torch.backends.cudnn.conv.fp32_precision = previous["conv_fp32"]
        torch.backends.cudnn.benchmark = previous["benchmark"]
        torch.backends.cudnn.deterministic = previous["deterministic"]
        torch.use_deterministic_algorithms(previous["algorithms"], warn_only=previous["warn_only"])
