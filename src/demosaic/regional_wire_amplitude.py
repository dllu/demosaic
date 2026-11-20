"""Estimate missing contrast with reciprocal Bayer measurements along a wire."""

import numpy as np


def tangent_neighbor_weights(windows):
    """Average adjacent measurement windows along each of the three wire rows."""
    shape = windows.shape
    if shape[-1] != 15:
        raise ValueError("Expected three across-wire rows of five along-wire windows")
    weights = windows.reshape(*shape[:-1], 3, 5)
    left = np.concatenate((weights[..., :1], weights[..., :-1]), axis=-1)
    right = np.concatenate((weights[..., 1:], weights[..., -1:]), axis=-1)
    return (0.25 * (left + 2 * weights + right)).reshape(shape)


def regional_deficit(estimates, limit, *, reciprocal):
    """Estimate a bounded positive deficit from two disjoint groups of CFA sites."""
    estimates = np.asarray(estimates, dtype=np.float64)
    if estimates.ndim != 2 or estimates.shape[0] != 2:
        raise ValueError("Expected two Bayer estimates for each region")
    if not np.isfinite(limit) or limit < 0:
        raise ValueError("Expected a finite nonnegative amplitude limit")

    valid = np.all(np.isfinite(estimates), axis=0)
    amounts = np.zeros(estimates.shape[1], dtype=np.float64)
    scores = estimates[:, valid]
    if reciprocal:
        a, b = np.maximum(scores, 0)
        pooled = np.sqrt(a) * np.sqrt(b)
    else:
        pooled = 0.5 * scores[0] + 0.5 * scores[1]
    amounts[valid] = np.clip(pooled, 0, limit)
    return amounts


def matched_supported_amplitude(carrier, spatial_support, regional_amplitude):
    """Match correction energy while holding the spatial support and carrier fixed."""
    supported_wave = carrier * spatial_support
    total = float(np.sum(np.square(supported_wave)))
    if total <= 1e-24:
        return 0.0
    regional_wave = carrier * regional_amplitude
    return float(np.sqrt(np.sum(np.square(regional_wave)) / total))
