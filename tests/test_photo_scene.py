"""Keep exact benchmark measurements, CFA phase and targets separate from context."""

import pytest
import torch

from demosaic.cfa import PATTERNS
from demosaic.photo_scene import benchmark_photo_context
from demosaic.scene_data import SceneRecipe, observe_scene
from demosaic.suite import observation


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("xy", [(0, 0), (1, 0), (0, 1), (1, 1)])
def test_actual_canonical_measurements_and_cfa_frame_preserved(pattern, xy):
    rgb = torch.rand(3, 67, 93, generator=torch.Generator().manual_seed(90))
    x, y = xy
    condition = {"name": "test-positive-noise", "shot": 0.001, "read": 1e-6, "exposure": 0.125}
    canonical = observation(
        rgb[None, :, y : y + 32, x : x + 32],
        ["source"],
        condition,
        pattern,
        [2, 1, 1.5],
        torch.eye(3).tolist(),
        42,
    )
    # A deliberately nonstandard original variance proves we preserve it instead
    # of silently recomputing the scored input with a different physical kernel.
    canonical["variance"].add_(0.0002)
    state = torch.get_rng_state().clone()
    field = benchmark_photo_context(
        rgb, (x, y, 32, 32), canonical, condition, identity="source", seed=7
    )
    assert torch.equal(state, torch.get_rng_state())
    assert field.source_origin_xy == xy and field.box_xywh == (0, 0, 32, 32)
    torch.testing.assert_close(field.packed[:, :16, :16], canonical["packed"][0], atol=0, rtol=0)
    torch.testing.assert_close(
        field.variance[:, :16, :16], canonical["variance"][0], atol=0, rtol=0
    )
    assert tuple(field.colors.tolist()) == PATTERNS[pattern]
    recipe = SceneRecipe(
        pattern,
        (2, 1, 1.5),
        ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        0.125,
        0.001,
        1e-6,
        0.03,
        field.noise_seed,
    )
    height, width = field.packed.shape[-2:]
    outside = observe_scene(rgb[:, y : y + 2 * height, x : x + 2 * width], recipe)
    torch.testing.assert_close(
        field.packed[:, 16:, 16:], outside.packed[:, 16:, 16:], atol=0, rtol=0
    )
    # A target-only intervention must not change the scene encoder's input.
    canonical["target"].fill_(123)
    replay = benchmark_photo_context(
        rgb, (x, y, 32, 32), canonical, condition, identity="source", seed=7
    )
    torch.testing.assert_close(field.packed, replay.packed, atol=0, rtol=0)


def test_offset_in_large_scene_preserves_source_location_without_resizing():
    rgb = torch.rand(3, 77, 109, generator=torch.Generator().manual_seed(1))
    condition = {"name": "ADC", "shot": 0.0, "read": 0.0, "exposure": 1.0}
    x, y = 41, 33
    crop = observation(
        rgb[None, :, y : y + 32, x : x + 32],
        ["id"],
        condition,
        "GRBG",
        [1, 1, 1],
        torch.eye(3).tolist(),
        42,
    )
    field = benchmark_photo_context(rgb, (x, y, 32, 32), crop, condition, identity="id", seed=42)
    assert field.source_origin_xy == (1, 1) and field.box_xywh == (40, 32, 32, 32)
    torch.testing.assert_close(field.packed[:, 16:32, 20:36], crop["packed"][0], atol=0, rtol=0)
