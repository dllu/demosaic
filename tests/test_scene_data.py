"""Exact same-observation/crop CFA alignment, signed read samples and RNG isolation."""

from dataclasses import replace
from unittest.mock import patch

import pytest
import torch

from demosaic.cfa import PATTERNS, mosaic
from demosaic.scene_context import scene_preview
from demosaic.scene_data import observe_scene, sample_scene_recipe, scene_crop_boxes


@pytest.mark.parametrize("pattern", list(PATTERNS))
def test_scene_and_crops_share_one_actual_sensor_draw_and_correct_CFA(pattern):
    rgb = torch.rand((3, 80, 120), generator=torch.Generator().manual_seed(41)) * 0.1
    recipe = replace(sample_scene_recipe(92), pattern=pattern, exposure=1.0, shot=0.0003, read=1e-6)
    from demosaic.noise import add_noise

    with patch("demosaic.scene_data.add_noise", wraps=add_noise) as draw:
        scene = observe_scene(rgb, recipe)
        boxes = scene_crop_boxes((80, 120), patch_size=32, count=5, seed=19)
        crops = scene.crops(boxes)
        scene_preview(scene.packed, scene.colors, scene.wb, scene.matrix, long_side=24)
        assert draw.call_count == 1
    for i, (x, y, w, h) in enumerate(boxes):
        torch.testing.assert_close(
            crops["packed"][i],
            scene.packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
            rtol=0,
            atol=0,
        )
        torch.testing.assert_close(
            crops["variance"][i],
            scene.variance[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
            rtol=0,
            atol=0,
        )
        expected = mosaic(scene.sensor_target[None], scene.colors)[0][
            :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2
        ]
        torch.testing.assert_close(
            mosaic(crops["sensor_target"][i : i + 1], crops["colors"][i])[0],
            expected,
            rtol=0,
            atol=0,
        )
    again = observe_scene(rgb, recipe)
    torch.testing.assert_close(scene.packed, again.packed, rtol=0, atol=0)
    with pytest.raises(ValueError, match="even native boxes"):
        scene.crops([[1, 0, 32, 32]])


def test_recipe_and_sensor_generators_do_not_consume_global_RNG_and_keep_signed_read_noise():
    state = torch.get_rng_state().clone()
    a = sample_scene_recipe(501)
    assert a == sample_scene_recipe(501) and a != sample_scene_recipe(502)
    rgb = torch.zeros(3, 64, 96)
    recipe = replace(a, shot=0.0, read=1e-5, black=0.05)
    scene = observe_scene(rgb, recipe)
    assert (scene.packed < 0).any() and (scene.packed > 0).any()
    torch.testing.assert_close(torch.get_rng_state(), state, rtol=0, atol=0)
    assert (scene.variance == recipe.read).all()


def test_clean_targets_cannot_change_an_already_constructed_preview_or_noisy_crops():
    scene = observe_scene(torch.full((3, 80, 120), 0.03), sample_scene_recipe(51))
    original, _ = scene_preview(scene.packed, scene.colors, scene.wb, scene.matrix)
    changed = replace(
        scene,
        target=torch.full_like(scene.target, float("nan")),
        sensor_target=torch.full_like(scene.sensor_target, float("nan")),
    )
    repeated, _ = scene_preview(changed.packed, changed.colors, changed.wb, changed.matrix)
    torch.testing.assert_close(original, repeated, rtol=0, atol=0)
    boxes = scene_crop_boxes((80, 120), patch_size=32, seed=73)
    torch.testing.assert_close(
        scene.crops(boxes)["packed"], changed.crops(boxes)["packed"], rtol=0, atol=0
    )
