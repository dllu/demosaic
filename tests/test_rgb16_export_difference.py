import importlib.util
from pathlib import Path

import numpy as np
import pytest


def operator():
    # The script imports the shared comparison helper as a neighboring module.
    import sys

    path = Path("scripts").resolve()
    sys.path.insert(0, str(path))
    try:
        spec = importlib.util.spec_from_file_location(
            "grid_exports", path / "evaluate_packed_grid.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module.export_difference


def test_rgb16_export_difference_keeps_sign_extrema_and_final_partial_chunk():
    reference = np.zeros((131, 7, 3), dtype=np.uint16)
    reference[0, 0, 0] = 65535
    actual = np.zeros_like(reference)
    actual[-1, -1, 2] = 65535
    result = operator()(actual, reference, rows=128)
    assert result["max_abs_DN16"] == 65535
    assert result["changed_values"] == result["changed_pixels"] == 2
    assert result["RGB_values"] == reference.size
    delta = actual.astype(np.float64) - reference.astype(np.float64)
    assert result["RMS_DN16"] == pytest.approx(float(np.square(delta).mean() ** 0.5))
    np.testing.assert_array_equal(result["mean_signed_DN16_RGB"], delta.mean(axis=(0, 1)))


def test_rgb16_export_difference_distinguishes_values_from_pixels():
    reference = np.zeros((3, 5, 3), dtype=np.uint16)
    actual = reference.copy()
    actual[1, 2] = [1, 2, 3]
    result = operator()(actual, reference)
    assert result["changed_values"] == 3 and result["changed_pixels"] == 1
    assert result["max_abs_DN16"] == 3
    assert operator()(actual, actual)["RMS_DN16"] == 0


@pytest.mark.parametrize("case", ["shape", "float", "channels", "empty", "rows"])
def test_rgb16_export_comparison_rejects_incompatible_inputs(case):
    reference = np.zeros((3, 5, 3), dtype=np.uint16)
    actual, rows = reference, 128
    if case == "shape":
        actual = np.zeros((4, 5, 3), dtype=np.uint16)
    elif case == "float":
        actual = reference.astype(np.float32)
    elif case == "channels":
        actual = reference = np.zeros((3, 5, 4), dtype=np.uint16)
    elif case == "empty":
        actual = reference = np.zeros((0, 5, 3), dtype=np.uint16)
    else:
        rows = 0
    with pytest.raises(ValueError, match="uint16"):
        operator()(actual, reference, rows=rows)
