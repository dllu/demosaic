"""A global least-squares fit weights sample energy, not individual tile gains."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from demosaic.cfa import PATTERNS


def operator(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "global_gain", Path("scripts/probe_saved_global_cfa_gain.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.global_gain


@pytest.mark.parametrize("colors", list(PATTERNS.values()))
def test_global_fit_is_independent_of_chunks_and_not_mean_tile_gain(monkeypatch, colors):
    function = operator(monkeypatch)
    rgb = np.ones((3, 42, 18), dtype=np.float32)
    rgb[:, :20] = 0.125
    raw = np.empty((42, 18), dtype=np.float32)
    for phase, c in enumerate(colors):
        measured = rgb[c, phase // 2 :: 2, phase % 2 :: 2].copy()
        measured[:10] *= 0.5
        measured[10:] *= 1.5
        raw[phase // 2 :: 2, phase % 2 :: 2] = measured
    expected = (20 * 0.125**2 * 0.5 + 22 * 1.5) / (20 * 0.125**2 + 22)
    assert abs(expected - 1) > 0.4
    originals = (rgb.copy(), raw.copy())
    for rows in [2, 10, 18, 256]:
        result = function(rgb, raw, colors, rows=rows)
        np.testing.assert_allclose(result["gains"], [expected] * 3, rtol=0, atol=2e-14)
        assert result["sample_counts_per_RGB"] == [189, 378, 189]
        assert result["max_absolute_gain_difference"] < 2e-14
    assert np.array_equal(rgb, originals[0]) and np.array_equal(raw, originals[1])


@pytest.mark.parametrize("problem", ["odd-chunk", "nonfinite", "odd-sensor", "shape"])
def test_invalid_full_frame_inputs_fail(monkeypatch, problem):
    function = operator(monkeypatch)
    rgb = np.ones((3, 8, 10), dtype=np.float32)
    raw = rgb[0].copy()
    rows = 4
    if problem == "odd-chunk":
        rows = 3
    elif problem == "nonfinite":
        raw[0, 0] = np.inf
    elif problem == "odd-sensor":
        rgb = rgb[:, :7]
        raw = raw[:7]
    else:
        rgb = rgb[:, :6]
    with pytest.raises(ValueError):
        function(rgb, raw, PATTERNS["RGGB"], rows=rows)
