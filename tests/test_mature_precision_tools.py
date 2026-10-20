"""Explicit CPU emulation and exception-safe mature-model policy overrides."""

from dataclasses import replace

import pytest
import torch
from mature_precision_tools import precision_policy
from torch import nn

from demosaic.model import ModelConfig
from demosaic.pretrained_rgb import RgbRestorationTrunk


def model():
    result = nn.Module()
    result.config = ModelConfig(
        restoration_backbone="pretrained-rgb",
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
    )
    result.pretrained_rgb = nn.Module()
    result.pretrained_rgb.network = RgbRestorationTrunk(middle_skip_fp32=True)
    return result.eval()


@pytest.mark.parametrize("policy", ["fp32", "fp16", "fp16-hidden"])
def test_native_head_tail_and_policy_restore_under_ambient_BF16(policy):
    net = model()
    original = net.config.to_dict()
    trunk = net.pretrained_rgb.network
    dtypes = {}
    handles = [
        layer.register_forward_pre_hook(
            lambda _m, args, key=key: dtypes.update({key: args[0].dtype})
        )
        for key, layer in [
            ("head", trunk.m_head),
            ("encoder", trunk.m_down1),
            ("tail", trunk.m_tail),
        ]
    ]
    rng = torch.get_rng_state().clone()
    try:
        with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16):
            with precision_policy(net, policy, "cpu", cpu_probe=True):
                prediction = trunk(
                    torch.full((1, 3, 16, 24), 0.2), torch.full((1, 1, 16, 24), 0.01)
                )
            assert (
                torch.is_autocast_enabled("cpu")
                and torch.get_autocast_dtype("cpu") == torch.bfloat16
            )
    finally:
        for handle in handles:
            handle.remove()
    assert dtypes == {
        "head": torch.float32,
        "encoder": torch.float16 if policy == "fp16-hidden" else torch.float32,
        "tail": torch.float32,
    }
    assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
    assert not trunk.hidden_autocast and net.config.to_dict() == original
    assert torch.equal(rng, torch.get_rng_state())


def test_exception_restores_policy_autocast_and_backend_flags():
    net = model()
    original = (torch.backends.cuda.matmul.fp32_precision, torch.backends.cudnn.conv.fp32_precision)
    with (
        pytest.raises(RuntimeError, match="planned"),
        precision_policy(net, "fp16-hidden", "cpu", cpu_probe=True),
    ):
        assert net.pretrained_rgb.network.hidden_autocast
        assert torch.is_autocast_enabled("cpu")
        raise RuntimeError("planned")
    assert not net.pretrained_rgb.network.hidden_autocast and not torch.is_autocast_enabled("cpu")
    assert original == (
        torch.backends.cuda.matmul.fp32_precision,
        torch.backends.cudnn.conv.fp32_precision,
    )


def test_production_CPU_cannot_silently_enable_half():
    net = model()
    with (
        pytest.raises(ValueError, match="explicitly enabled"),
        precision_policy(net, "fp16-hidden", "cpu"),
    ):
        raise AssertionError("Unreachable")
    assert not net.pretrained_rgb.network.hidden_autocast


@pytest.mark.parametrize(
    "change",
    [
        {"rgb_hidden_autocast": True},
        {"raw_spectral_residual": True},
        {"late_rgb_refinement": "global"},
        {"adc_cfa_projection": True},
        {"rgb_processing_scale": 2},
    ],
)
def test_other_paths_are_not_misrepresented_as_the_mature_baseline(change):
    net = model()
    net.config = replace(net.config, **change)
    with pytest.raises(ValueError, match="original mature"), precision_policy(net, "fp32", "cpu"):
        raise AssertionError("Unreachable")
