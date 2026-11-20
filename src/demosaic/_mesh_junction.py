"""Deliver the measured difference band only where both wires have RAW support."""

from dataclasses import dataclass
from functools import cache
from itertools import product

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

from ._mesh_near_phase import _pixel_map
from .mesh_carrier_fit import _JUNCTION_HALO, _ROI_SIZE, _sites

_HALO = _JUNCTION_HALO
_CONTEXT = _ROI_SIZE + 2 * _HALO
_CENTER = (_CONTEXT - 1) / 2
_CELL = 16
_SIDE = _ROI_SIZE // _CELL
_GAINS = 0.6318481533720487
_BANDS = ((2, 0), (0, 2), (1, 1), (1, -1))
_DIFFERENCE = (1, -1)
_NODES = tuple(product((-72, -24, 24, 72), repeat=2))
_AXIS = np.arange(_CONTEXT) - _CENTER
_GRID_Y, _GRID_X = np.meshgrid(_AXIS, _AXIS, indexing="ij")
_FIELD_EDGE = np.clip((112 - abs(_AXIS)) / 24, 0, 1)
_CORE = np.s_[..., _HALO:-_HALO, _HALO:-_HALO]


@cache
def _folds():
    rng = np.random.default_rng(411935)
    order = np.argsort(rng.random((64, 64, 4)), axis=-1)
    return order.reshape(64, 64, 2, 2).transpose(0, 2, 1, 3).reshape(128, 128)


def _step_from_discovery(packed, mask, sites):
    green = packed[sites].mean(axis=0)
    smooth = gaussian_filter(np.where(mask, green, 0.0), 2.8) / gaussian_filter(
        mask.astype(float), 2.8
    )
    angles = np.arange(36) * np.pi / 36
    offsets = np.arange(-46.0, 47.0, 4)
    along = np.linspace(-58, 58, 33)
    ux, uy = np.cos(angles)[:, None, None], np.sin(angles)[:, None, None]
    x = offsets[None, :, None] * ux - along[None, None, :] * uy
    y = offsets[None, :, None] * uy + along[None, None, :] * ux
    samples = np.stack(
        [
            map_coordinates(
                smooth,
                [(y + d * uy + 127) * 0.5, (x + d * ux + 127) * 0.5],
                order=1,
                prefilter=False,
            )
            for d in (-17, -7, 7, 17)
        ]
    )
    difference = samples[2] - samples[1]
    step = difference.mean(axis=-1)
    variation = np.maximum(
        abs((samples[3] - samples[2]).mean(-1)), abs((samples[1] - samples[0]).mean(-1))
    )
    sharpness = abs(step) - 0.75 * variation
    consistent = (np.sign(difference) * np.sign(step[..., None]) > 0).mean(-1) >= 0.8
    valid = (abs(step) >= 0.009) & consistent & (sharpness >= 0.0045)
    if not valid.any():
        return None
    a, i = np.unravel_index(np.argmax(np.where(valid, sharpness, -np.inf)), valid.shape)
    return angles[a], offsets[i]


def _wave_angles(x, y, frequencies):
    return np.stack([2 * np.pi * (fx * x + fy * y) for fx, fy in frequencies], axis=-1)


def _quadratures(angles):
    return np.stack((np.cos(angles), np.sin(angles)), axis=-1)


@dataclass
class _Observation:
    x: np.ndarray
    y: np.ndarray
    phase: np.ndarray
    raw: np.ndarray
    variance: np.ndarray
    fold: np.ndarray
    nuisance: np.ndarray
    angles: np.ndarray

    @classmethod
    def make(cls, packed, greens, frequencies, shot, read):
        fold = _folds()
        mask = fold == 0
        density = gaussian_filter(mask.astype(float), 3)
        coords = np.indices(fold.shape)
        records = []
        for site in greens:
            y = 2 * coords[0] + site // 2 - _CENTER
            x = 2 * coords[1] + site % 2 - _CENTER
            raw = packed[site].astype(np.float64)
            level = gaussian_filter(np.where(mask, raw, 0.0), 3) / density
            variance = np.maximum(2e-11, shot * level.clip(min=0) + read)
            records.append((x, y, np.full_like(x, site), raw, variance, fold))
        x, y, phase, raw, variance, fold = [
            np.concatenate([a.ravel() for a in term]) for term in zip(*records, strict=True)
        ]
        u, v, sign = x / 128, y / 128, np.where(phase == phase[0], 1.0, -1.0)
        background = np.column_stack((np.ones_like(x), u, v, sign, sign * u, sign * v))
        basis = [background, np.column_stack((u**2, v**2, u * v))]
        step = _step_from_discovery(packed, mask, greens)
        if step is not None:
            angle, offset = step
            transition = np.clip(0.5 + (x * np.cos(angle) + y * np.sin(angle) - offset) / 5, 0, 1)
            basis.append(transition[:, None] * background)
        return cls(
            x,
            y,
            phase,
            raw,
            variance,
            fold,
            np.column_stack(basis),
            _wave_angles(x, y, frequencies),
        )

    def held_score(self, signal, nuisance, inner):
        moments, powers = [], []
        for fold in (2, 3):
            selected = inner & (self.fold == fold)
            w = np.exp(-0.5 * (self.x[selected] ** 2 + self.y[selected] ** 2) / 75**2)
            variance = self.variance[selected]
            weight = w / variance
            fit = nuisance[selected]
            residual = signal[selected] - fit @ np.linalg.solve(
                (fit.T * weight) @ fit, (fit.T * weight) @ signal[selected]
            )
            projected = weight * residual
            moments.append(float(projected @ self.raw[selected]))
            powers.append(float(np.sum(projected**2 * variance)))
        signed = np.array(moments) / np.sqrt(np.maximum(1e-20, powers))
        return sum(moments) / np.sqrt(max(1e-20, sum(powers))), signed.min()


