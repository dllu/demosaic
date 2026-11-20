"""Refine two native wavevectors before testing the interior RAW evidence."""

from itertools import product

import numpy as np

_DIAGONALS = tuple(product((-1, 1), repeat=2))
_MOVES = np.asarray(
    [(0, 0)]
    + [(d, 0) for d in (-0.5, -0.25, 0.25, 0.5)]
    + [(0, d) for d in (-0.5, -0.25, 0.25, 0.5)]
    + list(product((-0.35, 0.35), repeat=2))
)


def _nearby(frequencies, native_side):
    radial = frequencies / np.linalg.norm(frequencies, axis=1, keepdims=True)
    tangent = np.stack((-radial[:, 1], radial[:, 0]), axis=1)
    delta = _MOVES[None, :, :1] * radial[:, None] + _MOVES[None, :, 1:] * tangent[:, None]
    return frequencies[:, None] + delta / native_side


def _design(raw, sites, xy, vectors, sensitivity, noise, innovation):
    y, x = np.nonzero(sites)
    points = xy[y, x]
    value = raw[y, x]
    if innovation:
        neighbors = np.mean([raw[y + dy, x + dx] for dy, dx in _DIAGONALS], axis=0)
        value = (value - neighbors) / np.sqrt(1.25)
    value = value / noise

    # Keep the two harmonics of each trial frequency on actual native Bayer coordinates.
    k = np.stack((vectors, 2 * vectors), axis=-2)
    angle = 2 * np.pi * (points.reshape(-1, 2) @ k.reshape(-1, 2).T)
    columns = np.stack((np.cos(angle), np.sin(angle)), axis=-1)
    if innovation:
        transfer = 1 - np.cos(4 * np.pi * k[..., 0]) * np.cos(4 * np.pi * k[..., 1])
        columns *= (transfer.reshape(-1) / np.sqrt(1.25))[None, :, None]
    columns = columns.reshape(len(x), 4, -1) * (sensitivity / noise)[None, :, None]
    if not innovation:
        # The holdout contrast eliminates the known plane span without estimating a wave on it.
        for phase in range(4):
            q, _ = np.linalg.qr(
                np.column_stack((np.ones(len(x)), points[:, phase] / max(raw.shape[:2]))),
                mode="reduced",
            )
            columns[:, phase] -= q @ (q.T @ columns[:, phase])
            value[:, phase] -= q @ (q.T @ value[:, phase])
    return columns.reshape(len(x) * 4, -1), value.ravel()


def refine_wire_frequencies(
    packed, radii, frequencies, sensitivity, *, shot, read, discovery_parity, innovation
):
    """Propose a bounded frequency move on exterior cells and check separate cells.

    Arrays use packed ``(H,W,4)`` Bayer order. Wavevectors give native cycles
    per pixel in x/y order. The aperture is described by per-site radii, with
    radius one at its scoring boundary. Only the requested packed parity can
    enter the proposal or confirmation. Eight-cell blocks keep each stencil's
    donors in the same split. The fit consumes a single noisy frame.
    """
    raw = np.asarray(packed, dtype=np.float64)
    radii = np.asarray(radii)
    frequencies = np.asarray(frequencies, dtype=np.float64)
    sensitivity = np.asarray(sensitivity, dtype=np.float64)
    if (
        raw.ndim != 3
        or raw.shape[-1] != 4
        or raw.shape != radii.shape
        or min(raw.shape[:2]) < 16
        or frequencies.shape != (2, 2)
        or np.any(np.linalg.norm(frequencies, axis=1) <= 0)
        or sensitivity.shape != (4,)
        or discovery_parity not in (0, 1)
        or not all(np.isfinite(x).all() for x in (raw, radii, frequencies, sensitivity))
        or not np.isfinite([shot, read]).all()
        or shot < 0
        or read < 0
    ):
        raise ValueError(
            "Require two finite nonzero native wavevectors and calibrated Bayer arrays"
        )

    h, w, _ = raw.shape
    y, x = np.indices((h, w))
    blocks = (y // 8 + x // 8) % 2
    same_split = (y % 8 > 0) & (y % 8 < 7) & (x % 8 > 0) & (x % 8 < 7)
    bounded = (y >= 2) & (x >= 2) & (y < h - 2) & (x < w - 2)
    usable = (radii.min(2) > 1.4) & (raw.max(2) < 0.98)
    # Share the exact site mask between the affine and innovation comparisons.
    sites = usable & bounded & same_split & ((x + y) % 2 == discovery_parity)
    sites &= (radii.min(2) > 1.5) & (radii.max(2) < 3.2)
    for dy, dx in _DIAGONALS:
        sites &= np.roll(usable, (-dy, -dx), axis=(0, 1))
    train, confirm = sites & (blocks == 0), sites & (blocks == 1)
    counts = (int(train.sum()), int(confirm.sum()))
    original = frequencies.tolist()
    if min(counts) < 32:
        return {
            "chosen": original,
            "nomination": original,
            "accepted": False,
            "cells": counts,
            "training_cell_gain": None,
            "heldout_gain": None,
        }

    native = np.stack(
        (
            2 * x[..., None] + np.array([0, 1, 0, 1]) - (2 * w - 1) / 2,
            2 * y[..., None] + np.array([0, 0, 1, 1]) - (2 * h - 1) / 2,
        ),
        axis=-1,
    )
    noise = np.sqrt(np.maximum(shot * np.median(raw[train], axis=0).clip(min=0) + read, 1e-12))
    trial = _nearby(frequencies, 2 * max(h, w))
    A, target = _design(raw, train, native, trial, sensitivity, noise, innovation)
    gram = A.T @ A
    rhs = A.T @ target
    first = np.arange(4 * len(_MOVES)).reshape(-1, 4)
    pairs = np.asarray([(np.r_[a, b]) for a in first for b in first + 4 * len(_MOVES)])
    system = gram[pairs[:, :, None], pairs[:, None, :]]
    # A tiny diagonal stabilizes weak or coincident trial columns. It leaves the score scale intact.
    stabilizer = 1e-9 * np.trace(system, axis1=1, axis2=2).clip(min=1)
    amplitudes = np.linalg.solve(system + stabilizer[:, None, None] * np.eye(8), rhs[pairs, None])[
        ..., 0
    ]
    energy = np.einsum("bi,bi->b", amplitudes, rhs[pairs])
    distance = (_MOVES**2).sum(1)
    index = int(np.argmax(energy - 4 * (distance[:, None] + distance[None]).ravel()))
    indices = np.unravel_index(index, (len(_MOVES), len(_MOVES)))
    nominated = trial[np.arange(2), indices].tolist()
    C, validation = _design(raw, confirm, native, trial, sensitivity, noise, innovation)
    prior_error = validation - C[:, pairs[0]] @ amplitudes[0]
    fitted_error = validation - C[:, pairs[index]] @ amplitudes[index]
    gain = float(prior_error @ prior_error - fitted_error @ fitted_error)
    accepted = index != 0 and gain > 2.0
    return {
        "chosen": nominated if accepted else original,
        "nomination": nominated,
        "accepted": accepted,
        "cells": counts,
        "training_cell_gain": float(energy[index] - energy[0]),
        "heldout_gain": gain,
    }
