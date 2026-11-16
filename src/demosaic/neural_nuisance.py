"""Independent neural nuisance fields for held-out RAW-wave reconstruction.

The supplied fields must be predictions from only their declared discovery
samples. The experiment producer verifies actual masked neural arguments; a
mask label alone cannot establish independence of an externally supplied field.
Final RGB retains the full-input parent, with wave replacement after scoring.
"""

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter

from .experiments.evaluation.withheld import geometry
from .local_validated_waves import (
    LocalCandidate,
    LocalWaveConfig,
    _refine_frequency,
    _residual_peak,
    _wave_columns,
    conditional_scores,
    fit_local_candidate,
    match_directions,
    replacement_components,
    support_weight,
)

_DEFAULT = LocalWaveConfig()


@dataclass(frozen=True)
class WithheldBackground:
    rgb: np.ndarray
    discovery_mask: np.ndarray

    def __post_init__(self):
        rgb, mask = np.asarray(self.rgb), np.asarray(self.discovery_mask)
        if (
            rgb.ndim != 3
            or rgb.shape[0] != 3
            or rgb.dtype not in (np.float32, np.float64)
            or mask.shape != rgb.shape[1:]
            or mask.dtype != bool
            or not np.isfinite(rgb).all()
        ):
            raise ValueError("Require a finite native RGB field with its boolean discovery mask")
        rgb, mask = rgb.copy(), mask.copy()
        rgb.setflags(write=False)
        mask.setflags(write=False)
        object.__setattr__(self, "rgb", rgb)
        object.__setattr__(self, "discovery_mask", mask)


def masked_packed_input(raw, discovery_mask):
    """Same-phase A-only imputation; retain measured A and ordinary signed read noise."""
    raw, mask = np.asarray(raw), np.asarray(discovery_mask)
    if (
        raw.ndim != 2
        or min(raw.shape) < 4
        or any(n % 2 for n in raw.shape)
        or raw.dtype not in (np.float32, np.float64)
        or mask.shape != raw.shape
        or mask.dtype != bool
        or not np.isfinite(raw[mask]).all()
    ):
        raise ValueError("Require finite discovery values on an even native grid")
    result = []
    for y in range(2):
        for x in range(2):
            value, observed = raw[y::2, x::2], mask[y::2, x::2]
            if not observed.any() or observed.all():
                raise ValueError("Every CFA phase requires discovery and validation samples")
            numerator = gaussian_filter(
                np.where(observed, value, 0).astype(np.float64),
                1.0,
                mode="constant",
                cval=0.0,
                truncate=3.0,
            )
            denominator = gaussian_filter(
                observed.astype(np.float64),
                1.0,
                mode="constant",
                cval=0.0,
                truncate=3.0,
            )
            filled = np.divide(
                numerator,
                denominator,
                out=np.full(value.shape, float(value[observed].mean())),
                where=denominator > 0,
            )
            result.append(np.where(observed, value, filled).astype(raw.dtype))
    return np.stack(result)


