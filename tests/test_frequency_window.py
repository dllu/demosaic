import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_frequency_features import (
    RawFrequencyFeatures,
    require_resume_frequency_window,
)


@pytest.mark.parametrize("value", [True, 0, 3, 96, 512, 128.0, None])
def test_invalid_window_rejects_before_constructing_a_model(value):
    with pytest.raises(ValueError, match="frequency window"):
        JointDemosaic(ModelConfig(raw_frequency_window=value))


def test_nondefault_window_requires_the_branch_and_legacy_defaults_remain_64():
    assert ModelConfig.from_checkpoint({}).raw_frequency_window == 64
    with pytest.raises(ValueError, match="requires frequency features"):
        JointDemosaic(ModelConfig(raw_frequency_window=128))
    require_resume_frequency_window({}, {"model": {"raw_frequency_window": 64}})


def test_changed_geometry_rejects_resume_even_though_weight_shapes_match():
    first = RawFrequencyFeatures(64)
    second = RawFrequencyFeatures(128)
    second.load_state_dict(first.state_dict(), strict=True)
    with pytest.raises(ValueError, match="Resume RAW frequency window differs"):
        require_resume_frequency_window({}, {"model": {"raw_frequency_window": 128}})


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("window", [128, 256])
def test_large_learned_window_preserves_colored_spatial_constants(pattern, window):
    branch = RawFrequencyFeatures(window)
    generator = torch.Generator().manual_seed(146)
    with torch.no_grad():
        for parameter in branch.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.1)
    colors = color_indices(pattern)
    raw = torch.tensor([0.03, 0.02, 0.01])[colors][None, :, None, None].expand(
        1, 4, window, window + 8
    )
    result = branch(raw, torch.full_like(raw, 1e-5), colors)
    assert result.shape == (1, 64, 2 * window, 2 * (window + 8))
    assert result.count_nonzero() == 0


@pytest.mark.parametrize("small_window,large_window", [(64, 128), (128, 256)])
def test_larger_context_changes_learned_output_but_not_initial_output_or_rng(
    small_window, large_window
):
    before = torch.get_rng_state()
    small, large = RawFrequencyFeatures(small_window), RawFrequencyFeatures(large_window)
    assert torch.equal(before, torch.get_rng_state())
    generator = torch.Generator().manual_seed(147)
    raw = torch.rand(1, 4, large_window, large_window, generator=generator) * 0.01
    variance = torch.full_like(raw, 1e-5)
    colors = color_indices("RGGB")
    assert small(raw, variance, colors).count_nonzero() == 0
    assert large(raw, variance, colors).count_nonzero() == 0
    with torch.no_grad():
        large.project.weight.copy_(torch.randn(large.project.weight.shape, generator=generator))
        small.load_state_dict(large.state_dict(), strict=True)
    assert not torch.equal(small(raw, variance, colors), large(raw, variance, colors))
    assert torch.equal(before, torch.get_rng_state())


@pytest.mark.parametrize("window", [128, 256])
def test_large_window_is_serialized_and_reconstructed_by_inference(tmp_path, window):
    cfg = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
        raw_frequency_features=True,
        raw_frequency_window=window,
    )
    model = JointDemosaic(cfg)
    path = tmp_path / "large-window.pt"
    torch.save({"model_config": cfg.to_dict(), "model": model.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.raw_frequency_window == window
    assert restored.pretrained_rgb.raw_frequency.max_window == window
    assert all(
        torch.equal(value, restored.restoration_state_dict()[name])
        for name, value in model.restoration_state_dict().items()
    )
