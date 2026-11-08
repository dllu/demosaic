"""Fresh realizations, physical moments, independent CFA and rejection checks."""

import copy

import numpy as np
import pytest
import torch
from renoise_cached_training import clean_sensor, noise_seed, renoise

from demosaic.prediction_archive import fingerprint


def fixture(paired=True, size=64):
    target = np.full((4, 3, size, size), 0.02, np.float32)
    target[::2, :, 16:48, 16:48] += 0.002
    colors = np.array([[0, 1, 1, 2], [0, 1, 1, 2], [2, 1, 1, 0], [2, 1, 1, 0]], np.int64)
    clean = np.stack(
        [
            np.stack([rgb[int(c), k // 2 :: 2, k % 2 :: 2] for k, c in enumerate(layout)])
            for rgb, layout in zip(target, colors, strict=True)
        ]
    )
    pairs = np.array([[0, 1], [2, 3]], np.int64) if paired else np.empty((0, 2), np.int64)
    a = {
        "target": target,
        "colors": colors,
        "packed": clean.copy(),
        "variance": np.zeros_like(clean),
        "wb": np.ones((4, 3), np.float32),
        "matrix": np.tile(np.eye(3, dtype=np.float32), (4, 1, 1)),
        "pair_indices": pairs,
        "pair_units": np.full((len(pairs), 1, 1, 1), 16 / 65535, np.float32),
    }
    m = {
        "noise": {"shot": 0.00128, "read": 6.5536e-6},
        "sensor": {
            "black_level": 0.03,
            "bit_depth": 16,
            "clean_packed_a": fingerprint(clean[::2]),
            "clean_packed_b": fingerprint(clean[1::2]),
        },
    }
    return a, m, clean


@pytest.mark.parametrize("paired", [True, False])
def test_only_RAW_and_noisy_variance_change_with_distinct_reproducible_local_seed(paired):
    a, m, expected = fixture(paired)
    np.testing.assert_array_equal(clean_sensor(a, m), expected)
    before = {k: v.copy() for k, v in a.items()}
    rng = torch.get_rng_state().clone()
    x, record = renoise(a, m, 1, 1)
    y, other = renoise(a, m, 1, 1)
    z, third = renoise(a, m, 1001, 1)
    assert record == other and record["seed"] != third["seed"]
    assert torch.equal(rng, torch.get_rng_state())
    assert record["Poisson_calls"] == (3 if paired else 1) and record["Gaussian_calls"] == 1
    assert not np.array_equal(x["packed"], z["packed"])
    for key in a:
        np.testing.assert_array_equal(a[key], before[key])
        np.testing.assert_array_equal(x[key], y[key])
        if key not in ["packed", "variance"]:
            assert x[key] is a[key]
    np.testing.assert_allclose(
        x["variance"],
        np.maximum(x["packed"], 0).astype(np.float64) * m["noise"]["shot"] + m["noise"]["read"],
        rtol=2e-7,
        atol=1e-12,
    )
    if paired:
        for first, second in a["pair_indices"]:
            mask = expected[first] == expected[second]
            np.testing.assert_array_equal(x["packed"][first][mask], x["packed"][second][mask])


def test_large_unpaired_ADC_samples_have_physical_mean_and_variance():
    a, m, _expected = fixture(False, size=512)
    a["target"][:] = 0.05
    x, _ = renoise(a, m, 2, 2)
    values = x["packed"].astype(np.float64)
    variance = m["noise"]["shot"] * 0.05 + m["noise"]["read"]
    assert abs(values.mean() - 0.05) < 8 * (variance / values.size) ** 0.5
    assert abs(values.var() / variance - 1) < 0.015


def test_ADC_reuses_every_array_without_noise_draws():
    a, m, _ = fixture()
    m["noise"] = {"shot": 0, "read": 0}
    x, record = renoise(a, m, 1, 1)
    assert all(x[k] is a[k] for k in a)
    assert record == {"seed": None, "Poisson_calls": 0, "Gaussian_calls": 0, "ADC_reused": True}


@pytest.mark.parametrize(
    "bad", ["dtype", "nan", "pairs", "camera", "hash", "clipped", "noise", "variance", "black"]
)
def test_bad_inputs_reject_before_any_sensor_draw(monkeypatch, bad):
    import renoise_cached_training as implementation

    a, m, _ = fixture(bad != "clipped")
    m = copy.deepcopy(m)
    if bad == "dtype":
        a["target"] = a["target"].astype(np.float64)
    if bad == "nan":
        a["target"][0, 0, 0, 0] = np.nan
    if bad == "pairs":
        a["pair_indices"][1] = [0, 3]
    if bad == "camera":
        a["wb"][0, 0] = 2
    if bad == "hash":
        m["sensor"]["clean_packed_a"]["sha256"] = "bad"
    if bad == "clipped":
        a["target"][0, 0, 0, 0] = 1
    if bad == "noise":
        m["noise"]["shot"] = -1
    if bad == "variance":
        a["variance"][0, 0, 0, 0] = -1
    if bad == "black":
        m["sensor"]["black_level"] = 0

    def forbidden(*args, **kwargs):
        raise AssertionError("A rejected input drew sensor noise")

    monkeypatch.setattr(implementation, "add_noise", forbidden)
    monkeypatch.setattr(implementation, "coupled_sensor_noise", forbidden)
    with pytest.raises(ValueError):
        renoise(a, m, 1, 1)


@pytest.mark.parametrize("args", [(0, 1), (1, -1), (True, 1), (1.5, 1)])
def test_invalid_seed_coordinates(args):
    with pytest.raises(ValueError):
        noise_seed(*args)


def test_fixed_schedule_seeds_are_unique():
    seeds = [noise_seed(row, (row - 1) % 1000 + 1) for row in range(1, 9001)]
    assert len(set(seeds)) == len(seeds) == 9000
