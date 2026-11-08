"""Orientation-conditioned whole-template projections, not isolated wire families.

Disjoint native Fourier sectors use the two fixed recipe normals. A residual
sector holds Nyquist axes and DC, avoiding ambiguous orientation there. The
energy-weighted gains exactly recompose the existing affine-detrended scalar.
No input selection, confidence, model fitting, or real-reference scoring occurs.
"""

import math

import numpy as np


def detrend(value):
    value = np.asarray(value, dtype=np.float64)
    if (
        value.ndim != 3
        or value.shape[0] != 3
        or min(value.shape[-2:]) < 16
        or not np.isfinite(value).all()
    ):
        raise ValueError("Expected finite native3xHxW RGB")
    h, w = value.shape[-2:]
    y, x = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    basis = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)
    q = np.linalg.qr(basis, mode="reduced")[0]
    flat = value.reshape(3, -1).T
    return (flat - q @ (q.T @ flat)).T.reshape(value.shape)


def sectors(shape, angles):
    if len(shape) != 2 or any(type(n) is not int or n < 16 or n % 2 for n in shape):
        raise ValueError("Expected even native axes>=16")
    if (
        len(angles) != 2
        or not all(math.isfinite(a) for a in angles)
        or abs(math.sin(angles[0] - angles[1])) < 1e-4
    ):
        raise ValueError("Expected two finite distinct orientation normals modulo pi")
    fy, fx = np.meshgrid(np.fft.fftfreq(shape[0]), np.fft.fftfreq(shape[1]), indexing="ij")
    score = np.stack([(fx * math.cos(a) + fy * math.sin(a)) ** 2 for a in angles])
    labels = np.argmax(score, axis=0)
    labels[(fx == 0) & (fy == 0) | (fx == -0.5) | (fy == -0.5)] = 2
    masks = np.stack([labels == i for i in range(3)])
    yy = (-np.arange(shape[0])) % shape[0]
    xx = (-np.arange(shape[1])) % shape[1]
    if not np.array_equal(masks, masks[:, yy][:, :, xx]):
        raise ArithmeticError("Orientation masks must be conjugate closed")
    assert np.all(masks.sum(0) == 1)
    return masks


def project(restored, present, empty, angles):
    if np.shape(restored) != np.shape(present) or np.shape(present) != np.shape(empty):
        raise ValueError("Native restored/present/empty shapes must match")
    t = detrend(np.asarray(present, dtype=np.float64) - empty)
    v = detrend(np.asarray(restored, dtype=np.float64) - empty)
    masks = sectors(t.shape[-2:], angles)
    ft, fv = [np.fft.fft2(a, norm="ortho") for a in [t, v]]
    power = np.sum(abs(ft) ** 2, axis=0)
    cross = np.sum((fv * ft.conj()).real, axis=0)
    total = float(np.sum(power))
    if total <= 0:
        raise ValueError("Nonzero constructed template required")
    records = []
    for i, mask in enumerate(masks):
        energy = float(np.sum(power[mask]))
        numerator = float(np.sum(cross[mask]))
        records.append(
            {
                "sector": i,
                "template_energy_fraction": energy / total,
                "template_energy": energy,
                "projection_numerator": numerator,
                "gain": numerator / energy if energy > 0 else None,
            }
        )
    gain = float(np.sum(cross) / total)
    spatial = float(np.sum(v * t) / np.sum(t * t))
    recomposed = sum(r["projection_numerator"] for r in records) / total
    if not np.isclose(gain, spatial, rtol=2e-12, atol=2e-12) or not np.isclose(
        gain, recomposed, rtol=2e-12, atol=2e-12
    ):
        raise ArithmeticError("Native Parseval/orientation decomposition failed")
    return {
        "whole_template_gain": gain,
        "spatial_whole_template_gain": spatial,
        "recomposed_gain": recomposed,
        "sectors": records,
        "scope": "Nearest-recipe-normal spectral sectors after full-context unweighted affine removal. Mask/envelope/intersection leakage remains; these are not exact isolated wire-family amplitudes. Residual sector includes Nyquist axes and DC.",
    }


def native_angles(recipe_angles, rotation, flip):
    """Normals after rot90 CCW in image coordinates, then horizontal flip.

    Array y increases downwards. No projective transform is accepted by this
    helper; callers must establish that the cached scene used only this D4 map.
    """
    if type(rotation) is not int or not 0 <= rotation < 4 or type(flip) is not bool:
        raise ValueError("Expected exact rot90 count0..3 and a boolean horizontal flip")
    result = []
    for angle in recipe_angles:
        if not math.isfinite(angle):
            raise ValueError("Expected finite recipe normals")
        transported = angle - rotation * math.pi / 2
        if flip:
            transported = math.pi - transported
        result.append(transported % math.pi)
    if len(result) != 2:
        raise ValueError("Expected exactly two recipe normals")
    return result
