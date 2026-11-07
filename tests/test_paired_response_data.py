"""Camera/CFA compatibility,exact empty pixels and stateless pair construction."""

import json
import random

import numpy as np
import pytest
import torch
from paired_response_data import paired_observation, source_batch

from demosaic.cfa import PATTERNS
from demosaic.suite import observation


class FakePhoto:
    def __getitem__(self, index):
        y, x = torch.meshgrid(torch.arange(32), torch.arange(32), indexing="ij")
        rgb = torch.stack([x.float() + 1, y.float() + 1, (x + y).float() + 1]) / 64
        return {
            "rgb": rgb,
            "source": json.dumps({"source_id": f"test-{index}", "kind": "photographic"}),
        }


def config():
    return {
        "seed": 160,
        "steps": 1000,
        "batch_size": 4,
        "pair_unit_floor_DN16": 16,
        "domains": {"mesh": 0.35, "weak": 0.1, "flat": 0.15, "mixed": 0.15, "photo": 0.25},
        "domain_sizes": {k: 32 for k in ["mesh", "weak", "flat", "mixed", "photo"]},
        "first_ten_domains": [
            "mesh",
            "photo",
            "flat",
            "mixed",
            "weak",
            "mesh",
            "photo",
            "flat",
            "mixed",
            "weak",
        ],
    }


@pytest.mark.parametrize("pattern", list(PATTERNS))
def test_ADC_only_pair_targets_and_all_phases_match_legacy_observation(pattern):
    rgb = torch.arange(3 * 8 * 12, dtype=torch.float32).reshape(1, 3, 8, 12) / 512
    other = rgb * 0.5
    condition = {"name": "test-adc", "shot": 0.0, "read": 0.0, "exposure": 1.0}
    wb = torch.tensor([[2.0, 1.0, 0.5]])
    inverse = torch.eye(3)[None]
    arrays, _ = paired_observation(rgb, other, condition, [pattern], wb, inverse, 16021)
    for slot, value in enumerate([rgb, other]):
        old = observation(
            value,
            [f"test-{slot}"],
            condition,
            pattern,
            wb[0].tolist(),
            torch.eye(3).tolist(),
            16022,
        )
        for key in ["packed", "variance", "colors", "wb", "matrix", "target"]:
            np.testing.assert_array_equal(arrays[key][slot : slot + 1], old[key].numpy())
        # Explicit phase coordinates independently identify the sampled color.
        clean = value.numpy()[0] / wb.numpy()[0, :, None, None]
        for phase, color in enumerate(PATTERNS[pattern]):
            yy, xx = divmod(phase, 2)
            physical = clean[color, yy::2, xx::2].clip(0)
            expected = (((physical * 0.97 + 0.03).clip(0, 1) * 65535).round() / 65535 - 0.03) / 0.97
            np.testing.assert_array_equal(arrays["packed"][slot, phase], expected)


def test_nontrivial_camera_transport_matches_independent_numpy():
    generator = torch.Generator().manual_seed(16023)
    rgb = torch.rand(2, 3, 8, 12, generator=generator)
    wb = torch.tensor([[1.3, 1.0, 0.8], [0.7, 1.0, 2.0]])
    inverse = torch.tensor([[[0.75, 0.25, 0], [0.125, 0.75, 0.125], [0, 0.25, 0.75]]]).expand(
        2, -1, -1
    )
    arrays, _ = paired_observation(
        rgb,
        rgb * 0.5,
        {"shot": 0.0, "read": 0.0, "exposure": 2.0, "name": "transport"},
        ["RGGB", "GBRG"],
        wb,
        inverse,
        16024,
    )
    for pair in range(2):
        for offset, factor in enumerate([1.0, 0.5]):
            expected = (
                np.einsum(
                    "ij,jhw->ihw",
                    inverse[pair].double().numpy(),
                    (rgb[pair].double().numpy() * 2 * factor).clip(0, 1),
                )
                / wb[pair].double().numpy()[:, None, None]
            )
            np.testing.assert_allclose(
                arrays["target"][2 * pair + offset], expected, rtol=2e-7, atol=2e-7
            )


def test_same_sensor_regions_have_identical_coupled_noise_after_camera_and_CFA():
    a = torch.full((2, 3, 16, 24), 0.02)
    b = a.clone()
    a[..., 4:12, 6:18] += 0.001
    arrays, metadata = paired_observation(
        a,
        b,
        {"shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0, "name": "noise"},
        ["GRBG", "BGGR"],
        torch.ones(2, 3),
        torch.eye(3)[None].expand(2, -1, -1),
        16025,
    )
    for pair in range(2):
        first, second = arrays["packed"][2 * pair : 2 * pair + 2]
        outside = np.ones_like(first, dtype=bool)
        outside[:, 2:6, 3:9] = False
        np.testing.assert_array_equal(first[outside], second[outside])
    assert metadata["identical_sensor_pixels"] == [288, 288]
    np.testing.assert_array_equal(arrays["pair_indices"], [[0, 1], [2, 3]])


@pytest.mark.parametrize("step", [1, 2, 3, 4, 5])
def test_source_replay_global_RNG_isolation_and_pair_layout(step):
    global_torch = torch.get_rng_state().clone()
    global_python = random.getstate()
    global_numpy = np.random.get_state()
    first, meta = source_batch(config(), FakePhoto(), step)
    second, other = source_batch(config(), FakePhoto(), step)
    assert meta == other
    for key in first:
        np.testing.assert_array_equal(first[key], second[key])
    assert torch.equal(torch.get_rng_state(), global_torch) and random.getstate() == global_python
    assert all(
        np.array_equal(a, b) if isinstance(a, np.ndarray) else a == b
        for a, b in zip(np.random.get_state(), global_numpy, strict=True)
    )
    assert first["target"].shape == (4, 3, 32, 32) and first["packed"].shape == (4, 4, 16, 16)
    assert meta["coupled_pairs"] == (2 if step in [1, 2, 5] else 0)
    if meta["coupled_pairs"]:
        np.testing.assert_array_equal(first["colors"][::2], first["colors"][1::2])
        np.testing.assert_array_equal(first["wb"][::2], first["wb"][1::2])
        np.testing.assert_array_equal(first["matrix"][::2], first["matrix"][1::2])
        assert np.any(first["target"][::2] != first["target"][1::2])
    else:
        assert first["pair_indices"].shape == (0, 2) and first["pair_units"].shape == (0, 1, 1, 1)
