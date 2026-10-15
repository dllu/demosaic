import json
from pathlib import Path

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, color_indices, malvar, mosaic
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import (
    RgbRestorationTrunk,
    initialize_rgb_prior,
    physical_rgb_features,
)


def config(**kwargs):
    return ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True, **kwargs
    )


def test_physical_features_preserve_original_observations_and_cfa_masks():
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    raw = torch.rand(4, 4, 7, 9) * 0.2 - 0.01
    wb = torch.tensor([1.5, 1.0, 2.0])[None].expand(4, -1)
    _, normalized, noise, condition, offset, span = physical_rgb_features(
        raw, raw.clamp_min(0) * 0.001 + 1e-6, colors, wb
    )
    measured, mask = condition[:, :3], condition[:, 3:6]
    torch.testing.assert_close(mask.sum(1), torch.ones(4, 14, 18))
    torch.testing.assert_close(mosaic(mask, colors), torch.ones_like(raw))
    recovered = measured * span + offset * mask
    torch.testing.assert_close(mosaic(recovered, colors), raw, atol=2e-8, rtol=1e-6)
    assert normalized.shape == (4, 3, 14, 18) and condition.shape[1] == 21
    assert torch.isfinite(noise).all() and (noise >= 0).all()


def test_normalization_and_features_are_independent_of_other_batch_images():
    first = torch.rand(1, 4, 8, 8) * 0.001
    second = torch.rand_like(first) * 50 - 10
    colors = color_indices("GBRG")
    a = physical_rgb_features(first, torch.ones_like(first) * 1e-8, colors)
    b = physical_rgb_features(
        torch.cat((first, second)),
        torch.cat((torch.ones_like(first) * 1e-8, torch.ones_like(second))),
        colors,
    )
    for single, batched in zip(a, b):
        torch.testing.assert_close(single, batched[:1], atol=0, rtol=0)


def test_flat_clipped_and_nearly_constant_noise_scales_remain_bounded():
    raw = torch.ones(2, 4, 8, 8)
    raw[1] = 0.4 + torch.rand_like(raw[1]) * 1e-5
    variance = torch.ones_like(raw) * 1e-3
    _, normalized, noise, condition, _offset, span = physical_rgb_features(
        raw, variance, color_indices("RGGB")
    )
    assert span[0].item() == 1
    assert normalized[0].abs().max() == 0
    assert torch.isfinite(condition).all() and torch.isfinite(noise).all()
    assert noise.max() <= 0.125001
    assert span[1].item() > 0.25


def test_verified_pretrained_topology_matches_original_rgb_inference(tmp_path):
    receipt = Path("docs/results/gaussian-color-joint8-source-and-weights.json")
    metadata = json.loads(receipt.read_text())
    if not Path(metadata["models"][0]["weights"]).exists():
        pytest.skip("External original RGB weights are not installed")
    from demosaic.gaussian import load_gaussian_prior

    original = load_gaussian_prior(receipt)
    model = JointDemosaic(config())
    lineage = initialize_rgb_prior(model, receipt, archive=tmp_path)
    assert lineage["prior"]["weights_sha256"] == metadata["models"][0]["sha256"]
    assert all(p.requires_grad for p in model.pretrained_rgb.network.parameters())
    image = torch.rand(1, 3, 16, 24)
    with torch.no_grad():
        expected = original.network(image, sigma=0.03, norm_equiv=False)
        actual = model.pretrained_rgb.network(image, torch.full_like(image[:, :1], 0.03))
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)


def test_physical_output_keeps_sub_16bit_values_under_autocast():
    class IdentityTrunk(nn.Module):
        def forward(self, rgb, noise, **kwargs):
            return rgb

    model = JointDemosaic(config())
    model.pretrained_rgb.network = IdentityTrunk()
    values = 0.01 + torch.arange(4 * 7 * 9).reshape(1, 4, 7, 9) / 65535
    colors = color_indices("BGGR")
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        actual = model(values, torch.zeros_like(values), colors)
    expected = malvar(values, colors)
    assert actual.dtype == torch.float32
    torch.testing.assert_close(actual, expected, atol=3e-9, rtol=1e-6)
    assert torch.unique(actual).numel() > 256


def test_actual_native_skip_preserves_16bit_ramp_with_bf16_deep_features():
    trunk = RgbRestorationTrunk()
    with torch.no_grad():
        for parameter in trunk.parameters():
            parameter.zero_()
        for channel in range(3):
            trunk.m_head.weight[channel, channel, 1, 1] = 1
            trunk.m_tail.weight[channel, channel, 1, 1] = 1
        ramp = 0.3 + torch.arange(3 * 16 * 24).reshape(1, 3, 16, 24) / 65535
        with torch.autocast("cpu", dtype=torch.bfloat16):
            restored = trunk(ramp, torch.zeros_like(ramp[:, :1]))
    assert restored.dtype == torch.float32
    torch.testing.assert_close(restored, ramp, atol=0, rtol=0)


def test_dino_gradients_auxiliary_and_checkpoint_roundtrip(monkeypatch, tmp_path):
    class FakeContext(nn.Module):
        def __init__(self, cfg, channels):
            super().__init__()
            self.backbone = nn.Conv2d(3, channels, 1).requires_grad_(False)
            self.adapter = nn.Conv2d(channels, channels, 1)
            self.gate = nn.Parameter(torch.zeros(1, channels, 1, 1))

        def forward(self, preview, size):
            with torch.no_grad():
                features = self.backbone(F.interpolate(preview, size=size))
            return self.adapter(features) * self.gate

    monkeypatch.setattr("demosaic.model.DinoContext", FakeContext)
    model = JointDemosaic(config(dino=True))
    colors = torch.stack([color_indices("RGGB"), color_indices("GRBG")])
    raw = torch.rand(2, 4, 7, 9) * 0.2
    prediction, auxiliary = model(raw, torch.ones_like(raw) * 1e-5, colors, auxiliary=True)
    assert prediction.shape == (2, 3, 14, 18)
    torch.testing.assert_close(auxiliary, mosaic(prediction, colors))
    prediction.square().mean().backward()
    assert torch.isfinite(model.pretrained_rgb.network.m_head.weight.grad).all()
    assert model.pretrained_rgb.measurement_adapter.weight.grad.abs().sum() > 0
    assert model.context.gate.grad.abs().sum() > 0
    assert all(p.grad is None for p in model.context.backbone.parameters())
    weights = model.restoration_state_dict()
    assert not any(k.startswith("context.backbone.") for k in weights)
    path = tmp_path / "pretrained.pt"
    torch.save({"model_config": model.config.to_dict(), "model": weights}, path)
    restored, _ = load_checkpoint(path)
    restored.context.backbone.load_state_dict(model.context.backbone.state_dict())
    with torch.no_grad():
        torch.testing.assert_close(restored(raw, torch.ones_like(raw) * 1e-5, colors), prediction)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 32},
        {"noise_modulation": True},
        {"noise_refinement": True},
        {"physical_fp32": False},
    ],
)
def test_invalid_pretrained_branch_configurations_rejected(kwargs):
    values = {"restoration_backbone": "pretrained-rgb", "width": 64, "camera_conditioning": True}
    values.update(kwargs)
    with pytest.raises(ValueError, match="Pretrained RGB"):
        JointDemosaic(ModelConfig(**values))
