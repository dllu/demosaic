"""Continuous measured-green frequency search on actual square RAW contexts.

This adaptive search reuses noisy input. Its cross power and refitted WLS
covariance are not calibrated confidence. Local inactive gates are handled
separately by the reconstruction policy.
"""

import numpy as np

from .phase_harmonic import _geometry


def frequency_fit(packed, colors, frequency, max_radius=0.22):
    """Maximize signed cross-DFT within 1.5 bins, on observed greens only.

    Phase-specific affine detrending and original Hann taper are
    fixed before the search. Physical CFA offsets are retained. This is adaptive
    reuse of noisy input, not calibrated confidence or independent validation.
    """
    packed = np.asarray(packed, dtype=np.float64)
    colors = np.asarray(colors)
    frequency = np.asarray(frequency, dtype=np.float64)
    if (
        packed.ndim != 3
        or packed.shape[0] != 4
        or packed.shape[1] != packed.shape[2]
        or packed.shape[1] < 128
        or not np.isfinite(packed).all()
        or colors.shape != (4,)
        or not np.issubdtype(colors.dtype, np.integer)
        or tuple(colors) not in {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
        or frequency.shape != (2,)
        or not np.isfinite(frequency).all()
    ):
        raise ValueError(
            "Require a finite square packed RAW field>=128, a standard CFA and a physical frequency"
        )
    if not np.isfinite(max_radius) or not 0.03 <= max_radius <= 0.34:
        raise ValueError("Frequency radius must lie between .03 and .34")
    if not (
        0.03 <= np.hypot(*frequency) <= max_radius
        and frequency[1] > 0
        and np.max(np.abs(frequency)) < 0.25
    ):
        raise ValueError(
            "Frequency must remain in the selected positive-fy annulus and component bounds"
        )
    n = packed.shape[1]
    radius = 1.5
    basis, window, inverse = _geometry((n, n))
    yy, xx = np.mgrid[:n, :n]
    planes = []
    for p in np.flatnonzero(np.asarray(colors) == 1):
        value = np.asarray(packed[p], np.float64)
        beta = inverse @ np.einsum("hwi,hw,hw->i", basis, window**2, value)
        v = window * (value - np.einsum("hwi,i->hw", basis, beta))
        x = (2 * xx + p % 2 - (n - 0.5)) / (2 * n)
        y = (2 * yy + p // 2 - (n - 0.5)) / (2 * n)
        a = np.exp(
            -2j * np.pi * (frequency[0] * (2 * xx + p % 2) + frequency[1] * (2 * yy + p // 2))
        )
        planes.append((v * a, np.stack([x, y])))
    calls = 0

    def evaluate(delta):
        nonlocal calls
        calls += 1
        s, derivatives, hessians = [], [], []
        for value, coord in planes:
            a = value * np.exp(-2j * np.pi * np.einsum("i,ihw->hw", delta, coord))
            s.append(a.sum())
            derivatives.append(-2j * np.pi * np.einsum("hw,ihw->i", a, coord))
            hessians.append(-4 * np.pi**2 * np.einsum("hw,ihw,jhw->ij", a, coord, coord))
        score = float(np.real(s[0] * np.conj(s[1])))
        grad = np.real(derivatives[0] * np.conj(s[1]) + s[0] * np.conj(derivatives[1]))
        hess = np.real(
            hessians[0] * np.conj(s[1])
            + s[0] * np.conj(hessians[1])
            + np.outer(derivatives[0], np.conj(derivatives[1]))
            + np.outer(derivatives[1].conj(), derivatives[0])
        )
        return score, grad, hess

    delta = np.zeros(2)
    original = evaluate(delta)[0]
    best = original
    # A small deterministic grid avoids Newton following the wrong local flank.
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            candidate = np.array([dx, dy], dtype=np.float64)
            fx, fy = np.asarray(frequency) + candidate / (2 * n)
            if not (
                0.03 <= np.hypot(fx, fy) <= max_radius and fy > 0 and max(abs(fx), abs(fy)) < 0.25
            ):
                continue
            score = evaluate(candidate)[0]
            if score > best:
                best, delta = score, candidate
    for _ in range(12):
        score, grad, hess = evaluate(delta)
        top = float(np.linalg.eigvalsh(hess).max())
        regular = max(0, top + max(abs(score), 1e-30) * 1e-6)
        step = -np.linalg.solve(hess - np.eye(2) * regular, grad)
        step *= min(1, 0.5 / max(float(np.linalg.norm(step)), 1e-30))
        accepted = False
        for shrink in [1, 0.5, 0.25, 0.125]:
            trial = np.clip(delta + shrink * step, -radius, radius)
            fx, fy = np.asarray(frequency) + trial / (2 * n)
            if not (
                0.03 <= np.hypot(fx, fy) <= max_radius and fy > 0 and max(abs(fx), abs(fy)) < 0.25
            ):
                continue
            value = evaluate(trial)[0]
            if value > best:
                delta, best, accepted = trial, value, True
                break
        if not accepted or np.linalg.norm(shrink * step) < 1e-5:
            break
    result = tuple(np.asarray(frequency) + delta / (2 * n))
    return result, {
        "delta_bins_xy": delta.tolist(),
        "original_cross": original,
        "refined_cross": best,
        "evaluations": calls,
    }
