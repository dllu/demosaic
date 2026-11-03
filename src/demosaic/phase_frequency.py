"""Small continuous frequency updates for already active measured-green waves.

This adaptive search reuses noisy input. Its cross power and refitted WLS
covariance are not calibrated confidence. Original inactive global gates stay off.
"""

import numpy as np

from .phase_harmonic import _fit_selected_harmonics, _geometry, fit_patch_harmonics


def frequency_fit(packed, colors, frequency):
    """Maximize signed cross-DFT within 1.5 bins, on observed greens only.

    Six-parameter phase-specific affine detrending and original Hann taper are
    fixed before the search. Physical CFA offsets are retained. This is adaptive
    reuse of noisy input, not calibrated confidence or independent validation.
    """
    packed = np.asarray(packed, dtype=np.float64)
    colors = np.asarray(colors)
    frequency = np.asarray(frequency, dtype=np.float64)
    if (
        packed.shape != (4, 128, 128)
        or not np.isfinite(packed).all()
        or colors.shape != (4,)
        or not np.issubdtype(colors.dtype, np.integer)
        or tuple(colors) not in {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
        or frequency.shape != (2,)
        or not np.isfinite(frequency).all()
    ):
        raise ValueError(
            "Require finite packed128 RAW, standard integer CFA, and a physical frequency"
        )
    if not (0.03 <= np.hypot(*frequency) <= 0.22 and frequency[1] > 0):
        raise ValueError("Frequency must remain in the original positive-fy annulus")
    radius = 1.5
    basis, window, inverse = _geometry((128, 128))
    yy, xx = np.mgrid[:128, :128]
    planes = []
    for p in np.flatnonzero(np.asarray(colors) == 1):
        value = np.asarray(packed[p], np.float64)
        beta = inverse @ np.einsum("hwi,hw,hw->i", basis, window**2, value)
        v = window * (value - np.einsum("hwi,i->hw", basis, beta))
        x = (2 * xx + p % 2 - 127.5) / 256
        y = (2 * yy + p // 2 - 127.5) / 256
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
            fx, fy = np.asarray(frequency) + candidate / 256
            if not (0.03 <= np.hypot(fx, fy) <= 0.22 and fy > 0):
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
            fx, fy = np.asarray(frequency) + trial / 256
            if not (0.03 <= np.hypot(fx, fy) <= 0.22 and fy > 0):
                continue
            value = evaluate(trial)[0]
            if value > best:
                delta, best, accepted = trial, value, True
                break
        if not accepted or np.linalg.norm(shrink * step) < 1e-5:
            break
    result = tuple(np.asarray(frequency) + delta / 256)
    return result, {
        "delta_bins_xy": delta.tolist(),
        "original_cross": original,
        "refined_cross": best,
        "evaluations": calls,
    }


def fit_refined(packed, variance, colors, base):
    old = fit_patch_harmonics(packed, variance, colors, base)
    if not old["peaks"]:
        return old
    # A clipped waveform violates the linear sinusoidal observation model.
    # Keep the complete original grid-TV fit for this window, including gates.
    if np.any(old["packed"] >= 1 - 1e-7):
        old["gate_limits"] = [1.0] * len(old["peaks"])
        old["searches"] = [{"clipped_window_fallback": True} for _ in old["peaks"]]
        return old
    gates, peaks, searches = [], [], []
    for k, (fx, fy, score) in enumerate(old["peaks"]):
        ids = [12 + 6 * k + 2, 12 + 6 * k + 3]
        g = old["beta"][ids]
        power = float(g @ np.linalg.solve(old["covariance"][np.ix_(ids, ids)], g))
        gate = max(0, 1 - 9 / max(power, 1e-12))
        gates.append(float(gate > 0))
        if gate:
            (fx, fy), info = frequency_fit(packed, colors, (fx, fy))
            others = [p for j, p in enumerate(old["peaks"]) if j != k] + peaks
            if any(np.hypot(fx - p[0], fy - p[1]) < 2 / 256 for p in others):
                fx, fy = old["peaks"][k][:2]
                info["collision_fallback"] = True
            searches.append(info)
        else:
            searches.append({"inactive_original_global_gate": True})
        peaks.append((fx, fy, score))
    new = _fit_selected_harmonics(old["packed"], old["variance"], old["colors"], old["base"], peaks)
    new["gate_limits"] = gates
    new["searches"] = searches
    return new
