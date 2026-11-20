"""Local mesh recovery with a phase prior from disjoint exterior Bayer samples."""

import numpy as np

from ._mesh_pooled import (
    _CENTER_BACKGROUND,
    _CORE,
    _SMOOTH,
    _STRIDE,
    _footprint,
    _rgb,
    _variance,
    _wave,
    _windows,
)
from .mesh_carrier_fit import _WINDOW, _positions

_CENTER = _WINDOW - 2 * _CORE[0].start
_RING = np.ones((_WINDOW, _WINDOW), dtype=bool)
_RING[_CORE] = False
_CENTER_PIXELS = np.ones((_CENTER, _CENTER), dtype=bool)
_PACKED_CORE = slice(_CORE[0].start // 2, -_CORE[0].start // 2)
_STATES = ((0,), (1,), (0, 1))
_LOG_PRIOR_ODDS = -6.0
_INCLUSION_CUTOFF = 0.2


def _evidence(windows, positions, wave, smooth, keep, shot, read):
    """Remove a separate smooth background on each green lattice."""
    matrices, moments = [], []
    for observed, (y, x) in zip(windows, positions, strict=True):
        mask = keep[y::2, x::2]
        background = smooth[y::2, x::2][mask]
        design = wave[y::2, x::2][mask]
        trend = np.linalg.pinv(background, rcond=1e-8) @ design
        residual = design - background @ trend
        raw = observed[:, mask]
        precision = 1 / _variance(raw, shot, read)
        matrices.append(precision[:, None, None] * (residual.T @ residual))
        moments.append(precision[:, None] * (raw @ residual))
    return np.sum(matrices, axis=0), np.sum(moments, axis=0)


def _ring_prior(gram, moment):
    covariance = np.linalg.pinv(gram, hermitian=True, rcond=1e-8)
    coefficient = (covariance @ moment[..., None])[..., 0].reshape(-1, 2, 2)
    variance = covariance.diagonal(axis1=-2, axis2=-1).reshape(-1, 2, 2).sum(axis=-1)
    energy = np.sum(coefficient**2, axis=-1)
    power = np.maximum(0, energy - variance)
    amplitude = np.sqrt(power)
    shrinkage = np.sqrt(power / energy.clip(min=1e-20))
    mean = (coefficient * shrinkage[..., None]).reshape(-1, 4)
    return mean, 0.00065 + 0.60 * amplitude


def _average_models(gram, moment, mean, deviation):
    """Integrate the coefficient prior for each subset of supported directions."""
    count = len(moment)
    estimates = np.zeros((count, 4, 4))
    scores = np.zeros((count, 4))
    included = np.zeros((4, 2))
    for index, directions in enumerate(_STATES, start=1):
        columns = [2 * direction + component for direction in directions for component in range(2)]
        diagonal = np.arange(len(columns))
        precision = np.repeat(1 / deviation[:, directions] ** 2, 2, axis=-1)
        prior = mean[:, columns]
        system = gram[:, columns][:, :, columns].copy()
        system[:, diagonal, diagonal] += precision
        location = precision * prior + moment[:, columns]
        update = np.linalg.solve(system, location[..., None])[..., 0]
        _, logdet = np.linalg.slogdet(system)
        gain = np.einsum("ni,ni->n", location, update)
        normalizer = np.sum(np.log(precision) - prior * (prior * precision), axis=-1)
        scores[:, index] = 0.5 * (normalizer - logdet + gain) + _LOG_PRIOR_ODDS * len(directions)
        estimates[:, index, columns] = update
        included[index, list(directions)] = 1
    probability = np.exp(scores - scores.max(axis=1, keepdims=True))
    probability /= probability.sum(axis=1, keepdims=True)
    average = np.einsum("ns,nsf->nf", probability, estimates).reshape(-1, 2, 2)
    return average, probability @ included


def _refine(parent, scene, colors, origin, frequencies, shot, read, neutral):
    positions = _positions(colors, *origin)
    greens = tuple(_footprint(scene, origin, position) for position in positions)
    if any(not np.isfinite(lattice).all() for lattice in greens):
        return parent
    windows = tuple(_windows(lattice, _WINDOW // 2, _STRIDE // 2) for lattice in greens)
    wave = _wave(_WINDOW, frequencies).reshape(_WINDOW, _WINDOW, 4)

    mean, deviation = _ring_prior(*_evidence(windows, positions, wave, _SMOOTH, _RING, shot, read))
    core = wave[_CORE]
    center = tuple(window[:, _PACKED_CORE, _PACKED_CORE] for window in windows)
    gram, moment = _evidence(
        center, positions, core, _CENTER_BACKGROUND, _CENTER_PIXELS, shot, read
    )
    estimated, inclusion = _average_models(gram, moment, mean, deviation)
    gate = np.maximum(0, (inclusion - _INCLUSION_CUTOFF) / (1 - _INCLUSION_CUTOFF))
    if not gate.any():
        return parent

    design = np.concatenate((_CENTER_BACKGROUND, core), axis=-1).reshape(_CENTER**2, -1)
    samples = _windows(parent[1], _CENTER, _STRIDE).reshape(-1, _CENTER**2)
    inherited = (samples @ np.linalg.pinv(design, rcond=1e-8)[-4:].T).reshape(-1, 2, 2)
    fit = np.linalg.pinv(gram, hermitian=True, rcond=1e-8) @ moment[..., None]
    cap = np.linalg.norm(fit.reshape(-1, 2, 2), axis=-1)
    delta = estimated - inclusion[..., None] * inherited
    norm = np.linalg.norm(delta, axis=-1).clip(min=1e-15)
    delta *= np.minimum(1, inclusion * cap / norm)[..., None]
    delta *= (gate / np.maximum(inclusion, 1e-15))[..., None]
    patches = np.einsum("yxf,nf->nyx", core, delta.reshape(-1, 4))
    result = parent + _rgb(patches, neutral, parent.dtype)
    return result if np.isfinite(result).all() else parent
