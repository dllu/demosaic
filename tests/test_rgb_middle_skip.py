import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import RgbRestorationTrunk


def inputs():
    rgb = torch.rand(1, 3, 32, 32, generator=torch.Generator().manual_seed(7))
    return rgb, torch.full((1, 1, 32, 32), 0.015)


def test_absent_and_zero_context_match_values_and_gradients_in_bfloat16():
    torch.manual_seed(3)
    trunk = RgbRestorationTrunk(middle_skip_fp32=True)
    rgb, noise = inputs()
    rgb.requires_grad_(True)
    zero = torch.zeros(1, 512, 4, 4)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        absent = trunk(rgb, noise)
        present = trunk(rgb, noise, middle_offset=zero)
    torch.testing.assert_close(absent, present, rtol=0, atol=0)
    parameters = [rgb, trunk.m_head.weight, trunk.m_body[0].res[0].weight]
    first = torch.autograd.grad(absent.sum(), parameters)
    second = torch.autograd.grad(present.sum(), parameters)
    for a, b in zip(first, second):
        torch.testing.assert_close(a, b, rtol=0, atol=0)


def test_legacy_default_is_preserved_and_exposes_the_context_promotion():
    torch.manual_seed(4)
    default = RgbRestorationTrunk()
    explicit = RgbRestorationTrunk(middle_skip_fp32=False)
    explicit.load_state_dict(default.state_dict(), strict=True)
    rgb, noise = inputs()
    seen = []
    handle = default.m_body.register_forward_pre_hook(lambda module, args: seen.append(args[0].dtype))
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        a = default(rgb, noise)
        b = explicit(rgb, noise)
        default(rgb, noise, middle_offset=torch.zeros(1, 512, 4, 4))
    handle.remove()
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    assert seen == [torch.bfloat16, torch.float32]
    assert default.state_dict().keys() == explicit.state_dict().keys()


def test_existing_float32_context_offset_keeps_identical_predictions():
    torch.manual_seed(5)
    old = RgbRestorationTrunk()
    matched = RgbRestorationTrunk(middle_skip_fp32=True)
    matched.load_state_dict(old.state_dict(), strict=True)
    rgb, noise = inputs()
    offset = torch.randn(1, 512, 4, 4) * 0.01
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        a = old(rgb, noise, middle_offset=offset)
        b = matched(rgb, noise, middle_offset=offset)
    torch.testing.assert_close(a, b, rtol=0, atol=0)


@pytest.mark.parametrize("enabled", [False, True])
def test_policy_survives_portable_checkpoint_and_older_default(tmp_path, enabled):
    cfg = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        rgb_middle_skip_fp32=enabled,
    )
    model = JointDemosaic(cfg).eval()
    config = cfg.to_dict()
    if not enabled:
        config.pop("rgb_middle_skip_fp32")
    path = tmp_path / "checkpoint.pt"
    torch.save({"model_config": config, "model": model.restoration_state_dict(), "step": 0}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.rgb_middle_skip_fp32 is enabled
    assert restored.pretrained_rgb.network.middle_skip_fp32 is enabled
    raw = torch.rand(1, 4, 16, 16, generator=torch.Generator().manual_seed(7)) * 0.3
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        a = model(raw, torch.full_like(raw, 0.001), color_indices("RGGB"))
        b = restored(raw, torch.full_like(raw, 0.001), color_indices("RGGB"))
    torch.testing.assert_close(a, b, rtol=0, atol=0)


def test_policy_rejects_an_unrelated_backbone():
    with pytest.raises(ValueError, match="middle skips"):
        JointDemosaic(ModelConfig(rgb_middle_skip_fp32=True))
