"""Check weak detail with close Bayer measurements outside the delivery crop."""

import numpy as np
from scipy.ndimage import map_coordinates

from ._mesh_weak_phase import (
    _CELL,
    _GAIN,
    _PIXEL_COORDS,
    _SIDE,
    _SITES,
    _background,
    _carrier,
    _cells,
    _variance,
)
from .mesh_carrier_fit import _ROI_SIZE, _sites

_RIM = 32
_ALONG = range(0, _ROI_SIZE, _RIM)
_PATCHES = (
    *((x, y) for y in (-_RIM, _ROI_SIZE) for x in _ALONG),
    *((x, y) for x in (-_RIM, _ROI_SIZE) for y in _ALONG),
)
_STATION_CENTERS = (
    np.indices((_SIDE, _SIDE), dtype=np.float64).reshape(2, -1).T + 0.5
) * _CELL - 0.5
_NEIGHBOR_OFFSETS = np.array(((-1, 0), (-1, -1), (0, -1), (1, -1)))


def _observations(scene, origin, frequencies, weak, shot, read):
    x, y = origin
    coefficients = []
    information = []
    for dx, dy in _PATCHES:
        wave = _carrier(_RIM, dx, dy, frequencies).reshape(_RIM, _RIM, 4)
        design = np.concatenate((_background(_RIM), wave), axis=-1)
        measured = []
        precisions = []
        for r, c in _SITES:
            samples = _sites(scene, x + dx, y + dy, _RIM, r, c).ravel()
            if not np.isfinite(samples).all():
                return None
            projection = np.linalg.pinv(design[r::2, c::2].reshape(samples.size, -1), rcond=1e-8)
            weak_projection = projection[6 + 2 * weak : 8 + 2 * weak]
            measured.append(weak_projection @ samples)
            variance = _variance(samples.mean(), shot, read)
            precisions.append(1 / (variance * np.square(weak_projection).sum(axis=1).mean()))
        coefficients.append(measured)
        information.append(precisions)
    return np.asarray(coefficients), np.asarray(information)


def _pool_phases(coefficients, information, frequency, greens):
    centers = np.asarray(_PATCHES)[:, ::-1] + (_RIM - 1) / 2
    distance = _STATION_CENTERS[:, None] - centers
    normal = frequency[::-1] / np.linalg.norm(frequency)
    tangent = normal[::-1] * np.array((-1.0, 1.0))
    weights = np.exp(-0.5 * ((distance @ normal / 50) ** 2 + (distance @ tangent / 100) ** 2))
    total = weights @ information
    typical = weights @ (np.linalg.norm(coefficients, axis=-1) * information) / total
    mean = np.einsum("nd,dsi,ds->nsi", weights, coefficients, information) / total[..., None]
    precision = total**2 / (weights**2 @ information)
    amplitude = np.linalg.norm(mean, axis=-1)
    reliable = (amplitude >= 0.65 * typical) & (amplitude**2 * precision >= 16)
    unit = mean / np.maximum(1e-15, amplitude[..., None])
    agreement = (unit[:, greens[0]] * unit[:, greens[1]]).sum(axis=-1)
    eligible = reliable[:, greens].all(axis=-1) & (agreement >= 0.5)
    return np.where(reliable[..., None], mean, 0.0), eligible


def _evidence_scores(sites, coefficients, frequencies, weak, greens, shot, read):
    wave = _carrier(_ROI_SIZE, 0, 0, frequencies)
    moments, powers = [], []
    for samples, phase, (r, c) in zip(sites, coefficients.transpose(1, 0, 2), _SITES, strict=True):
        values = _cells(samples).astype(np.float64)
        variance = _variance(values.mean(axis=1), shot, read)
        strong = _cells(wave[r::2, c::2, 1 - weak])
        background = _background(_CELL)[r::2, c::2].reshape(1, values.shape[1], 6)
        nuisance = np.concatenate(
            (np.broadcast_to(background, (*values.shape, 6)), strong), axis=-1
        )
        template = (_cells(wave[r::2, c::2, weak]) @ phase[..., None])[..., 0]
        projection = (np.linalg.pinv(nuisance, rcond=1e-8) @ template[..., None])[..., 0]
        template -= np.einsum("npi,ni->np", nuisance, projection)
        moments.append(np.einsum("np,np->n", template, values) / variance)
        powers.append(np.einsum("np,np->n", template, template) / variance)
    moment, power = np.asarray(moments), np.asarray(powers)
    separate = moment / np.sqrt(np.maximum(1e-10, power))
    pooled = moment.sum(axis=0) / np.sqrt(np.maximum(1e-10, power.sum(axis=0)))
    return pooled, separate[list(greens)].min(axis=0)


