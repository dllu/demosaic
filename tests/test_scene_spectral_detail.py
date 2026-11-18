"""Phase-safe conditioning of measured spectral proposals."""

import torch

from demosaic.late_spectral_detail import LateSpectralDetail
from demosaic.scene_context import SceneGrid
from demosaic.scene_restoration import EncodedScene
from demosaic.scene_spectral_detail import SceneSpectralDetail


def fixture():
    generator = torch.Generator().manual_seed(2701)
    packed = torch.rand(2, 4, 16, 24, generator=generator) * 0.05 + 0.12
    variance = packed * 0.001 + 1e-6
    base = torch.full((2, 3, 32, 48), 0.15)
    colors = torch.tensor([[0, 1, 1, 2], [1, 2, 0, 1]])
    features = tuple(
        torch.rand((1, 3, 64 // stride, 64 // stride), generator=generator)
        for stride in (4, 8, 16, 32)
    )
    scene = EncodedScene(features, SceneGrid((128, 128), (64, 64), (64, 64)))
    return (base, packed, variance, colors), scene, [(0, 0, 48, 32), (48, 32, 48, 32)]


def test_context_scale_preserves_inherited_initial_gain_and_parent():
    args, scene, boxes = fixture()
    head = SceneSpectralDetail([3] * 4, max_window=8)
    actual = head(*args, scene=scene, boxes_xywh=boxes, mode="spatial")
    torch.testing.assert_close(actual, args[0], atol=0, rtol=0)
    with torch.no_grad():
        head.frequency_out.bias.fill_(0.25)
    bare = LateSpectralDetail(max_window=8)
    bare.load_state_dict(
        {k: v for k, v in head.state_dict().items() if not k.startswith("scene_adapter.")}
    )
    actual = head(*args, scene=scene, boxes_xywh=boxes, mode="pooled")
    torch.testing.assert_close(actual, bare(*args), atol=0, rtol=0)


def test_spatial_gain_changes_strength_without_drawing_a_pattern_on_constant_raw():
    args, scene, boxes = fixture()
    head = SceneSpectralDetail([3] * 4, max_window=8)
    with torch.no_grad():
        head.scene_adapter.output.weight.fill_(0.12)
        head.scene_adapter.output.bias[:] = torch.tensor([-0.5, 0.5])
        head.frequency_out.bias.fill_(0.25)
    scale = head.frame_scale(args[1], scene, boxes, "spatial")
    swapped = head.frame_scale(args[1], scene, list(reversed(boxes)), "spatial")
    pooled = head.frame_scale(args[1], scene, boxes, "pooled")
    reverse = (-torch.arange(8)) % 8
    torch.testing.assert_close(scale.index_select(-2, reverse).index_select(-1, reverse), scale)
    assert scale.min() > 0.25 and scale.max() < 1.75
    assert not torch.equal(scale, swapped)
    assert torch.equal(*pooled.chunk(2))
    base, packed, variance, colors = args
    raw_flat = packed[..., :1, :1].expand_as(packed)
    actual = head(base, raw_flat, variance, colors, scene=scene, boxes_xywh=boxes, mode="spatial")
    torch.testing.assert_close(actual, base, atol=0, rtol=0)
    output = head(*args, scene=scene, boxes_xywh=boxes, mode="spatial")
    (output - 0.2).square().mean().backward()
    assert head.scene_adapter.output.weight.grad.abs().sum() > 0
