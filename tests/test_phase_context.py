"""Physical frequencies, nonduplicated contexts and exact legacy fallbacks."""

import numpy as np
import pytest
import torch

from demosaic.phase_context import context_frequencies, context_origin, correct_context_patch
from demosaic.phase_context_frequency import frequency_fit
from demosaic.phase_frequency import frequency_fit as legacy_frequency_fit
from demosaic.phase_harmonic import fit_patch_harmonics, refine_phase_harmonics
from demosaic.phase_tv import correct_edge_phase_patch

PATTERNS = [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)]


def _wave(size, frequency, colors):
    y, x = np.mgrid[:size, :size]
    wave = np.cos(2 * np.pi * (frequency[0] * x + frequency[1] * y) + 0.7)
    base = np.full((3, size, size), 0.02)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    return base, target, packed


@pytest.mark.parametrize("size", [256, 512])
@pytest.mark.parametrize("colors", PATTERNS)
def test_measured_high_frequency_search_recovers_physical_wave(size, colors):
    known = np.array([0.2343, 0.1482])
    _, _, packed = _wave(size, known, colors)
    guess = np.round(known * size) / size
    actual, _ = frequency_fit(packed, np.asarray(colors), guess, max_radius=0.34)
    np.testing.assert_allclose(actual, known, rtol=0, atol=2e-6)


@pytest.mark.parametrize("colors", PATTERNS)
def test_original_band_native256_search_is_exactly_legacy(colors):
    _, _, packed = _wave(256, (-0.0713, 0.0532), colors)
    guess = (-18 / 256, 14 / 256)
    actual, info = frequency_fit(packed, np.asarray(colors), guess)
    expected, old = legacy_frequency_fit(packed, np.asarray(colors), guess)
    np.testing.assert_array_equal(actual, expected)
    assert info == old


def test_pure_fundamental_does_not_propose_absent_high_harmonics():
    _, _, packed = _wave(512, (0.1113, 0.0712), PATTERNS[0])
    peaks, _ = context_frequencies(packed, np.full_like(packed, 1e-7), np.array(PATTERNS[0]))
    assert peaks
    assert all(np.hypot(fx, fy) <= 0.22 for fx, fy, _ in peaks)


@pytest.mark.parametrize("colors", PATTERNS)
@pytest.mark.parametrize("mode", ["wide", "cross"])
def test_small_image_and_clipped_window_retain_exact_sparse_or_grid_result(colors, mode):
    base, _, packed = _wave(256, (-0.0713, 0.0532), colors)
    raw = np.empty((256, 256))
    for p in range(4):
        raw[p // 2 :: 2, p % 2 :: 2] = packed[p]
    expected, _ = refine_phase_harmonics(raw, colors, base, shot=0, read=1e-7, envelope="sparse")
    value, info = refine_phase_harmonics(raw, colors, base, shot=0, read=1e-7, envelope=mode)
    np.testing.assert_array_equal(value, expected)
    assert info["envelope"] == mode and info["effective_envelope"] == "sparse"
    assert info["context_small_image_fallback"] and info["context"]["windows"] == 0
    packed[0, 40, 50] = 1
    variance = np.full_like(packed, 1e-7)
    expected, _ = correct_edge_phase_patch(packed, variance, colors, base)
    actual, info = correct_context_patch(
        packed,
        variance,
        colors,
        base,
        [(0.2343, 0.1482, 10)],
        variance_floor=1e-3,
        cross_phase_support=mode == "cross",
    )
    np.testing.assert_array_equal(actual, expected)
    assert info["context_clipped_local_fallback"]


def test_flat_local_measurements_ignore_a_frequency_hint_from_elsewhere():
    base = np.full((3, 256, 256), 0.02)
    packed = np.full((4, 128, 128), 0.02)
    actual, _ = correct_context_patch(
        packed, np.full_like(packed, 1e-7), PATTERNS[0], base, [(0.2343, 0.1482, 10)]
    )
    np.testing.assert_array_equal(actual, base)


def test_context_grid_uses_actual_even_origin_windows_including_odd_edges():
    assert [context_origin(x, 1024) for x in [0, 128, 256, 384, 512, 640, 768]] == [
        0,
        0,
        192,
        192,
        448,
        448,
        512,
    ]
    for size in [512, 513, 1024, 11662]:
        for start in range(0, size - 255, 128):
            origin = context_origin(start, size)
            assert origin % 2 == 0 and 0 <= origin <= size - 512
    with pytest.raises(ValueError):
        context_origin(0, 511)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_context_patch_CPU_CUDA_match_without_RNG_or_state_leak():
    base, _, packed = _wave(256, (0.2343, 0.1482), PATTERNS[0])
    variance = np.full_like(packed, 1e-7)
    hints = [(0.2343, 0.1482, 10)]
    before, gpu_before = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    expected, _ = correct_context_patch(packed, variance, PATTERNS[0], base, hints)
    actual, _ = correct_context_patch(packed, variance, PATTERNS[0], base, hints, device="cuda")
    np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-16)
    assert torch.equal(before, torch.get_rng_state())
    assert torch.equal(gpu_before, torch.cuda.get_rng_state())


