import hashlib
import importlib.util
from pathlib import Path

import pytest
import torch
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic


def packed_config(**kwargs):
    return ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True,
        variance_stabilization=True, physical_anchors=True, rgb_processing_scale=2,
        **kwargs,
    )


class IdentityTrunk(nn.Module):
    def forward(self, rgb, noise, *, return_features=False, **kwargs):
        if return_features:
            return rgb, rgb.new_zeros(len(rgb), 64, *rgb.shape[-2:])
        return rgb


@pytest.mark.parametrize("stabilized,anchors", [(False, False), (True, False), (True, True)])
def test_default_matches_original_source_with_same_weights_and_observation(stabilized, anchors):
    legacy_path = Path(__file__).parent / "fixtures" / "pretrained_rgb_legacy.py"
    assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == (
        "b1ad94724e2732a1d61ae43ed03406d8b468e2548ab606d5eb7e37b58c617031"
    )
    spec = importlib.util.spec_from_file_location("demosaic.legacy_rgb", legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    torch.manual_seed(77)
    old = legacy.PretrainedRgbDemosaic(stabilized=stabilized, physical_anchors=anchors)
    new = PretrainedRgbDemosaic(stabilized=stabilized, physical_anchors=anchors)
    new.load_state_dict(old.state_dict(), strict=True)
    assert old.state_dict().keys() == new.state_dict().keys()
    raw = torch.rand(2, 4, 7, 9) * .1
    colors = torch.stack([color_indices("RGGB"), color_indices("GBRG")])
    wb = torch.tensor([[2., 1., 1.5], [1.4, 1., 2.2]])
    matrix = torch.eye(3)[None].expand(2, -1, -1)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        old.set_noise([.001, .002], [1e-6, 2e-6])
        new.set_noise([.001, .002], [1e-6, 2e-6])
        expected = old(raw, torch.ones_like(raw), colors, wb, matrix)
        actual = new(raw, torch.ones_like(raw), colors, wb, matrix)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_native_ramp_survives_zero_corrections_and_nonmultiple_dimensions(pattern):
    model = JointDemosaic(packed_config())
    model.pretrained_rgb.network = IdentityTrunk()
    raw = .3 + torch.arange(4 * 9 * 13).reshape(1, 4, 9, 13) / 65535
    colors = color_indices(pattern)
    model.set_noise(0, 0)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        actual = model(raw, torch.zeros_like(raw), colors)
    expected = malvar(raw, colors)
    assert actual.shape == (1, 3, 18, 26) and actual.dtype == torch.float32
    assert torch.unique(actual).numel() > 256
    torch.testing.assert_close(actual, expected, rtol=0, atol=1 / 65535 / 8)


def test_phase_head_receives_unaveraged_measurements_and_routes_individual_pixels():
    model = JointDemosaic(packed_config())
    branch = model.pretrained_rgb
    branch.network = IdentityTrunk()
    model.set_noise(0, 0)
    raw = torch.rand(1, 4, 9, 13) * .2
    colors = color_indices("RGGB")
    with torch.no_grad():
        before = model(raw, torch.zeros_like(raw), colors)
        # Green BR output receives the original TL measurement; feature64 is
        # the first of the four separate CFA values, before12 phase labels.
        branch.phase_head.weight[7, 64, 1, 1] = .01
        after = model(raw, torch.zeros_like(raw), colors)
    difference = after - before
    expected = torch.zeros_like(difference)
    offset = malvar(raw, colors).amin()
    expected[:, 1, 1::2, 1::2] = .01 * (raw[:, 0] - offset)
    torch.testing.assert_close(difference, expected, atol=3e-8, rtol=1e-4)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_pooled_noise_gain_matches_gaussian_monte_carlo_with_white_balance(pattern):
    branch = PretrainedRgbDemosaic(stabilized=True, processing_scale=2)
    colors = color_indices(pattern)[None]
    balance = torch.tensor([[2., 1., 1.5]])
    predicted_variance = branch.pooled_noise_gain(colors, balance).square().item()
    torch.manual_seed(445)
    samples = torch.randn(8192, 4, 3, 3)
    observed = malvar(samples, colors.expand(len(samples), -1), balance)
    observed = observed[..., 2:4, 2:4].mean((-2, -1))
    empirical = observed.var(0, unbiased=True).mean().item()
    assert abs(empirical / predicted_variance - 1) < .05
    unit = branch.pooled_noise_gain(colors, torch.ones(1, 3)).item()
    assert abs(unit - .6564979553222656) < 1e-7


def test_real_trunk_backpropagates_to_both_phase_modules_and_roundtrips(tmp_path):
    model = JointDemosaic(packed_config()).to(memory_format=torch.channels_last)
    model.set_noise(0, 1e-6)
    raw = torch.rand(1, 4, 9, 13) * .2
    prediction = model(raw, torch.ones_like(raw) * 1e-6, color_indices("BGGR"))
    prediction.square().mean().backward()
    for module in [model.pretrained_rgb.phase_adapter, model.pretrained_rgb.phase_head]:
        assert torch.isfinite(module.weight.grad).all() and module.weight.grad.abs().sum() > 0
    from demosaic.inference import load_checkpoint

    path = tmp_path / "packed.pt"
    torch.save({"model_config": model.config.to_dict(), "model": model.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    restored.to(memory_format=torch.channels_last)
    restored.set_noise(0, 1e-6)
    with torch.no_grad():
        actual = restored(raw, torch.ones_like(raw) * 1e-6, color_indices("BGGR"))
    torch.testing.assert_close(actual, prediction, rtol=0, atol=0)


@pytest.mark.parametrize("values", [{"rgb_processing_scale": 3}, {"rgb_processing_scale": 2}])
def test_invalid_scale_or_unstabilized_model_rejected(values):
    with pytest.raises(ValueError):
        JointDemosaic(ModelConfig(**values))
