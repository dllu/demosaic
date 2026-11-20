"""Use a fixed exterior RAW phase to check local weak-carrier support."""

from functools import lru_cache

import numpy as np
from scipy.ndimage import map_coordinates

from .mesh_carrier_fit import _DONOR, _ROI_SIZE, _donor_boxes, _sites

_CELL = 16
_SIDE = _ROI_SIZE // _CELL
_SITES = tuple(np.ndindex(2, 2))
_PIXEL_COORDS = (np.indices((_ROI_SIZE, _ROI_SIZE), dtype=np.float64) + 0.5) / _CELL - 0.5
_GAIN = 0.9731861532279491
_CUTOFF = 2.5


@lru_cache(maxsize=2)
def _background(size):
    y, x = (np.indices((size, size), dtype=np.float64) - (size - 1) / 2) / size
    return np.stack((np.ones_like(x), x, y, x * x, x * y, y * y), axis=-1)


def _carrier(size, dx, dy, frequencies):
    y, x = np.indices((size, size), dtype=np.float64)
    cycles = (x + dx)[..., None] * frequencies[:, 0] + (y + dy)[..., None] * frequencies[:, 1]
    phase = 2 * np.pi * cycles
    return np.stack((np.cos(phase), np.sin(phase)), axis=-1)


def _variance(mean, shot, read):
    return np.maximum(2e-11, shot * np.maximum(0, mean) + read)


def _exterior_phase(scene, origin, greens, frequencies, weak, shot, read, clearance):
    x, y = origin
    coefficients = []
    information = []
    for left, top in _donor_boxes(x, y, clearance):
        wave = _carrier(_DONOR, left - x, top - y, frequencies).reshape(_DONOR, _DONOR, 4)
        design = np.concatenate((_background(_DONOR), wave), axis=-1)
        fitted, precision = [], []
        for row, column in _SITES:
            # Express each donor in the same absolute Bayer phase as the query.
            r, c = (row + y - top) % 2, (column + x - left) % 2
            values = _sites(scene, left, top, _DONOR, r, c).ravel()
            if not np.isfinite(values).all():
                fitted.append(np.zeros(2))
                precision.append(0.0)
                continue
            inverse = np.linalg.pinv(design[r::2, c::2].reshape(values.size, -1), rcond=1e-8)
            projection = inverse[6 + 2 * weak : 8 + 2 * weak]
            variance = _variance(values.mean(), shot, read)
            fitted.append(projection @ values)
            precision.append(1 / (variance * np.square(projection).sum(axis=1).mean()))
        coefficients.append(fitted)
        information.append(precision)
    estimates, weights = np.asarray(coefficients), np.asarray(information)
    total = weights.sum(axis=0)
    consensus = np.einsum("dci,dc->ci", estimates, weights) / np.maximum(1e-12, total)[:, None]
    radii = np.linalg.norm(estimates, axis=-1)
    scale = (radii * weights).sum(axis=0) / np.maximum(1e-12, total)
    norm = np.linalg.norm(consensus, axis=-1)
    reliable = (norm >= 0.65 * scale) & (norm**2 * total >= 16)
    if any(not reliable[2 * r + c] for r, c in greens):
        return None
    return consensus * reliable[:, None]


def _cells(array):
    half = _CELL // 2
    return (
        array.reshape(_SIDE, half, _SIDE, half, *array.shape[2:])
        .swapaxes(1, 2)
        .reshape(_SIDE * _SIDE, half * half, *array.shape[2:])
    )


def _taper(scene, origin, greens, frequencies, weak, shot, read, clearance):
    """Scale only the new weak correction using a spatially fixed prediction."""
    if any(not np.isfinite(_sites(scene, *origin, _ROI_SIZE, *site)).all() for site in _SITES):
        return _GAIN
    phase = _exterior_phase(scene, origin, greens, frequencies, weak, shot, read, clearance)
    if phase is None:
        return _GAIN
    wave = _carrier(_ROI_SIZE, 0, 0, frequencies)
    moment = np.zeros(_SIDE * _SIDE)
    precision = np.zeros_like(moment)
    for (r, c), p in zip(_SITES, phase, strict=True):
        values = _cells(_sites(scene, *origin, _ROI_SIZE, r, c)).astype(np.float64)
        variance = _variance(values.mean(axis=1), shot, read)
        strong = _cells(wave[r::2, c::2, 1 - weak])
        smooth = _background(_CELL)[r::2, c::2].reshape(1, values.shape[1], 6)
        nuisance = np.concatenate((np.broadcast_to(smooth, (*values.shape, 6)), strong), axis=-1)
        template = _cells(wave[r::2, c::2, weak]) @ p
        projection = (np.linalg.pinv(nuisance, rcond=1e-8) @ template[..., None])[..., 0]
        template -= np.einsum("npi,ni->np", nuisance, projection)
        moment += np.einsum("np,np->n", template, values) / variance
        precision += np.einsum("np,np->n", template, template) / variance
    score = moment / np.sqrt(np.maximum(1e-10, precision))
    local = map_coordinates(
        score.reshape(_SIDE, _SIDE), _PIXEL_COORDS, order=1, mode="nearest", prefilter=False
    )
    return _GAIN * np.clip(1 + (local - _CUTOFF) / 2, 0, 1)
