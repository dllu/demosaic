"""Additional A-only fine-band carriers above the unchanged broad proposals."""

import numpy as np

from .carrier_spectrum import discovery_weights, weighted_spectrum
from .experiments.evaluation.withheld import geometry
from .local_validated_waves import LocalCandidate, _refine_frequency, _wave_columns

FINE_BAND = (1 / 16, 0.24)


def admissible_fine(frequencies, coarse, shape, *, native_bins=1.5, family_degrees=20):
    """Avoid duplicate coarse profiles and their uncertain integer harmonics.

    A coarse carrier already in the fine band owns its angular family. For
    lower-frequency carriers, harmonic exclusion radii grow with harmonic
    order, reflecting the same input-frequency displacement multiplied by h.
    These fixed exclusions are not calibrated uncertainty or completeness.
    """
    frequencies = np.asarray(frequencies, np.float64)
    radius = np.linalg.norm(frequencies, axis=-1)
    allowed = (radius >= FINE_BAND[0]) & (radius <= FINE_BAND[1])
    allowed &= (frequencies[..., 1] > 0) | ((frequencies[..., 1] == 0) & (frequencies[..., 0] > 0))
    for frequency in coarse:
        frequency = np.asarray(frequency, np.float64)
        norm = np.linalg.norm(frequency)
        for h in range(1, int(FINE_BAND[1] / norm) + 1):
            distance = np.minimum(
                np.linalg.norm((frequencies - h * frequency) * shape[::-1], axis=-1),
                np.linalg.norm((frequencies + h * frequency) * shape[::-1], axis=-1),
            )
            allowed &= distance > h * native_bins
        if norm >= FINE_BAND[0]:
            alignment = np.abs(np.sum(frequencies * frequency, axis=-1)) / np.maximum(
                radius * norm, 1e-30
            )
            allowed &= alignment <= np.cos(np.deg2rad(family_degrees))
    return allowed


def fit_fine_candidate(raw, colors, reference, *, shot, read, config):
    """Keep the broad fit as nuisance; discover two extra, distinct fine carriers."""
    raw, colors = np.asarray(raw, np.float64), np.asarray(colors)
    if (
        raw.shape != reference.discovery_mask.shape
        or colors.shape != raw.shape
        or not np.isfinite(raw[reference.discovery_mask]).all()
        or config.harmonics != 1
        or reference.unit_keys != ((0, 0), (1, 0))
    ):
        raise ValueError("Require matching A-only native CFA and two H1 broad carriers")
    xx, yy, _, _ = geometry(raw.shape)
    green = ((colors == 1) & reference.discovery_mask).ravel()
    nuisance = reference.design
    if config.frequency_weighting == "uniform":
        weights = np.ones(int(green.sum()))
    else:
        weights = discovery_weights(
            raw,
            green,
            nuisance[:, : reference.wave_slices[0][0]],
            shot=shot,
            read=read,
            hann=config.frequency_weighting == "hann-inverse-variance",
        )
    fy, fx = np.meshgrid(np.fft.fftfreq(raw.shape[0]), np.fft.fftfreq(raw.shape[1]), indexing="ij")

    def admissible(frequency):
        return admissible_fine(
            frequency,
            reference.frequencies_xy,
            raw.shape,
            native_bins=config.match_native_bins,
            family_degrees=config.family_degrees,
        )

    allowed = admissible(np.stack([fx, fy], axis=-1))
    frequencies = []
    for direction in (0, 1):
        power = weighted_spectrum(raw, green, nuisance, weights)
        available = allowed.copy()
        if direction:
            first = frequencies[0]
            alignment = np.abs(fx * first[0] + fy * first[1]) / np.maximum(
                np.hypot(fx, fy) * np.linalg.norm(first), 1e-30
            )
            available &= alignment <= np.cos(np.deg2rad(config.family_degrees))
        if not available.any():
            return None
        index = np.unravel_index(np.argmax(np.where(available, power, -np.inf)), raw.shape)
        frequency = _refine_frequency(
            raw,
            green,
            nuisance,
            xx,
            yy,
            (fx[index], fy[index]),
            config.frequency_refinements,
            avoid=frequencies[0] if direction else None,
            family_degrees=config.family_degrees,
            weights=weights,
            admissible=admissible,
        )
        frequencies.append(frequency)
        nuisance = np.column_stack((nuisance, _wave_columns(xx, yy, frequency)))
    n = reference.design.shape[1]
    slices = ((n, n + 2), (n + 2, n + 4))
    design = nuisance
    full, nulls = np.empty(raw.size), np.empty((2, raw.size))
    operators, coefficients = [], []
    for color in range(3):
        selected = reference.selected_indices[color]
        destination = (colors == color).ravel()
        precision = 1 / np.sqrt(reference.variance_cfa.ravel()[selected])
        operator = np.linalg.pinv(design[selected] * precision[:, None], rcond=1e-10)
        operator *= precision[None]
        coefficient = operator @ raw.ravel()[selected]
        full[destination] = design[destination] @ coefficient
        for direction, (start, stop) in enumerate(slices):
            keep = np.ones(design.shape[1], bool)
            keep[start:stop] = False
            null_coefficient = np.linalg.lstsq(
                design[selected][:, keep] * precision[:, None],
                raw.ravel()[selected] * precision,
                rcond=1e-10,
            )[0]
            nulls[direction, destination] = design[destination][:, keep] @ null_coefficient
        operators.append(operator)
        coefficients.append(coefficient)
    fields = tuple(_wave_columns(xx, yy, f).reshape(*raw.shape, 2) for f in frequencies)
    return LocalCandidate(
        tuple(frequencies),
        reference.edge_geometry,
        reference.discovery_mask.copy(),
        design,
        reference.selected_indices,
        tuple(operators),
        np.stack(coefficients),
        fields,
        slices,
        fields,
        slices,
        ((0, 0), (1, 0)),
        full.reshape(raw.shape),
        nulls.reshape(2, *raw.shape),
        reference.variance_cfa.copy(),
    )
