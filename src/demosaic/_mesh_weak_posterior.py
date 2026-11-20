"""Apply a local ring prior only to the weaker measured mesh direction."""

import numpy as np
from scipy.special import expit

from ._mesh_pooled import (
    _CENTER_BACKGROUND,
    _CENTERS,
    _CORE,
    _SMOOTH,
    _STRIDE,
    _correction,
    _dominant,
    _footprint,
    _inverse,
    _measure_nodes,
    _rgb,
    _wave,
    _windows,
)
from ._mesh_presence import _CENTER, _CENTER_PIXELS, _PACKED_CORE, _RING, _evidence, _ring_prior
from .mesh_carrier_fit import _POOLED_FOOTPRINT, _WINDOW, _positions

_LOG_PRIOR_ODDS = -5.0
_INCLUSION_CUTOFF = 0.20


def _weak_correction(parent, wave, direction, positions, windows, shot, read, previous):
    outer = wave.reshape(_WINDOW, _WINDOW, 4)
    means, deviations = _ring_prior(
        *_evidence(windows, positions, outer, _SMOOTH, _RING, shot, read)
    )
    carrier = wave[_CORE][..., direction, :]
    strong = wave[_CORE][..., 1 - direction, :]
    background = np.concatenate((_CENTER_BACKGROUND, strong), axis=-1)
    center = tuple(plane[:, _PACKED_CORE, _PACKED_CORE] for plane in windows)
    gram, moment = _evidence(center, positions, carrier, background, _CENTER_PIXELS, shot, read)
    prior = means.reshape(-1, 2, 2)[:, direction]
    precision = 1 / deviations[:, direction] ** 2
    system = gram + precision[:, None, None] * np.eye(2)
    location = moment + precision[:, None] * prior
    fitted = np.linalg.solve(system, location[..., None])[..., 0]
    _, logdet = np.linalg.slogdet(system)
    gain = np.sum(location * fitted, axis=1)
    energy = precision * np.sum(prior**2, axis=1)
    log_evidence = 0.5 * (2 * np.log(precision) - logdet + gain - energy)
    probability = expit(log_evidence + _LOG_PRIOR_ODDS)
    strength = np.maximum(0, (probability - _INCLUSION_CUTOFF) / (1 - _INCLUSION_CUTOFF))
    selected = strength > 0
    if not selected.any():
        return previous

    design = np.concatenate((background, carrier), axis=-1).reshape(_CENTER**2, -1)
    samples = _windows(parent[1], _CENTER, _STRIDE).reshape(-1, _CENTER**2)
    inherited = samples @ np.linalg.pinv(design, rcond=1e-8)[-2:].T
    central_fit = np.linalg.solve(gram, moment[..., None])[..., 0]
    cap = np.linalg.norm(central_fit, axis=1)
    delta = (fitted - inherited) * strength[:, None]
    norm = np.linalg.norm(delta, axis=1).clip(min=1e-15)
    delta *= np.minimum(1, strength * cap / norm)[:, None]
    revised = np.einsum("yxf,nf->nyx", carrier, delta)
    return np.where(selected[:, None, None], revised, previous)


def _refine(
    parent,
    context,
    scene,
    colors,
    origin,
    frequencies,
    shot,
    read,
    neutral,
    *,
    guard_clearance=None,
):
    positions = _positions(colors, *origin)
    greens = tuple(_footprint(scene, origin, position) for position in positions)
    if any(not np.isfinite(lattice).all() for lattice in greens):
        return parent
    observed = tuple(_windows(g, _WINDOW // 2, _STRIDE // 2) for g in greens)
    wave = _wave(_WINDOW, frequencies)
    design = np.concatenate((_SMOOTH, wave.reshape(_WINDOW, _WINDOW, 4)), axis=-1)
    projection = _inverse(design.reshape(_WINDOW**2, -1))[-4:]
    parent_patches = _windows(context[1], _WINDOW, _STRIDE).reshape(len(_CENTERS), -1)
    inherited = np.einsum("dp,np->nd", projection, parent_patches).reshape(-1, 2, 2)
    corrections = [
        _correction(wave, d, positions, observed, None, parent_patches, inherited[:, d], shot, read)
        for d in range(2)
    ]
    guides = _wave(_POOLED_FOOTPRINT, frequencies)
    first, second = (
        _dominant(*_measure_nodes(plane, guides, site, shot, read))
        for plane, site in zip(greens, positions, strict=True)
    )
    taper = None
    if first is not None and first == second:
        weak = 1 - first
        revised = _weak_correction(
            parent, wave, weak, positions, observed, shot, read, corrections[weak]
        )
        if guard_clearance is not None and not np.array_equal(revised, corrections[weak]):
            from ._mesh_weak_phase import _taper

            baseline = parent + _rgb(sum(corrections), neutral, parent.dtype)
            taper = _taper(scene, origin, positions, frequencies, weak, shot, read, guard_clearance)
        corrections[weak] = revised
    combined = corrections[0] + corrections[1]
    if taper is None and not combined.any():
        return parent
    result = parent + _rgb(combined, neutral, parent.dtype)
    if taper is not None:
        result = (baseline + taper * (result.astype(np.float64) - baseline)).astype(parent.dtype)
    return result if np.isfinite(result).all() else parent