def _distinct_bands(frequencies):
    accepted = []
    candidates = list(frequencies)
    for pair in _BANDS:
        f = np.asarray(pair) @ frequencies
        if abs(f).sum() >= 0.48 or np.linalg.norm(f) < 0.037:
            continue
        if any(min(np.linalg.norm(f - g), np.linalg.norm(f + g)) < 0.018 for g in candidates):
            continue
        candidates.append(f)
        accepted.append(pair)
    return accepted


def _discovery(obs, bands):
    inner = np.maximum(abs(obs.x), abs(obs.y)) <= 96
    train = inner & (obs.fold == 0)
    weight = np.exp(-0.5 * (obs.x[train] ** 2 + obs.y[train] ** 2) / 75**2) / obs.variance[train]
    waves = _quadratures(obs.angles)
    base = np.column_stack((obs.nuisance, waves.reshape(len(obs.x), 4)))

    def fit(columns):
        columns = columns[train]
        return np.linalg.inv((columns.T * weight) @ columns) @ (
            (columns.T * weight) @ obs.raw[train]
        )

    beta = fit(base)[-4:].reshape(2, 2)
    phase = np.arctan2(-beta[:, 1], beta[:, 0])
    known = obs.angles + phase
    for direction in range(2):
        nuisance = np.column_stack((obs.nuisance, waves[:, 1 - direction]))
        total, each = obs.held_score(np.cos(known[:, direction]), nuisance, inner)
        if total < 2.75 or each <= 0:
            return None
    harmonics = _quadratures(known @ np.asarray(bands).T)
    signed = fit(np.column_stack((base, harmonics[..., 0])))[-len(bands) :]
    index = bands.index(_DIFFERENCE)
    magnitude = float(abs(signed[index]))
    sign = float(signed[index]) / max(1e-20, magnitude)
    others = np.delete(harmonics, index, axis=1).reshape(len(obs.x), -1)
    total, each = obs.held_score(
        sign * harmonics[:, index, 0], np.column_stack((base, others)), inner
    )
    if total < 3.25 or each < 0.9:
        return None
    return phase, base, harmonics, index, sign, magnitude


