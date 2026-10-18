"""The opt-in search must preserve settings, quotas and early CLI validation."""

from types import SimpleNamespace

import pytest
import torch

from demosaic.cli import main
from demosaic.precision import cudnn_autotune


@pytest.fixture
def cuda_quota(monkeypatch):
    state = {"fraction": 0.75, "changes": []}
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 0)

    def get_fraction(device):
        # The real getter rejects a bare torch.device("cuda").
        assert device.type == "cuda" and device.index is not None
        return state["fraction"]

    monkeypatch.setattr(torch.cuda, "get_per_process_memory_fraction", get_fraction)
    monkeypatch.setattr(
        torch.cuda,
        "get_device_properties",
        lambda device: SimpleNamespace(total_memory=128 * 2**30),
    )

    def set_fraction(fraction, device):
        state["fraction"] = fraction
        state["changes"].append((fraction, str(device)))

    monkeypatch.setattr(torch.cuda, "set_per_process_memory_fraction", set_fraction)
    return state


@pytest.mark.parametrize("fail", [False, True])
def test_restores_flags_precision_and_quota(cuda_quota, fail):
    original = (
        torch.backends.cudnn.benchmark,
        torch.backends.cudnn.benchmark_limit,
        torch.backends.cudnn.conv.fp32_precision,
        torch.backends.cuda.matmul.fp32_precision,
    )
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.benchmark_limit = 3
        torch.backends.cudnn.conv.fp32_precision = "tf32"
        torch.backends.cuda.matmul.fp32_precision = "tf32"

        def exercise():
            with cudnn_autotune("cuda:0", enabled=True) as policy:
                assert torch.backends.cudnn.benchmark
                assert torch.backends.cudnn.benchmark_limit == 10
                assert torch.backends.cudnn.conv.fp32_precision == "ieee"
                assert torch.backends.cuda.matmul.fp32_precision == "ieee"
                assert policy["allocator_limit_bytes"] == 16 * 2**30
                assert cuda_quota["fraction"] == 0.125
                if fail:
                    raise RuntimeError("inference failed")

        if fail:
            with pytest.raises(RuntimeError, match="inference failed"):
                exercise()
        else:
            exercise()
        assert not torch.backends.cudnn.benchmark
        assert torch.backends.cudnn.benchmark_limit == 3
        assert torch.backends.cudnn.conv.fp32_precision == "tf32"
        assert torch.backends.cuda.matmul.fp32_precision == "tf32"
        assert cuda_quota["fraction"] == 0.75
    finally:
        torch.backends.cudnn.benchmark, torch.backends.cudnn.benchmark_limit = original[:2]
        torch.backends.cudnn.conv.fp32_precision = original[2]
        torch.backends.cuda.matmul.fp32_precision = original[3]


def test_preserves_stricter_existing_quota(cuda_quota):
    cuda_quota["fraction"] = 0.05
    with cudnn_autotune("cuda", enabled=True) as policy:
        assert cuda_quota["fraction"] == 0.05
        assert policy["allocator_limit_bytes"] == int(128 * 2**30 * 0.05)
    assert cuda_quota["fraction"] == 0.05


def test_disabled_does_not_query_cuda(monkeypatch):
    def unexpected(*args):
        raise AssertionError("CUDA queried for disabled autotuning")

    monkeypatch.setattr(torch.cuda, "get_per_process_memory_fraction", unexpected)
    with cudnn_autotune("cpu", enabled=False, precision="bfloat16") as policy:
        assert policy == {"enabled": False}


def test_bare_cuda_resolves_the_active_device(monkeypatch, cuda_quota):
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 2)
    with cudnn_autotune("cuda", enabled=True):
        assert cuda_quota["changes"] == [(0.125, "cuda:2")]
    assert cuda_quota["changes"][-1] == (0.75, "cuda:2")


@pytest.mark.parametrize("device,precision", [("cpu", "float32"), ("cuda", "float16")])
def test_rejects_unsupported_policy_before_cuda(cuda_quota, device, precision):
    with (
        pytest.raises(ValueError, match="requires CUDA and float32"),
        cudnn_autotune(device, enabled=True, precision=precision),
    ):
        pytest.fail("invalid policy entered")
    assert not cuda_quota["changes"]


@pytest.mark.parametrize("device,precision", [("cpu", "float32"), ("cuda", "bfloat16")])
def test_cli_rejects_policy_before_input_loading(tmp_path, monkeypatch, device, precision):
    monkeypatch.setattr(torch, "set_num_threads", lambda _: None)
    monkeypatch.setattr(torch, "set_float32_matmul_precision", lambda _: None)
    with pytest.raises(ValueError, match="requires --device cuda and --precision float32"):
        main(
            [
                "infer",
                str(tmp_path / "missing.pt"),
                str(tmp_path / "missing.npy"),
                str(tmp_path / "output.tiff"),
                "--device",
                device,
                "--precision",
                precision,
                "--cudnn-benchmark",
                "--shot",
                "0.001",
                "--read",
                "0.000001",
            ]
        )
    assert not (tmp_path / "output.tiff").exists()


def test_cli_rejects_half_precision_refinement_before_input_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(torch, "set_num_threads", lambda _: None)
    monkeypatch.setattr(torch, "set_float32_matmul_precision", lambda _: None)
    with pytest.raises(ValueError, match="including --refinement-precision float32"):
        main(
            [
                "infer",
                str(tmp_path / "missing.pt"),
                str(tmp_path / "missing.npy"),
                str(tmp_path / "output.tiff"),
                "--precision",
                "float32",
                "--refinement-precision",
                "float16",
                "--cudnn-benchmark",
                "--shot",
                "0.001",
                "--read",
                "0.000001",
            ]
        )
    assert not (tmp_path / "output.tiff").exists()


def test_hidden_half_checkpoint_rejection_restores_quota(tmp_path, monkeypatch, cuda_quota):
    import numpy as np

    from demosaic import inference

    monkeypatch.setattr(torch, "set_num_threads", lambda _: None)
    monkeypatch.setattr(torch, "set_float32_matmul_precision", lambda _: None)
    monkeypatch.setattr(
        inference,
        "load_checkpoint",
        lambda *args, **kwargs: (
            SimpleNamespace(config=SimpleNamespace(rgb_hidden_autocast=True)),
            {},
        ),
    )
    raw = tmp_path / "input.npy"
    np.save(raw, np.zeros((32, 32), dtype=np.float32), allow_pickle=False)
    with pytest.raises(ValueError, match="Checkpoint forces hidden half precision"):
        main(
            [
                "infer",
                str(tmp_path / "model.pt"),
                str(raw),
                str(tmp_path / "output.tiff"),
                "--precision",
                "float32",
                "--cudnn-benchmark",
                "--shot",
                "0.001",
                "--read",
                "0.000001",
            ]
        )
    assert cuda_quota["fraction"] == 0.75
    assert not (tmp_path / "output.tiff").exists()
