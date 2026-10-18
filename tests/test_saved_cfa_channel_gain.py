"""Independent calibration fixtures for the fixed saved-grid counterfactual."""

import importlib.util
from pathlib import Path

import pytest
import torch

from demosaic.cfa import PATTERNS


def operator():
    spec = importlib.util.spec_from_file_location(
        "saved_gain", Path("scripts/probe_saved_cfa_gain_grid.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.channel_gain


def test_spatially_varying_rgb_known_gains_separate_samples_and_all_phases():
    function = operator()
    generator = torch.Generator().manual_seed(91)
    rgb = torch.rand((4, 3, 12, 16), generator=generator) + 0.2
    labels = torch.tensor(list(PATTERNS.values()))
    desired = torch.tensor([[0.8, 1.1, 1.2], [1.3, 0.9, 0.7], [0.5, 1.4, 1.1], [1.1, 0.6, 1.7]])
    observed = torch.empty((4, 4, 6, 8))
    # Construct the physical sensor samples directly, without mosaic/helper.
    for b in range(4):
        for phase, color in enumerate(labels[b]):
            observed[b, phase] = rgb[b, color, phase // 2 :: 2, phase % 2 :: 2] * desired[b, color]
    result, gains = function(rgb, observed, labels)
    torch.testing.assert_close(gains, desired.double(), rtol=1e-7, atol=1e-7)
    torch.testing.assert_close(result, rgb * desired[..., None, None], rtol=1e-7, atol=1e-7)
    assert result.dtype == torch.float32 and gains.dtype == torch.float64


def test_two_green_phases_and_no_clipping_or_gain_bounds():
    function = operator()
    rgb = torch.ones((1, 3, 8, 8))
    observed = torch.stack([torch.full((4, 4), x) for x in [-2.0, 2.0, 4.0, 3.0]])[None]
    result, gain = function(rgb, observed, torch.tensor(PATTERNS["RGGB"]))
    torch.testing.assert_close(gain, torch.tensor([[-2.0, 3.0, 3.0]], dtype=torch.float64))
    torch.testing.assert_close(result[:, 0], torch.full((1, 8, 8), -2.0))


def test_zero_prediction_retains_existing_denominator_floor_behavior():
    result, gain = operator()(
        torch.zeros((1, 3, 8, 8)), torch.ones((1, 4, 4, 4)), torch.tensor(PATTERNS["RGGB"])
    )
    assert torch.equal(result, torch.zeros_like(result)) and torch.equal(
        gain, torch.zeros_like(gain)
    )


@pytest.mark.parametrize("problem", ["nonfinite", "shape", "labels"])
def test_invalid_observations_fail(problem):
    rgb, observed = torch.ones((1, 3, 8, 8)), torch.ones((1, 4, 4, 4))
    colors = torch.tensor(PATTERNS["RGGB"])
    if problem == "nonfinite":
        observed[0, 0, 0, 0] = float("nan")
    elif problem == "shape":
        rgb = rgb[..., :6]
    else:
        colors[0] = 1
    with pytest.raises(ValueError):
        operator()(rgb, observed, colors)
