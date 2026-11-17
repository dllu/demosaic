"""Exact weighted sinusoid benefits on the native Fourier grid, using A only."""

import numpy as np


def weighted_spectrum(raw, selected, nuisance, weights):
    """Added weighted-LS benefit of cosine/sine after nuisance projection.

    Weights contain only selected sensor samples and are normalized to mean1.
    Fourier sums compute the two-column Gram matrix and its projection against
    the weighted nuisance QR basis; frequency-dependent energy is retained.
    No value outside ``selected`` is read, including for normalization.
    """
    raw, selected, nuisance, weights = (
        np.asarray(raw, np.float64),
        np.asarray(selected),
        np.asarray(nuisance, np.float64),
        np.asarray(weights, np.float64),
    )
    if (
        raw.ndim != 2
        or selected.shape != (raw.size,)
        or selected.dtype != bool
        or nuisance.ndim != 2
        or nuisance.shape[0] != raw.size
        or nuisance.shape[1] < 1
        or weights.shape != (int(selected.sum()),)
        or len(weights) < max(16, nuisance.shape[1] + 2)
        or not np.isfinite(raw.ravel()[selected]).all()
        or not np.isfinite(nuisance[selected]).all()
        or not np.isfinite(weights).all()
        or np.any(weights <= 0)
    ):
        raise ValueError("Require finite discovery samples, nuisance and positive A-only weights")
    scale = weights / weights.mean()
    sigma = np.sqrt(scale)
    basis = nuisance[selected] * sigma[:, None]
    if np.linalg.matrix_rank(basis) != basis.shape[1]:
        raise ValueError("Require full-rank weighted nuisance support")
    q, _ = np.linalg.qr(basis, mode="reduced")
    values = raw.ravel()[selected] * sigma
    residual = values - q @ (q.T @ values)
    field = np.zeros(raw.shape)
    field.ravel()[selected] = residual * sigma
    cross = np.fft.fft2(field)
    field.ravel()[selected] = scale
    mass = np.fft.fft2(field)
    iy, ix = np.indices(raw.shape)
    double = mass[(2 * iy) % raw.shape[0], (2 * ix) % raw.shape[1]]
    cc = (scale.sum() + double.real) / 2
    ss = (scale.sum() - double.real) / 2
    cs = -double.imag / 2
    for column in q.T:
        field.ravel()[selected] = column * sigma
        transform = np.fft.fft2(field)
        cosine, sine = transform.real, -transform.imag
        cc -= cosine**2
        ss -= sine**2
        cs -= cosine * sine
    cosine, sine = cross.real, -cross.imag
    determinant = cc * ss - cs**2
    valid = determinant > 1e-10 * scale.sum() ** 2
    benefit = np.zeros(raw.shape)
    benefit[valid] = (ss * cosine**2 - 2 * cs * cosine * sine + cc * sine**2)[valid] / determinant[
        valid
    ]
    return np.maximum(benefit, 0)


def discovery_weights(raw, selected, nuisance, *, shot, read, hann=False):
    """A-only analytic variance proxy, optionally times a fixed native Hann."""
    values = np.asarray(raw).ravel()[selected]
    proxy = nuisance[selected] @ np.linalg.lstsq(nuisance[selected], values, rcond=1e-10)[0]
    weights = 1 / (read + shot * np.maximum(proxy, 1e-6))
    if hann:
        axes = [0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(n) + 0.5) / n) for n in raw.shape]
        weights *= np.outer(*axes).ravel()[selected]
    return weights
