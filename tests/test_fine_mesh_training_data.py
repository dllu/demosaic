"""Independent recipe transport and exact physical/counterfactual preservation."""

import copy
import random

import numpy as np
import pytest
import torch
from fine_mesh_training_data import (
    CONTRAST_EDGES, edit_recipe, edited_observation, render_recipe, selected_mesh_batch,
)
from paired_response_data import source_batch
from test_paired_response_data import config

from demosaic.textures import crossed_line_texture


@pytest.mark.parametrize("seed", [0, 1, 7, 21, 167])
@pytest.mark.parametrize("present", [False, True])
def test_recipe_renderer_replays_original_pixels_without_rng(seed, present):
    expected, recipe = crossed_line_texture(96, random.Random(seed), pixel_scale=2, present=present)
    before_torch, before_python = torch.get_rng_state().clone(), random.getstate()
    actual, measured = render_recipe(recipe)
    assert torch.equal(actual, expected) and measured == recipe
    assert torch.equal(before_torch, torch.get_rng_state()) and before_python == random.getstate()


@pytest.mark.parametrize("ordinal", range(0, 8, 2))
@pytest.mark.parametrize("pair", [0, 1])
def test_quantile_transport_matches_independent_log_affine_formula(ordinal, pair):
    recipe = crossed_line_texture(32, random.Random(312), present=True)[1]
    before = copy.deepcopy(recipe)
    edited = edit_recipe(recipe, ordinal, pair)
    band = ((ordinal // 2) * 2 + pair) % 4
    q = (np.log(recipe["periods_final_pixels"]) - np.log(6)) / (np.log(32) - np.log(6))
    expected = np.exp(np.log(6) + q * (np.log(10) - np.log(6)))
    np.testing.assert_allclose(edited["periods_final_pixels"], expected, rtol=3e-16)
    lo, hi = CONTRAST_EDGES[band : band + 2]
    c = recipe["requested_peak_relative_contrast"]
    expected = np.exp(np.log(lo) + (np.log(c)-np.log(.005))/(np.log(.2)-np.log(.005))*(np.log(hi)-np.log(lo)))
    assert abs(edited["requested_peak_relative_contrast"] - expected) < 1e-15
    assert recipe == before and lo <= edited["requested_peak_relative_contrast"] <= hi
    assert all(6 <= v <= 10 for v in edited["periods_final_pixels"])
    for key in ["seed", "level", "tint", "contrast_direction", "background_slope", "angles_radians", "phases_cycles", "wire_sigma_final_pixels", "mask_center_final_pixels", "mask_radii_final_pixels"]:
        assert recipe[key] == edited[key]


def test_schedule_keeps_half_legacy_and_balances_all_four_bands():
    selected = [i for i in range(341) if selected_mesh_batch(i)]
    assert len(selected) == 171
    counts = np.bincount([((i // 2) * 2 + p) % 4 for i in selected for p in range(2)])
    np.testing.assert_array_equal(counts, [86, 86, 85, 85])
    for invalid in [-1, True, 1.0]:
        with pytest.raises(ValueError):
            selected_mesh_batch(invalid)


@pytest.mark.parametrize("adc", [False, True])
def test_edited_sensor_batch_keeps_exact_background_camera_noise_and_global_rng(adc):
    cfg = config()
    if adc:
        cfg["first_ten_domains"][2] = "mesh"
    step = 3 if adc else 1
    original, meta = source_batch(cfg, None, step)
    item = {"step": step, "metadata": meta}
    before_torch, before_python = torch.get_rng_state().clone(), random.getstate()
    changed, observed = edited_observation(item, original, 0)
    assert observed["noise"] == meta["noise"] and observed["sensor"]["seed"] == meta["sensor"]["seed"]
    assert observed["sensor"]["sampler_calls"] == {"Poisson": 3, "Gaussian": 1}
    for key in ["target", "matrix", "wb", "colors"]:
        np.testing.assert_array_equal(changed[key][1::2], original[key][1::2])
    assert np.any(changed["target"][::2] != original["target"][::2])
    assert np.array_equal(changed["pair_indices"], [[0, 1], [2, 3]])
    # Exact clean sensor reconstruction from the saved target, independent Bayer slicing.
    for parity, field in [(0, "clean_packed_a"), (1, "clean_packed_b")]:
        clean = np.stack([np.stack([rgb[int(color), k//2::2, k%2::2] for k, color in enumerate(colors)])
                          for rgb, colors in zip(changed["target"][parity::2], changed["colors"][parity::2], strict=True)])
        from demosaic.prediction_archive import fingerprint
        assert fingerprint(clean) == observed["sensor"][field]
    assert torch.equal(before_torch, torch.get_rng_state()) and before_python == random.getstate()


def test_new_contrast_keeps_same_positive_empty_canvas_and_bounded_signal():
    for seed in range(20):
        _, old = crossed_line_texture(64, random.Random(seed), present=True)
        new = edit_recipe(old, 2, 1)  # Highest contrast band.
        a, _ = render_recipe(new)
        b, _ = render_recipe(dict(new, present=False))
        empty, _ = render_recipe(dict(old, present=False))
        assert torch.equal(b, empty) and a.min() >= 0
        assert (a-b).abs().max() <= new["level"] * .4 * (1+1e-6)
