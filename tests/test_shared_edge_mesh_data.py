"""Shared nuisance structure, weak increments, calibration and sensor contracts."""

import copy
import random

import numpy as np
import pytest
import torch
from coherent_pair_objective import paired_coherent_response_loss
from paired_response_counters import count_source_draws
from paired_response_data import source_batch
from shared_edge_mesh_data import pair_recipe, render_pair, shared_edge_observation
from test_paired_response_data import config

from demosaic.cfa import PATTERNS
from demosaic.data import augment_before_downsample
from demosaic.prediction_archive import fingerprint


def old_mixed(*, adc=False):
    cfg = config()
    cfg["domain_sizes"] = {k: 64 for k in cfg["domain_sizes"]}
    if adc:
        cfg["first_ten_domains"][2] = "mixed"
    step = 3 if adc else 4
    arrays, metadata = source_batch(cfg, None, step)
    return {"step": step, "metadata": metadata}, arrays


@pytest.mark.parametrize("index", range(8))
def test_geometry_keeps_common_edges_and_transports_only_weak_increment(index):
    recipe = pair_recipe(64, 4, index // 2, index % 2)
    raw_a, raw_b, _ = render_pair(recipe, augment=False)
    a, b, measured = render_pair(recipe)
    delta = augment_before_downsample(
        raw_a - raw_b, 64, random.Random(recipe["geometry_seed"]), optical_blur_probability=0.0
    )
    torch.testing.assert_close(a - b, delta, rtol=2e-3, atol=1e-7)
    assert a.min() >= 0 and a.max() < 1
    if not recipe["mesh"]["present"]:
        assert torch.equal(a, b) and measured["peak_relative_contrast"] == 0
    else:
        assert (a - b).abs().max() > 0
        assert ((a - b).abs().sum(0) == 0).sum() > 64**2 // 5
    # Shared broad scene has a genuine edge; it is not a constant replacement.
    gradient = max(float(b.diff(dim=-1).abs().max()), float(b.diff(dim=-2).abs().max()))
    assert gradient > 0.001


@pytest.mark.parametrize("pattern", list(PATTERNS))
@pytest.mark.parametrize("adc", [False, True])
def test_new_pairs_keep_camera_CFA_noise_and_exact_unmodified_sensor_pixels(pattern, adc):
    item, old = old_mixed(adc=adc)
    old["colors"][:] = PATTERNS[pattern]
    before = copy.deepcopy(item)
    torch_rng, python_rng = torch.get_rng_state().clone(), random.getstate()
    numpy_rng = np.random.get_state()
    with count_source_draws() as calls:
        a, metadata = shared_edge_observation(item, old, 0)
    assert item == before
    assert metadata["noise"] == item["metadata"]["noise"]
    assert metadata["coupled_pairs"] == 2
    assert calls == {
        "sensor_Poisson": 3,
        "sensor_Gaussian": 1,
        "procedural_Poisson": 0,
        "procedural_Gaussian": 0,
        "coupled_sensor_calls": 1,
        "ordinary_sensor_calls": 0,
    }
    for field in ["wb", "matrix", "colors"]:
        np.testing.assert_array_equal(a[field], old[field][[0, 0, 2, 2]])
    np.testing.assert_array_equal(a["pair_indices"], [[0, 1], [2, 3]])
    clean = []
    for parity, key in [(0, "clean_packed_a"), (1, "clean_packed_b")]:
        packed = np.stack(
            [
                np.stack([rgb[int(c), k // 2 :: 2, k % 2 :: 2] for k, c in enumerate(colors)])
                for rgb, colors in zip(a["target"][parity::2], a["colors"][parity::2], strict=True)
            ]
        )
        assert fingerprint(packed) == metadata["sensor"][key]
        clean.append(packed)
    for pair in range(2):
        unchanged = clean[0][pair] == clean[1][pair]
        assert unchanged.sum() > unchanged.size // 5
        np.testing.assert_array_equal(
            a["packed"][2 * pair][unchanged], a["packed"][2 * pair + 1][unchanged]
        )
    expected_units = np.maximum(
        np.sqrt(
            np.mean(
                metadata["noise"]["shot"] * np.abs(clean[0].astype(np.float64) - clean[1]),
                axis=(1, 2, 3),
            )
        ),
        16 / 65535,
    )
    np.testing.assert_allclose(a["pair_units"].reshape(-1), expected_units, rtol=3e-7, atol=1e-12)
    # The deterministic no-increment control remains exactly the same observation.
    np.testing.assert_array_equal(a["target"][0], a["target"][1])
    np.testing.assert_array_equal(a["packed"][0], a["packed"][1])
    assert torch.equal(torch_rng, torch.get_rng_state()) and python_rng == random.getstate()
    after = np.random.get_state()
    assert numpy_rng[0] == after[0] and numpy_rng[2:] == after[2:]
    np.testing.assert_array_equal(numpy_rng[1], after[1])


def test_broad_edge_alone_cannot_satisfy_new_pair_response_target():
    item, old = old_mixed()
    a, _ = shared_edge_observation(item, old, 1)
    target = torch.from_numpy(a["target"])
    edge_only = target.clone()
    edge_only[::2] = target[1::2]
    edge_only.requires_grad_(True)
    pairs = torch.from_numpy(a["pair_indices"])
    loss = paired_coherent_response_loss(edge_only, target, pairs)
    assert loss > 0
    loss.backward()
    assert edge_only.grad.abs().max() > 0
    assert paired_coherent_response_loss(target, target, pairs) == 0


def test_no_increment_schedule_retains_controls_and_both_period_ranges():
    recipes = [pair_recipe(64, 4 + n, n // 2, n % 2) for n in range(20)]
    assert sum(not r["mesh"]["present"] for r in recipes) == 4
    assert {r["background"]["kind"] for r in recipes} == {
        "vertical-step",
        "bar",
        "slanted-step",
        "corner",
    }
    assert {r["placement_relative_to_edge"] for r in recipes} == {
        "negative-side",
        "at-edge",
        "positive-side",
    }


def test_non_mixed_rows_and_corrupt_calibration_rejected():
    item, old = old_mixed()
    item["metadata"]["domain"] = "photo"
    with pytest.raises(ValueError, match="mixed"):
        shared_edge_observation(item, old, 0)
    item["metadata"]["domain"] = "mixed"
    old["wb"][0, 0] += 0.1
    with pytest.raises(AssertionError):
        shared_edge_observation(item, old, 0)
