"""Directional window weights and contrasts for measured wire support."""

import math

import numpy as np


def directional_windows(x, y, theta, normal_radius, tangent_radius):
    """Return interpolation weights for three across-wire and five along-wire sites."""
    cosine, sine = math.cos(theta), math.sin(theta)
    normal = (cosine * x + sine * y) / normal_radius
    tangent = (-sine * x + cosine * y) / tangent_radius

    def hats(position, count):
        scaled = (position.clip(-1, 1) + 1) * (count - 1) / 2
        return np.maximum(1 - np.abs(scaled[..., None] - np.arange(count)), 0)

    rows = hats(normal, 3)
    cols = hats(tangent, 5)
    return (rows[..., :, None] * cols[..., None, :]).reshape(*normal.shape, 15)


def window_contrast(carrier, nuisance, weight):
    """Return a weighted, nuisance-orthogonal coefficient on fixed CFA sites.

    The carrier and nuisance columns are already whitened. The weight applies
    a spatial taper. The second return value is the contrast's L2 length and
    gives its standard error under independent unit noise.
    """
    selected = weight > 1e-6
    if selected.sum() < nuisance.shape[1] + 8:
        return selected, None, None

    taper = np.sqrt(weight[selected])
    basis = nuisance[selected] * taper[:, None]
    wave = carrier[selected] * taper
    coefficients = np.linalg.lstsq(basis, wave, rcond=1e-9)[0]
    projected = wave - basis @ coefficients
    power = projected @ projected
    if power <= 1e-12 or power < 1e-5 * (wave @ wave):
        return selected, None, None
    contrast = taper * projected / power
    return selected, contrast, float(np.linalg.norm(contrast))


def soft_wire_support(amplitude, error, exterior):
    """Shrink each signed continuation score using both reciprocal folds."""
    amplitude, error = np.asarray(amplitude), np.asarray(error)
    if amplitude.shape != error.shape or amplitude.ndim != 2 or amplitude.shape[0] != 2:
        raise ValueError("Expected paired amplitudes and errors for each window")
    if not math.isfinite(exterior) or exterior <= 0:
        return np.zeros(amplitude.shape[1])

    supported = np.all(np.isfinite(amplitude) & np.isfinite(error) & (error > 0), axis=0)
    result = np.zeros(amplitude.shape[1])
    paired = amplitude[:, supported]
    ratio = paired.mean(0) / exterior
    evidence = paired.sum(0) / np.hypot(*error[:, supported])

    def ramp(value, low, high):
        fraction = np.clip((value - low) / (high - low), 0, 1)
        return fraction**2 * (3 - 2 * fraction)

    result[supported] = (
        np.all(paired > 0, axis=0) * ramp(ratio, 0.33, 0.83) * ramp(evidence, 0.75, 3.25)
    )
    return result


def energy_matched_gain(mask, carrier):
    """Match the squared change of a spatially weighted carrier by a scalar gain."""
    energy = np.square(carrier)
    norm = float(energy.sum())
    if norm <= 1e-12:
        return 0.0
    return float(np.sqrt((np.square(mask) * energy).sum() / norm))
