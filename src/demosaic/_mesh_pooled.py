"""Weak-direction phase pooling for the native RAW mesh crop."""

from dataclasses import dataclass
from functools import cache

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.linalg import solve
from scipy.ndimage import map_coordinates

from .mesh_carrier_fit import (
    _EDGE,
    _POOLED_FOOTPRINT,
    _POOLED_HALO,
    _ROI_SIZE,
    _SMOOTH,
    _WINDOW,
    _cosine_background,
    _positions,
    _sites,
)

_CENTER = _WINDOW - 2 * _POOLED_HALO
_NODE = 24
_SIDE = _POOLED_FOOTPRINT // _NODE
_STRIDE = _CENTER // 2
_CORE = np.s_[_POOLED_HALO:-_POOLED_HALO, _POOLED_HALO:-_POOLED_HALO]
_GREEN_CORE = np.s_[_POOLED_HALO // 2 : -_POOLED_HALO // 2, _POOLED_HALO // 2 : -_POOLED_HALO // 2]
_CENTERS = tuple(
    (y, x)
    for y in range(0, _ROI_SIZE - _CENTER + 1, _STRIDE)
    for x in range(0, _ROI_SIZE - _CENTER + 1, _STRIDE)
)
_CENTER_TAPER = np.sin(np.pi * (np.arange(_CENTER) + 0.5) / _CENTER) ** 2
_TAPER = np.outer(_CENTER_TAPER, _CENTER_TAPER)
_CENTER_BACKGROUND = _cosine_background(_CENTER)
_NODE_BACKGROUND = _cosine_background(_NODE)
_INTERPOLATION = (np.indices((_POOLED_FOOTPRINT, _POOLED_FOOTPRINT)) - (_NODE - 1) / 2) / _NODE
_ABSOLUTE = (6.0, 1.5)
_RELATIVE = np.array((1.0, 0.2))
_GAIN = 0.73


def _wave(size, frequencies):
    y, x = np.indices((size, size), dtype=np.float64) - (size - 1) / 2
    phase = 2 * np.pi * (x[..., None] * frequencies[:, 0] + y[..., None] * frequencies[:, 1])
    return np.stack((np.cos(phase), np.sin(phase)), axis=-1)


@cache
def _laplacian():
    matrix = np.zeros((_SIDE * _SIDE, _SIDE * _SIDE))
    for y in range(_SIDE):
        for x in range(_SIDE):
            i = y * _SIDE + x
            for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < _SIDE and 0 <= nx < _SIDE:
                    j = ny * _SIDE + nx
                    weight = 1 / np.hypot(dx, dy)
                    matrix[i, i] += weight
                    matrix[j, j] += weight
                    matrix[i, j] -= weight
                    matrix[j, i] -= weight
    return matrix


def _variance(values, shot, read):
    return np.maximum(2e-11, shot * np.maximum(0.0, values.mean(axis=-1)) + read)


def _nodes(array):
    """Collect nonoverlapping blocks from one of the packed green lattices."""
    node = _NODE // 2
    shape = array.shape[2:]
    return (
        array.reshape(_SIDE, node, _SIDE, node, *shape)
        .swapaxes(1, 2)
        .reshape(_SIDE * _SIDE, node * node, *shape)
    )


def _measure_nodes(green, wave, position, shot, read):
    # The global phase origin lets the node coefficients be pooled directly.
    y, x = position
    columns = _nodes(wave[y::2, x::2].reshape(_POOLED_FOOTPRINT // 2, _POOLED_FOOTPRINT // 2, 4))
    background = _NODE_BACKGROUND[y::2, x::2]
    smooth = np.broadcast_to(
        background.reshape(1, (_NODE // 2) ** 2, -1), (*columns.shape[:2], background.shape[-1])
    )
    design = np.concatenate((smooth, columns), axis=-1)
    gram = np.einsum("npi,npj->nij", design, design)
    inv = np.linalg.pinv(gram, rcond=1e-9, hermitian=True)
    values = _nodes(green)
    moment = np.einsum("npi,np->ni", design, values)
    coeff = np.einsum("nij,nj->ni", inv[:, -4:], moment).reshape(-1, 2, 2)
    diagonal = np.diagonal(inv, axis1=-2, axis2=-1)[:, -4:]
    information = (1 / diagonal).reshape(-1, 2, 2).mean(axis=-1)
    precision = information / _variance(values, shot, read)[:, None]
    return coeff, precision


def _dominant(coeff, precision):
    power = np.maximum(0, np.median(np.sum(coeff**2, axis=-1) - 2 / precision, axis=0))
    winner = int(np.argmax(power))
    return winner if power[winner] > max(1e-12, 1.25 * power[1 - winner]) else None


def _phase_template(wave, coeff, precision):
    diagonal = np.diag(precision)
    matrix = diagonal + 0.5 * np.median(precision) * _laplacian()
    smooth = solve(matrix, precision[:, None] * coeff, assume_a="pos", check_finite=False)
    field = np.stack(
        [
            map_coordinates(
                smooth[:, i].reshape(_SIDE, _SIDE), _INTERPOLATION, order=1, mode="nearest"
            )
            for i in (0, 1)
        ],
        axis=-1,
    )
    field /= np.linalg.norm(field, axis=-1, keepdims=True).clip(min=1e-12)
    return np.sum(field * wave, axis=-1)


def _windows(plane, size, stride):
    views = sliding_window_view(plane, (size, size))[::stride, ::stride]
    return np.ascontiguousarray(views).reshape(len(_CENTERS), size, size)


def _sample(field, position):
    y, x = position
    return field[y::2, x::2].reshape(-1, field.shape[-1])


def _inverse(basis):
    # Solve the small Gram system before applying it to the full pixel basis.
    gram = np.einsum("pi,pj->ij", basis, basis)
    inverse = solve(gram, np.eye(len(gram)), assume_a="pos", check_finite=False, overwrite_a=True)
    return np.einsum("ij,pj->ip", inverse, basis)


@dataclass
class _Projection:
    fit: np.ndarray
    held: np.ndarray
    inverse: np.ndarray

    @classmethod
    def from_window(cls, background, positions):
        fit, held = (_sample(background, p) for p in positions)
        return cls(fit, held, _inverse(fit))

    def residual(self, fit, held):
        """Remove the nuisance contribution fitted on the first lattice."""
        coef = np.einsum("dp,...p->...d", self.inverse, fit)
        return (
            fit - np.einsum("pd,...d->...p", self.fit, coef),
            held - np.einsum("pd,...d->...p", self.held, coef),
        )


def _scores(held, prediction, variance):
    return np.einsum("...p,...p->...", 2 * held - prediction, prediction) / variance


def _ramp(scores):
    excess = np.maximum(0, scores - _ABSOLUTE)
    return np.min(excess / (excess + _ABSOLUTE), axis=-1)


@dataclass
class _Fit:
    scores: np.ndarray
    values: np.ndarray


def _fold(wave, backgrounds, positions, observed, dynamic, shot, read):
    wide, narrow = (_Projection.from_window(basis, positions) for basis in backgrounds)
    full = tuple(planes.reshape(len(_CENTERS), -1) for planes in observed)
    center = tuple(
        planes[:, _GREEN_CORE[0], _GREEN_CORE[1]].reshape(len(_CENTERS), -1) for planes in observed
    )
    broad_variance, center_variance = (_variance(data[0], shot, read) for data in (full, center))
    train, hold = wide.residual(*full)
    _, middle = narrow.residual(*center)
    plain = tuple(_sample(wave, p).T for p in positions)
    plain_core = tuple(_sample(wave[_CORE], p).T for p in positions)
    plane_train, plane_held = wide.residual(*plain)
    _, plane_middle = narrow.residual(*plain_core)
    coefficients = np.einsum("dp,np->nd", _inverse(plane_train.T), train)
    planar_scores = np.stack(
        (
            _scores(hold, np.einsum("nd,dp->np", coefficients, plane_held), broad_variance),
            _scores(middle, np.einsum("nd,dp->np", coefficients, plane_middle), center_variance),
        ),
        axis=-1,
    )
    planar = _Fit(planar_scores, coefficients)
    candidate = None
    if dynamic is not None:
        patches = tuple(
            _windows(dynamic[y::2, x::2], _WINDOW // 2, _STRIDE // 2) for y, x in positions
        )
        f, h = wide.residual(*(p.reshape(len(_CENTERS), -1) for p in patches))
        _, c = narrow.residual(
            *(p[:, _GREEN_CORE[0], _GREEN_CORE[1]].reshape(len(_CENTERS), -1) for p in patches)
        )
        amplitude = np.maximum(
            0, np.einsum("np,np->n", f, train) / np.einsum("np,np->n", f, f).clip(min=1e-12)
        )
        scores = np.stack(
            (
                _scores(hold, h * amplitude[:, None], broad_variance),
                _scores(middle, c * amplitude[:, None], center_variance),
            ),
            axis=-1,
        )
        candidate = _Fit(scores, amplitude)
    return planar, candidate


def _correction(waves, direction, positions, observed, templates, parent, prior, shot, read):
    wave = waves[..., direction, :]
    rival = waves[..., 1 - direction, :]
    background = np.concatenate((_SMOOTH, rival), axis=-1)
    center_background = np.concatenate((_CENTER_BACKGROUND, rival[_CORE]), axis=-1)
    original = []
    candidates = []
    for fold in range(2):
        indices = slice(None) if fold == 0 else slice(None, None, -1)
        base, candidate = _fold(
            wave,
            (background, center_background),
            positions[indices],
            observed[indices],
            None if templates is None else templates[fold],
            shot,
            read,
        )
        original.append(base)
        candidates.append(candidate)
    gain = _ramp(np.minimum(original[0].scores, original[1].scores))
    fitted = (original[0].values + original[1].values) / 2
    delta = gain[:, None] * (fitted - prior)
    limit = np.linalg.norm(fitted, axis=-1)
    delta *= np.minimum(1, limit / np.linalg.norm(delta, axis=-1).clip(min=1e-12))[:, None]
    correction = np.einsum("yxd,nd->nyx", wave[_CORE], delta)
    if templates is None:
        return correction

    improved = np.all(
        (candidates[0].scores - original[0].scores > _RELATIVE)
        & (candidates[1].scores - original[1].scores > _RELATIVE),
        axis=-1,
    )
    gain = _ramp(np.minimum(candidates[0].scores, candidates[1].scores))
    chosen = improved & (gain > 0)
    if chosen.any():
        bg = background.reshape(_WINDOW**2, -1)
        inverse = _inverse(bg)
        lift = np.zeros_like(correction[chosen])
        for template, candidate in zip(templates, candidates, strict=True):
            patches = _windows(template, _WINDOW, _STRIDE)[chosen]
            flattened = patches.reshape(len(lift), -1)
            coeff = np.einsum("dp,np->nd", inverse, flattened)
            residual = flattened - np.einsum("pd,nd->np", bg, coeff)
            before = np.einsum("np,np->n", residual, parent[chosen])
            before /= np.einsum("np,np->n", residual, residual).clip(min=1e-12)
            amplitude = candidate.values[chosen]
            delta_scalar = np.clip((amplitude - before) * gain[chosen], -amplitude, amplitude)
            lift += patches[:, _CORE[0], _CORE[1]] * delta_scalar[:, None, None]
        correction[chosen] = lift / 2
    return correction


@cache
def _delivery_weights():
    mass = np.zeros((_ROI_SIZE, _ROI_SIZE))
    for y, x in _CENTERS:
        mass[y : y + _CENTER, x : x + _CENTER] += _TAPER
    return _GAIN * _EDGE[:, None] * _EDGE[None, :] / np.maximum(0.02, mass)


def _rgb(patches, neutral, dtype):
    field = np.zeros((_ROI_SIZE, _ROI_SIZE))
    for (y, x), tile in zip(_CENTERS, patches, strict=True):
        field[y : y + _CENTER, x : x + _CENTER] += _TAPER * tile
    rgb = neutral[:, None, None] * (_delivery_weights() * field)
    return rgb.astype(dtype)


def _refine(parent, parent_green, scene, colors, origin, frequencies, shot, read, neutral):
    x, y = origin
    positions = _positions(colors, x, y)
    greens = tuple(
        _sites(scene, x - _POOLED_HALO, y - _POOLED_HALO, _POOLED_FOOTPRINT, row, col).astype(
            np.float64
        )
        for row, col in positions
    )
    if not all(np.isfinite(plane).all() for plane in greens):
        return parent
    global_wave = _wave(_POOLED_FOOTPRINT, frequencies)
    nodes = tuple(
        _measure_nodes(plane, global_wave, p, shot, read)
        for plane, p in zip(greens, positions, strict=True)
    )
    first, second = (_dominant(*terms) for terms in nodes)
    weak = 1 - first if first is not None and first == second else None
    templates = None
    if weak is not None:
        templates = tuple(
            _phase_template(global_wave[..., weak, :], coeff[:, weak], precision[:, weak])
            for coeff, precision in nodes
        )

    local_wave = _wave(_WINDOW, frequencies)
    parent_design = np.concatenate((_SMOOTH, local_wave.reshape(_WINDOW, _WINDOW, 4)), axis=-1)
    projection = _inverse(parent_design.reshape(_WINDOW**2, -1))[-4:]
    parent_patches = _windows(parent_green, _WINDOW, _STRIDE).reshape(len(_CENTERS), -1)
    prior = np.einsum("dp,np->nd", projection, parent_patches).reshape(-1, 2, 2)
    observed = tuple(_windows(g, _WINDOW // 2, _STRIDE // 2) for g in greens)
    corrections = tuple(
        _correction(
            local_wave,
            d,
            positions,
            observed,
            templates if d == weak else None,
            parent_patches,
            prior[:, d],
            shot,
            read,
        )
        for d in range(2)
    )
    if not any(part.any() for part in corrections):
        return parent
    if weak is None:
        result = parent + _rgb(corrections[0] + corrections[1], neutral, parent.dtype)
    else:
        result = parent + _rgb(corrections[1 - weak], neutral, parent.dtype)
        result += _rgb(corrections[weak], neutral, parent.dtype)
    return result if np.isfinite(result).all() else parent
