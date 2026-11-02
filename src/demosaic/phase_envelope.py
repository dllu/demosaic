"""Local green sine/cosine evidence transports both phase and amplitude.

Selection, affine fitting and variance estimation reuse the same noisy input.
The conditional covariance is not calibrated confidence or a false-positive rate.
"""

import numpy as np

from .phase_harmonic import fit_patch_harmonics, native_envelope, separable_sum


def local_green_phasor(residual, variance, colors, phase_planes, frequency, sigma_native=32):
    """Fit sine/cosine coefficients at physical packed-cell centers.

    For each Gaussian neighborhood, G = sum(k*t*t'/var), b = sum(k*r*t/var),
    H = sum(k²*t*t'/var). Coefficients are G^-1 b and their conditional noise
    covariance is G^-1 H G^-1. The two greens have distinct shifted kernels.
    Fitted frequency/affine backgrounds and observed variance are held fixed in
    this propagation; their estimation/selection uncertainty is not included.
    """
    if sigma_native <= 0 or not np.isfinite(sigma_native):
        raise ValueError("Local phasor scale must be finite and positive")
    h, w = residual.shape[-2:]
    yy, xx = np.mgrid[:h, :w]
    fx, fy = frequency
    rhs = np.zeros((2, h, w))
    gram = np.zeros((3, h, w))
    noise = np.zeros_like(gram)
    sigma = sigma_native / 2
    radius = int(np.ceil(4 * sigma))
    coordinates = np.arange(-radius, radius + 1)
    for p in np.flatnonzero(np.asarray(colors) == 1):
        oy, ox = divmod(int(p), 2)
        angle = 2 * np.pi * (fx * (2 * xx + ox) + fy * (2 * yy + oy))
        cos, sin = np.cos(angle), np.sin(angle)
        var = variance[p].clip(1e-10)
        ky = np.exp(-0.5 * ((coordinates - (oy - 0.5) / 2) / sigma) ** 2)
        kx = np.exp(-0.5 * ((coordinates - (ox - 0.5) / 2) / sigma) ** 2)
        ky, kx = ky / ky.sum(), kx / kx.sum()
        for i, t in enumerate([cos, sin]):
            rhs[i] += separable_sum((residual[p] - phase_planes[p]) * t / var, ky, kx)
        for i, t in enumerate([cos * cos, cos * sin, sin * sin]):
            gram[i] += separable_sum(t / var, ky, kx)
            noise[i] += separable_sum(t / var, ky**2, kx**2)
    a, b, d = gram
    det = np.maximum(a * d - b * b, 1e-32)
    ia, ib, id = d / det, -b / det, a / det
    c = ia * rhs[0] + ib * rhs[1]
    s = ib * rhs[0] + id * rhs[1]
    h0, h1, h2 = noise
    v0 = ia * ia * h0 + 2 * ia * ib * h1 + ib * ib * h2
    v1 = ia * ib * h0 + (ia * id + ib * ib) * h1 + ib * id * h2
    v2 = ib * ib * h0 + 2 * ib * id * h1 + id * id * h2
    power = np.maximum(
        0, (v2 * c * c - 2 * v1 * c * s + v0 * s * s) / np.maximum(v0 * v2 - v1 * v1, 1e-32)
    )
    return (
        np.stack([c, s]),
        power,
        {"rhs": rhs, "gram": gram, "noise": noise, "covariance": np.stack([v0, v1, v2])},
    )


def correct_complex_patch(packed, variance, colors, base):
    """Fixed local complex envelope for the v1 input-selected global phasors.

    Joint local green coefficients determine a complex ratio to the global green
    phasor. Shrink by max(0,1-9/power), cap its magnitude at3, and rotate/scale all
    global RGB phasors together. The global gate and32-pixel aprons are retained.
    Neither target/reference nor RNG enters the correction.
    """
    fitted = fit_patch_harmonics(packed, variance, colors, base)
    base = fitted["base"]
    peaks = fitted["peaks"]
    if not peaks:
        return base.copy(), {"peaks": []}
    beta, cov = fitted["beta"], fitted["covariance"]
    planes = np.stack(
        [(fitted["plane"] @ beta[3 * p : 3 * p + 3]).reshape(128, 128) for p in range(4)]
    )
    yy, xx = np.mgrid[:256, :256]
    field = np.zeros_like(base)
    details = []
    for k, (fx, fy, score) in enumerate(peaks):
        ids = [12 + 6 * k + 2, 12 + 6 * k + 3]
        g = beta[ids]
        power = float(g @ np.linalg.solve(cov[np.ix_(ids, ids)], g))
        gate = max(0, 1 - 9 / max(power, 1e-12))
        if gate == 0:
            details.append({"gate": 0})
            continue
        coeff, lp, _ = local_green_phasor(
            fitted["residual"], fitted["variance"], fitted["colors"], planes, (fx, fy)
        )
        re = (g[0] * coeff[0] + g[1] * coeff[1]) / float(g @ g)
        im = (g[1] * coeff[0] - g[0] * coeff[1]) / float(g @ g)
        amplitude = np.hypot(re, im)
        scale = np.minimum(1, 3 / np.maximum(amplitude, 1e-16)) * np.maximum(
            0, 1 - 9 / np.maximum(lp, 1e-16)
        )
        re = native_envelope(re * scale)
        im = native_envelope(im * scale)
        angle = 2 * np.pi * (fx * xx + fy * yy)
        for c in range(3):
            i = 12 + 6 * k + 2 * c
            co = beta[i] * re + beta[i + 1] * im
            si = beta[i + 1] * re - beta[i] * im
            field[c] += gate * (co * np.cos(angle) + si * np.sin(angle))
        details.append(
            {
                "gate": gate,
                "local_active_fraction": float(np.mean(scale > 0)),
                "mean_amplitude": float(np.mean(amplitude * scale)),
            }
        )
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    return base + field * taper[None], {"peaks": peaks, "local": details, "complex_shrink": 9}
