"""Reference-white compatibility and physical fixtures for the fixed new policy."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, mosaic
from demosaic.data import camera_pair


def operator(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "guarded_gain", Path("scripts/guarded_cfa_gain.py")
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("labels", list(PATTERNS.values()))
def test_perfect_reference_white_target_survives_exposed_sensor_conflict(monkeypatch, labels):
    m = operator(monkeypatch)
    from probe_saved_cfa_gain_grid import channel_gain

    rgb = torch.full((1, 3, 64, 64), 0.2)
    rgb[..., :32] = torch.tensor([3.6, 1.8, 0.9])[None, :, None, None]
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor(
        [
            [
                [1.117647, -0.0588235, -0.0588235],
                [-0.0588235, 1.117647, -0.0588235],
                [-0.0588235, -0.0588235, 1.117647],
            ]
        ]
    )
    clean, target = camera_pair(rgb, torch.linalg.inv(matrix), wb, reconstruct_highlights=True)
    colors = torch.tensor(labels)[None]
    observed = mosaic(clean.clamp(0, 1), colors)
    old, _ = channel_gain(target, observed, colors)
    assert float((old - target).square().mean()) > 1e-3
    result, gain, terms = m.correct(
        target, observed, torch.zeros_like(observed), colors, wb, matrix
    )
    assert torch.equal(result, target) and torch.equal(gain, torch.ones_like(gain))
    assert torch.all(terms["count"] >= 256)


def test_supported_midtones_recover_small_channel_error_without_cross_sample_fitting(monkeypatch):
    m = operator(monkeypatch)
    rng = torch.Generator().manual_seed(81)
    rgb = torch.rand((4, 3, 64, 64), generator=rng) * 0.15 + 0.15
    desired = torch.tensor(
        [[1.02, 0.98, 1.01], [0.99, 1.03, 0.97], [1.01, 1.02, 0.99], [0.98, 1.01, 1.04]]
    )
    colors = torch.tensor(list(PATTERNS.values()))
    observed = torch.empty((4, 4, 32, 32))
    for b in range(4):
        for phase, c in enumerate(colors[b]):
            observed[b, phase] = rgb[b, c, phase // 2 :: 2, phase % 2 :: 2] * desired[b, c]
    variance = torch.full_like(observed, 1e-6)
    wb = torch.ones((4, 3))
    matrix = torch.eye(3).expand(4, -1, -1)
    result, gain, terms = m.correct(rgb, observed, variance, colors, wb, matrix)
    torch.testing.assert_close(gain, desired.double(), rtol=1e-7, atol=1e-7)
    torch.testing.assert_close(result, rgb * desired[..., None, None], rtol=1e-7, atol=1e-7)
    oracle = m.numpy_terms(
        rgb.numpy(), observed.numpy(), variance.numpy(), colors.numpy(), wb.numpy(), matrix.numpy()
    )
    np.testing.assert_array_equal(oracle["count"], terms["count"].numpy())
    np.testing.assert_allclose(m.numpy_solve(oracle), gain.numpy(), rtol=2e-12, atol=2e-12)


def test_empty_low_signal_and_ADC_clipping_preserve_output(monkeypatch):
    m = operator(monkeypatch)
    rgb = torch.full((1, 3, 64, 64), 0.01)
    packed = torch.ones((1, 4, 32, 32))
    result, gain, terms = m.correct(
        rgb,
        packed,
        torch.full_like(packed, 0.001),
        torch.tensor(PATTERNS["RGGB"]),
        torch.ones((1, 3)),
        torch.eye(3)[None],
    )
    assert torch.equal(result, rgb) and torch.equal(gain, torch.ones_like(gain))
    assert not terms["count"].any()


def test_fixed_gain_bounds_and_continuous_monotone_neutral_white_taper(monkeypatch):
    m = operator(monkeypatch)
    x = torch.linspace(0.85, 1.02, 1024)
    rgb = x[None, None, None].expand(1, 3, 2, -1)
    wb = torch.ones((1, 3))
    matrix = torch.eye(3)[None]
    for g in [0.95, 1.05]:
        result = m.apply_gain(rgb, torch.full((1, 3), g, dtype=torch.float64), wb, matrix)
        assert torch.all(torch.diff(result, dim=-1) >= 0)
        assert torch.equal(result[..., x >= 0.98], rgb[..., x >= 0.98])
    terms = {
        "numerator": torch.tensor([[0.5, 2.0, 1.0]]),
        "denominator": torch.ones((1, 3)),
        "count": torch.full((1, 3), 512),
    }
    torch.testing.assert_close(m.solve(terms), torch.tensor([[0.95, 1.05, 1.0]]))


@pytest.mark.parametrize("problem", ["nonfinite", "negative-variance", "shape"])
def test_invalid_inputs_fail(monkeypatch, problem):
    m = operator(monkeypatch)
    rgb = torch.ones((1, 3, 64, 64)) * 0.2
    packed = torch.ones((1, 4, 32, 32)) * 0.2
    variance = torch.zeros_like(packed)
    if problem == "nonfinite":
        rgb[0, 0, 0, 0] = float("nan")
    elif problem == "negative-variance":
        variance -= 1
    else:
        rgb = rgb[..., :32]
    with pytest.raises(ValueError):
        m.correct(
            rgb,
            packed,
            variance,
            torch.tensor(PATTERNS["RGGB"]),
            torch.ones((1, 3)),
            torch.eye(3)[None],
        )
