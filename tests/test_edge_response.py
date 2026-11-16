import numpy as np
import pytest
import torch

from demosaic.experiments.data.edge_response import edge_observation, render_scene, scene_recipe
from demosaic.experiments.evaluation.edge_response import measure


def test_lower_noise_profile_preserves_exact_targets_and_camera():
    recipe = scene_recipe(1, size=64)
    original, _ = edge_observation(recipe, "far", "GRBG", 0)
    lower, metadata = edge_observation(
        recipe,
        "far",
        "GRBG",
        0,
        condition={"name": "iso400-prior", "shot": 0.00008, "read": 2.56e-8, "exposure": 1.0},
    )
    for key in ["target", "wb", "matrix", "colors", "quiet", "edge_band"]:
        np.testing.assert_array_equal(original[key], lower[key])
    assert lower["variance"].mean() < original["variance"].mean()
    assert metadata["noise"]["name"] == "iso400-prior"


def test_response_scoring_requires_the_actual_increment_not_just_the_shared_edge():
    target, _, masks = render_scene(scene_recipe(0, size=96), "near")
    arrays = dict(target=target.numpy(), **masks)
    exact = measure(arrays, arrays["target"])
    assert exact["strong_gain"] == exact["weak_gain"] == 1
    assert exact["quiet_error_RMS_DN16"] == exact["weak_increment_error_RMS_DN16"] == 0
    unchanged_background = np.broadcast_to(arrays["target"][0:1], arrays["target"].shape)
    absent = measure(arrays, unchanged_background)
    assert absent["strong_gain"] == absent["weak_gain"] == 0
    assert absent["quiet_error_RMS_DN16"] == 0
    assert absent["weak_increment_error_RMS_DN16"] > 0


def test_directional_counterfactuals_and_edge_distance_are_preserved():
    recipe = scene_recipe(0, size=96)
    near, components, masks = render_scene(recipe, "near")
    _far, far_components, far_masks = render_scene(recipe, "far")
    torch.testing.assert_close(near[1] - near[0], components[0], atol=3e-8, rtol=1e-4)
    torch.testing.assert_close(near[2] - near[1], components[1], atol=3e-8, rtol=1e-4)
    torch.testing.assert_close(components, far_components, rtol=0, atol=0)
    assert components[1].square().sum() < components[0].square().sum()
    assert masks["quiet"].sum() > 100 and far_masks["quiet"].sum() > 100
    assert not np.array_equal(masks["edge_band"], far_masks["edge_band"])


@pytest.mark.parametrize("pattern", ["RGGB", "GRBG", "GBRG", "BGGR"])
def test_role_noise_is_independent_repeats_are_fresh_and_global_rng_is_unchanged(pattern):
    recipe = scene_recipe(2, size=64)
    before = torch.get_rng_state().clone()
    first, _ = edge_observation(recipe, "near", pattern, 0)
    second, _ = edge_observation(recipe, "near", pattern, 1)
    replay, _ = edge_observation(recipe, "near", pattern, 0)
    assert torch.equal(before, torch.get_rng_state())
    for k in first:
        np.testing.assert_array_equal(first[k], replay[k])
    np.testing.assert_array_equal(first["target"], second["target"])
    assert not np.array_equal(first["packed"], second["packed"])
    # Sensor sites with exactly identical clean targets still get independent noise.
    quiet = first["quiet"][::2, ::2]
    assert (first["packed"][0, 0][quiet] != first["packed"][1, 0][quiet]).mean() > 0.95