def fit_neural_candidate(raw, colors, reference, background, *, config=_DEFAULT):
    """Add one own-color neural nuisance coordinate; retain A-only edge/noise proxy.

    The CFA-interleaved feature is used only on each color's actual sensor
    sites. It is not an RGB nuisance image at unmeasured color locations.
    Frequencies are reselected/refined after adding this competing nuisance.
    """
    raw, colors = np.asarray(raw, np.float64), np.asarray(colors)
    if (
        raw.shape != reference.full_cfa.shape
        or colors.shape != raw.shape
        or background.rgb.shape != (3, *raw.shape)
        or not np.array_equal(background.discovery_mask, reference.discovery_mask)
        or not np.isfinite(raw[reference.discovery_mask]).all()
        or not np.isin(colors, (0, 1, 2)).all()
        or config.harmonics != 1
        or config.support_unit != "direction"
    ):
        raise ValueError("Require matching A-only background/mask, native CFA and H1 geometry")
    xx, yy, _, _ = geometry(raw.shape)
    feature = np.minimum(background.rgb[colors, yy, xx].astype(np.float64), 1.0)
    base_columns = reference.wave_slices[0][0]
    nuisance = np.column_stack((reference.design[:, :base_columns], feature.ravel()))
    mask = reference.discovery_mask
    green = ((colors == 1) & mask).ravel()
    first = _refine_frequency(
        raw,
        green,
        nuisance,
        xx,
        yy,
        _residual_peak(raw, green, nuisance),
        config.frequency_refinements,
        harmonics=1,
    )
    one = np.column_stack((nuisance, _wave_columns(xx, yy, first)))
    second = _refine_frequency(
        raw,
        green,
        one,
        xx,
        yy,
        _residual_peak(raw, green, one, avoid=first, family_degrees=config.family_degrees),
        config.frequency_refinements,
        avoid=first,
        family_degrees=config.family_degrees,
        harmonics=1,
    )
    waves = [_wave_columns(xx, yy, f) for f in (first, second)]
    n = nuisance.shape[1]
    slices = ((n, n + 2), (n + 2, n + 4))
    design = np.column_stack((nuisance, *waves))
    full, nulls = np.empty(raw.size), np.empty((2, raw.size))
    operators, coefficients = [], []
    for color in range(3):
        selected = reference.selected_indices[color]
        destination = (colors == color).ravel()
        inverse_sigma = 1 / np.sqrt(reference.variance_cfa.ravel()[selected])
        weighted = design[selected] * inverse_sigma[:, None]
        operator = np.linalg.pinv(weighted, rcond=1e-10) * inverse_sigma[None]
        coefficient = operator @ raw.ravel()[selected]
        full[destination] = design[destination] @ coefficient
        for direction, (start, stop) in enumerate(slices):
            keep = np.ones(design.shape[1], bool)
            keep[start:stop] = False
            subset = design[:, keep]
            null_coefficient = np.linalg.lstsq(
                subset[selected] * inverse_sigma[:, None],
                raw.ravel()[selected] * inverse_sigma,
                rcond=1e-10,
            )[0]
            nulls[direction, destination] = subset[destination] @ null_coefficient
        operators.append(operator)
        coefficients.append(coefficient)
    fields = tuple(w.reshape(*raw.shape, 2) for w in waves)
    return LocalCandidate(
        (first, second),
        reference.edge_geometry,
        mask.copy(),
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


def conditional_components(candidate, parent, raw, colors, background=None):
    """Replace the nuisance-residualized wave increment that validation actually tests.

    A neural nuisance can be strongly correlated with a wave. Delivering its
    unresidualized sinusoid would amplify an arbitrarily assigned coefficient.
    Each color instead uses W-X_null*beta, including its own neural RGB field
    at unmeasured locations. No parent value enters the residualization fit.
    """
    shape = candidate.full_cfa.shape
    parent, raw, colors = (
        np.asarray(parent, np.float64),
        np.asarray(raw, np.float64),
        np.asarray(colors),
    )
    if parent.shape != (3, *shape) or colors.shape != shape or raw.shape != shape:
        raise ValueError("Require the matching native RGB/CFA grid")
    result = np.empty((2, 3, *shape))
    fractions = np.empty((2, 3))
    spectra = np.empty((2, 3, 2))
    neural_column = candidate.wave_slices[0][0] - 1 if background is not None else None
    for color in range(3):
        selected = candidate.selected_indices[color]
        precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
        fitted_parent = candidate.operators[color] @ parent[color].ravel()[selected]
        full_delta = candidate.coefficients[color] - fitted_parent
        native_design = candidate.design
        if background is not None:
            native_design = native_design.copy()
            native_design[:, neural_column] = np.minimum(background.rgb[color].ravel(), 1.0)
        full_component = native_design @ full_delta
        for direction, (start, stop) in enumerate(candidate.wave_slices):
            keep = np.ones(candidate.design.shape[1], bool)
            keep[start:stop] = False
            nuisance = candidate.design[:, keep]
            waves = candidate.wave_fields[direction].reshape(-1, 2)
            rhs = np.column_stack(
                (
                    raw.ravel()[selected] - parent[color].ravel()[selected],
                    waves[selected],
                )
            )
            null_fit = np.linalg.lstsq(
                nuisance[selected] * precision[:, None],
                rhs * precision[:, None],
                rcond=1e-10,
            )[0]
            beta = null_fit[:, 1:]
            residual_selected = (waves[selected] - nuisance[selected] @ beta) * precision[:, None]
            wave_selected = waves[selected] * precision[:, None]
            fractions[direction, color] = np.sum(residual_selected**2) / np.sum(wave_selected**2)
            values, vectors = np.linalg.eigh(wave_selected.T @ wave_selected)
            inverse_root = (vectors / np.sqrt(np.maximum(values, 1e-30))) @ vectors.T
            spectra[direction, color] = np.linalg.eigvalsh(
                inverse_root @ (residual_selected.T @ residual_selected) @ inverse_root
            )
            result[direction, color] = (
                full_component - native_design[:, keep] @ null_fit[:, 0]
            ).reshape(shape)
    return result, fractions, spectra


def restore_neural_nuisance(
    parent,
    packed,
    colors,
    backgrounds,
    *,
    shot,
    read,
    thresholds=(0.0, 2.0, 4.0),
    config=_DEFAULT,
):
    """Matched analytic/neural-nuisance H1 corrections under one global CFA split."""
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
        raise ValueError("Require matching finite native RGB, packed RAW and CFA")
    h, w = parent.shape[1:]
    allowed = np.array([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    if (
        h % 2
        or w % 2
        or min(h, w) < config.window
        or not (allowed == colors).all(1).any()
        or not np.isfinite([shot, read]).all()
        or min(shot, read) < 0
        or config.harmonics != 1
        or config.support_unit != "direction"
        or config.matching != "cardinality"
    ):
        raise ValueError("Require H1/cardinality geometry and valid native axes/CFA/noise")
    if not thresholds or len(set(thresholds)) != len(thresholds):
        raise ValueError("Require distinct nonempty fixed thresholds")
    for t in thresholds:
        support_weight(0, t)
    outputs = {
        (mode, float(t)): parent.copy()
        for mode in (
            "H1-global",
            "H1-local",
            "conditional-global",
            "conditional-local",
            "global",
            "local",
        )
        for t in thresholds
    }
    if shot + read == 0:
        return outputs, {"patches": 0, "identity_zero_noise": True}
    if (
        backgrounds is None
        or len(backgrounds) != 2
        or any(b.rgb.shape != parent.shape for b in backgrounds)
        or not np.array_equal(backgrounds[0].discovery_mask, ~backgrounds[1].discovery_mask)
    ):
        raise ValueError("Require complementary whole-context neural discovery masks")
    raw = np.empty((h, w), np.float64)
    for phase in range(4):
        raw[phase // 2 :: 2, phase % 2 :: 2] = packed[phase]
    cfa = np.tile(colors.reshape(2, 2), (h // 2, w // 2))
    totals = {key: np.zeros(parent.shape) for key in outputs}
    denominator = np.zeros((h, w))
    n = config.window
    taper = np.sin(np.pi * (np.arange(n) + 0.5) / n) ** 2
    blend = taper[:, None] * taper[None]
    positions = [
        np.unique(np.r_[np.arange(0, length - n + 1, config.stride), length - n])
        for length in (h, w)
    ]
    records = []
    for y in positions[0]:
        for x in positions[1]:
            region = np.s_[y : y + n, x : x + n]
            tile, layout = raw[region], cfa[region]
            masks = [b.discovery_mask[region] for b in backgrounds]
            reference = [
                fit_local_candidate(tile, layout, mask, shot=shot, read=read, config=config)
                for mask in masks
            ]
            neural = [
                fit_neural_candidate(
                    tile,
                    layout,
                    r,
                    WithheldBackground(b.rgb[:, region[0], region[1]], mask),
                    config=config,
                )
                for r, b, mask in zip(reference, backgrounds, masks, strict=True)
            ]
            tile_records = {}
            for prefix, candidates in [("H1-", reference), ("", neural)]:
                scores = [
                    conditional_scores(
                        c,
                        tile,
                        layout,
                        ~c.discovery_mask,
                        window=config.validation_window,
                        stride=config.validation_stride,
                    )
                    for c in candidates
                ]
                matched = match_directions(
                    candidates[0].frequencies_xy,
                    candidates[1].frequencies_xy,
                    tile.shape,
                    config.match_native_bins,
                    matching=config.matching,
                )
                # Only this final projection may consume the full-input parent.
                rgb = parent[:, region[0], region[1]]
                local_backgrounds = (
                    [
                        WithheldBackground(b.rgb[:, region[0], region[1]], mask)
                        for b, mask in zip(backgrounds, masks, strict=True)
                    ]
                    if not prefix
                    else [None, None]
                )
                unique = [
                    conditional_components(c, rgb, tile, layout, b)
                    for c, b in zip(candidates, local_backgrounds, strict=True)
                ]
                components = [u[0] for u in unique]
                legacy = [replacement_components(c, rgb) for c in candidates] if prefix else None
                maxima = []
                for a, b, _distance in matched:
                    component = (components[0][a] + components[1][b]) / 2
                    local = np.minimum(scores[0][0][a], scores[1][0][b])
                    glob = np.minimum(scores[0][1][a], scores[1][1][b])
                    deliveries = [("conditional-" if prefix else "", component)]
                    if legacy is not None:
                        deliveries.append(("H1-", (legacy[0][a] + legacy[1][b]) / 2))
                    for destination, delivered in deliveries:
                        for t in thresholds:
                            totals[destination + "local", float(t)][:, region[0], region[1]] += (
                                delivered * support_weight(local, t) * blend
                            )
                            totals[destination + "global", float(t)][:, region[0], region[1]] += (
                                delivered * support_weight(glob, t)[:, None, None] * blend
                            )
                    maxima.append(float(local.max()))
                tile_records[prefix or "neural"] = {
                    "frequencies": [c.frequencies_xy for c in candidates],
                    "matched": matched,
                    "local_max": maxima,
                    "wave_residual_energy_fraction_by_direction_color": [
                        u[1].tolist() for u in unique
                    ],
                    "wave_residual_Gram_eigenvalues_by_direction_color": [
                        u[2].tolist() for u in unique
                    ],
                    "heldout_full_standardized_MSE_by_color": [
                        [
                            float(
                                np.mean(
                                    (
                                        tile[(~c.discovery_mask) & (layout == color)]
                                        - c.full_cfa[(~c.discovery_mask) & (layout == color)]
                                    )
                                    ** 2
                                    / c.variance_cfa[(~c.discovery_mask) & (layout == color)]
                                )
                            )
                            for color in range(3)
                        ]
                        for c in candidates
                    ],
                }
                if not prefix:
                    column = reference[0].wave_slices[0][0]
                    tile_records["neural"]["neural_nuisance_coefficients_by_color"] = [
                        c.coefficients[:, column].tolist() for c in candidates
                    ]
            denominator[region] += blend
            records.append({"xy": [int(x), int(y)], "arms": tile_records})
    for key in outputs:
        outputs[key] = (parent.astype(np.float64) + totals[key] / denominator).astype(parent.dtype)
    return outputs, {
        "patches": len(records),
        "identity_zero_noise": False,
        "records": records,
        "shared_global_CFA_partition": True,
        "shared_analytic_edges_and_variance_proxy": True,
        "parent_used_for_discovery_or_validation": False,
        "geometry_config": config.to_dict(),
        "scope": "Own-color A-only neural nuisance coordinate, upper-censored at sensor white; residual frequency reselection and joint WLS. Matched analytic control shares global split, edge, noise weights and validation rules. Parent projected only after scoring. Empirical scores, not calibrated confidence; final RGB retains full-input parent.",
    }