def test_duplicate_context_hint_keeps_original_local_dictionary():
    base, _, packed = _wave(256, (-0.0713, 0.0532), PATTERNS[0])
    variance = np.full_like(packed, 1e-7)
    fitted = fit_patch_harmonics(packed, variance, np.array(PATTERNS[0]), base)
    expected, _ = correct_edge_phase_patch(packed, variance, PATTERNS[0], base, sparse_support=True)
    # A duplicate hint cannot add a second copy of an original physical wave.
    actual, _ = correct_context_patch(packed, variance, PATTERNS[0], base, fitted["peaks"])
    np.testing.assert_array_equal(actual, expected)


def test_original_inactive_gates_remain_off_with_an_additional_context_hint():
    _, target, packed = _wave(256, (-0.0713, 0.0532), PATTERNS[0])
    variance = np.full_like(packed, 1e-7)
    fitted = fit_patch_harmonics(packed, variance, np.array(PATTERNS[0]), target)
    assert fitted["peaks"]
    actual, info = correct_context_patch(
        packed, variance, PATTERNS[0], target, [(0.2343, 0.1482, 10)]
    )
    np.testing.assert_array_equal(actual, target)
    assert all(item["gate"] == 0 for item in info["local"])


def test_noise_floor_uses_exact_propagated_unit_variance():
    from demosaic.phase_harmonic import green_pair
    from demosaic.phase_noise_floor import unit_noise

    rng = np.random.default_rng(391)
    packed = rng.normal(0.02, 0.003, (4, 32, 48))
    variance = rng.uniform(1e-6, 2e-5, packed.shape)
    before = green_pair(packed, variance, np.array(PATTERNS[0]))
    after = green_pair(packed, variance + 3e-6, np.array(PATTERNS[0]))
    expected = np.broadcast_to(3e-6 * unit_noise((32, 48)), before["noise_variance"].shape)
    np.testing.assert_allclose(
        after["noise_variance"] - before["noise_variance"], expected, rtol=1e-13
    )


def test_noise_floor_recovers_gaussian_variance_and_never_reduces_prior():
    from demosaic.phase_harmonic import green_pair
    from demosaic.phase_noise_floor import estimate_variance_floor

    packed = np.random.default_rng(392).normal(0.02, np.sqrt(1e-5), (4, 256, 256))
    colors = np.array(PATTERNS[0])
    info = estimate_variance_floor(green_pair(packed, np.full_like(packed, 1e-6), colors))
    assert abs(info["added_pixel_variance"] + 1e-6 - 1e-5) < 8e-7
    info = estimate_variance_floor(green_pair(packed, np.full_like(packed, 2e-5), colors))
    assert info["added_pixel_variance"] == 0


def test_noise_floor_rejects_regression_flat_under_Haar_prior_mismatch():
    from demosaic.noise import add_noise
    from demosaic.phase_harmonic import green_pair
    from demosaic.phase_noise_floor import estimate_variance_floor

    colors = np.array([2, 1, 1, 0])
    tint = np.array([0.8552155451259615, 1, 0.6654494000859297])
    base = np.broadcast_to((tint * 0.00027812224246522726)[:, None, None], (3, 512, 512)).copy()
    packed = np.stack([base[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    packed = add_noise(
        torch.from_numpy(packed)[None].float(),
        0.00128,
        6.553600000000001e-6,
        black_level=0.03,
        generator=torch.Generator().manual_seed(202611171069),
    )[0].numpy()
    variance = np.maximum(packed, 0) * 0.0014635775921166604 + 1.0715704128646712e-6
    floor = estimate_variance_floor(green_pair(packed, variance, colors))
    assert floor["added_pixel_variance"] > 3e-6
    raw = np.empty((512, 512), np.float32)
    for p in range(4):
        raw[p // 2 :: 2, p % 2 :: 2] = packed[p]
    value, info = refine_phase_harmonics(
        raw, colors, base, shot=0.0014635775921166604, read=1.0715704128646712e-6, envelope="wide"
    )
    np.testing.assert_array_equal(value, base.astype(np.float32))
    assert info["context"]["variance_floor_positive_windows"] == 1
