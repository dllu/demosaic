"""Actual source and sensor calls stay distinct without changing sampled data."""

from pathlib import Path

import numpy as np
import pytest
import torch
import yaml
from paired_response_counters import count_source_draws
from paired_response_data import source_batch


@pytest.mark.parametrize(
    "step,sensor_poisson,sensor_gaussian,procedural_gaussian",
    [(1, 3, 1, 0), (3, 4, 4, 0), (24, 3, 1, 1)],
)
def test_real_sensor_boundaries_preserve_source_arrays(
    step, sensor_poisson, sensor_gaussian, procedural_gaussian
):
    config = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1] / "configs/quality-v143-paired-response-v160.yaml"
        ).read_text()
    )
    state = torch.get_rng_state().clone()
    with count_source_draws() as counts:
        actual, metadata = source_batch(config, None, step)
    expected, expected_metadata = source_batch(config, None, step)
    assert metadata == expected_metadata
    for key in actual:
        np.testing.assert_array_equal(actual[key], expected[key])
    assert torch.equal(state, torch.get_rng_state())
    assert counts == {
        "sensor_Poisson": sensor_poisson,
        "sensor_Gaussian": sensor_gaussian,
        "procedural_Poisson": 0,
        "procedural_Gaussian": procedural_gaussian,
        "coupled_sensor_calls": int(step != 3),
        "ordinary_sensor_calls": 4 * int(step == 3),
    }
