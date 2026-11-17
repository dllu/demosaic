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
            or self.background not in ("step", "piecewise_affine")
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


def _wave_columns(xx, yy, frequency, harmonics=1):
    fx, fy = frequency
    phase = 2 * np.pi * (xx * fx + yy * fy)
    return np.column_stack(
        [
            column.ravel()
            for h in range(1, harmonics + 1)
            for column in (np.cos(h * phase), np.sin(h * phase))
        ]
    )


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


def fit_local_candidate(raw, colors, discovery_mask, *, shot, read, config=_DEFAULT_CONFIG):
    """A-only edge/frequency/amplitude/noise fitting with two competing directions."""
    raw, colors, discovery_mask = (
        np.asarray(raw, np.float64),
        np.asarray(colors),
        np.asarray(discovery_mask),
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
    if config.background == "piecewise_affine":
        step = nuisance[:, 3]
        nuisance = np.column_stack((nuisance, x.ravel() * step, y.ravel() * step))
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
    waves = [_wave_columns(xx, yy, f, count) for f, count in zip(frequencies, counts, strict=True)]
    n = nuisance.shape[1]
    wave_slices = ((n, n + 2 * first_harmonics), (n + 2 * first_harmonics, n + 2 * sum(counts)))
    wave_fields = tuple(
        wave.reshape(*raw.shape, 2 * count) for wave, count in zip(waves, counts, strict=True)
    )
    if config.support_unit == "direction":
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
    operators, indices, coefficients = [], [], []
    for color in range(3):
        selected = np.flatnonzero(((colors == color) & discovery_mask).ravel())
        destination = (colors == color).ravel()
        background_coeff = np.linalg.lstsq(nuisance[selected], raw.ravel()[selected], rcond=1e-10)[
            0
        ]
        proxy = nuisance @ background_coeff
        noise = read + shot * np.maximum(proxy, 1e-6)
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
        indices.append(selected)
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


def conditional_scores(candidate, raw, colors, validation_mask, *, window=65, stride=16):
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
    local, global_scores = np.zeros((units, 3, h, w)), np.zeros((units, 3))
    for direction in range(units):
        for color in range(3):
            selected = mask & (colors == color)
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
            improvement[selected] = ((value - base) ** 2 - (value - full) ** 2) / variance
            energy[selected] = (full - base) ** 2 / variance
            numerator = _box_sums(improvement, ay, ax, window)
            denominator = 2 * np.sqrt(np.maximum(_box_sums(energy, ay, ax, window), 0))
            scores = np.divide(
                numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0
            )
            horizontal = np.stack([np.interp(np.arange(w), ax, row) for row in scores])
            local[direction, color] = np.stack(
                [np.interp(np.arange(h), ay, horizontal[:, x]) for x in range(w)], axis=1
            )
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


def _match_units(first, second, matched_directions, maximum_native_bins):
    """Match the same harmonic; apply the radius in its actual frequency bins."""
    lookup = {key: index for index, key in enumerate(second.unit_keys)}
    result = []
    for a, b, distance in matched_directions:
        for index, (direction, harmonic) in enumerate(first.unit_keys):
            other = lookup.get((b, harmonic))
            scaled_distance = distance * max(1, harmonic)
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
    conditional_delivery=False,
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
    if discovery_mask is not None:
        discovery_mask = np.asarray(discovery_mask)
        if discovery_mask.shape != (h, w) or discovery_mask.dtype != bool:
            raise ValueError("Require a native boolean global discovery mask")
    for threshold in thresholds:
        support_weight(0, threshold)
    outputs = {(mode, float(t)): parent.copy() for mode in ["global", "local"] for t in thresholds}
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
            candidates = [
                fit_local_candidate(tile, layout, mask, shot=shot, read=read, config=config)
                for mask in [split, ~split]
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
            scores = [
                conditional_scores(
                    c,
                    tile,
                    layout,
                    ~c.discovery_mask,
                    window=config.validation_window,
                    stride=config.validation_stride,
                )
                for c in predictors
            ]
            matched = match_directions(
                candidates[0].frequencies_xy,
                candidates[1].frequencies_xy,
                tile.shape,
                config.match_native_bins,
                matching=config.matching,
            )
            rgb = parent[:, y : y + n, x : x + n]
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
            units = _match_units(*candidates, matched, config.match_native_bins)
            local_max, global_max = [], []
            for a, b, _distance in units:
                component = (components[0][a] + components[1][b]) / 2
                local = np.minimum(scores[0][0][a], scores[1][0][b])
                global_score = np.minimum(scores[0][1][a], scores[1][1][b])
                for threshold in thresholds:
                    totals["local", float(threshold)][:, y : y + n, x : x + n] += (
                        component * support_weight(local, threshold) * blend
                    )
                    totals["global", float(threshold)][:, y : y + n, x : x + n] += (
                        component * support_weight(global_score, threshold)[:, None, None] * blend
                    )
                local_max.append(float(np.max(local)))
                global_max.append(global_score.tolist())
            denominator[region] += blend
            records.append(
                {
                    "xy": [int(x), int(y)],
                    "frequencies": [c.frequencies_xy for c in candidates],
                    "edges": [c.edge_geometry for c in candidates],
                    "harmonics": [
                        [(stop - start) // 2 for start, stop in c.wave_slices] for c in candidates
                    ],
                    "matched": matched,
                    "unit_keys": [c.unit_keys for c in candidates],
                    "matched_units": units,
                    "local_max": local_max,
                    "global_scores": global_max,
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
    )
