"""Verify a Bayer phase fitted outside each station's local neighborhood."""

from itertools import product

import numpy as np

from ._mesh_near_phase import _evidence_scores, _pixel_map
from ._mesh_weak_phase import _CELL, _SIDE, _SITES, _background, _carrier, _variance
from .mesh_carrier_fit import _ROI_SIZE, _sites

_DONOR_SIZE = 32
_DONORS = np.array(tuple(product(range(0, _ROI_SIZE, _DONOR_SIZE), repeat=2)))
_CENTERS = np.indices((_SIDE, _SIDE), dtype=np.float64).reshape(2, -1)[::-1].T
_DISTANCE = (_CENTERS[:, None] + 0.5) * _CELL - 0.5 - (_DONORS + (_DONOR_SIZE - 1) / 2)
# A square of three stations centered on the held station must miss the donor.
_DISJOINT = (np.abs(_DISTANCE) >= (3 * _CELL + _DONOR_SIZE) / 2).any(axis=-1)


def _estimate_phases(scene, origin, frequencies, shot, read):
    coefficients, precision = [], []
    x, y = origin
    for dx, dy in _DONORS:
        waves = _carrier(_DONOR_SIZE, dx, dy, frequencies).reshape(_DONOR_SIZE, _DONOR_SIZE, 4)
        basis = np.concatenate((_background(_DONOR_SIZE), waves), axis=-1)
        estimates, weights = [], []
        for r, c in _SITES:
            pixels = _sites(scene, x + dx, y + dy, _DONOR_SIZE, r, c).astype(np.float64).ravel()
            if not np.isfinite(pixels).all():
                return None
            fit = np.linalg.pinv(basis[r::2, c::2].reshape(pixels.size, -1), rcond=1e-8)[-4:]
            estimates.append((fit @ pixels).reshape(2, 2))
            variance = _variance(pixels.mean(), shot, read)
            weights.append(1 / (variance * np.square(fit).sum(axis=1).reshape(2, 2).mean(axis=1)))
        coefficients.append(estimates)
        precision.append(weights)
    return np.asarray(coefficients), np.asarray(precision)


def _pool_phase(coefficients, precision, frequency, greens):
    normal = frequency / np.linalg.norm(frequency)
    tangent = normal[::-1] * (-1, 1)
    distance = (_DISTANCE @ normal / 50) ** 2 + (_DISTANCE @ tangent / 75) ** 2
    weights = _DISJOINT * np.exp(-0.5 * distance)
    mass = weights @ precision
    mean = np.einsum("nd,dsi,ds->nsi", weights, coefficients, precision) / mass[..., None]
    information = mass**2 / (weights**2 @ precision)
    amplitude = np.linalg.norm(mean, axis=-1)
    corrected = np.sqrt(np.maximum(0, np.sum(coefficients**2, axis=-1) - 2 / precision))
    typical = (weights @ (corrected * precision)) / mass
    reliable = (amplitude**2 * information >= 16) & (amplitude >= 0.55 * typical)
    unit = mean / np.maximum(1e-15, amplitude[..., None])
    agree = (unit[:, greens[0]] * unit[:, greens[1]]).sum(axis=-1)
    eligible = reliable[:, greens].all(axis=-1) & (agree >= 0.5)
    return np.where(reliable[..., None], mean, 0), eligible


def _internal_taper(scene, origin, sites, frequencies, direction, shot, read, estimates):
    if estimates is None:
        return None
    coefficients, precision = estimates
    greens = tuple(2 * r + c for r, c in sites)
    phase, eligible = _pool_phase(
        coefficients[..., direction, :], precision[..., direction], frequencies[direction], greens
    )
    if not eligible.any():
        return None
    raw = [_sites(scene, *origin, _ROI_SIZE, r, c) for r, c in _SITES]
    pooled, lesser = _evidence_scores(raw, phase, frequencies, direction, greens, shot, read)
    score = np.minimum(np.minimum(pooled, lesser + 1.5), 2 * lesser)
    strength = np.where(eligible, np.clip((score - 1.5) / 2, 0, 1), 0)
    own = strength.reshape(_SIDE, _SIDE).repeat(_CELL, axis=0).repeat(_CELL, axis=1)
    return np.minimum(_pixel_map(strength), own)
