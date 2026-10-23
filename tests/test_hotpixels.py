import numpy as np
import pytest

from demosaic.hotpixels import repair_hot_pixels


def test_isolated_defects_in_all_four_cfa_phases_preserve_other_sites_and_input():
    raw = np.empty((31, 37), dtype=np.float32)
    for phase, value in enumerate([0.01, 0.02, 0.03, 0.04]):
        raw[phase // 2 :: 2, phase % 2 :: 2] = value
    positions = [(8, 8), (8, 17), (17, 8), (17, 17)]
    for y, x in positions:
        raw[y, x] = 0.9
    original = raw.copy()
    clean, report = repair_hot_pixels(raw, shot=0.001, read=1e-6, rows=3)
    np.testing.assert_array_equal(raw, original)
    assert report["corrected_pixels"] == 4
    assert report["phase_counts_row_major"] == [1, 1, 1, 1]
    for y, x in positions:
        assert clean[y, x] == raw[y - 2, x]
        original[y, x] = clean[y, x]
    np.testing.assert_array_equal(clean, original)


def test_edges_thin_lines_and_spatially_supported_light_are_preserved():
    raw = np.full((65, 73), 0.005, dtype=np.float32)
    raw[:, 30:] = 0.2  # Strong straight edge.
    raw[12:53, 12] = 0.8  # Native one-pixel line spans same-phase neighbors.
    raw[44:49, 44:49] = 0.9  # Real light with a spatial footprint.
    raw[0, 0] = 0.9  # Unsupported image border is deliberately untouched.
    clean, report = repair_hot_pixels(raw, shot=0.001, read=1e-6)
    np.testing.assert_array_equal(clean, raw)
    assert report["corrected_pixels"] == 0


def test_noise_gate_rejects_moderate_outliers_and_retains_signed_black_noise():
    raw = np.full((16, 16), -0.001, dtype=np.float32)
    raw[8, 8] = 0.01
    clean, report = repair_hot_pixels(raw, shot=0.001, read=1e-4)
    np.testing.assert_array_equal(clean, raw)
    assert report["corrected_pixels"] == 0


def test_adjacent_other_color_signal_protects_small_real_light():
    raw = np.full((33, 35), 0.01, dtype=np.float32)
    raw[16, 16] = 0.8
    raw[16, 17] = 0.4
    clean, report = repair_hot_pixels(raw, shot=0.001, read=1e-6)
    np.testing.assert_array_equal(clean, raw)
    assert report["coherent_candidates_preserved"] == 2


def test_representative_poisson_read_noise_is_not_removed_as_hot_pixels():
    rng = np.random.default_rng(830)
    signal = np.repeat(np.array([0.002, 0.02, 0.2])[None], 512, axis=0)
    signal = np.repeat(signal, 256, axis=1)
    shot, read = 0.00128, 6.5536e-6
    raw = (rng.poisson(signal / shot) * shot + rng.normal(0, np.sqrt(read), signal.shape)).astype(
        np.float32
    )
    clean, report = repair_hot_pixels(raw, shot=shot, read=read)
    np.testing.assert_array_equal(clean, raw)
    assert report["corrected_pixels"] == 0


def test_results_do_not_depend_on_strip_boundaries_or_corrected_neighbors():
    rng = np.random.default_rng(3)
    raw = rng.uniform(0.003, 0.006, (41, 53)).astype(np.float32)
    raw[6, 6] = 0.8
    raw[20, 20] = 0.9
    raw[20, 22] = 0.9  # Cluster is not treated as an isolated defect.
    first, a = repair_hot_pixels(raw, shot=0.001, read=1e-6, rows=1)
    second, b = repair_hot_pixels(raw, shot=0.001, read=1e-6, rows=17)
    np.testing.assert_array_equal(first, second)
    assert a["corrected_pixels"] == b["corrected_pixels"] == 1
    assert a["coordinates_yx_int64_sha256"] == b["coordinates_yx_int64_sha256"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"shot": -1},
        {"read": float("nan")},
        {"sigma": 0},
        {"ratio": 1},
        {"rows": 0},
        {"min_delta": -1},
    ],
)
def test_invalid_parameters_do_not_change_input(kwargs):
    raw = np.zeros((8, 8), dtype=np.float32)
    options = {"shot": 0.001, "read": 1e-6, **kwargs}
    with pytest.raises(ValueError):
        repair_hot_pixels(raw, **options)
    assert not raw.any()
