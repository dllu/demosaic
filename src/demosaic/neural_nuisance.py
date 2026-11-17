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


def fit_neural_candidate(
    raw, colors, reference, background, *, config=_DEFAULT, reselect_frequencies=True
):
    """Add one own-color neural nuisance coordinate; retain A-only edge/noise proxy.

    The CFA-interleaved feature is used only on each color's actual sensor
    sites. It is not an RGB nuisance image at unmeasured color locations.
    Frequencies are normally reselected/refined after adding this competing
    nuisance. The explicit ablation retains the analytic reference proposals.
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
    if reselect_frequencies:
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
    else:
        first, second = reference.frequencies_xy
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
    at unmeasured locations. The residualization design and wave projection
    depend only on discovery data; the parent enters the final difference RHS.
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
    reselect_frequencies=True,
    aggregation_config=None,
    phase_guide=False,
    add_fine_carriers=False,
    fine_reconstruction="phase",
    fine_support="independent",
    fine_validation="nuisance",
):
    """Matched analytic/neural nuisances; optional fixed-background phase delivery."""
    if type(phase_guide) is not bool or (phase_guide and aggregation_config is None):
        raise ValueError("Range guidance requires the phase reconstruction option")
    if type(add_fine_carriers) is not bool or (
        add_fine_carriers and (aggregation_config is None or reselect_frequencies)
    ):
        raise ValueError(
            "Additional fine carriers require phase reconstruction and fixed proposals"
        )
    if fine_reconstruction not in ("phase", "sinusoidal") or (
        fine_reconstruction != "phase" and not add_fine_carriers
    ):
        raise ValueError("Require an enabled fine pair for sinusoidal fine reconstruction")
    if fine_support not in ("independent", "joint") or (
        fine_support == "joint" and (not add_fine_carriers or fine_reconstruction != "sinusoidal")
    ):
        raise ValueError("Joint colour support requires enabled sinusoidal fine carriers")
    if fine_validation not in ("nuisance", "neural-parent") or (
        fine_validation == "neural-parent"
        and (
            not add_fine_carriers or fine_reconstruction != "sinusoidal" or fine_support != "joint"
        )
    ):
        raise ValueError("Neural-parent validation requires joint sinusoidal fine carriers")
    if aggregation_config is not None:
        from .phase_aggregation import PhaseAggregateConfig

        if not isinstance(aggregation_config, PhaseAggregateConfig) or config.amplitude_window:
            raise ValueError("Phase aggregation replaces the amplitude model; require no local WLS")
        if fine_reconstruction == "sinusoidal" and aggregation_config.window < 17:
            raise ValueError("Sinusoidal fine amplitudes require a window of at least17 pixels")
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
                    reselect_frequencies=reselect_frequencies,
                )
                for r, b, mask in zip(reference, backgrounds, masks, strict=True)
            ]
            candidate_groups = [("H1-", "H1-", reference, True), ("neural", "", neural, False)]
            fine_unavailable = []
            if add_fine_carriers:
                from .fine_carrier_proposals import fit_fine_candidate

                fine = [
                    fit_fine_candidate(tile, layout, r, shot=shot, read=read, config=config)
                    for r in reference
                ]
                fine_unavailable = [
                    fold for fold, candidate in enumerate(fine) if candidate is None
                ]
                fine_neural = [
                    fit_neural_candidate(
                        tile,
                        layout,
                        r,
                        WithheldBackground(b.rgb[:, region[0], region[1]], mask),
                        config=config,
                        reselect_frequencies=False,
                    )
                    for r, b, mask in zip(fine, backgrounds, masks, strict=True)
                    if not fine_unavailable
                ]
                if not fine_unavailable:
                    candidate_groups.extend(
                        [("fine-H1-", "H1-", fine, False), ("fine-neural", "", fine_neural, False)]
                    )
            tile_records = {}
            for record_key, prefix, candidates, legacy_control in candidate_groups:
                fine_sinusoidal = (
                    record_key.startswith("fine-") and fine_reconstruction == "sinusoidal"
                )
                local_backgrounds = (
                    [
                        WithheldBackground(b.rgb[:, region[0], region[1]], mask)
                        for b, mask in zip(backgrounds, masks, strict=True)
                    ]
                    if not prefix
                    else [None, None]
                )
                spatial = None
                nuisance_mode = "global" if fine_sinusoidal else config.amplitude_nuisance
                if config.amplitude_window or fine_sinusoidal:
                    from .spatial_carrier_amplitudes import SpatialCarrierOperator

                    spatial = [
                        SpatialCarrierOperator(
                            c,
                            layout,
                            window=aggregation_config.window
                            if fine_sinusoidal
                            else config.amplitude_window,
                            stride=aggregation_config.query_stride
                            if fine_sinusoidal
                            else config.amplitude_stride,
                            background=b,
                            nuisance_mode=nuisance_mode,
                        )
                        for c, b in zip(candidates, local_backgrounds, strict=True)
                    ]
                predictors = candidates if spatial is None else [s.predict(tile) for s in spatial]
                if fine_sinusoidal and fine_validation == "neural-parent":
                    predictors = [
                        s.predict_parent_innovation(
                            tile, WithheldBackground(b.rgb[:, region[0], region[1]], mask)
                        )
                        for s, b, mask in zip(spatial, backgrounds, masks, strict=True)
                    ]
                score_function = conditional_scores
                if fine_sinusoidal and fine_support == "joint":
                    from .joint_colour_evidence import joint_conditional_scores

                    score_function = joint_conditional_scores
                reference_scores = [
                    score_function(
                        c,
                        tile,
                        layout,
                        ~c.discovery_mask,
                        window=config.validation_window,
                        stride=config.validation_stride,
                    )
                    for c in predictors
                ]
                scores = reference_scores
                phase = None
                phase_predictors = None
                if aggregation_config is not None and not fine_sinusoidal:
                    from .background_phase_aggregation import BackgroundPhaseOperator

                    phase = [
                        BackgroundPhaseOperator(
                            c,
                            layout,
                            aggregation_config,
                            guide_rgb=backgrounds[fold].rgb[:, region[0], region[1]]
                            if phase_guide
                            else None,
                            shot=shot,
                            read=read,
                        )
                        for fold, c in enumerate(candidates)
                    ]
                    phase_predictors = [p.predict(tile) for p in phase]
                    scores = []
                    for pair in phase_predictors:
                        evaluated = [
                            conditional_scores(
                                p,
                                tile,
                                layout,
                                ~p.discovery_mask,
                                window=config.validation_window,
                                stride=config.validation_stride,
                            )
                            for p in pair
                        ]
                        scores.append(
                            tuple(np.concatenate([v[i] for v in evaluated]) for i in (0, 1))
                        )
                matched = match_directions(
                    candidates[0].frequencies_xy,
                    candidates[1].frequencies_xy,
                    tile.shape,
                    config.match_native_bins,
                    matching=config.matching,
                )
                # Only this final projection may consume the full-input parent.
                rgb = parent[:, region[0], region[1]]
                if phase is not None:
                    components = [p.components(tile, rgb) for p in phase]
                    unique = None
                    legacy = (
                        [replacement_components(c, rgb) for c in candidates]
                        if legacy_control
                        else None
                    )
                elif spatial is None:
                    unique = [
                        conditional_components(c, rgb, tile, layout, b)
                        for c, b in zip(candidates, local_backgrounds, strict=True)
                    ]
                    legacy = (
                        [replacement_components(c, rgb) for c in candidates]
                        if legacy_control
                        else None
                    )
                else:
                    local_components = [s.components(tile, rgb) for s in spatial]
                    unique = [value[0] for value in local_components]
                    legacy = [value[1] for value in local_components] if legacy_control else None
                if unique is not None:
                    components = (
                        [value[1] for value in local_components]
                        if fine_sinusoidal
                        else [u[0] for u in unique]
                    )
                maxima = []
                for a, b, _distance in matched:
                    component = (components[0][a] + components[1][b]) / 2
                    local = np.minimum(scores[0][0][a], scores[1][0][b])
                    glob = np.minimum(scores[0][1][a], scores[1][1][b])
                    deliveries = [("conditional-" if prefix else "", component)]
                    if legacy is not None:
                        deliveries.append(("H1-", (legacy[0][a] + legacy[1][b]) / 2))
                    for destination, delivered in deliveries:
                        delivered_local, delivered_global = local, glob
                        if phase is not None and destination == "H1-":
                            delivered_local = np.minimum(
                                reference_scores[0][0][a], reference_scores[1][0][b]
                            )
                            delivered_global = np.minimum(
                                reference_scores[0][1][a], reference_scores[1][1][b]
                            )
                        for t in thresholds:
                            totals[destination + "local", float(t)][:, region[0], region[1]] += (
                                delivered * support_weight(delivered_local, t) * blend
                            )
                            totals[destination + "global", float(t)][:, region[0], region[1]] += (
                                delivered
                                * support_weight(delivered_global, t)[:, None, None]
                                * blend
                            )
                    maxima.append(float(local.max()))
                tile_records[record_key] = {
                    "frequencies": [c.frequencies_xy for c in candidates],
                    "matched": matched,
                    "local_max": maxima,
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
                        for c in predictors
                    ],
                }
                if unique is not None:
                    tile_records[record_key].update(
                        wave_residual_energy_fraction_by_direction_color=[
                            u[1].tolist() for u in unique
                        ],
                        wave_residual_Gram_eigenvalues_by_direction_color=[
                            u[2].tolist() for u in unique
                        ],
                    )
                if phase_predictors is not None:
                    arm = tile_records[record_key]
                    arm["H1_diagnostics_scope"] = "Not phase-kernel diagnostics; omitted."
                    arm["heldout_full_standardized_MSE_by_color"] = [
                        [
                            float(
                                np.mean(
                                    [
                                        np.mean(
                                            (tile[selected] - p.full_cfa[selected]) ** 2
                                            / p.variance_cfa[selected]
                                        )
                                        for p in pair
                                    ]
                                )
                            )
                            for color in range(3)
                            for selected in [(~pair[0].discovery_mask) & (layout == color)]
                        ]
                        for pair in phase_predictors
                    ]
                    arm["heldout_MSE_scope"] = (
                        "Mean of the two direction-specific phase full models."
                    )
                if spatial is not None:
                    tile_records[record_key]["wave_diagnostic_scope"] = (
                        "Energy-weighted local-query averages; normalized Gram inverse cutoff1e-8. Geometry/global variance unchanged."
                    )
                    tile_records[record_key]["amplitude_nuisance"] = nuisance_mode
                    tile_records[record_key]["amplitude_window"] = spatial[0].window
                    if fine_sinusoidal:
                        tile_records[record_key]["carrier_delivery"] = (
                            "Sinusoidal full-fit coefficients; full/null used for validation."
                        )
                        tile_records[record_key]["colour_support"] = fine_support
                        tile_records[record_key]["validation_target"] = fine_validation
                        if fine_validation == "neural-parent":
                            tile_records[record_key]["heldout_MSE_scope"] = (
                                "A-only neural RGB plus both unshrunk full-fit fine innovations; "
                                "each null removes one delivered direction. Not full-input or broad+fine risk."
                            )
                if not prefix:
                    column = candidates[0].wave_slices[0][0] - 1
                    tile_records[record_key]["neural_nuisance_coefficients_by_color"] = [
                        c.coefficients[:, column].tolist() for c in candidates
                    ]
                    if spatial is not None:
                        tile_records[record_key]["neural_coefficient_scope"] = (
                            "Global background coefficients used in prediction; only residual carrier amplitudes vary locally."
                            if nuisance_mode == "global"
                            else "Global discovery coefficients only; actual prediction/delivery use local-query coefficients."
                        )
                    if phase is not None:
                        tile_records[record_key]["neural_coefficient_scope"] = (
                            "Global joint-fit background coefficients used in both phase full/null models."
                        )
            denominator[region] += blend
            records.append(
                {
                    "xy": [int(x), int(y)],
                    "arms": tile_records,
                    "fine_proposal_unavailable_folds": fine_unavailable,
                }
            )
    for key in outputs:
        outputs[key] = (parent.astype(np.float64) + totals[key] / denominator).astype(parent.dtype)
    return outputs, {
        "patches": len(records),
        "identity_zero_noise": False,
        "records": records,
        "shared_global_CFA_partition": True,
        "shared_analytic_edges_and_variance_proxy": True,
        "neural_frequency_source": "residual-reselection"
        if reselect_frequencies
        else "fixed-analytic-proposals",
        "parent_used_for_discovery_or_validation": False,
        "geometry_config": config.to_dict(),
        "aggregation_config": aggregation_config.to_dict() if aggregation_config else None,
        "phase_guide": phase_guide,
        "add_fine_carriers": add_fine_carriers,
        "fine_reconstruction": fine_reconstruction,
        "fine_support": fine_support,
        "fine_validation": fine_validation,
        "scope": "Own-color A-only neural nuisance coordinate, upper-censored at sensor white; declared frequency source and joint WLS. Matched analytic control shares global split, edge, noise weights and validation rules. Parent projected only after scoring. Empirical scores, not calibrated confidence; final RGB retains full-input parent."
        + (
            " Conditional/neural delivery uses local signed phase averages after a fixed global joint-fit background and per-direction global competing H1 fit. Identical composite linear map projects RAW and parent. H1 control retains its own original H1 validation scores."
            if aggregation_config is not None
            else ""
        )
        + (
            " Both phase arms also condition normalized averages on their own-color A-only neural field, clipped0..1 and transformed by physical shot/read standard-deviation units. Fixed two-noise-unit range bins and [1,2,1]/4 range smoothing; RGB amplitudes remain separate."
            if phase_guide
            else ""
        )
        + (
            " Additional1/16..0.24-native fine pair discovered after projecting the original broad design, with coarse-profile/harmonic duplicate exclusions. Broad corrections retained; fine full/null and parent maps include broad carriers in global nuisance. Fine directions have separate A/B matching/validation; raw-H1 controls unchanged. More candidates do not confer calibrated confidence."
            if add_fine_carriers
            else ""
        )
        + (
            " Fine delivery instead uses native local sinusoidal full-fit coefficients, with full/null prediction for validation, the same query window/stride and frozen global broad/background nuisance. Separate RGB coefficients; identical full-fit RAW/parent carrier map, no phase/range/edge-side fine pooling. Broad guided phase and H1 controls unchanged. This changes the fine waveform, fit, delivery and support model, not an isolated harmonic-only ablation or strict spectral cutoff."
            if fine_reconstruction == "sinusoidal"
            else ""
        )
        + (
            " Fine support pools held-out variance-normalized full/null gains and energies over all actual CFA colours before normalization. One scalar support per direction/pixel preserves independently fitted RGB amplitudes/phases. It can admit noisy weak colour coefficients; it is not green-only validation or calibrated colour confidence. Broad support and raw-H1 controls unchanged."
            if fine_support == "joint"
            else ""
        )
        + (
            " Fine full/null validation instead composes the genuine A-only neural RGB field with both unshrunk sinusoidal RAW-minus-that-field innovations; each null removes one delivered direction. Same full-fit operator and separately fitted RGB coefficients. Full-input parent remains excluded from scoring. Does not validate the later broad+fine sum or calibrate final-estimator confidence."
            if fine_validation == "neural-parent"
            else ""
        ),
    }
