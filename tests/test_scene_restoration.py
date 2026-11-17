"""Scene/local forward counts, preserved initialization and useful adapter gradients."""

from types import SimpleNamespace

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from demosaic.scene_restoration import EncodedScene, WholeSceneRestorer


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.config = SimpleNamespace(model_type="dinov3_convnext", hidden_sizes=[3] * 4)
        self.calls = 0
        self.anchor = nn.Parameter(torch.ones(()), requires_grad=False)

    def forward(self, pixel_values, output_hidden_states):
        self.calls += 1
        return SimpleNamespace(
            hidden_states=(
                pixel_values,
                *[F.avg_pool2d(pixel_values, stride) for stride in [4, 8, 16, 32]],
            )
        )


class LocalContext(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = Encoder()
        self.register_buffer("mean", torch.zeros(1, 3, 1, 1))
        self.register_buffer("std", torch.ones(1, 3, 1, 1))

    def forward(self, preview, size):
        self.backbone(preview, output_hidden_states=True)
        return (
            preview.new_zeros(len(preview), 128, size[0] * 4, size[1] * 4),
            preview.new_zeros(len(preview), 256, size[0] * 2, size[1] * 2),
            preview.new_zeros(len(preview), 512, *size),
        )


class Trunk(nn.Module):
    rgb_refinement = None

    def forward(self, packed, variance, colors, wb, matrix, context):
        raw = F.interpolate(packed[:, :3], scale_factor=2)
        extra = context(raw, (raw.shape[-2] // 8, raw.shape[-1] // 8))[2]
        return raw + F.interpolate(
            extra[:, :3], size=raw.shape[-2:], mode="bilinear", align_corners=False
        )


class Base(nn.Module):
    def __init__(self):
        super().__init__()
        self.config = SimpleNamespace(
            restoration_backbone="pretrained-rgb",
            rgb_processing_scale=1,
            dino_feature_fusion="convnext-pyramid",
        )
        self.context = LocalContext()
        self.pretrained_rgb = Trunk()

    def forward(self, packed, variance, colors, wb, matrix):
        return self.pretrained_rgb(packed, variance, colors, wb, matrix, context=self.context)


def inputs():
    generator = torch.Generator().manual_seed(40)
    scene = torch.rand(4, 64, 96, generator=generator)
    tiles = torch.stack([scene[:, :16, :16], scene[:, 32:48, 48:64]])
    args = (
        tiles,
        tiles * 0.001,
        torch.tensor([[0, 1, 1, 2]]).expand(2, -1),
        torch.ones(2, 3),
        torch.eye(3)[None].expand(2, -1, -1),
    )
    return scene, args, [[0, 0, 32, 32], [96, 64, 32, 32]]


@pytest.mark.parametrize("mode", ["pooled", "spatial"])
def test_heterogeneous_scenes_keep_crop_assignment_and_original_local_batch(mode):
    model = WholeSceneRestorer(Base(), mode=mode, adapter_width=4).eval()
    raw, args, _ = inputs()
    other = torch.rand(4, 80, 128, generator=torch.Generator().manual_seed(222))
    scenes = [model.encode_scene(r, args[2][0], args[3][0], args[4][0]) for r in [raw, other]]
    with torch.no_grad():
        model.adapter.output.weight.fill_(0.12)
    boxes = [[0, 0, 32, 32], [0, 0, 32, 32]]
    before = model.base.context.backbone.calls
    actual = model(*args, scene=scenes, boxes_xywh=boxes)
    assert model.base.context.backbone.calls == before + 1
    expected = torch.cat(
        [
            model(*(v[i : i + 1] for v in args), scene=scenes[i], boxes_xywh=[boxes[i]])
            for i in range(2)
        ]
    )
    torch.testing.assert_close(actual, expected, atol=1e-6, rtol=1e-6)
    swapped = model(*args, scene=scenes[::-1], boxes_xywh=boxes)
    assert (actual - swapped).abs().max() > 1e-4


def test_reject_missing_scene_assignment_before_local_encoder():
    model = WholeSceneRestorer(Base(), mode="spatial", adapter_width=4)
    raw, args, boxes = inputs()
    encoded = model.encode_scene(raw, args[2][0], args[3][0], args[4][0])
    before = model.base.context.backbone.calls
    with pytest.raises(ValueError, match="one encoded scene per"):
        model(*args, scene=[encoded], boxes_xywh=boxes)
    assert model.base.context.backbone.calls == before


@pytest.mark.parametrize("mode", ["none", "pooled", "spatial"])
def test_zero_initialization_preserves_base_and_retains_local_encoder(mode):
    model = WholeSceneRestorer(Base(), mode=mode, adapter_width=4)
    raw, args, boxes = inputs()
    encoded = model.encode_scene(raw, args[2][0], args[3][0], args[4][0])
    assert model.base.context.backbone.calls == 1
    actual = model(*args, scene=encoded, boxes_xywh=boxes)
    assert model.base.context.backbone.calls == 2
    torch.testing.assert_close(actual, model.base(*args), atol=0, rtol=0)
    assert all(not f.requires_grad for f in encoded.features)


def test_adapter_learns_and_spatial_context_uses_coordinates_without_reencoding():
    torch.manual_seed(81)
    model = WholeSceneRestorer(Base(), mode="spatial", adapter_width=4)
    raw, args, boxes = inputs()
    encoded = model.encode_scene(raw, args[2][0], args[3][0], args[4][0])
    optimizer = torch.optim.SGD(model.adapter.parameters(), lr=0.1)
    for _ in range(2):
        optimizer.zero_grad()
        output = model(*args, scene=encoded, boxes_xywh=boxes)
        (output - 1).square().mean().backward()
        assert model.adapter.output.weight.grad.abs().sum() > 0
        optimizer.step()
    assert model.adapter.projections[0].weight.grad.abs().sum() > 0
    assert model.base.context.backbone.calls == 3  # one scene, two crop forwards
    a = model.adapter(encoded, boxes, (4, 4), mode="spatial")
    b = model.adapter(encoded, list(reversed(boxes)), (4, 4), mode="spatial")
    torch.testing.assert_close(a.flip(0), b, atol=0, rtol=0)
    assert (a - b).abs().max() > 1e-7
    pooled = model.adapter(encoded, boxes, (4, 4), mode="pooled")
    torch.testing.assert_close(pooled[0], pooled[1], atol=0, rtol=0)
    shuffled = EncodedScene(tuple(f.flip(-1) for f in encoded.features), encoded.grid)
    assert (model.adapter(shuffled, boxes, (4, 4), mode="spatial") - a).abs().max() > 1e-7
    with pytest.raises(ValueError, match="matching native crops"):
        model(*args, scene=encoded, boxes_xywh=[[0, 0, 64, 64], [96, 64, 32, 32]])
