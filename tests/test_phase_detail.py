"""Conditional amplitudes retain selection, physical colors and exact fallbacks."""

import numpy as np
import pytest

from demosaic import phase_cross
from demosaic.phase_harmonic import _fit_selected_harmonics
from demosaic.phase_tv import _correct_fitted_patch

PATTERNS = [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)]


def fitted_wave(colors, power):
    y, x = np.mgrid[:256, :256]
    frequency = (0.0713, 0.0532)
    wave = np.cos(2 * np.pi * (frequency[0] * x + frequency[1] * y) + 0.7)
    base = np.full((3, 256, 256), 0.02)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    fitted = _fit_selected_harmonics(
        packed, np.full_like(packed, 1e-7), np.array(colors), base, [(*frequency, 10)]
    )
    # Set a known global power while keeping the actual physical observations,
    # local covariance, phasor/support/refit and color transport unchanged.
    g = fitted["beta"][14:16]
    fitted["covariance"][14:16, 14:16] = np.eye(2) * (g @ g) / power
    return fitted


def fixed_support(monkeypatch, *, empty=False):
    support = np.zeros((1, 256, 256), bool)
    if not empty:
        support[:, 64:192, 48:208] = True
    calls = []

    def masks(*args, **kwargs):
        calls.append(True)
        return support, {"solver": {"converged": True}}

    monkeypatch.setattr(phase_cross, "cross_phase_masks", masks)
    return support[0], calls


@pytest.mark.parametrize("colors", PATTERNS)
@pytest.mark.parametrize("power", [18, 45])
def test_selected_wave_recovers_only_global_shrink_inside_same_support(monkeypatch, colors, power):
    fitted = fitted_wave(colors, power)
    support, _ = fixed_support(monkeypatch)
    baseline, _ = _correct_fitted_patch(fitted, sparse_support=True, cross_phase_support=True)
    actual, info = _correct_fitted_patch(
        fitted, sparse_support=True, cross_phase_support=True, selection_only_gate=True
    )
    base = fitted["base"]
    gate = 1 - 9 / power
    assert np.max(np.abs(actual - base)) > 1e-4
    np.testing.assert_allclose(actual - base, (baseline - base) / gate, rtol=2e-12, atol=2e-17)
    np.testing.assert_array_equal(actual[:, ~support], base[:, ~support])
    # The common scalar retains the preexisting physical RGB transport.
    np.testing.assert_allclose((actual - base)[0] / 0.0015, (actual - base)[1] / 0.002, atol=2e-12)
    assert info["local"][0]["applied_gate"] == 1


def test_inactive_or_rejected_support_cannot_restore_a_wave(monkeypatch):
    _, calls = fixed_support(monkeypatch, empty=True)
    for power in (8, 18):
        fitted = fitted_wave(PATTERNS[0], power)
        actual, _ = _correct_fitted_patch(
            fitted, sparse_support=True, cross_phase_support=True, selection_only_gate=True
        )
        np.testing.assert_array_equal(actual, fitted["base"])
    assert len(calls) == 1  # The inactive gate never reaches mask fitting.


@pytest.mark.parametrize("colors", PATTERNS)
def test_clipped_window_preserves_original_amplitude_policy(monkeypatch, colors):
    fitted = fitted_wave(colors, 18)
    fitted["searches"] = [{"clipped_window_fallback": True}]
    _, calls = fixed_support(monkeypatch)
    expected, _ = _correct_fitted_patch(fitted, sparse_support=True, cross_phase_support=True)
    actual, info = _correct_fitted_patch(
        fitted, sparse_support=True, cross_phase_support=True, selection_only_gate=True
    )
    np.testing.assert_array_equal(actual, expected)
    assert not calls and info["local"][0]["applied_gate"] == pytest.approx(0.5)


def test_selection_only_gate_requires_reciprocal_support():
    with pytest.raises(ValueError, match="require reciprocal"):
        _correct_fitted_patch(
            {"base": np.zeros((3, 256, 256)), "peaks": []}, selection_only_gate=True
        )
