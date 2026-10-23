import numpy as np
import pytest

from demosaic.hotpixels import repair_hot_pixels


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("kind", ["same-phase", "diagonal-green"])
def test_pairs_cannot_mask_each_other_and_input_is_unchanged(pattern, kind):
    raw = np.full((33, 35), 0.002, dtype=np.float32)
    green = next(i for i, c in enumerate(pattern) if c == "G")
    y, x = 14 + green // 2, 14 + green % 2
    other = (y + 2, x) if kind == "same-phase" else (y + 1, x + 1)
    raw[y, x] = 1
    raw[other] = 0.5
    original = raw.copy()
    isolated, old = repair_hot_pixels(raw, shot=0.00128, read=6.5536e-6, pattern=pattern)
    clean, new = repair_hot_pixels(
        raw, shot=0.00128, read=6.5536e-6, pattern=pattern, clusters=True
    )
    np.testing.assert_array_equal(raw, original)
    np.testing.assert_array_equal(isolated, original)
    assert old["corrected_pixels"] == 0
    assert new["corrected_pixels"] == 2
    assert np.all(clean == np.float32(0.002))


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_small_light_with_different_color_support_is_preserved(pattern):
    raw = np.full((33, 35), 0.002, dtype=np.float32)
    raw[16, 16] = 0.8
    raw[16, 17] = 0.4
    clean, report = repair_hot_pixels(
        raw, shot=0.00128, read=6.5536e-6, pattern=pattern, clusters=True
    )
    np.testing.assert_array_equal(clean, raw)
    assert report["coherent_candidates_preserved"] == 2


def test_narrow_diagonal_green_line_and_white_point_footprint_survive():
    raw = np.full((65, 71), 0.002, dtype=np.float32)
    for n in range(10, 40):
        raw[n, n + 1] = 0.7
    raw[48:50, 48:50] = 0.9
    clean, report = repair_hot_pixels(raw, shot=0.00128, read=6.5536e-6, clusters=True)
    # Two-pixel ends are protected by their same-phase continuation.
    np.testing.assert_array_equal(clean, raw)
    assert report["corrected_pixels"] == 0


def test_cluster_processing_is_simultaneous_and_strip_invariant():
    raw = np.full((33, 35), 0.002, dtype=np.float32)
    raw[15, 14] = 1
    raw[17, 14] = 0.5
    a, ra = repair_hot_pixels(raw, shot=0.00128, read=6.5536e-6, clusters=True, rows=1)
    b, rb = repair_hot_pixels(raw, shot=0.00128, read=6.5536e-6, clusters=True, rows=11)
    np.testing.assert_array_equal(a, b)
    assert ra["coordinates_yx_int64_sha256"] == rb["coordinates_yx_int64_sha256"]
    assert ra["corrected_pixels"] == rb["corrected_pixels"] == 2
