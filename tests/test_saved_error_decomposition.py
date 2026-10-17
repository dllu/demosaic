import importlib.util
from pathlib import Path

import numpy as np
import pytest


def script():
    path = Path("scripts/decompose_control_errors.py")
    spec = importlib.util.spec_from_file_location("saved_errors", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_constant_color_error_has_only_mean_energy():
    module = script()
    error = np.broadcast_to(np.array([1, -2, 3])[:, None, None], (3, 32, 48))
    result = module.decompose(error)
    assert result["MSE"] == pytest.approx(14 / 3)
    assert result["mean_bias_MSE"] == result["MSE"]
    assert result["zero_mean_MSE"] == 0
    assert all(value == 0 for value in result["zero_mean_Haar_MSE_by_block_side"].values())
    assert module.audit(error, result) < 1e-14


@pytest.mark.parametrize("side", [2, 4, 8, 16])
def test_exact_dyadic_stripes_isolate_their_spatial_band(side):
    module = script()
    stripes = np.where(np.arange(32) % side < side // 2, -1.0, 1.0)
    error = np.broadcast_to(stripes, (3, 32, 32))
    result = module.decompose(error)
    assert result["mean_bias_MSE"] == 0
    bands = result["zero_mean_Haar_MSE_by_block_side"]
    assert bands[str(side)] == pytest.approx(1)
    assert sum(value for key, value in bands.items() if key != str(side)) == 0
    assert module.audit(error, result) < 1e-14


def test_independent_block_averages_detect_corrupted_band_assignment():
    module = script()
    error = np.random.default_rng(42).normal(size=(3, 48, 32)) + np.array([1, -2, 3])[:, None, None]
    result = module.decompose(error)
    assert module.audit(error, result) < 1e-14
    bands = result["zero_mean_Haar_MSE_by_block_side"]
    bands["2"], bands["4"] = bands["4"], bands["2"]
    with pytest.raises(ValueError, match="independent identities"):
        module.audit(error, result)


@pytest.mark.parametrize("shape", [(3, 31, 32), (1, 32, 32), (3, 0, 32)])
def test_invalid_native_geometry_is_rejected(shape):
    with pytest.raises(ValueError):
        script().decompose(np.zeros(shape))
