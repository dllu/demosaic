"""Backend settings only: these tests do not claim CUDA/model execution."""

from contextlib import nullcontext

import pytest
import torch
from mature_precision_execution import execution_snapshot, fixed_execution


@pytest.mark.parametrize("raise_inside", [False, True])
@pytest.mark.parametrize("ambient_determinism", [False, True])
def test_fixed_backend_contract_and_exact_restoration(
    monkeypatch, raise_inside, ambient_determinism
):
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    enabled = torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(ambient_determinism, warn_only=True)
    original, initialized = execution_snapshot(), torch.cuda.is_initialized()
    try:
        with (
            pytest.raises(RuntimeError, match="injected") if raise_inside else nullcontext(),
            fixed_execution() as active,
        ):
            assert active == execution_snapshot()
            assert not active["cudnn_benchmark"] and active["cudnn_deterministic"]
            assert active["deterministic_algorithms"] and not active["deterministic_warn_only"]
            assert active["convolution_fp32"] == active["matmul_fp32"] == "ieee"
            assert active["SDPA_math"]
            assert not any(
                active[k]
                for k in [
                    "SDPA_flash",
                    "SDPA_efficient",
                    "SDPA_cudnn",
                    "fp16_accumulation",
                    "fp16_reduced_precision_reduction",
                    "bf16_reduced_precision_reduction",
                    "math_SDPA_reduced_precision_reduction",
                ]
            )
            if raise_inside:
                raise RuntimeError("injected")
        assert execution_snapshot() == original
        assert torch.cuda.is_initialized() == initialized
    finally:
        torch.use_deterministic_algorithms(enabled, warn_only=warn_only)


def test_workspace_must_be_supplied_before_start(monkeypatch):
    monkeypatch.delenv("CUBLAS_WORKSPACE_CONFIG", raising=False)
    original = execution_snapshot()
    with pytest.raises(ValueError, match="before starting"), fixed_execution():
        raise AssertionError("unreachable")
    assert execution_snapshot() == original


def test_nested_scope_restores_outer_fixed_settings(monkeypatch):
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    original = execution_snapshot()
    with fixed_execution() as outer:
        with fixed_execution() as inner:
            assert inner == outer
        assert execution_snapshot() == outer
    assert execution_snapshot() == original
