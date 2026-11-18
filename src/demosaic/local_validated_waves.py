"""Experimental local RAW-wave replacement above an already restored image.

Discovery and conditional validation never see the parent. Per-direction/color
support uses disjoint CFA samples; scores are empirical, not calibrated risks.
The accepted analytic component replaces its projection in the parent instead
of adding the entire measured signal twice. Parent projection happens only
after discovery/validation. Finite support is still approximate.
"""

from dataclasses import asdict, dataclass
from itertools import permutations

import numpy as np

from .experiments.evaluation.withheld import fit_candidate, geometry, stratified_split


@dataclass(frozen=True)
class LocalWaveConfig:
    window: int = 256
    stride: int = 128
    validation_window: int = 129
    validation_stride: int = 32
    edge_refinements: int = 3
    frequency_refinements: int = 1
    family_degrees: float = 20.0
    match_native_bins: float = 1.5
    matching: str = "cardinality"
    harmonics: int = 1
    support_unit: str = "direction"
    background: str = "step"
    edge_search: str = "bounded-grid"
    frequency_weighting: str = "uniform"
    amplitude_window: int = 0
    amplitude_stride: int = 32
    amplitude_nuisance: str = "local"
    split_seed: int = 202611160909

    def __post_init__(self):
        if (
            any(
                type(v) is not int
                for v in [
                    self.window,
                    self.stride,
                    self.validation_window,
                    self.validation_stride,
                    self.edge_refinements,
                    self.frequency_refinements,
                    self.split_seed,
                    self.harmonics,
                    self.amplitude_window,
                    self.amplitude_stride,
                ]
            )
            or not np.isfinite([self.family_degrees, self.match_native_bins]).all()
            or self.window < 32
            or self.window % 4
            or not 1 <= self.stride <= self.window
            or self.stride % 2
            or self.validation_window < 3
            or self.validation_window % 2 != 1
            or not 1 <= self.validation_stride <= self.window
            or not 0 <= self.edge_refinements <= 3
            or not 0 <= self.frequency_refinements <= 2
            or not 0 < self.family_degrees < 90
            or not 0 < self.match_native_bins <= 4
            or self.matching not in ("legacy", "cardinality")
            or not 1 <= self.harmonics <= 4
            or self.support_unit not in ("direction", "harmonic")
            or self.background
            not in (
                "step",
                "piecewise_affine",
                "parallel_step",
                "curved_step",
                "curved4_step",
            )
            or self.edge_search not in ("bounded-grid", "full-frame")
            or self.frequency_weighting
            not in ("uniform", "inverse-variance", "hann-inverse-variance")
            or (
                self.amplitude_window != 0
                and (self.amplitude_window < 17 or self.amplitude_window % 2 != 1)
            )
            or not 1 <= self.amplitude_stride <= 64
            or self.amplitude_nuisance not in ("local", "global")
        ):
            raise ValueError("Invalid local-wave geometry")

    def to_dict(self):
        return asdict(self)


_DEFAULT_CONFIG = LocalWaveConfig()


@dataclass(frozen=True)
class LocalCandidate:
    frequencies_xy: tuple
    edge_geometry: tuple
    discovery_mask: np.ndarray
    design: np.ndarray
    selected_indices: tuple
    operators: tuple
    coefficients: np.ndarray
    wave_fields: tuple
    wave_slices: tuple
    unit_fields: tuple
    unit_slices: tuple
    unit_keys: tuple
    full_cfa: np.ndarray
    conditional_null_cfa: np.ndarray
    variance_cfa: np.ndarray
    guide_search_excluded: int = 0
    phase_reliability_degrees: int | None = None
    donor_phase_shifts: tuple = ()
    phase_bright_side: np.ndarray | None = None
    phase_side_profiles: bool = False
    guide_crosschecks: tuple = ()
    phase_drifts: tuple = ()
    phase_drift_trials: tuple = ()
    parallel_edges: tuple | None = None
    flexible_edges: tuple | None = None


def _phase_cycles(xx, yy, frequency, offset):
    phase = xx * frequency[0] + yy * frequency[1]
    return phase if offset is None else phase + offset


def _wave_columns(xx, yy, frequency, harmonics=1, *, offset=None):
    phase = 2 * np.pi * _phase_cycles(xx, yy, frequency, offset)
    return np.column_stack(
        [
            column.ravel()
            for h in range(1, harmonics + 1)
            for column in (np.cos(h * phase), np.sin(h * phase))
        ]
    )


def _phase_bin_weights(xx, yy, frequency, bins, *, offset=None):
    """Circular linear-interpolation weights for a native periodic profile."""
    phase = np.remainder(_phase_cycles(xx, yy, frequency, offset), 1).ravel() * bins
    left = np.floor(phase).astype(np.int64)
    fraction = phase - left
    weights = np.zeros((phase.size, bins), dtype=np.float64)
    indices = np.arange(phase.size)
    weights[indices, left % bins] = 1 - fraction
    weights[indices, (left + 1) % bins] = fraction
    return weights


def _phase_harmonic_columns(xx, yy, frequency, bins, orders):
    """Evaluate Fourier modes on a periodic knot grid before native interpolation."""
    phase = 2 * np.pi * np.arange(bins) / bins
    modes = []
    for order in orders:
        modes.append(np.cos(order * phase))
        if 2 * order != bins:
            modes.append(np.sin(order * phase))
    return _phase_bin_weights(xx, yy, frequency, bins) @ np.column_stack(modes)


