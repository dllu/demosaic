"""Known physical carriers, search bounds, exact bypasses and refined inference."""

import numpy as np
import pytest

from demosaic.phase_frequency import fit_refined, frequency_fit
from demosaic.phase_harmonic import refine_phase_harmonics
from demosaic.phase_tv import correct_edge_phase_patch

LAYOUTS = [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)]


def wave(colors, frequency):
    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    carrier = np.cos(2 * np.pi * (frequency[0] * xx + frequency[1] * yy) + 0.7)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * carrier
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    return base, target, packed


@pytest.mark.parametrize("colors", LAYOUTS)
def test_physical_off_bin_frequency_recovers_with_phase_specific_affine_backgrounds(colors):
    truth = (-0.0713, 0.0532)
    _, _, packed = wave(colors, truth)
    yy, xx = np.mgrid[:128, :128]
    for p in range(4):
        packed[p] += 0.001 * p + 0.002 * xx / 127 - 0.003 * yy / 127
    before = packed.copy()
    actual, info = frequency_fit(packed, colors, (-0.0703125, 0.0546875))
    np.testing.assert_allclose(actual, truth, rtol=0, atol=2e-6)
    np.testing.assert_array_equal(packed, before)
    assert info["refined_cross"] > info["original_cross"]
    assert max(np.abs(info["delta_bins_xy"])) <= 1.5


@pytest.mark.parametrize(
    "truth,initial",
    [((0.026, 0.002), (0.03125, 0.00390625)), ((0.08, -0.003), (0.078125, 0.00390625))],
)
def test_search_cannot_escape_original_band_or_positive_frequency_half_plane(truth, initial):
    _, _, packed = wave(LAYOUTS[0], truth)
    actual, info = frequency_fit(packed, LAYOUTS[0], initial)
    assert 0.03 <= np.hypot(*actual) <= 0.22 and actual[1] > 0
    assert max(np.abs(info["delta_bins_xy"])) <= 1.5
    assert info["refined_cross"] >= info["original_cross"]


def test_refined_wave_improves_native_error_and_reports_actual_search():
    colors = LAYOUTS[0]
    base, target, packed = wave(colors, (-0.0713, 0.0532))
    variance = np.full_like(packed, 1e-7)
    fixed, _ = correct_edge_phase_patch(packed, variance, colors, base)
    actual, info = correct_edge_phase_patch(packed, variance, colors, base, refine_frequency=True)
    roi = (..., slice(48, 208), slice(48, 208))
    assert np.mean((actual[roi] - target[roi]) ** 2) < np.mean((fixed[roi] - target[roi]) ** 2)
    assert any("evaluations" in s for s in info["frequency_searches"])
    raw = np.empty((256, 256), np.float32)
    for p in range(4):
        raw[p // 2 :: 2, p % 2 :: 2] = packed[p]
    restored, metadata = refine_phase_harmonics(
        raw, colors, base, shot=0, read=1e-7, refine_frequency=True
    )
    assert restored.dtype == np.float32
    assert metadata["method"] == "local-phase-harmonic-v4"
    assert metadata["frequency_search"]["solves"] > 0
    assert metadata["refine_frequency"] and metadata["new_model_calls"] == 0


def test_original_inactive_gates_and_ADC_only_stay_off():
    colors = LAYOUTS[0]
    base, target, packed = wave(colors, (-0.0713, 0.0532))
    # The parent already contains the exact observed wave: no residual gate.
    fitted = fit_refined(packed, np.full_like(packed, 1e-7), colors, target)
    assert fitted["gate_limits"] == [0.0] * len(fitted["peaks"])
    actual, _ = correct_edge_phase_patch(
        packed, np.full_like(packed, 1e-7), colors, target, refine_frequency=True
    )
    np.testing.assert_array_equal(actual, target)
    actual, _ = correct_edge_phase_patch(
        packed, np.zeros_like(packed), colors, base, refine_frequency=True
    )
    np.testing.assert_array_equal(actual, base)


def test_invalid_frequency_or_envelope_rejected():
    base, _, packed = wave(LAYOUTS[0], (-0.0713, 0.0532))
    with pytest.raises(ValueError, match="annulus"):
        frequency_fit(packed, LAYOUTS[0], (0.1, -0.01))
    with pytest.raises(ValueError, match="finite"):
        frequency_fit(packed * np.nan, LAYOUTS[0], (0.1, 0.01))
    with pytest.raises(ValueError, match="edge"):
        refine_phase_harmonics(
            np.ones((256, 256)),
            LAYOUTS[0],
            base,
            shot=0,
            read=1e-7,
            envelope="complex",
            refine_frequency=True,
        )


def test_observed_clipping_retains_original_grid_TV_exactly():
    colors = LAYOUTS[0]
    base, _, packed = wave(colors, (-0.0713, 0.0532))
    packed[0, 40, 50] = 1.0
    variance = np.full_like(packed, 1e-7)
    fixed, _ = correct_edge_phase_patch(packed, variance, colors, base)
    guarded, info = correct_edge_phase_patch(packed, variance, colors, base, refine_frequency=True)
    np.testing.assert_array_equal(guarded, fixed)
    assert any(s.get("clipped_window_fallback") for s in info["frequency_searches"])
