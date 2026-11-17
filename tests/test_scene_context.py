"""True CFA preview colours, whole-scene coordinates, padding and query gradients."""

import numpy as np
import pytest
import torch

from demosaic.color import render
from demosaic.neural_nuisance import masked_packed_input
from demosaic.scene_context import SceneGrid, sample_scene_features, scene_preview


@pytest.mark.parametrize("colors", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
def test_scene_preview_preserves_CFA_calibration_and_aspect_without_clean_input(colors):
    packed = (
        torch.tensor([0.1, 0.2, 0.3])[torch.tensor(colors), None, None].expand(4, 60, 100).clone()
    )
    greens = [i for i, c in enumerate(colors) if c == 1]
    packed[greens[0]] += 0.01
    packed[greens[1]] -= 0.01
    wb, matrix = [1.3, 1, 1.6], torch.eye(3)
    preview, grid = scene_preview(packed, colors, wb, matrix, long_side=50, exposure=2)
    expected = render(
        torch.tensor([0.1, 0.2, 0.3])[None, :, None, None] * 2, torch.tensor(wb)[None], matrix[None]
    )
    torch.testing.assert_close(preview, expected.expand(1, 3, 30, 50))
    assert grid == SceneGrid((120, 200), (30, 50), (32, 64))
    assert scene_preview(packed, colors, wb, matrix)[0].shape[-2:] == (60, 100)


def test_A_only_scene_preview_cannot_read_withheld_values():
    rng = np.random.default_rng(41)
    raw = rng.normal(0.04, 0.002, (80, 120)).astype(np.float32)
    mask = rng.random(raw.shape) < 0.5
    first = masked_packed_input(raw, mask)
    raw[~mask] = np.nan
    second = masked_packed_input(raw, mask)
    a = scene_preview(torch.from_numpy(first), [0, 1, 1, 2], [1, 1, 1], torch.eye(3))
    b = scene_preview(torch.from_numpy(second), [0, 1, 1, 2], [1, 1, 1], torch.eye(3))
    torch.testing.assert_close(a[0], b[0], atol=0, rtol=0)


def test_spatial_queries_use_native_boxes_and_do_not_warp_rectangular_padding():
    grid = SceneGrid((600, 1000), (60, 100), (64, 128))
    yy, xx = torch.meshgrid(torch.arange(16), torch.arange(32), indexing="ij")
    feature = torch.stack(((xx + 0.5) * 4, (yy + 0.5) * 4))[None].double().requires_grad_()
    boxes = [[100, 100, 200, 160], [600, 300, 200, 160]]
    actual = sample_scene_features(feature, grid, 4, boxes, (4, 5))
    for i, (x, y, w, h) in enumerate(boxes):
        expected_x = (x + (torch.arange(5) + 0.5) * w / 5) * 0.1
        expected_y = (y + (torch.arange(4) + 0.5) * h / 4) * 0.1
        torch.testing.assert_close(
            actual[i, 0], expected_x[None].expand(4, -1).double(), atol=1e-12, rtol=0
        )
        torch.testing.assert_close(
            actual[i, 1], expected_y[:, None].expand(-1, 5).double(), atol=1e-12, rtol=0
        )
    actual.sum().backward()
    assert feature.grad.abs().sum() > 0
    batched = torch.cat([sample_scene_features(feature, grid, 4, [b], (4, 5)) for b in boxes])
    torch.testing.assert_close(actual, batched, atol=0, rtol=0)
    with pytest.raises(ValueError, match="inside the scene"):
        sample_scene_features(feature, grid, 4, [[950, 0, 100, 100]], (4, 5))


@pytest.mark.parametrize("dtype", [torch.bfloat16, torch.float16])
def test_large_native_coordinate_queries_use_FP32_even_for_low_precision_features(dtype):
    grid = SceneGrid((6000, 10000), (600, 1000), (608, 1024))
    feature = torch.arange(19 * 32, dtype=torch.float32).reshape(1, 1, 19, 32).to(dtype)
    boxes = [[4970, 2990, 256, 256], [5271, 2001, 257, 283]]
    result = sample_scene_features(feature, grid, 32, boxes, (32, 32))
    expected = sample_scene_features(feature.float(), grid, 32, boxes, (32, 32)).to(dtype)
    torch.testing.assert_close(result, expected, rtol=0, atol=0)
