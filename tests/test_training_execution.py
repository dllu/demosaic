"""Scoped settings and actual optimizer checkpoints for execution profiles."""

import copy
import json

import numpy as np
import pytest
import torch
import yaml

from demosaic.execution import training_execution, validate_training_execution


def settings():
    return (
        torch.backends.cuda.matmul.fp32_precision,
        torch.backends.cudnn.conv.fp32_precision,
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.deterministic,
        torch.are_deterministic_algorithms_enabled(),
        torch.is_deterministic_algorithms_warn_only_enabled(),
    )


@pytest.mark.parametrize("policy,strict", [("throughput-v1", False), ("deterministic-v1", True)])
def test_profiles_are_explicit_and_restore_caller_after_failure(policy, strict):
    before, rng = settings(), torch.get_rng_state().clone()
    with (
        pytest.raises(RuntimeError, match="unsupported-operation-test"),
        training_execution(policy, "cpu") as runtime,
    ):
        assert torch.backends.cudnn.benchmark is not strict
        assert torch.backends.cudnn.deterministic is strict
        assert torch.are_deterministic_algorithms_enabled() is strict
        assert not torch.is_deterministic_algorithms_warn_only_enabled()
        assert runtime["policy"] == policy and runtime["device_type"] == "cpu"
        assert runtime["cublas_workspace_config"] is None
        raise RuntimeError("unsupported-operation-test")
    assert settings() == before
    assert torch.equal(torch.get_rng_state(), rng)


def test_nested_profiles_restore_the_strict_caller():
    before = settings()
    with training_execution("deterministic-v1", "cpu"):
        strict = settings()
        with training_execution("throughput-v1", "cpu"):
            assert not torch.are_deterministic_algorithms_enabled()
        assert settings() == strict
    assert settings() == before


@pytest.mark.parametrize("value", [None, False, 0, [], "deterministic", "unknown"])
def test_invalid_policy_is_rejected(value):
    with pytest.raises(ValueError, match="Training execution"):
        validate_training_execution(value)


@pytest.mark.parametrize("workspace", [None, "", ":16:8", "invalid"])
def test_missing_verified_cuda_workspace_fails_without_initializing_cuda(monkeypatch, workspace):
    before = settings()
    initialized = torch.cuda.is_initialized()
    if workspace is None:
        monkeypatch.delenv("CUBLAS_WORKSPACE_CONFIG", raising=False)
    else:
        monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", workspace)
    with (
        pytest.raises(ValueError, match="before starting the process"),
        training_execution("deterministic-v1", "cuda"),
    ):
        raise AssertionError("Invalid CUDA environment must fail before entering")
    assert settings() == before and torch.cuda.is_initialized() == initialized


def identical(actual, expected):
    if isinstance(expected, torch.Tensor):
        assert torch.equal(actual, expected)
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            identical(actual[key], expected[key])
    elif isinstance(expected, (tuple, list)):
        assert type(actual) is type(expected) and len(actual) == len(expected)
        for a, b in zip(actual, expected, strict=True):
            identical(a, b)
    else:
        assert actual == expected


@pytest.mark.parametrize("policy", ["throughput-v1", "deterministic-v1"])
def test_actual_checkpoint_resume_and_execution_change_guards(tmp_path, monkeypatch, policy):
    import demosaic.train as training

    source = tmp_path / "clean.npy"
    np.save(source, np.random.default_rng(7).integers(0, 65536, (48, 48, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split})
            for split in ("train", "val")
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "training_execution": policy,
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "seed": 48,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 4,
        "val_batches": 1,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    before = settings()
    full = torch.load(training.train(path), map_location="cpu", weights_only=True)
    assert settings() == before
    assert full["config"]["training_execution"] == policy
    runtime = full["config"]["training_execution_runtime"]
    assert runtime["deterministic_algorithms"] is (policy == "deterministic-v1")
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    partial = training.train(path, stop_after=2)
    if policy == "throughput-v1":
        # An old checkpoint without either new key keeps its historical default.
        legacy = torch.load(partial, map_location="cpu", weights_only=True)
        del legacy["config"]["training_execution"]
        del legacy["config"]["training_execution_runtime"]
        torch.save(legacy, partial)
    resumed = torch.load(
        training.train(path, resume=partial), map_location="cpu", weights_only=True
    )
    for key in ("model", "ema", "optimizer", "torch_rng", "python_rng", "cuda_rng", "step", "best"):
        identical(resumed[key], full[key])
    assert settings() == before

    def forbidden_constructor(*args, **kwargs):
        raise AssertionError("Execution changes must be rejected before model construction")

    monkeypatch.setattr(training, "JointDemosaic", forbidden_constructor)
    wrong = copy.deepcopy(config)
    wrong["run"] = str(tmp_path / "rejected")
    wrong["training_execution"] = (
        "deterministic-v1" if policy == "throughput-v1" else "throughput-v1"
    )
    path.write_text(yaml.safe_dump(wrong))
    with pytest.raises(ValueError, match="Resume training execution differs"):
        training.train(path, resume=partial)
    assert settings() == before
    if policy == "deterministic-v1":
        state = torch.load(partial, map_location="cpu", weights_only=True)
        state["config"]["training_execution_runtime"]["torch_version"] = "different-runtime"
        changed = tmp_path / "changed-runtime.pt"
        torch.save(state, changed)
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match="strict execution environment differs"):
            training.train(path, resume=changed)
        assert settings() == before
