"""Fixed native-band controls and gradient projections for feature-loss diagnosis."""

import numpy as np


def basis():
    c = np.cos(np.pi * (np.arange(16)[None] + 0.5) * np.arange(16)[:, None] / 16) * np.sqrt(2 / 16)
    c[0] /= np.sqrt(2)
    return c


def annulus():
    radius = np.hypot(np.arange(16)[:, None] / 32, np.arange(16)[None] / 32)
    return (radius >= 1 / 8) & (radius < 1 / 3)


def blocks(value):
    value = np.asarray(value, np.float64)
    if value.shape == (1, 3, 256, 256):
        value = value[..., 48:208, 48:208]
    if value.shape != (1, 3, 160, 160) or not np.isfinite(value).all():
        raise ValueError("Need one finite RGB native256 context or native160 interior")
    return value.reshape(1, 3, 10, 16, 10, 16).transpose(0, 2, 4, 1, 3, 5).reshape(100, 3, 16, 16)


def coefficients(value):
    c = basis()
    return (c @ blocks(value) @ c.T)[..., annulus()]


def reconstruct(values):
    values = np.asarray(values, np.float64)
    if values.shape != (100, 3, int(annulus().sum())) or not np.isfinite(values).all():
        raise ValueError("Need finite selected-annulus coefficients for100 RGB blocks")
    full = np.zeros((100, 3, 16, 16), np.float64)
    full[..., annulus()] = values
    c = basis()
    native = (
        (c.T @ full @ c).reshape(10, 10, 3, 16, 16).transpose(2, 0, 3, 1, 4).reshape(1, 3, 160, 160)
    )
    canvas = np.zeros((1, 3, 256, 256), np.float64)
    canvas[..., 48:208, 48:208] = native
    return canvas


def reference_mask(target, wb, matrix, bin_index):
    if isinstance(bin_index, bool) or bin_index not in range(5):
        raise ValueError("Choose a fixed reference contrast bin0..4")
    rgb = np.einsum(
        "bij,bjhw->bihw",
        matrix.astype(np.float64),
        target.astype(np.float64) * wb.astype(np.float64)[..., None, None],
    )
    color = blocks(rgb)
    luma = np.einsum("c,bchw->bhw", np.array([0.2126, 0.7152, 0.0722]), color)
    c = basis()
    selected = (c @ luma @ c.T)[..., annulus()]
    means = luma.mean((-1, -2))
    rms = np.sqrt(np.sum(selected**2, axis=-1) / 256)
    valid = (
        ((color >= 0) & (color <= 1)).all((1, 2, 3))
        & (means >= 0.02)
        & (means <= 0.9)
        & (rms >= 1e-5)
    )
    contrast = rms / np.maximum(means, 1e-12)
    edges = (0, 0.02, 0.05, 0.1, 0.2, np.inf)
    keep = valid & (contrast >= edges[bin_index]) & (contrast < edges[bin_index + 1])
    if not keep.any():
        raise ValueError("No reference-supported blocks in the declared bin")
    return keep


def controlled_bands(target, mask):
    """Keep DC/other bands; contrast loss, wrong phase and orthogonal wrong detail."""
    if target.shape != (1, 3, 256, 256) or mask.shape != (100,) or mask.dtype != bool:
        raise ValueError("Need native256 target and100 reference-selected Boolean blocks")
    t = coefficients(target)
    t[~mask] = 0
    q = np.roll(t, 1, axis=-1)
    norm2 = np.sum(t * t, axis=-1, keepdims=True)
    q -= np.sum(q * t, axis=-1, keepdims=True) / np.maximum(norm2, 1e-30) * t
    degenerate = (np.sum(q * q, axis=-1, keepdims=True) < 1e-20 * norm2) & (norm2 > 0)
    alternate = np.eye(t.shape[-1])[np.argmin(np.abs(t), axis=-1)]
    alternate -= np.sum(alternate * t, axis=-1, keepdims=True) / np.maximum(norm2, 1e-30) * t
    q = np.where(degenerate, alternate, q)
    q *= np.sqrt(norm2 / np.maximum(np.sum(q * q, axis=-1, keepdims=True), 1e-30))
    band, wrong = reconstruct(t), reconstruct(q)
    variants = {
        "reference": target.copy(),
        "half-band": (target - 0.5 * band).astype(np.float32),
        "phase-flip": (target - 2 * band).astype(np.float32),
        "orthogonal-band": (target - band + wrong).astype(np.float32),
    }
    return variants, band, wrong


def gradient_projection(gradient, prediction, target, mask):
    g, p, t = [coefficients(v)[mask] for v in (gradient, prediction, target)]
    error = p - t
    dot = float(np.sum(g * error))
    magnitude = float(np.linalg.norm(g) * np.linalg.norm(error))
    energy = float(np.sum(t * t))
    return {
        "blocks": int(mask.sum()),
        "directional_derivative_toward_true_band": -dot,
        "descent_cosine_to_true_band_correction": dot / magnitude if magnitude else None,
        "negative_gradient_target_gain_slope": -float(np.sum(g * t)) / energy if energy else None,
        "target_band_projection_gain": float(np.sum(p * t)) / energy if energy else None,
        "gradient_band_L2": float(np.linalg.norm(g)),
        "band_error_L2": float(np.linalg.norm(error)),
    }
