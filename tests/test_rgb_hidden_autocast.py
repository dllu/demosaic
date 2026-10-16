import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import RgbRestorationTrunk


def test_hidden_autocast_keeps_physical_head_and_tail_fp32():
    trunk = RgbRestorationTrunk(hidden_autocast=True)
    dtypes = {}
    handles = [
        trunk.m_down1.register_forward_pre_hook(
            lambda _, args: dtypes.update(encoder=args[0].dtype)
        ),
        trunk.m_tail.register_forward_pre_hook(
            lambda _, args: dtypes.update(tail=args[0].dtype)
        ),
    ]
    rgb = torch.rand(1, 3, 16, 24)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        prediction = trunk(rgb, torch.zeros_like(rgb[:, :1]))
    assert dtypes == {"encoder": torch.bfloat16, "tail": torch.float32}
    assert prediction.dtype == torch.float32
    with torch.no_grad():
        trunk(rgb, torch.zeros_like(rgb[:, :1]))
    assert dtypes == {"encoder": torch.float32, "tail": torch.float32}
    for handle in handles:
        handle.remove()


def test_default_and_explicit_fp32_paths_remain_bitwise_identical():
    trunk = RgbRestorationTrunk()
    original = RgbRestorationTrunk(hidden_autocast=True)
    original.load_state_dict(trunk.state_dict())
    rgb = torch.rand(1, 3, 16, 16)
    with torch.no_grad():
        torch.testing.assert_close(
            trunk(rgb, rgb[:, :1] * 0.01), original(rgb, rgb[:, :1] * 0.01),
            atol=0, rtol=0,
        )
    assert list(trunk.state_dict()) == list(original.state_dict())
    assert not ModelConfig().rgb_hidden_autocast


@pytest.mark.parametrize("pattern", PATTERNS)
def test_native_adc_ramp_survives_hidden_bf16_and_odd_dimensions(pattern):
    config = ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True,
        variance_stabilization=True, physical_anchors=True, rgb_hidden_autocast=True,
    )
    model = JointDemosaic(config).eval()
    model.set_noise(0, 0)
    trunk = model.pretrained_rgb.network
    with torch.no_grad():
        for parameter in trunk.parameters():
            parameter.zero_()
        for channel in range(3):
            trunk.m_head.weight[channel, channel, 1, 1] = 1
            trunk.m_tail.weight[channel, channel, 1, 1] = 1
        raw = 0.3 + torch.arange(4 * 7 * 13).reshape(1, 4, 7, 13) / 65535
        colors = color_indices(pattern)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            result = model(raw, torch.zeros_like(raw), colors)
    assert result.shape == (1, 3, 14, 26) and result.dtype == torch.float32
    torch.testing.assert_close(result, malvar(raw, colors), atol=1 / 65535 / 8, rtol=0)
    assert torch.unique((result * 65535).round()).numel() > 256


def test_hidden_policy_checkpoint_roundtrip(tmp_path):
    config = ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True,
        rgb_hidden_autocast=True,
    )
    model = JointDemosaic(config).eval()
    path = tmp_path / "hidden.pt"
    torch.save({"model_config": config.to_dict(), "model": model.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.rgb_hidden_autocast
    assert restored.pretrained_rgb.network.hidden_autocast
    raw = torch.rand(1, 4, 8, 8)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        torch.testing.assert_close(
            model(raw, torch.zeros_like(raw), color_indices("RGGB")),
            restored(raw, torch.zeros_like(raw), color_indices("RGGB")), atol=0, rtol=0,
        )


def test_hidden_policy_rejects_local_backbone():
    with pytest.raises(ValueError, match="hidden autocast"):
        JointDemosaic(ModelConfig(rgb_hidden_autocast=True))
