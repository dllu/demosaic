import importlib.util
from pathlib import Path

import numpy as np
import pytest


def script():
    path = Path("scripts/benchmark_packed_compilation.py")
    spec = importlib.util.spec_from_file_location("compile_difference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_rgb_difference_includes_last_partial_chunk_and_unclipped_channels():
    module = script()
    reference = np.linspace(-0.03, 1.3, 3 * 131 * 17).reshape(3, 131, 17)
    actual = reference.copy()
    actual[2, -1, -1] += 2 / 65535
    result = module.difference(actual, reference, rows=128)
    delta = actual - reference
    assert result["elements"] == delta.size
    assert result["max_abs"] == float(np.abs(delta).max())
    assert result["RMS"] == pytest.approx(float(np.sqrt(np.square(delta).mean())), rel=1e-13)
    assert not result["passes_predeclared_bound"]
    # Whole-frame verification must not silently restrict itself to the usual
    # display ROI, clip HDR values or average each unequal chunk equally.
    assert result["max_abs_DN16"] > 1.99


def test_numerical_bound_rejects_spatially_constant_bias_despite_small_maximum():
    module = script()
    reference = np.zeros((3, 129, 7), dtype=np.float64)
    result = module.difference(reference + 0.5 / 65535, reference)
    assert result["max_abs_DN16"] == pytest.approx(0.5)
    assert result["RMS_DN16"] == pytest.approx(0.5)
    assert not result["passes_predeclared_bound"]
    assert module.difference(reference, reference)["passes_predeclared_bound"]


def test_full_rgb_validation_rejects_nonfinite_pixels_and_mismatched_shapes():
    module = script()
    reference = np.zeros((3, 131, 9), dtype=np.float32)
    broken = reference.copy()
    broken[2, -1, -1] = np.nan
    for first, second in [(broken, reference), (reference, broken)]:
        with pytest.raises(ValueError, match="Nonfinite"):
            module.difference(first, second)
    for other in [np.zeros((1, 131, 9)), np.zeros((3, 0, 9)), np.zeros((3, 131, 8))]:
        with pytest.raises(ValueError, match="matching"):
            module.difference(reference, other)
    with pytest.raises(ValueError, match="positive"):
        module.difference(reference, reference, rows=0)