def _signed_evidence(sites, coefficients, frequencies, weak, greens, shot, read):
    pooled, lesser_green = _evidence_scores(
        sites, coefficients, frequencies, weak, greens, shot, read
    )
    return np.minimum(pooled, lesser_green + 1.5)


def _local_phase(scene, origin, green_sites, frequencies, weak, shot, read):
    sites = [_sites(scene, *origin, _ROI_SIZE, r, c) for r, c in _SITES]
    if not all(np.isfinite(site).all() for site in sites):
        return None
    observations = _observations(scene, origin, frequencies, weak, shot, read)
    if observations is None:
        return None
    greens = tuple(2 * r + c for r, c in green_sites)
    phases, eligible = _pool_phases(*observations, frequencies[weak], greens)
    if not eligible.any():
        return None
    return sites, phases, greens, eligible


def _pixel_map(values):
    return map_coordinates(
        values.reshape(_SIDE, _SIDE), _PIXEL_COORDS, order=1, mode="nearest", prefilter=False
    )


def _near_taper(scene, origin, green_sites, frequencies, weak, shot, read):
    """Return an eligibility map and the strength verified inside that area."""
    local = _local_phase(scene, origin, green_sites, frequencies, weak, shot, read)
    if local is None:
        return None
    sites, phases, greens, eligible = local
    score = _signed_evidence(sites, phases, frequencies, weak, greens, shot, read)
    strength = np.where(eligible, np.clip(1 + (score - 2.5) / 2, 0, 1), 0.0)
    return _pixel_map(eligible.astype(np.float64)), _GAIN * _pixel_map(strength)


def _along_wire_neighbor(values, eligible, frequency):
    tangent = frequency * (-1, 1)
    alignment = abs(_NEIGHBOR_OFFSETS @ tangent) / np.linalg.norm(_NEIGHBOR_OFFSETS, axis=1)
    dy, dx = _NEIGHBOR_OFFSETS[np.argmax(alignment)]
    padded = np.pad(
        np.where(eligible, values, -np.inf).reshape(_SIDE, _SIDE), 1, constant_values=-np.inf
    )
    before = padded[1 - dy : 1 - dy + _SIDE, 1 - dx : 1 - dx + _SIDE]
    after = padded[1 + dy : 1 + dy + _SIDE, 1 + dx : 1 + dx + _SIDE]
    return np.maximum(before, after).ravel()


def _replicated_taper(scene, origin, green_sites, frequencies, direction, shot, read):
    """Require both greens in a station and repeated phase along the wire."""
    local = _local_phase(scene, origin, green_sites, frequencies, direction, shot, read)
    if local is None:
        return None
    sites, phases, greens, eligible = local
    pooled, lesser_green = _evidence_scores(
        sites, phases, frequencies, direction, greens, shot, read
    )
    score = np.minimum(np.minimum(pooled, lesser_green + 1.5), 2 * lesser_green)
    adjacent = _along_wire_neighbor(score, eligible, frequencies[direction])
    strength = np.where(eligible, np.clip((np.minimum(score, adjacent + 0.5) - 1.5) / 2, 0, 1), 0)
    station = strength.reshape(_SIDE, _SIDE).repeat(_CELL, axis=0).repeat(_CELL, axis=1)
    return _GAIN * np.minimum(_pixel_map(strength), station)
