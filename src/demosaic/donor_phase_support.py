"""Select phase-basis harmonics from a separate noisy RAW region."""

import numpy as np

from .local_validated_waves import fit_local_candidate, signed_knot_shape, stratified_split

PHASE_BINS = 8
FUNDAMENTAL = ((1,), (1,))
ALL_HARMONICS = ((1, 2, 3, 4),) * 2


def donor_phase_templates(raw, colors, frequencies, *, shot, read, config):
    """Recover two shape-only knot profiles in a donor disjoint from the query."""
    fit = fit_local_candidate(
        raw,
        colors,
        np.ones(raw.shape, dtype=bool),
        shot=shot,
        read=read,
        config=config,
        guide_frequencies_xy=frequencies,
        phase_bins=PHASE_BINS,
    )
    variance = fit.variance_cfa.ravel()
    precision = [np.sqrt(np.sum(1 / variance[i])) for i in fit.selected_indices]
    return np.stack(
        [
            signed_knot_shape(fit.coefficients[:, start:stop], precision)
            for start, stop in fit.wave_slices
        ]
    )


def donor_harmonic_scores(raw, colors, frequencies, *, shot, read, config):
    """Score higher modes against otherwise identical conditional donor fits.

    The result has axes fold, direction, and harmonic orders 2, 3, 4.
    Neither donor phase nor color coefficients are needed by the query.
    """
    raw, colors = np.asarray(raw, np.float64), np.asarray(colors)
    discovery = stratified_split(raw.shape, config.split_seed)
    result = []
    for fold in (discovery, ~discovery):
        full = fit_local_candidate(
            raw,
            colors,
            fold,
            shot=shot,
            read=read,
            config=config,
            guide_frequencies_xy=frequencies,
            phase_bins=PHASE_BINS,
            phase_harmonics=ALL_HARMONICS,
        )
        improvements, energies = np.zeros((2, 3)), np.zeros((2, 3))
        for color, selected in enumerate(full.selected_indices):
            held = (colors == color) & ~fold
            sigma = np.sqrt(full.variance_cfa.ravel()[selected])
            held_sigma = np.sqrt(full.variance_cfa[held])
            error = (raw[held] - full.full_cfa[held]) / held_sigma
            values = raw.ravel()[selected] / sigma
            weighted = full.design[selected] / sigma[:, None]
            other = full.design[held.ravel()] / held_sigma[:, None]
            for direction, (start, _stop) in enumerate(full.wave_slices):
                for i, (left, right) in enumerate(((2, 4), (4, 6), (6, 7))):
                    keep = np.ones(full.design.shape[1], dtype=bool)
                    keep[start + left : start + right] = False
                    null = np.linalg.lstsq(weighted[:, keep], values, rcond=1e-10)[0]
                    difference = full.full_cfa[held] / held_sigma - other[:, keep] @ null
                    energy = difference @ difference
                    improvements[direction, i] += error @ difference + energy / 2
                    energies[direction, i] += energy
        result.append(
            np.divide(
                improvements, np.sqrt(energies), out=np.zeros_like(energies), where=energies > 0
            )
        )
    return np.stack(result)