def _validate_phase_bins(phase_bins, guide, config, phase_harmonics=None):
    if type(phase_bins) is not int or (phase_bins and not 3 <= phase_bins <= 12):
        raise ValueError("Phase interpolation requires 3 to 12 bins")
    if phase_bins and (
        guide is None
        or config.harmonics != 1
        or config.support_unit != "direction"
        or config.amplitude_window
    ):
        raise ValueError("Phase bins require fixed guides and one whole-query fit per direction")
    if phase_harmonics is not None and (
        not phase_bins
        or len(phase_harmonics) != 2
        or any(
            len(orders) == 0
            or any(type(k) is not int or not 1 <= k <= phase_bins // 2 for k in orders)
            or tuple(orders) != tuple(sorted(set(orders)))
            for orders in phase_harmonics
        )
    ):
        raise ValueError("Require sorted, distinct phase harmonics for both fixed guides")


def _harmonic_count(frequency, maximum):
    """Fix degrees of freedom before refinement; keep every harmonic below .24."""
    return max(1, min(maximum, int(np.floor((0.24 + 1e-12) / np.linalg.norm(frequency)))))


def _residual_peak(raw, selected, nuisance, *, avoid=None, family_degrees=20.0, weights=None):
    """Choose a green A-only FFT peak after refitting all competing columns."""
    if weights is None:
        fitted = (
            nuisance[selected]
            @ np.linalg.lstsq(nuisance[selected], raw.ravel()[selected], rcond=1e-10)[0]
        )
        residual = np.zeros(raw.size)
        residual[selected] = raw.ravel()[selected] - fitted
        power = np.abs(np.fft.fft2(residual.reshape(raw.shape))) ** 2
    else:
        from .carrier_spectrum import weighted_spectrum

        power = weighted_spectrum(raw, selected, nuisance, weights)
    fy, fx = np.meshgrid(np.fft.fftfreq(raw.shape[0]), np.fft.fftfreq(raw.shape[1]), indexing="ij")
    radius = np.hypot(fx, fy)
    allowed = (radius >= 1 / 64) & (radius <= 0.24) & ((fy > 0) | ((fy == 0) & (fx > 0)))
    if avoid is not None:
        alignment = np.abs(
            (fx * avoid[0] + fy * avoid[1]) / np.maximum(radius * np.linalg.norm(avoid), 1e-30)
        )
        allowed &= alignment <= np.cos(np.deg2rad(family_degrees))
    index = np.unravel_index(np.argmax(np.where(allowed, power, -np.inf)), raw.shape)
    return (float(fx[index]), float(fy[index]))


def _refine_frequency(
    raw,
    selected,
    nuisance,
    xx,
    yy,
    frequency,
    levels,
    *,
    avoid=None,
    family_degrees=20.0,
    harmonics=1,
    weights=None,
    admissible=None,
):
    basis = nuisance[selected]
    values = raw.ravel()[selected]
    if weights is not None:
        sigma = np.sqrt(weights / weights.mean())
        basis = basis * sigma[:, None]
        values = values * sigma
    q, _ = np.linalg.qr(basis, mode="reduced")
    residual = values - q @ (q.T @ values)
    chosen = np.asarray(frequency)
    radius = 0.5 / min(raw.shape)
    for _ in range(levels):
        candidates = [
            chosen + [dx, dy]
            for dy in np.linspace(-radius, radius, 9)
            for dx in np.linspace(-radius, radius, 9)
        ]
        best = -np.inf
        chosen_next = chosen
        for candidate in candidates:
            if not 1 / 64 <= np.linalg.norm(candidate) <= 0.24 / harmonics:
                continue
            if admissible is not None and not admissible(candidate):
                continue
            if avoid is not None and abs(np.dot(candidate, avoid)) > np.cos(
                np.deg2rad(family_degrees)
            ) * np.linalg.norm(candidate) * np.linalg.norm(avoid):
                continue
            waves = _wave_columns(xx, yy, candidate, harmonics)[selected]
            if weights is not None:
                waves = waves * sigma[:, None]
            waves = waves - q @ (q.T @ waves)
            coefficient = np.linalg.lstsq(waves, residual, rcond=1e-10)[0]
            benefit = float(np.sum((waves @ coefficient) ** 2))
            if benefit > best:
                best, chosen_next = benefit, candidate
        chosen = chosen_next
        radius /= 4
    return tuple(float(v) for v in chosen)


def _guide_frequencies(value, family_degrees):
    frequencies = np.asarray(value, dtype=np.float64)
    if frequencies.shape != (2, 2) or not np.isfinite(frequencies).all():
        raise ValueError("Require two finite guide frequencies in native cycles per pixel")
    radius = np.linalg.norm(frequencies, axis=1)
    if np.any((radius < 1 / 64) | (radius > 0.24)):
        raise ValueError("Guide frequencies must lie in the native search annulus")
    cosine = abs(float(frequencies[0] @ frequencies[1] / np.prod(radius)))
    if cosine > np.cos(np.deg2rad(family_degrees)):
        raise ValueError("Guide directions must belong to separate orientation families")
    return tuple(tuple(float(v) for v in row) for row in frequencies)


def _validate_guide_search(recenter, guard_px, bins, harmonics, crosscheck=False):
    if type(recenter) is not bool or (recenter and (not bins or harmonics is not None)):
        raise ValueError("Guide recentering requires the full interpolated phase basis")
    if type(guard_px) is not int or guard_px < 0 or (guard_px and not recenter):
        raise ValueError("An edge guard requires phase-guide recentering and a native pixel width")
    if type(crosscheck) is not bool or (crosscheck and not recenter):
        raise ValueError("Guide cross-check requires phase-guide recentering")


def _validate_phase_drift(enabled, bins, harmonics, templates):
    if type(enabled) is not bool or (enabled and (not bins or harmonics or templates is not None)):
        raise ValueError("Phase drift requires the full query-fitted phase basis")


def _validate_phase_hessians(value, shape, guide, bins, harmonics, adaptive, templates):
    if value is None:
        return None
    if guide is None or not bins or harmonics is not None or adaptive or templates is not None:
        raise ValueError(
            "Fixed phase Hessians require fixed frequencies and a query-fitted phase basis"
        )
    hessians = np.asarray(value, np.float64)
    if (
        hessians.shape != (2, 2, 2)
        or not np.isfinite(hessians).all()
        or not np.array_equal(hessians, hessians.transpose(0, 2, 1))
    ):
        raise ValueError("Require two finite symmetric native phase Hessians")
    if any(
        not phase_gradient_in_annulus(frequency, hessian, shape)
        for frequency, hessian in zip(guide, hessians, strict=True)
    ):
        raise ValueError("Fixed phase geometry leaves the native frequency annulus")
    return tuple(tuple(tuple(float(v) for v in row) for row in hessian) for hessian in hessians)


def phase_gradient_in_annulus(frequency, hessian, shape):
    """Conservatively bound the frequency norm throughout a native rectangle."""
    hy, hx = (np.asarray(shape, dtype=np.float64) - 1) / 2
    corners = np.array([[-hx, -hy], [-hx, hy], [hx, -hy], [hx, hy]])
    deviation = np.max(np.linalg.norm(corners @ np.asarray(hessian), axis=1))
    radius = np.linalg.norm(frequency)
    return radius - deviation >= 1 / 64 and radius + deviation <= 0.24


def _validate_shared_phase_shape(shared, bins, harmonics):
    if type(shared) is not bool or (shared and (not bins or harmonics is not None)):
        raise ValueError("A shared phase shape requires the full interpolated phase basis")


def _donor_templates(value, bins, harmonics, shared):
    if value is None:
        return None
    profiles = np.asarray(value, np.float64)
    if (
        bins != 8
        or harmonics is not None
        or shared
        or profiles.shape != (2, bins)
        or not np.isfinite(profiles).all()
        or np.any(np.ptp(profiles, axis=1) == 0)
    ):
        raise ValueError("Require two finite nonconstant eight-knot donor profiles")
    return tuple(tuple(row) for row in profiles)


def signed_knot_shape(coefficient, precision):
    """Return a unit waveform, with the DC handled by the nuisance intercept."""
    knots = np.column_stack((coefficient, -coefficient.sum(axis=1)))
    _, _, directions = np.linalg.svd(np.asarray(precision)[:, None] * knots, full_matrices=False)
    return directions[0]


def _shared_phase_fields(waves, nuisance, values, indices, variances):
    """Estimate one signed-amplitude waveform subspace per direction."""
    design = np.column_stack((nuisance, *waves))
    coefficients, precision = [], []
    for measured, noise in zip(indices, variances, strict=True):
        sigma = 1 / np.sqrt(noise[measured])
        coefficients.append(
            np.linalg.lstsq(
                design[measured] * sigma[:, None], values[measured] * sigma, rcond=1e-10
            )[0]
        )
        precision.append(np.linalg.norm(sigma))
    coefficients = np.stack(coefficients)
    fields = []
    start = nuisance.shape[1]
    for wave in waves:
        stop = start + wave.shape[1]
        shape = signed_knot_shape(coefficients[:, start:stop], precision)
        fields.append(wave @ shape[:-1, None])
        start = stop
    return fields


def shifted_donor_knots(profile, turns):
    """Evaluate cyclic translations of one eight-knot Fourier interpolant."""
    spectrum = np.fft.rfft(profile)
    spectrum[0] = 0
    rotation = np.exp(-2j * np.pi * np.arange(len(spectrum))[:, None] * np.asarray(turns))
    return np.fft.irfft(spectrum[:, None] * rotation, n=len(profile), axis=0)


def _donor_phase_fields(waves, templates, nuisance, values, indices, variances):
    """Select query phase on discovery samples after projecting out competitors."""
    search = np.arange(24) / 24
    fields, phases = [], []
    for direction, template in enumerate(templates):
        trials = shifted_donor_knots(template, search)
        norms = np.linalg.norm(trials, axis=0)
        usable = norms > norms.max() * 1e-10
        trials = np.divide(trials, norms, out=np.zeros_like(trials), where=usable)[:-1]
        competitor = np.column_stack((nuisance, waves[1 - direction]))
        energy = np.zeros(len(search))
        for measured, noise in zip(indices, variances, strict=True):
            whitener = 1 / np.sqrt(noise[measured])
            null = competitor[measured] * whitener[:, None]
            joint = np.column_stack((waves[direction][measured], values[measured]))
            joint *= whitener[:, None]
            joint -= null @ np.linalg.lstsq(null, joint, rcond=1e-10)[0]
            basis, residual = joint[:, :-1], joint[:, -1]
            cross = (basis.T @ residual) @ trials
            power = np.sum(trials * ((basis.T @ basis) @ trials), axis=0)
            energy += np.divide(cross**2, power, out=np.zeros_like(power), where=power > 0)
        best = np.argmax(energy)
        fields.append(waves[direction] @ trials[:, best, None])
        phases.append(float(search[best]))
    return fields, tuple(phases)


def _green_edge_polarity(raw, green, nuisance, shot, read):
    """Measure the strength and polarity of the discovery-fold green step."""
    design, values = nuisance[green], raw.ravel()[green]
    coefficients = np.linalg.lstsq(design, values, rcond=1e-10)[0]
    brightest = max(float(np.max(design @ coefficients)), 1e-6)
    if abs(coefficients[3]) <= 2 * np.sqrt(read + shot * brightest):
        return 0
    return 1 if coefficients[3] > 0 else -1


def _edge_guarded_green(raw, green, nuisance, x, y, angle, offset, width, shot, read):
    """Exclude a band around a strong discovery-fold step from frequency selection."""
    if not _green_edge_polarity(raw, green, nuisance, shot, read):
        return green
    cx, cy = np.cos(angle), np.sin(angle)
    per_pixel = np.hypot(2 * cx / raw.shape[1], 2 * cy / raw.shape[0])
    distance = np.abs(x * cx + y * cy - offset).ravel() / per_pixel
    return green & (distance >= width)


def _phase_side_option(mode, bins, harmonics, shared, templates):
    if mode not in (None, "validation", "profiles") or (
        mode is not None and (not bins or harmonics is not None or shared or templates is not None)
    ):
        raise ValueError("Edge-side phase support requires independent full phase profiles")


def _bright_edge_side(raw, green, nuisance, selected, shot, read):
    polarity = _green_edge_polarity(raw, green, nuisance, shot, read)
    if polarity == 0:
        return None
    bright = nuisance[:, 3] == (polarity > 0)
    # Require at least one eighth of each measured color on each side.
    for sites in selected:
        count = np.count_nonzero(bright[sites])
        if 8 * min(count, len(sites) - count) < len(sites):
            return None
    return bright.reshape(raw.shape)


def _crosscheck_guide_move(
    x, y, values, background, competitor, origin, proposal, split, shot, read
):
    """Measure held-out error reductions in both directions within discovery."""
    columns = [_wave_columns(x, y, f) for f in (origin, proposal)]
    return _crosscheck_phase_columns(values, background, competitor, columns, split, shot, read)


def _crosscheck_phase_columns(values, background, competitor, columns, split, shot, read):
    if min(split.sum(), (~split).sum()) <= competitor.shape[1] + 2:
        return (0.0, 0.0)
    designs = [np.column_stack((competitor, wave)) for wave in columns]
    reductions = []
    for train in (split, ~split):
        test = ~train
        coef = np.linalg.lstsq(background[train], values[train], rcond=1e-10)[0]
        inv_sigma = 1 / np.sqrt(read + shot * np.maximum(background @ coef, 1e-6))
        target = values[train] * inv_sigma[train]
        errors = []
        for design in designs:
            coef = np.linalg.lstsq(design[train] * inv_sigma[train, None], target, rcond=1e-10)[0]
            residual = (values[test] - design[test] @ coef) * inv_sigma[test]
            errors.append(residual @ residual)
        reductions.append(float(errors[0] - errors[1]))
    return tuple(reductions)


def _recenter_phase_guides(
    raw, green, nuisance, xx, yy, frequencies, bins, shot, read, family, crosschecks=None
):
    """Search a bounded frequency cross using only one fold's green measurements."""
    x, y = xx.ravel()[green], yy.ravel()[green]
    background = nuisance[green]
    values = raw.ravel()[green]
    fitted = background @ np.linalg.lstsq(background, values, rcond=1e-10)[0]
    inverse_sigma = 1 / np.sqrt(read + shot * np.maximum(fitted, 1e-6))
    spacing = 1 / min(raw.shape)
    cosine = np.cos(np.deg2rad(family))
    chosen = [np.asarray(f) for f in frequencies]
    if crosschecks is not None:
        split = stratified_split(raw.shape, 202611170713).ravel()[green]
    for index, origin in enumerate(chosen.copy()):
        other = chosen[1 - index]
        knot = _phase_bin_weights(x, y, other, bins)
        design = np.column_stack((background, knot[:, :-1] - knot[:, -1:]))
        u, s, _ = np.linalg.svd(design * inverse_sigma[:, None], full_matrices=False)
        basis = u[:, s > 1e-10 * s[0]]
        target = values * inverse_sigma
        target -= basis @ (basis.T @ target)
        radial = origin / np.linalg.norm(origin)
        tangent = np.array([-radial[1], radial[0]])
        candidates = [origin]
        for direction in (radial, tangent):
            candidates.extend(origin + step * spacing * direction for step in (-0.5, 0.5, -1, 1))
        scores = np.full(len(candidates), -np.inf)
        for i, candidate in enumerate(candidates):
            norm = np.linalg.norm(candidate)
            if not 1 / 64 <= norm <= 0.24:
                continue
            if abs(other @ candidate) > cosine * np.linalg.norm(other) * norm:
                continue
            columns = _wave_columns(x, y, candidate) * inverse_sigma[:, None]
            columns -= basis @ (basis.T @ columns)
            coefficient = np.linalg.lstsq(columns, target, rcond=1e-10)[0]
            projection = columns @ coefficient
            scores[i] = projection @ projection
        best = int(np.argmax(scores))
        if scores[best] > scores[0] + 4:
            if crosschecks is not None:
                gains = _crosscheck_guide_move(
                    x, y, values, background, design, origin, candidates[best], split, shot, read
                )
                accepted = min(gains) > 0
                crosschecks.append(
                    {
                        "direction": index,
                        "origin_xy": origin.tolist(),
                        "proposed_xy": candidates[best].tolist(),
                        "full_discovery_gain": float(scores[best] - scores[0]),
                        "nested_error_reductions": gains,
                        "accepted": accepted,
                    }
                )
                if not accepted:
                    continue
            chosen[index] = candidates[best]
    return tuple(tuple(float(v) for v in f) for f in chosen)


def _phase_coordinates(x, y, shape, frequency):
    h, w = shape
    x = (x - (w - 1) / 2) / min(shape)
    y = (y - (h - 1) / 2) / min(shape)
    fx, fy = np.asarray(frequency) / np.linalg.norm(frequency)
    return fx * x + fy * y, -fy * x + fx * y


def _drift_offset(x, y, shape, frequency, drift):
    if drift == (0, 0):
        return None
    normal, tangent = _phase_coordinates(x, y, shape, frequency)
    return 0.5 * (drift[0] * normal**2 + drift[1] * tangent**2)


def _fixed_phase_offset(xx, yy, shape, hessian):
    if not np.any(hessian):
        return None
    x, y = xx - (shape[1] - 1) / 2, yy - (shape[0] - 1) / 2
    (xx_coef, xy_coef), (_, yy_coef) = hessian
    return 0.5 * (xx_coef * x**2 + 2 * xy_coef * x * y + yy_coef * y**2)


def _search_phase_drifts(raw, green, nuisance, xx, yy, frequencies, bins, shot, read):
    """Fit quadratic phase on one fold and cross-check it within that fold."""
    chosen, trials = [(0, 0), (0, 0)], []
    background, values = nuisance[green], raw.ravel()[green]
    if len(values) < 2 * (nuisance.shape[1] + bins + 2):
        return tuple(chosen), ()
    x, y = xx.ravel()[green], yy.ravel()[green]
    fitted = background @ np.linalg.lstsq(background, values, rcond=1e-10)[0]
    inverse_sigma = 1 / np.sqrt(read + shot * np.maximum(fitted, 1e-6))
    split = stratified_split(raw.shape, 202611170714).ravel()[green]
    for index, frequency in enumerate(frequencies):
        other = 1 - index
        offset = _drift_offset(x, y, raw.shape, frequencies[other], chosen[other])
        knot = _phase_bin_weights(x, y, frequencies[other], bins, offset=offset)
        design = np.column_stack((background, knot[:, :-1] - knot[:, -1:]))
        u, s, _ = np.linalg.svd(design * inverse_sigma[:, None], full_matrices=False)
        basis = u[:, s > 1e-10 * s[0]]
        target = values * inverse_sigma
        target -= basis @ (basis.T @ target)
        std_axes = _phase_coordinates(xx, yy, raw.shape, frequency)
        radius = np.linalg.norm(frequency)
        drift_grid = [(0, 0)]
        for axis, coordinate in enumerate(std_axes):
            for q in (-12, -8, -4, 4, 8, 12):
                deviation = abs(q) * np.max(np.abs(coordinate)) / min(raw.shape)
                if radius - deviation >= 1 / 64 and radius + deviation <= 0.24:
                    drift_grid.append((q, 0) if axis == 0 else (0, q))
        waves, scores = [], []
        for drift in drift_grid:
            offset = _drift_offset(x, y, raw.shape, frequency, drift)
            wave = _wave_columns(x, y, frequency, offset=offset)
            columns = wave * inverse_sigma[:, None]
            columns -= basis @ (basis.T @ columns)
            fit = columns @ np.linalg.lstsq(columns, target, rcond=1e-10)[0]
            scores.append(float(fit @ fit))
            waves.append(wave)
        best = int(np.argmax(scores))
        gain = scores[best] - scores[0]
        if gain > 4:
            reductions = _crosscheck_phase_columns(
                values, background, design, (waves[0], waves[best]), split, shot, read
            )
            accepted = min(reductions) > 0
            if accepted:
                chosen[index] = drift_grid[best]
            trials.append(
                {
                    "direction": index,
                    "proposed": drift_grid[best],
                    "full_discovery_gain": gain,
                    "nested_error_reductions": reductions,
                    "accepted": accepted,
                }
            )
    return tuple(chosen), tuple(trials)


def _compatible_drifts(candidates, direction_a, direction_b, xx, yy):
    frequencies = [c.frequencies_xy[k] for c, k in zip(candidates, (direction_a, direction_b))]
    offsets = [
        _drift_offset(xx, yy, xx.shape, f, c.phase_drifts[k])
        for c, k, f in zip(candidates, (direction_a, direction_b), frequencies, strict=True)
    ]
    if offsets[0] is None and offsets[1] is None:
        return True
    a, b = [0.0 if offset is None else offset for offset in offsets]
    sign = np.sign(np.dot(*frequencies))
    return np.std(a - sign * b) <= 0.25


def fit_local_candidate(
    raw,
    colors,
    discovery_mask,
    *,
    shot,
    read,
    config=_DEFAULT_CONFIG,
    guide_frequencies_xy=None,
    phase_bins=0,
    phase_harmonics=None,
    recenter_phase_guides=False,
    phase_guide_edge_guard_px=0,
    phase_guide_crosscheck=False,
    phase_drift_search=False,
    guide_phase_hessians_xy=None,
    shared_phase_shape=False,
    donor_phase_templates=None,
    phase_edge_side=None,
):
    """Fit query nuisance, phase and amplitude on the discovery fold.

    Optional guides supply initial frequencies and can constrain the phase
    basis. The bounded search, when enabled, reads only this fold's green sites.
    """
    _validate_phase_bins(phase_bins, guide_frequencies_xy, config, phase_harmonics)
    _validate_guide_search(
        recenter_phase_guides,
        phase_guide_edge_guard_px,
        phase_bins,
        phase_harmonics,
        phase_guide_crosscheck,
    )
    _validate_shared_phase_shape(shared_phase_shape, phase_bins, phase_harmonics)
    templates = _donor_templates(
        donor_phase_templates, phase_bins, phase_harmonics, shared_phase_shape
    )
    _validate_phase_drift(phase_drift_search, phase_bins, phase_harmonics, templates)
    _phase_side_option(phase_edge_side, phase_bins, phase_harmonics, shared_phase_shape, templates)
    raw, colors, discovery_mask = (
        np.asarray(raw, np.float64),
        np.asarray(colors),
        np.asarray(discovery_mask),
    )
    hessians = _validate_phase_hessians(
        guide_phase_hessians_xy,
        raw.shape,
        guide_frequencies_xy,
        phase_bins,
        phase_harmonics,
        phase_drift_search or recenter_phase_guides,
        templates,
    )
    initial = fit_candidate(
        raw,
        colors,
        discovery_mask,
        shot=shot,
        read=read,
        nuisance="step",
        peaks=1,
        edge_refinements=config.edge_refinements,
        edge_search=config.edge_search,
    )
    xx, yy, affine, _ = geometry(raw.shape)
    angle, offset = initial.edge_geometry
    x, y = 2 * (xx + 0.5) / raw.shape[1] - 1, 2 * (yy + 0.5) / raw.shape[0] - 1
    nuisance = np.column_stack((affine, (x * np.cos(angle) + y * np.sin(angle) > offset).ravel()))
    green = ((colors == 1) & discovery_mask).ravel()
    first_frequency = initial.frequencies_xy[0]
    edge_for_validation = nuisance
    parallel = None
    flexible = None
    if config.background == "piecewise_affine":
        step = nuisance[:, 3]
        nuisance = np.column_stack((nuisance, x.ravel() * step, y.ravel() * step))
        edge_for_validation = nuisance
    elif config.background in ("parallel_step", "curved_step", "curved4_step"):
        from .full_frame_edge import supported_parallel_edges

        values = raw.ravel()[green]
        single = nuisance[green]
        residual = values - single @ np.linalg.lstsq(single, values, rcond=1e-10)[0]
        parallel = supported_parallel_edges(
            values,
            np.column_stack((x.ravel()[green], y.ravel()[green])),
            angle,
            offset,
            residual @ residual,
            shot,
            read,
        )
        if parallel is not None:
            normal, first, second = parallel
            pos = (x * np.cos(normal) + y * np.sin(normal)).ravel()
            nuisance = np.column_stack((affine, pos > first, pos > second))
        if config.background != "parallel_step":
            from .flexible_edge import edge_terms, fit_flexible_edges

            xy = affine[:, 1:]
            normal, *offsets = parallel if parallel is not None else (angle, offset)
            flexible = fit_flexible_edges(
                values,
                xy[green],
                normal,
                offsets,
                min(raw.shape),
                shot,
                read,
                maximum=4 if config.background == "curved4_step" else 2,
            )
            if flexible is not None:
                nuisance = np.column_stack((affine, edge_terms(xy, *flexible)))
    excluded = 0
    crosschecks = [] if phase_guide_crosscheck else None
    drifts, drift_trials = (), ()
    if guide_frequencies_xy is not None:
        frequencies = _guide_frequencies(guide_frequencies_xy, config.family_degrees)
        search = green
        if phase_guide_edge_guard_px:
            search = _edge_guarded_green(
                raw, green, nuisance, x, y, angle, offset, phase_guide_edge_guard_px, shot, read
            )
            excluded = int(green.sum() - search.sum())
        if recenter_phase_guides and (
            not phase_guide_edge_guard_px or search.sum() >= nuisance.shape[1] + phase_bins + 1
        ):
            frequencies = _recenter_phase_guides(
                raw,
                search,
                nuisance,
                xx,
                yy,
                frequencies,
                phase_bins,
                shot,
                read,
                config.family_degrees,
                **({"crosschecks": crosschecks} if crosschecks is not None else {}),
            )
        counts = tuple(_harmonic_count(f, config.harmonics) for f in frequencies)
        if phase_drift_search:
            drifts, drift_trials = _search_phase_drifts(
                raw, search, nuisance, xx, yy, frequencies, phase_bins, shot, read
            )
    else:
        if config.background != "step":
            first_frequency = _residual_peak(raw, green, nuisance)
        weights = None
        if config.frequency_weighting != "uniform":
            from .carrier_spectrum import discovery_weights

            weights = discovery_weights(
                raw,
                green,
                nuisance,
                shot=shot,
                read=read,
                hann=config.frequency_weighting == "hann-inverse-variance",
            )
            first_frequency = _residual_peak(raw, green, nuisance, weights=weights)
        first_harmonics = _harmonic_count(first_frequency, config.harmonics)
        first = _refine_frequency(
            raw,
            green,
            nuisance,
            xx,
            yy,
            first_frequency,
            config.frequency_refinements,
            harmonics=first_harmonics,
            weights=weights,
        )
        one = np.column_stack((nuisance, _wave_columns(xx, yy, first, first_harmonics)))
        second_frequency = _residual_peak(
            raw, green, one, avoid=first, family_degrees=config.family_degrees, weights=weights
        )
        second_harmonics = _harmonic_count(second_frequency, config.harmonics)
        second = _refine_frequency(
            raw,
            green,
            one,
            xx,
            yy,
            second_frequency,
            config.frequency_refinements,
            avoid=first,
            family_degrees=config.family_degrees,
            harmonics=second_harmonics,
            weights=weights,
        )
        frequencies = (first, second)
        counts = (first_harmonics, second_harmonics)
    if phase_harmonics is not None:
        waves = [
            _phase_harmonic_columns(xx, yy, f, phase_bins, orders)
            for f, orders in zip(frequencies, phase_harmonics, strict=True)
        ]
    elif phase_bins:
        waves = []
        for index, frequency in enumerate(frequencies):
            offset = None
            if drifts:
                offset = _drift_offset(xx, yy, raw.shape, frequency, drifts[index])
            elif hessians is not None:
                offset = _fixed_phase_offset(xx, yy, raw.shape, hessians[index])
            weights = _phase_bin_weights(xx, yy, frequency, phase_bins, offset=offset)
            # Parameterize a zero-mean knot profile. The existing nuisance
            # intercept handles the DC shared across phase bins.
            waves.append(weights[:, :-1] - weights[:, -1:])
    else:
        waves = [
            _wave_columns(xx, yy, f, count) for f, count in zip(frequencies, counts, strict=True)
        ]
    indices, noise_fields = [], []
    for color in range(3):
        selected = np.flatnonzero(((colors == color) & discovery_mask).ravel())
        background_coeff = np.linalg.lstsq(nuisance[selected], raw.ravel()[selected], rcond=1e-10)[
            0
        ]
        proxy = nuisance @ background_coeff
        indices.append(selected)
        noise_fields.append(read + shot * np.maximum(proxy, 1e-6))
    shifts = ()
    if shared_phase_shape:
        waves = _shared_phase_fields(waves, nuisance, raw.ravel(), indices, noise_fields)
    if templates is not None:
        waves, shifts = _donor_phase_fields(
            waves, templates, nuisance, raw.ravel(), indices, noise_fields
        )
    bright = (
        _bright_edge_side(raw, green, edge_for_validation, indices, shot, read)
        if phase_edge_side is not None
        else None
    )
    split_profiles = bright is not None and phase_edge_side == "profiles"
    if split_profiles:
        side = bright.ravel()[:, None]
        waves = [np.column_stack((wave * ~side, wave * side)) for wave in waves]
    n = nuisance.shape[1]
    split = n + waves[0].shape[1]
    wave_slices = ((n, split), (split, split + waves[1].shape[1]))
    wave_fields = tuple(wave.reshape(*raw.shape, wave.shape[1]) for wave in waves)
    if split_profiles:
        unit_slices, unit_fields, unit_keys = [], [], []
        width = phase_bins - 1
        for direction, (start, _) in enumerate(wave_slices):
            for side in (0, 1):
                offset = side * width
                unit_slices.append((start + offset, start + offset + width))
                unit_fields.append(wave_fields[direction][..., offset : offset + width])
                unit_keys.append((direction, side))
    elif config.support_unit == "direction":
        unit_slices, unit_fields, unit_keys = wave_slices, wave_fields, ((0, 0), (1, 0))
    else:
        unit_slices, unit_fields, unit_keys = [], [], []
        for direction, (start, stop) in enumerate(wave_slices):
            for column in range(start, stop, 2):
                offset = column - start
                unit_slices.append((column, column + 2))
                unit_fields.append(wave_fields[direction][..., offset : offset + 2])
                unit_keys.append((direction, offset // 2 + 1))
    design = np.column_stack((nuisance, *waves))
    full_cfa, nulls, variance = (
        np.empty(raw.size),
        np.empty((len(unit_slices), raw.size)),
        np.empty(raw.size),
    )
    operators, coefficients = [], []
    for color, (selected, noise) in enumerate(zip(indices, noise_fields, strict=True)):
        destination = (colors == color).ravel()
        inverse_sigma = 1 / np.sqrt(noise[selected])
        weighted = design[selected] * inverse_sigma[:, None]
        operator = np.linalg.pinv(weighted, rcond=1e-10) * inverse_sigma[None]
        coefficient = operator @ raw.ravel()[selected]
        full_cfa[destination] = design[destination] @ coefficient
        variance[destination] = noise[destination]
        for unit, (start, stop) in enumerate(unit_slices):
            keep = np.ones(design.shape[1], bool)
            keep[start:stop] = False
            subset = design[:, keep]
            null_coeff = np.linalg.lstsq(
                subset[selected] * inverse_sigma[:, None],
                raw.ravel()[selected] * inverse_sigma,
                rcond=1e-10,
            )[0]
            nulls[unit, destination] = subset[destination] @ null_coeff
        operators.append(operator)
        coefficients.append(coefficient)
    return LocalCandidate(
        frequencies,
        initial.edge_geometry,
        discovery_mask.copy(),
        design,
        tuple(indices),
        tuple(operators),
        np.stack(coefficients),
        wave_fields,
        wave_slices,
        tuple(unit_fields),
        tuple(unit_slices),
        tuple(unit_keys),
        full_cfa.reshape(raw.shape),
        nulls.reshape(len(unit_slices), *raw.shape),
        variance.reshape(raw.shape),
        excluded,
        phase_bins - 1 if shared_phase_shape or shifts else None,
        shifts,
        bright,
        split_profiles,
        tuple(crosschecks or ()),
        drifts,
        drift_trials,
        parallel,
        flexible,
    )


def _box_sums(field, centers_y, centers_x, window):
    h, w = field.shape
    radius = window // 2
    y0, y1 = np.maximum(0, centers_y - radius), np.minimum(h, centers_y + radius + 1)
    x0, x1 = np.maximum(0, centers_x - radius), np.minimum(w, centers_x + radius + 1)
    integral = np.pad(field.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (
        integral[y1[:, None], x1]
        - integral[y0[:, None], x1]
        - integral[y1[:, None], x0]
        + integral[y0[:, None], x0]
    )


def phase_fit_reliability(candidate, colors):
    """Estimate supported phase-profile energy using the discovery sites only.

    Whitened full/null differences contain fit noise as well as signal.
    Subtract one unit of expected noise energy per added knot coefficient.
    This plug-in shrinkage uses a nominal dimension and an estimated sensor
    variance. It is not a probability or a calibrated noise test.
    """
    reliability = np.zeros((len(candidate.unit_slices), 3), dtype=np.float64)
    for direction, (start, stop) in enumerate(candidate.unit_slices):
        # A one-column shape selected on this fold is not a fixed one-parameter fit.
        degrees = candidate.phase_reliability_degrees or stop - start
        difference = candidate.full_cfa - candidate.conditional_null_cfa[direction]
        discovery = candidate.discovery_mask
        if candidate.phase_side_profiles:
            discovery = discovery & (
                candidate.phase_bright_side == candidate.unit_keys[direction][1]
            )
        for color in range(3):
            selected = discovery & (colors == color)
            energy = np.sum(difference[selected] ** 2 / candidate.variance_cfa[selected])
            if energy > degrees:
                reliability[direction, color] = 1 - degrees / energy
    return reliability


def oriented_validation_footprint(window, frequency, orientation):
    """Sample a two-to-one validation rectangle on the native pixel lattice."""
    normal = np.asarray(frequency, np.float64)
    normal = normal / np.linalg.norm(normal)
    tangent = np.array([-normal[1], normal[0]])
    long_radius, short_radius = window / np.sqrt(2), window / (2 * np.sqrt(2))
    radius = int(np.ceil(np.hypot(long_radius, short_radius)))
    y, x = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    along = x * tangent[0] + y * tangent[1]
    across = x * normal[0] + y * normal[1]
    if orientation == "across":
        along, across = across, along
    return (np.abs(along) <= long_radius) & (np.abs(across) <= short_radius)


def conditional_scores(
    candidate,
    raw,
    colors,
    validation_mask,
    *,
    window=65,
    stride=16,
    reliability=None,
    orientation=None,
    bright_cross_edge_weight=0.0,
):
    """Assess each fixed direction/harmonic and color against its A-only null."""
    raw, colors, mask = np.asarray(raw, np.float64), np.asarray(colors), np.asarray(validation_mask)
    if (
        raw.shape != candidate.full_cfa.shape
        or mask.shape != raw.shape
        or mask.dtype != bool
        or (mask & candidate.discovery_mask).any()
        or not np.isfinite(raw[mask]).all()
    ):
        raise ValueError("Require finite disjoint validation samples")
    h, w = raw.shape
    ay, ax = [np.unique(np.r_[np.arange(0, n, stride), n - 1]) for n in raw.shape]
    units = len(candidate.unit_keys)
    if reliability is not None and (
        reliability.shape != (units, 3)
        or not np.isfinite(reliability).all()
        or np.any((reliability < 0) | (reliability > 1))
    ):
        raise ValueError("Require finite per-direction and color reliability in [0, 1]")
    if orientation not in (None, "along", "across"):
        raise ValueError("Unknown orientation for validation support")
    if orientation is not None:
        from scipy.signal import fftconvolve

    side_map = getattr(candidate, "phase_bright_side", None)
    if (
        not np.isfinite(bright_cross_edge_weight)
        or not 0 <= bright_cross_edge_weight <= 1
        or (bright_cross_edge_weight and getattr(candidate, "phase_side_profiles", False))
    ):
        raise ValueError("Bright cross-edge weight must be in [0, 1] for shared edge profiles")
    local, global_scores = np.zeros((units, 3, h, w)), np.zeros((units, 3))
    for direction in range(units):
        sides = (None,)
        if side_map is not None:
            sides = (
                (candidate.unit_keys[direction][1],) if candidate.phase_side_profiles else (0, 1)
            )
        if orientation is not None:
            family = candidate.unit_keys[direction][0]
            footprint = oriented_validation_footprint(
                window, candidate.frequencies_xy[family], orientation
            )
        for color in range(3):
            selected = mask & (colors == color)
            if side_map is not None and candidate.phase_side_profiles:
                selected &= side_map == sides[0]
            improvement, energy = np.zeros(raw.shape), np.zeros(raw.shape)
            base, full, value, variance = [
                v[selected]
                for v in [
                    candidate.conditional_null_cfa[direction],
                    candidate.full_cfa,
                    raw,
                    candidate.variance_cfa,
                ]
            ]
            if reliability is not None:
                full = base + reliability[direction, color] * (full - base)
            improvement[selected] = ((value - base) ** 2 - (value - full) ** 2) / variance
            energy[selected] = (full - base) ** 2 / variance
            for side in sides:
                side_mask = side_map == side if side is not None else None
                cross = bright_cross_edge_weight if side == 1 else 0.0
                if side_mask is None or cross == 1:
                    signal, power = improvement, energy
                else:
                    signal = np.where(side_mask, improvement, cross * improvement)
                    # The held-out score variance contains the squared sample weights.
                    power = np.where(side_mask, energy, cross**2 * energy)
                if orientation is None:
                    numerator = _box_sums(signal, ay, ax, window)
                    support_energy = _box_sums(power, ay, ax, window)
                else:
                    centers = np.ix_(ay, ax)
                    numerator = fftconvolve(signal, footprint, mode="same")[centers]
                    support_energy = fftconvolve(power, footprint, mode="same")[centers]
                    # Ignore roundoff at centers with no contributing energy.
                    floor = 64 * np.finfo(np.float64).eps * power.sum()
                    support_energy = np.where(support_energy > floor, support_energy, 0)
                denominator = 2 * np.sqrt(np.maximum(support_energy, 0))
                scores = np.divide(
                    numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0
                )
                horizontal = np.stack([np.interp(np.arange(w), ax, row) for row in scores])
                image = np.stack(
                    [np.interp(np.arange(h), ay, horizontal[:, x]) for x in range(w)], axis=1
                )
                if side_mask is None:
                    local[direction, color] = image
                else:
                    local[direction, color, side_mask] = image[side_mask]
            norm = 2 * np.sqrt(energy.sum())
            global_scores[direction, color] = improvement.sum() / norm if norm > 0 else 0
    return local, global_scores


def match_directions(first, second, shape, maximum_native_bins, *, matching="cardinality"):
    if (
        np.asarray(first).shape != (2, 2)
        or np.asarray(second).shape != (2, 2)
        or not np.isfinite([*np.ravel(first), *np.ravel(second), maximum_native_bins]).all()
        or maximum_native_bins <= 0
        or matching not in ("legacy", "cardinality")
    ):
        raise ValueError("Require two finite frequency pairs and a positive matching radius")
    scale = np.asarray(shape[::-1])
    distances = np.empty((2, 2))
    for a in range(2):
        for b in range(2):
            x, y = np.asarray(first[a]), np.asarray(second[b])
            distances[a, b] = min(np.linalg.norm((x - y) * scale), np.linalg.norm((x + y) * scale))

    def cost(order):
        costs = np.array([distances[i, order[i]] for i in range(2)])
        valid = costs <= maximum_native_bins
        if matching == "legacy":
            return (float(costs.sum()),)
        return (-int(valid.sum()), float(costs[valid].sum()), float(costs.sum()))

    order = min(permutations(range(2)), key=cost)
    return [
        (i, order[i], float(distances[i, order[i]]))
        for i in range(2)
        if distances[i, order[i]] <= maximum_native_bins
    ]


def support_weight(score, threshold):
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("Require a finite nonnegative fixed threshold")
    score = np.asarray(score, np.float64)
    if not np.isfinite(score).all():
        raise ValueError("Require finite predictive scores")
    if threshold == 0:
        return (score > 0).astype(np.float64)
    return np.where(score > threshold, 1 - (threshold / np.maximum(score, threshold)) ** 2, 0)


def pooled_support_score(first, second):
    """Average the fold scores only where both predictions reduce held-out error."""
    lower = np.minimum(first, second)
    return np.where(lower > 0, (first + second) / 2, lower)


def donor_subharmonic_scores(raw, colors, frequencies, *, shot, read, config=_DEFAULT_CONFIG):
    """Test whether the donor supports half of each existing guide frequency.

    The nuisance geometry and existing frequencies may use the entire donor.
    Each fold fits its own amplitudes and variance proxy. Only the additional
    half-frequency columns can improve validation over the fixed two-guide null.
    These empirical scores only choose geometry for a disjoint query.
    """
    raw, colors = np.asarray(raw, np.float64), np.asarray(colors)
    if not np.isfinite([shot, read]).all() or min(shot, read) < 0 or shot + read == 0:
        raise ValueError("Require a positive donor noise prior")
    frequencies = np.asarray(_guide_frequencies(frequencies, config.family_degrees))
    fixed = fit_local_candidate(
        raw,
        colors,
        np.ones(raw.shape, dtype=bool),
        shot=shot,
        read=read,
        config=config,
        guide_frequencies_xy=frequencies,
    )
    split = stratified_split(raw.shape, config.split_seed)
    xx, yy, _, _ = geometry(raw.shape)
    baseline = fixed.design
    nuisance = baseline[:, : fixed.unit_slices[0][0]]
    candidates = [
        np.column_stack((baseline, _wave_columns(xx, yy, f / 2)))
        if np.linalg.norm(f) / 2 >= 1 / 64
        else None
        for f in frequencies
    ]
    scores = np.zeros((2, 2), dtype=np.float64)
    for fold, discovery in enumerate((split, ~split)):
        improvements, energies = np.zeros(2), np.zeros(2)
        for color in range(3):
            selected = (colors == color) & discovery
            a, b = selected.ravel(), ((colors == color) & ~discovery).ravel()
            values = raw.ravel()
            offset = np.linalg.lstsq(nuisance[a], values[a], rcond=1e-10)[0]
            inverse_variance = 1 / (read + shot * np.maximum(nuisance @ offset, 1e-6))
            sigma = np.sqrt(inverse_variance[a])
            weighted = values[a] * sigma
            coefficient = np.linalg.lstsq(baseline[a] * sigma[:, None], weighted, rcond=1e-10)[0]
            null = baseline[b] @ coefficient
            for i, design in enumerate(candidates):
                if design is None:
                    continue
                coefficient = np.linalg.lstsq(design[a] * sigma[:, None], weighted, rcond=1e-10)[0]
                change = design[b] @ coefficient - null
                inner = np.sum((values[b] - null) * change * inverse_variance[b])
                energy = np.sum(change**2 * inverse_variance[b])
                improvements[i] += inner - energy / 2
                energies[i] += energy
        scores[fold] = np.divide(
            improvements, np.sqrt(energies), out=np.zeros(2), where=energies > 0
        )
    return scores


def phase_profile_agreement(first, second):
    """Signed cosine between zero-mean linearly interpolated periodic profiles."""
    a = np.concatenate((first, -first.sum(axis=-1, keepdims=True)), axis=-1)
    b = np.concatenate((second, -second.sum(axis=-1, keepdims=True)), axis=-1)
    ma = (a + np.roll(a, -1, axis=-1)) / 2
    mb = (b + np.roll(b, -1, axis=-1)) / 2
    # Composite Simpson weights integrate the piecewise quadratic products exactly.
    cross = np.sum(a * b + 2 * ma * mb, axis=-1)
    norm = np.sqrt(np.sum(a**2 + 2 * ma**2, axis=-1)) * np.sqrt(np.sum(b**2 + 2 * mb**2, axis=-1))
    return np.clip(np.divide(cross, norm, out=np.zeros_like(cross), where=norm > 0), -1, 1)


def _match_units(first, second, matched_directions, maximum_native_bins):
    """Match the same harmonic; apply the radius in its actual frequency bins."""
    lookup = {key: index for index, key in enumerate(second.unit_keys)}
    is_side = getattr(first, "phase_side_profiles", False)
    result = []
    for a, b, distance in matched_directions:
        for index, (direction, harmonic) in enumerate(first.unit_keys):
            other = lookup.get((b, harmonic))
            scaled_distance = distance * (1 if is_side else max(1, harmonic))
            if direction == a and other is not None and scaled_distance <= maximum_native_bins:
                result.append((index, other, scaled_distance))
    return result


def replacement_components(candidate, parent):
    """Project the parent only after all raw-only predictors/scores are fixed."""
    parent = np.asarray(parent, np.float64)
    shape = candidate.full_cfa.shape
    if parent.shape != (3, *shape) or not np.isfinite(parent).all():
        raise ValueError("Require finite matching camera RGB parent")
    result = np.empty((len(candidate.unit_keys), 3, *shape))
    for color in range(3):
        fitted = (
            candidate.operators[color] @ parent[color].ravel()[candidate.selected_indices[color]]
        )
        for direction, (start, stop) in enumerate(candidate.unit_slices):
            delta = candidate.coefficients[color, start:stop] - fitted[start:stop]
            result[direction, color] = candidate.unit_fields[direction] @ delta
    return result


def _refit_phase_components(candidate, raw, colors, parent, pooled_scores):
    """Refit delivered coefficients on all CFA sites after validation is fixed."""
    by_unit = {
        unit: 0.25 + 0.75 * support_weight(score, 1) for unit, score in pooled_scores.items()
    }
    shape = (len(candidate.unit_keys), 3, *raw.shape)
    uniform, focused = np.zeros(shape), np.zeros(shape)
    for color in range(3):
        measured = colors == color
        sigma = np.sqrt(candidate.variance_cfa[measured])
        design = candidate.design[measured.ravel()] / sigma[:, None]
        residual = (raw[measured] - parent[color, measured]) / sigma
        full = np.linalg.lstsq(design, residual, rcond=1e-10)[0]
        for unit, weights in by_unit.items():
            start, stop = candidate.unit_slices[unit]
            basis = candidate.unit_fields[unit]
            uniform[unit, color] = basis @ full[start:stop]
            spatial = np.sqrt(weights[color, measured])
            coef = np.linalg.lstsq(design * spatial[:, None], residual * spatial, rcond=1e-10)[0]
            focused[unit, color] = basis @ coef[start:stop]
    return uniform, focused


def restore_local_waves(
    parent,
    packed,
    colors,
    *,
    shot,
    read,
    thresholds=(2.0,),
    config=_DEFAULT_CONFIG,
    discovery_mask=None,
    evidence_mask=None,
    conditional_delivery=False,
    guide_frequencies_xy=None,
    phase_bins=0,
    phase_harmonics=None,
    shrink_phase_fit=False,
    compare_pooled_support=False,
    compare_phase_agreement=False,
    compare_oriented_support=False,
    compare_joint_colour_support=False,
    compare_pooled_refit=False,
    compare_matched_refit=False,
    compare_phase_averages=False,
    recenter_phase_guides=False,
    phase_guide_edge_guard_px=0,
    phase_guide_crosscheck=False,
    phase_drift_search=False,
    guide_phase_hessians_xy=None,
    shared_phase_shape=False,
    donor_phase_templates=None,
    phase_edge_side=None,
    bright_cross_edge_weight=0.0,
    active_guide_directions=None,
):
    """Return paired global/local support variants with one input-only discovery pass."""
    parent, packed, colors = np.asarray(parent), np.asarray(packed), np.asarray(colors)
    if (
        parent.ndim != 3
        or parent.shape[0] != 3
        or parent.dtype not in (np.float32, np.float64)
        or packed.shape != (4, parent.shape[1] // 2, parent.shape[2] // 2)
        or colors.shape != (4,)
        or not np.isfinite(parent).all()
        or not np.isfinite(packed).all()
    ):
        raise ValueError("Require matching finite native RGB, packed RAW and four CFA colors")
    h, w = parent.shape[1:]
    allowed = np.array([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    if (
        h % 2
        or w % 2
        or min(h, w) < config.window
        or not (allowed == colors).all(1).any()
        or not np.isfinite([shot, read]).all()
        or min(shot, read) < 0
    ):
        raise ValueError("Invalid native axes/CFA/noise priors")
    if not thresholds or len(set(thresholds)) != len(thresholds):
        raise ValueError("Require a nonempty distinct set of fixed thresholds")
    if type(conditional_delivery) is not bool:
        raise ValueError("Require an explicit boolean conditional-delivery choice")
    _validate_phase_bins(phase_bins, guide_frequencies_xy, config, phase_harmonics)
    if active_guide_directions is not None and (
        guide_frequencies_xy is None
        or len(active_guide_directions) != 2
        or any(type(value) is not bool for value in active_guide_directions)
        or recenter_phase_guides
        or phase_drift_search
    ):
        raise ValueError("Delivery direction selection requires two fixed guide flags")
    _validate_guide_search(
        recenter_phase_guides,
        phase_guide_edge_guard_px,
        phase_bins,
        phase_harmonics,
        phase_guide_crosscheck,
    )
    _validate_shared_phase_shape(shared_phase_shape, phase_bins, phase_harmonics)
    templates = _donor_templates(
        donor_phase_templates, phase_bins, phase_harmonics, shared_phase_shape
    )
    _validate_phase_drift(phase_drift_search, phase_bins, phase_harmonics, templates)
    _phase_side_option(phase_edge_side, phase_bins, phase_harmonics, shared_phase_shape, templates)
    if (
        not np.isfinite(bright_cross_edge_weight)
        or not 0 <= bright_cross_edge_weight <= 1
        or (bright_cross_edge_weight and phase_edge_side != "validation")
    ):
        raise ValueError(
            "Bright cross-edge weight requires same-side validation and a value in [0, 1]"
        )
    if phase_edge_side is not None and (compare_joint_colour_support or compare_phase_agreement):
        raise ValueError("Edge-side support uses per-color fold evidence")
    if type(shrink_phase_fit) is not bool or (shrink_phase_fit and not phase_bins):
        raise ValueError("Require phase bins for discovery-only phase-fit shrinkage")
    if type(compare_pooled_support) is not bool:
        raise ValueError("Require an explicit boolean pooled-support choice")
    if type(compare_phase_agreement) is not bool or (
        compare_phase_agreement
        and (
            not phase_bins
            or phase_harmonics is not None
            or recenter_phase_guides
            or phase_drift_search
            or shared_phase_shape
            or templates is not None
            or not compare_pooled_support
        )
    ):
        raise ValueError("Phase agreement requires fixed phase bins and pooled support")
    if type(compare_oriented_support) is not bool or (
        compare_oriented_support and not compare_pooled_support
    ):
        raise ValueError("Oriented support requires pooled support")
    if type(compare_joint_colour_support) is not bool or (
        compare_joint_colour_support and not compare_pooled_support
    ):
        raise ValueError("Joint color support requires pooled support")
    if type(compare_pooled_refit) is not bool or (
        compare_pooled_refit
        and (not shrink_phase_fit or not compare_pooled_support or conditional_delivery)
    ):
        raise ValueError("Refit requires shrunken phase profiles and pooled RAW-wave support")
    if type(compare_matched_refit) is not bool or (
        compare_matched_refit
        and (
            not compare_pooled_refit
            or config.amplitude_window
            or bright_cross_edge_weight
            or phase_edge_side == "profiles"
        )
    ):
        raise ValueError("Matched refit requires shared profiles and default spatial weights")
    if type(compare_phase_averages) is not bool or (
        compare_phase_averages
        and (
            not compare_pooled_refit
            or config.amplitude_window
            or config.support_unit != "direction"
            or bright_cross_edge_weight
            or phase_edge_side == "profiles"
            or guide_frequencies_xy is None
            or guide_phase_hessians_xy is not None
            or recenter_phase_guides
            or phase_drift_search
        )
    ):
        raise ValueError("Phase averages require fixed planar guides and shared direction profiles")
    if guide_frequencies_xy is not None:
        guide_frequencies_xy = _guide_frequencies(guide_frequencies_xy, config.family_degrees)
    hessians = _validate_phase_hessians(
        guide_phase_hessians_xy,
        (h, w),
        guide_frequencies_xy,
        phase_bins,
        phase_harmonics,
        phase_drift_search or recenter_phase_guides,
        templates,
    )
    guide = {} if guide_frequencies_xy is None else {"guide_frequencies_xy": guide_frequencies_xy}
    if phase_bins:
        guide["phase_bins"] = phase_bins
    if phase_harmonics is not None:
        guide["phase_harmonics"] = phase_harmonics
    if recenter_phase_guides:
        guide["recenter_phase_guides"] = True
    if phase_guide_edge_guard_px:
        guide["phase_guide_edge_guard_px"] = phase_guide_edge_guard_px
    if phase_guide_crosscheck:
        guide["phase_guide_crosscheck"] = True
    if phase_drift_search:
        guide["phase_drift_search"] = True
    if hessians is not None:
        guide["guide_phase_hessians_xy"] = hessians
    if shared_phase_shape:
        guide["shared_phase_shape"] = True
    if templates is not None:
        guide["donor_phase_templates"] = templates
    if phase_edge_side is not None:
        guide["phase_edge_side"] = phase_edge_side
    if discovery_mask is not None:
        discovery_mask = np.asarray(discovery_mask)
        if discovery_mask.shape != (h, w) or discovery_mask.dtype != bool:
            raise ValueError("Require a native boolean global discovery mask")
    if evidence_mask is not None:
        evidence_mask = np.asarray(evidence_mask)
        if evidence_mask.shape != (h, w) or evidence_mask.dtype != bool:
            raise ValueError("Require a native boolean mask for fit and validation samples")
    for threshold in thresholds:
        support_weight(0, threshold)
    modes = ("global", "local", "pooled-local") if compare_pooled_support else ("global", "local")
    if compare_phase_agreement:
        modes += ("phase-agreement",)
    orientations = ("along", "across") if compare_oriented_support else ()
    modes += orientations
    if compare_joint_colour_support:
        from .joint_colour_evidence import joint_conditional_scores

        modes += ("joint", "joint-veto")
    refit_modes = ("all-site-refit", "weighted-refit") if compare_pooled_refit else ()
    modes += refit_modes
    matched_modes = ("matched-refit", "orthogonal-refit") if compare_matched_refit else ()
    modes += matched_modes
    if compare_matched_refit:
        from .matched_query_evidence import matched_query_scores
    average_modes = (
        ("square-average", "tangent-average", "tangent-predictive-gate")
        if compare_phase_averages
        else ()
    )
    modes += average_modes
    if compare_phase_averages:
        from .surface_phase_aggregation import SurfacePhaseProposal
    outputs = {(mode, float(t)): parent.copy() for mode in modes for t in thresholds}
    if shot + read == 0:
        return outputs, {"patches": 0, "identity_zero_noise": True}
    raw = np.empty((h, w), np.float64)
    for phase in range(4):
        raw[phase // 2 :: 2, phase % 2 :: 2] = packed[phase]
    cfa = np.tile(colors.reshape(2, 2), (h // 2, w // 2))
    totals = {key: np.zeros(parent.shape, np.float64) for key in outputs}
    denominator = np.zeros((h, w))
    n = config.window
    taper = np.sin(np.pi * (np.arange(n) + 0.5) / n) ** 2
    blend = taper[:, None] * taper[None]
    positions = [
        np.unique(np.r_[np.arange(0, length - n + 1, config.stride), length - n])
        for length in [h, w]
    ]
    records = []
    for y in positions[0]:
        for x in positions[1]:
            region = np.s_[y : y + n, x : x + n]
            tile, layout = raw[region], cfa[region]
            split = (
                stratified_split(tile.shape, config.split_seed + int(y) * w + int(x))
                if discovery_mask is None
                else discovery_mask[region]
            )
            folds = (split, ~split)
            if evidence_mask is not None:
                folds = tuple(mask & evidence_mask[region] for mask in folds)
            validation = folds[::-1]
            patch_guide = guide
            if hessians is not None:
                center_delta = np.array([x + (n - w) / 2, y + (n - h) / 2])
                local_frequencies = (
                    np.asarray(guide_frequencies_xy) + np.asarray(hessians) @ center_delta
                )
                patch_guide = {
                    **guide,
                    "guide_frequencies_xy": tuple(map(tuple, local_frequencies)),
                }
            candidates = [
                fit_local_candidate(
                    tile, layout, mask, shot=shot, read=read, config=config, **patch_guide
                )
                for mask in folds
            ]
            active_sides = [c.phase_bright_side is not None for c in candidates]
            if phase_edge_side is not None and active_sides[0] != active_sides[1]:
                plain = {k: v for k, v in patch_guide.items() if k != "phase_edge_side"}
                candidates = [
                    fit_local_candidate(
                        tile, layout, mask, shot=shot, read=read, config=config, **plain
                    )
                    for mask in folds
                ]
            spatial = None
            if config.amplitude_window:
                from .spatial_carrier_amplitudes import SpatialCarrierOperator

                spatial = [
                    SpatialCarrierOperator(
                        c,
                        layout,
                        window=config.amplitude_window,
                        stride=config.amplitude_stride,
                        nuisance_mode=config.amplitude_nuisance,
                    )
                    for c in candidates
                ]
            predictors = candidates if spatial is None else [s.predict(tile) for s in spatial]
            reliability = (
                [phase_fit_reliability(c, layout) for c in candidates]
                if shrink_phase_fit
                else [None, None]
            )
            scores = [
                conditional_scores(
                    c,
                    tile,
                    layout,
                    test,
                    window=config.validation_window,
                    stride=config.validation_stride,
                    bright_cross_edge_weight=bright_cross_edge_weight,
                    **({"reliability": weight} if weight is not None else {}),
                )
                for c, test, weight in zip(predictors, validation, reliability, strict=True)
            ]
            oriented_scores = {
                mode: [
                    conditional_scores(
                        c,
                        tile,
                        layout,
                        test,
                        window=config.validation_window,
                        stride=config.validation_stride,
                        reliability=weight,
                        orientation=mode,
                        bright_cross_edge_weight=bright_cross_edge_weight,
                    )[0]
                    for c, test, weight in zip(predictors, validation, reliability, strict=True)
                ]
                for mode in orientations
            }
            if compare_joint_colour_support:
                joint_scores = [
                    joint_conditional_scores(
                        c,
                        tile,
                        layout,
                        test,
                        window=config.validation_window,
                        stride=config.validation_stride,
                        reliability=weight,
                    )[0]
                    for c, test, weight in zip(predictors, validation, reliability, strict=True)
                ]
            matched = match_directions(
                candidates[0].frequencies_xy,
                candidates[1].frequencies_xy,
                tile.shape,
                config.match_native_bins,
                matching=config.matching,
            )
            if active_guide_directions is not None:
                matched = [
                    (a, b, distance)
                    for a, b, distance in matched
                    if a == b and active_guide_directions[a]
                ]
            if phase_drift_search:
                yy, xx = np.indices(tile.shape)
                matched = [
                    (a, b, distance)
                    for a, b, distance in matched
                    if _compatible_drifts(candidates, a, b, xx, yy)
                ]
            units = _match_units(*candidates, matched, config.match_native_bins)
            if compare_phase_averages and units:
                proposals = {
                    (fold, index, tangent): SurfacePhaseProposal(
                        candidates[fold],
                        tile,
                        layout,
                        validation[fold],
                        reliability[fold],
                        index,
                        config,
                        tangent=tangent,
                    )
                    for pair in units
                    for fold, index in enumerate(pair[:2])
                    for tangent in (False, True)
                }
            rgb = parent[:, y : y + n, x : x + n]
            if compare_phase_averages and units:
                yy, xx = np.indices(tile.shape)
                parent_cfa = rgb[layout, yy, xx]
            if spatial is None:
                if conditional_delivery:
                    from .neural_nuisance import conditional_components

                    components = [
                        conditional_components(c, rgb, tile, layout)[0] for c in candidates
                    ]
                else:
                    components = [replacement_components(c, rgb) for c in candidates]
            else:
                values = [s.components(tile, rgb) for s in spatial]
                components = [value[0][0] if conditional_delivery else value[1] for value in values]
            pooled_scores = (
                [pooled_support_score(scores[0][0][a], scores[1][0][b]) for a, b, _ in units]
                if compare_pooled_support
                else [None] * len(units)
            )
            if compare_pooled_refit:
                refitted = [
                    _refit_phase_components(
                        c,
                        tile,
                        layout,
                        rgb,
                        {pair[fold]: p for pair, p in zip(units, pooled_scores, strict=True)},
                    )
                    for fold, c in enumerate(candidates)
                ]
                paired_refits = tuple(zip(refitted[0], refitted[1], strict=True))
            if compare_matched_refit:
                contrasts = [
                    matched_query_scores(
                        c,
                        tile,
                        layout,
                        test,
                        weight,
                        window=config.validation_window,
                        stride=config.validation_stride,
                    )
                    for c, test, weight in zip(candidates, validation, reliability, strict=True)
                ]
                alternative = []
                for mode in range(len(matched_modes)):
                    scores_by_pair = [
                        pooled_support_score(contrasts[0][mode, a], contrasts[1][mode, b])
                        for a, b, _ in units
                    ]
                    refits = [
                        _refit_phase_components(
                            c,
                            tile,
                            layout,
                            rgb,
                            {pair[fold]: p for pair, p in zip(units, scores_by_pair, strict=True)},
                        )[1]
                        for fold, c in enumerate(candidates)
                    ]
                    alternative.append((scores_by_pair, refits))
            local_max, global_max = [], []
            agreements = []
            for pair_index, ((a, b, _distance), pooled) in enumerate(
                zip(units, pooled_scores, strict=True)
            ):
                if shrink_phase_fit:
                    component = (
                        reliability[0][a, :, None, None] * components[0][a]
                        + reliability[1][b, :, None, None] * components[1][b]
                    ) / 2
                else:
                    component = (components[0][a] + components[1][b]) / 2
                first, second = scores[0][0][a], scores[1][0][b]
                local = np.minimum(first, second)
                global_score = np.minimum(scores[0][1][a], scores[1][1][b])
                refit_components = (
                    [
                        (
                            reliability[0][a, :, None, None] * left[a]
                            + reliability[1][b, :, None, None] * right[b]
                        )
                        / 2
                        for left, right in paired_refits
                    ]
                    if compare_pooled_refit
                    else ()
                )
                matched_delivery = (
                    [
                        (
                            fit[0][a] * reliability[0][a, :, None, None] / 2
                            + fit[1][b] * reliability[1][b, :, None, None] / 2,
                            contrast[pair_index],
                        )
                        for contrast, fit in alternative
                    ]
                    if compare_matched_refit
                    else ()
                )
                if compare_joint_colour_support:
                    joint = pooled_support_score(joint_scores[0][a], joint_scores[1][b])
                    color_veto = local > 0
                oriented_pooled = [
                    (mode, pooled_support_score(folds[0][a], folds[1][b]))
                    for mode, folds in oriented_scores.items()
                ]
                if compare_phase_averages:
                    measured = []
                    for tangent in (False, True):
                        left, right = proposals[0, a, tangent], proposals[1, b, tangent]
                        pooled_raw = pooled_support_score(left.scores, right.scores)
                        estimate = (
                            reliability[0][a, :, None, None] * left.correction(parent_cfa, layout)
                            + reliability[1][b, :, None, None]
                            * right.correction(parent_cfa, layout)
                        ) / 2
                        measured.append((estimate, pooled_raw))
                    measured.append((measured[-1][0], pooled))
                if compare_phase_agreement:
                    slices = [slice(*c.unit_slices[index]) for c, index in zip(candidates, (a, b))]
                    agreement = phase_profile_agreement(
                        candidates[0].coefficients[:, slices[0]],
                        candidates[1].coefficients[:, slices[1]],
                    )
                    agreements.append(agreement.tolist())
                    agreement_weight = np.maximum(agreement, 0)[:, None, None]
                for threshold in thresholds:
                    totals["local", float(threshold)][:, y : y + n, x : x + n] += (
                        component * support_weight(local, threshold) * blend
                    )
                    totals["global", float(threshold)][:, y : y + n, x : x + n] += (
                        component * support_weight(global_score, threshold)[:, None, None] * blend
                    )
                    if compare_pooled_support:
                        weight = support_weight(pooled, threshold)
                        pooled_delivery = component * weight * blend
                        totals["pooled-local", float(threshold)][:, y : y + n, x : x + n] += (
                            pooled_delivery
                        )
                        if compare_phase_agreement:
                            totals["phase-agreement", float(threshold)][
                                :, y : y + n, x : x + n
                            ] += pooled_delivery * agreement_weight
                        for mode, fitted in zip(refit_modes, refit_components, strict=True):
                            totals[mode, float(threshold)][:, y : y + n, x : x + n] += (
                                fitted * weight * blend
                            )
                        for mode, (fitted, contrast) in zip(
                            matched_modes, matched_delivery, strict=True
                        ):
                            totals[mode, float(threshold)][:, y : y + n, x : x + n] += (
                                fitted * support_weight(contrast, threshold) * blend
                            )
                    if compare_phase_averages:
                        for mode, (measured_component, local_score) in zip(
                            average_modes, measured, strict=True
                        ):
                            totals[mode, float(threshold)][:, y : y + n, x : x + n] += (
                                measured_component * support_weight(local_score, threshold) * blend
                            )
                    for mode, score in oriented_pooled:
                        totals[mode, float(threshold)][:, y : y + n, x : x + n] += (
                            component * support_weight(score, threshold) * blend
                        )
                    if compare_joint_colour_support:
                        shared = component * support_weight(joint, threshold) * blend
                        totals["joint", float(threshold)][:, y : y + n, x : x + n] += shared
                        totals["joint-veto", float(threshold)][:, y : y + n, x : x + n] += (
                            shared * color_veto
                        )
                local_max.append(float(np.max(local)))
                global_max.append(global_score.tolist())
            denominator[region] += blend
            records.append(
                {
                    "xy": [int(x), int(y)],
                    "frequencies": [c.frequencies_xy for c in candidates],
                    "edges": [c.edge_geometry for c in candidates],
                    **(
                        {"parallel_edges": [c.parallel_edges for c in candidates]}
                        if config.background in ("parallel_step", "curved_step", "curved4_step")
                        else {}
                    ),
                    **(
                        {"flexible_edges": [c.flexible_edges for c in candidates]}
                        if config.background in ("curved_step", "curved4_step")
                        else {}
                    ),
                    **(
                        {"phase_bins": phase_bins}
                        if phase_bins
                        else {
                            "harmonics": [
                                [(stop - start) // 2 for start, stop in c.wave_slices]
                                for c in candidates
                            ]
                        }
                    ),
                    "matched": matched,
                    "unit_keys": [c.unit_keys for c in candidates],
                    "matched_units": units,
                    "local_max": local_max,
                    "global_scores": global_max,
                    **(
                        {"guide_search_excluded": [c.guide_search_excluded for c in candidates]}
                        if phase_guide_edge_guard_px
                        else {}
                    ),
                    **(
                        {"guide_crosschecks": [c.guide_crosschecks for c in candidates]}
                        if phase_guide_crosscheck
                        else {}
                    ),
                    **(
                        {
                            "phase_drifts": [c.phase_drifts for c in candidates],
                            "phase_drift_trials": [c.phase_drift_trials for c in candidates],
                        }
                        if phase_drift_search
                        else {}
                    ),
                    **(
                        {"donor_phase_shifts": [c.donor_phase_shifts for c in candidates]}
                        if templates is not None
                        else {}
                    ),
                    **(
                        {
                            "phase_edge_side_detected": active_sides,
                            "phase_edge_side_applied": all(active_sides),
                        }
                        if phase_edge_side is not None
                        else {}
                    ),
                    **({"phase_agreement": agreements} if compare_phase_agreement else {}),
                    **(
                        {"discovery_reliability": [weight.tolist() for weight in reliability]}
                        if shrink_phase_fit
                        else {}
                    ),
                }
            )
    for key in outputs:
        outputs[key] = (parent.astype(np.float64) + totals[key] / denominator).astype(parent.dtype)
    return outputs, {
        "patches": len(records),
        "identity_zero_noise": False,
        "records": records,
        "config": config.to_dict(),
        "parent_used_for_discovery_or_validation": False,
        **(
            {"active_guide_directions": list(active_guide_directions)}
            if active_guide_directions is not None
            else {}
        ),
        **guide,
        **(
            {"bright_cross_edge_weight": float(bright_cross_edge_weight)}
            if bright_cross_edge_weight
            else {}
        ),
        **({"shrink_phase_fit": True} if shrink_phase_fit else {}),
        **({"compare_pooled_support": True} if compare_pooled_support else {}),
        **({"compare_matched_refit": True} if compare_matched_refit else {}),
        **({"compare_phase_averages": True} if compare_phase_averages else {}),
        **({"compare_phase_agreement": True} if compare_phase_agreement else {}),
        **({"compare_oriented_support": True} if compare_oriented_support else {}),
        **({"compare_joint_colour_support": True} if compare_joint_colour_support else {}),
        **(
            {"compare_pooled_refit": True, "refit_weight_floor": 0.25, "refit_weight_threshold": 1}
            if compare_pooled_refit
            else {}
        ),
        "delivery": "conditional-full-minus-null" if conditional_delivery else "raw-wave",
        "scope": "Raw-only A/B conditional predictive scores and per-color/local support, with parent projection after scoring. Empirical plug-in scores, not calibrated confidence; parent has seen all RAW and the final corrected output is not an independent prediction.",
    }


def restore_conditional_waves(
    parent,
    packed,
    colors,
    *,
    shot,
    read,
    thresholds=(2.0,),
    config=_DEFAULT_CONFIG,
    discovery_mask=None,
    guide_frequencies_xy=None,
):
    """Standalone analytic conditional delivery; no neural nuisance fields needed."""
    return restore_local_waves(
        parent,
        packed,
        colors,
        shot=shot,
        read=read,
        thresholds=thresholds,
        config=config,
        discovery_mask=discovery_mask,
        conditional_delivery=True,
        guide_frequencies_xy=guide_frequencies_xy,
    )