@cache
def _held_stations():
    """Indices of the 32 reserved samples per CFA phase in each 16×16 station."""
    packed_side = _CONTEXT // 2
    margin = _HALO // 2
    packed_cell = _CELL // 2
    core = np.s_[margin:-margin, margin:-margin]
    indices = np.arange(packed_side**2).reshape(packed_side, packed_side)[core]
    reserved = _folds()[core] >= 2

    def by_station(grid):
        return (
            grid.reshape(_SIDE, packed_cell, _SIDE, packed_cell)
            .transpose(0, 2, 1, 3)
            .reshape(_SIDE**2, packed_cell**2)
        )

    # Four folds partition every aligned 2×2 group of packed cells.
    held = by_station(indices)[by_station(reserved)].reshape(_SIDE**2, packed_cell**2 // 2)
    return held + np.arange(2)[:, None, None] * packed_side**2


def _local_wire_support(obs, known):
    held = _held_stations()
    x, y = obs.x[held], obs.y[held]
    u = (x - x.mean(axis=-1, keepdims=True)) / _CELL
    v = (y - y.mean(axis=-1, keepdims=True)) / _CELL
    nuisance = np.stack((np.ones_like(u), u, v, u**2, u * v, v**2), axis=-1)
    weight = 1 / np.sqrt(obs.variance[held])
    weighted_raw = obs.raw[held] * weight
    waves = _quadratures(known[held])
    moments = []
    powers = []
    for d in range(2):
        controls = np.concatenate((nuisance, waves[..., 1 - d, :]), axis=-1) * weight[..., None]
        signal = waves[..., d, 0] * weight
        q, r = np.linalg.qr(controls)
        scores = q.swapaxes(-1, -2) @ signal[..., None]
        residual = signal - (q @ scores)[..., 0]
        diagonal = abs(np.diagonal(r, axis1=-2, axis2=-1))
        poorly_conditioned = diagonal.min(axis=-1) < 1e-6 * diagonal.max(axis=-1)
        for phase, station in zip(*np.nonzero(poorly_conditioned), strict=True):
            design = controls[phase, station]
            target = signal[phase, station]
            residual[phase, station] = (
                target - design @ np.linalg.lstsq(design, target, rcond=1e-8)[0]
            )
        moments.append(np.sum(residual * weighted_raw, axis=-1))
        powers.append(np.sum(residual**2, axis=-1))
    moments, powers = np.asarray(moments), np.asarray(powers)
    per_green = moments / np.sqrt(np.maximum(1e-10, powers))
    pooled = moments.sum(axis=1) / np.sqrt(np.maximum(1e-10, powers.sum(axis=1)))
    support = np.clip(np.minimum(pooled, per_green.min(axis=1) + 1.5).min(axis=0) / 1.5, 0, 1)
    own = support.reshape(_SIDE, _SIDE).repeat(_CELL, axis=0).repeat(_CELL, axis=1)
    return np.minimum(_pixel_map(support), own)


def _amplitudes(obs, columns, index, sign, maximum, parent_green):
    result = []
    core = np.maximum(abs(obs.x), abs(obs.y)) <= 101
    measured = np.column_stack((obs.raw, parent_green))
    for y, x in _NODES:
        distance = (obs.x - x) ** 2 + (obs.y - y) ** 2
        window = np.exp(-0.5 * distance / 35**2) / obs.variance
        votes, variances = [], []
        for fold in (1, 2, 3):
            selected = core & (obs.fold == fold) & (distance <= 80**2)
            a = columns[selected]
            weights = window[selected]
            cov = np.linalg.pinv((a.T * weights) @ a, hermitian=True, rcond=1e-9)
            coefficients = cov @ ((a.T * weights) @ measured[selected])
            votes.append(sign * coefficients[index])
            variances.append(cov[index, index] * sign**2)
        votes, variances = np.asarray(votes), np.asarray(variances)
        evidence = np.mean(
            [max(0, votes[a, 0]) * max(0, votes[b, 0]) for a, b in ((0, 1), (0, 2), (1, 2))]
        )
        floor = np.mean([(variances[a] * variances[b]) ** 0.5 for a, b in ((0, 1), (0, 2), (1, 2))])
        shrink = max(0.0, 1 - floor / max(1e-20, evidence))
        raw, parent = np.average(votes, weights=1 / variances, axis=0)
        result.append(np.clip(raw * shrink - max(0.0, parent), 0, 1.5 * maximum))
    gy, gx = (_GRID_Y + 72) / 48, (_GRID_X + 72) / 48
    return map_coordinates(
        np.asarray(result).reshape(4, 4), [gy, gx], order=1, mode="nearest", prefilter=False
    )


def _refine(parent, context, scene, colors, origin, frequencies, shot, read, neutral):
    bands = _distinct_bands(frequencies)
    if _DIFFERENCE not in bands:
        return parent
    x, y = origin[0] - _HALO, origin[1] - _HALO
    packed = np.stack([_sites(scene, x, y, _CONTEXT, r, c) for r, c in np.ndindex(2, 2)])
    greens = [
        2 * r + c for r, c in np.ndindex(2, 2) if colors[2 * ((y + r) % 2) + (x + c) % 2] == 1
    ]
    if not np.isfinite(packed[greens]).all():
        return parent
    observations = _Observation.make(packed, greens, frequencies, shot, read)
    guide = _discovery(observations, bands)
    if guide is None:
        return parent
    phase, base, harmonics, index, sign, maximum = guide
    if maximum <= 0:
        return parent
    support = _local_wire_support(observations, observations.angles + phase)
    if not support.any():
        return parent
    rgb = context[1].copy()
    rgb[_CORE] = parent[1]
    inherited = rgb[(observations.y + _CENTER).astype(int), (observations.x + _CENTER).astype(int)]
    columns = np.column_stack((base, harmonics.reshape(len(base), -1)))
    amplitudes = _amplitudes(
        observations, columns, base.shape[1] + 2 * index, sign, maximum, inherited
    )
    angle = _wave_angles(_GRID_X, _GRID_Y, frequencies) + phase
    carrier = angle[..., 0] - angle[..., 1]
    residual = amplitudes * (sign * np.cos(carrier)) * (_FIELD_EDGE[:, None] * _FIELD_EDGE)
    # Match the inherited crop's first rounding before applying the held support.
    field = (residual[None] * neutral[:, None, None]).astype(np.float32)
    result = (parent + support * (_GAINS * field[_CORE].astype(np.float64))).astype(parent.dtype)
    return result if np.isfinite(result).all() else parent
