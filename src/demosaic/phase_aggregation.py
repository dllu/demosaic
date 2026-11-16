"""Experimental held-out validation of local, same-color phase averaging.

Geometry and nuisance fits use only discovery samples. The phase-conditioned
average and unconditioned local average each have nonnegative normalized
measurement weights. Their difference is a signed detail operator; neither
the complete correction nor delivered RGB is a convex average or safety bound.
"""

from dataclasses import asdict, dataclass
from types import SimpleNamespace

import numpy as np
from scipy.ndimage import map_coordinates

from .experiments.evaluation.withheld import geometry, stratified_split
from .local_validated_waves import (
    LocalWaveConfig,
    _box_sums,
    conditional_scores,
    fit_local_candidate,
    match_directions,
    replacement_components,
    support_weight,
)


@dataclass(frozen=True)
class PhaseAggregateConfig:
    bins: int = 32
    window: int = 129
    query_stride: int = 16
    edge_stopping: bool = True
    parent_projection: str = "conditional_null"

    def __post_init__(self):
        if (
            any(type(v) is not int for v in (self.bins, self.window, self.query_stride))
            or not 8 <= self.bins <= 128
            or self.window < 3
            or self.window % 2 != 1
            or not 1 <= self.query_stride <= 64
            or type(self.edge_stopping) is not bool
            or self.parent_projection not in ("innovation", "conditional_null")
        ):
            raise ValueError("Invalid phase aggregation geometry")

    def to_dict(self):
        return asdict(self)


_DEFAULT_AGGREGATION = PhaseAggregateConfig()
_DEFAULT_GEOMETRY = LocalWaveConfig()


class PhaseAggregateOperator:
    """Fixed linear signed operator, reading discovery values of each color only."""

    def __init__(self, candidate, colors, direction, config=_DEFAULT_AGGREGATION):
        self.mask = np.asarray(candidate.discovery_mask)
        self.colors = np.asarray(colors)
        self.shape = self.mask.shape
        self.config = config
        if (
            self.mask.ndim != 2
            or self.mask.dtype != bool
            or self.colors.shape != self.shape
            or not np.isin(self.colors, (0, 1, 2)).all()
            or direction not in (0, 1)
            or not np.isfinite(candidate.variance_cfa).all()
            or np.any(candidate.variance_cfa <= 0)
        ):
            raise ValueError("Require a positive A-only noise proxy and native CFA mask")
        h, w = self.shape
        xx, yy, _, _ = geometry(self.shape)
        frequency = np.asarray(candidate.frequencies_xy[direction])
        if frequency.shape != (2,) or not np.isfinite(frequency).all():
            raise ValueError("Require a finite input-only frequency")
        phase = np.minimum(
            np.remainder(xx * frequency[0] + yy * frequency[1], 1) * config.bins,
            np.nextafter(float(config.bins), 0),
        )
        lower = np.floor(phase).astype(np.int64)
        fraction = phase - lower
        angle, offset = candidate.edge_geometry
        if not np.isfinite([angle, offset]).all():
            raise ValueError("Require finite A-only edge geometry")
        x, y = 2 * (xx + 0.5) / w - 1, 2 * (yy + 0.5) / h - 1
        self.side = (
            x * np.cos(angle) + y * np.sin(angle) > offset
            if config.edge_stopping
            else np.zeros(self.shape, bool)
        )
        self.ay, self.ax = [
            np.unique(np.r_[np.arange(0, n, config.query_stride), n - 1]) for n in self.shape
        ]
        cy = np.interp(np.arange(h), self.ay, np.arange(len(self.ay)))
        cx = np.interp(np.arange(w), self.ax, np.arange(len(self.ax)))
        self.coordinates = np.array(
            [phase, np.broadcast_to(cy[:, None], self.shape), np.broadcast_to(cx, self.shape)]
        )
        self.spatial_coordinates = self.coordinates[1:]
        self.groups = []
        for color in range(3):
            for side in (False, True):
                indices = np.flatnonzero(
                    (self.mask & (self.colors == color) & (self.side == side)).ravel()
                )
                if not len(indices):
                    continue
                variance = candidate.variance_cfa.ravel()[indices]
                weight = np.median(variance) / variance
                group = {
                    "color": color,
                    "side": side,
                    "indices": indices,
                    "weight": weight,
                    "lower": lower.ravel()[indices],
                    "fraction": fraction.ravel()[indices],
                }
                histogram = self._histogram(group, np.ones(len(indices)))
                group["phase_denominator"] = self._phase_query(histogram)
                group["local_denominator"] = self._spatial_query(histogram.sum(0))
                self.groups.append(group)

    def _histogram(self, group, values):
        h, w = self.shape
        indices, lower, fraction = (group[k] for k in ("indices", "lower", "fraction"))
        a = lower * h * w + indices
        b = ((lower + 1) % self.config.bins) * h * w + indices
        value = values * group["weight"]
        volume = np.bincount(
            np.r_[a, b],
            weights=np.r_[value * (1 - fraction), value * fraction],
            minlength=self.config.bins * h * w,
        ).reshape(self.config.bins, h, w)
        return np.stack([_box_sums(v, self.ay, self.ax, self.config.window) for v in volume])

    def _phase_query(self, histogram):
        # Fixed circular [1,2,3,2,1]/9 smoothing; no selected bandwidth or phase fit.
        smooth = (
            sum(
                weight * np.roll(histogram, offset, axis=0)
                for offset, weight in zip(range(-2, 3), (1, 2, 3, 2, 1), strict=True)
            )
            / 9
        )
        periodic = np.concatenate([smooth, smooth[:1]], axis=0)
        return map_coordinates(periodic, self.coordinates, order=1, prefilter=False, mode="nearest")

    def _spatial_query(self, histogram):
        return map_coordinates(
            histogram, self.spatial_coordinates, order=1, prefilter=False, mode="nearest"
        )

    def apply(self, values):
        """Phase average minus local mean, independently for each CFA color/side."""
        values = np.asarray(values, np.float64)
        if values.shape != self.shape or not np.isfinite(values[self.mask]).all():
            raise ValueError("Require finite discovery values on the fixed native grid")
        result = np.zeros((3, *self.shape))
        for group in self.groups:
            histogram = self._histogram(group, values.ravel()[group["indices"]])
            p, q = group["phase_denominator"], group["local_denominator"]
            phase = np.divide(self._phase_query(histogram), p, out=np.zeros_like(p), where=p > 0)
            local = np.divide(
                self._spatial_query(histogram.sum(0)), q, out=np.zeros_like(q), where=q > 0
            )
            active = (self.side == group["side"]) & (p > 0) & (q > 0)
            result[group["color"], active] = (phase - local)[active]
        return result


def aggregate_candidate(candidate, raw, colors, config=_DEFAULT_AGGREGATION):
    """Build RAW-only candidate increments before accepting any parent argument."""
    raw = np.asarray(raw, np.float64)
    h, w = raw.shape
    yy, xx = np.indices(raw.shape)
    operators, increments, scores = [], [], []
    for direction in range(2):
        operator = PhaseAggregateOperator(candidate, colors, direction, config)
        increment = operator.apply(raw - candidate.conditional_null_cfa[direction])
        observed = increment[colors, yy, xx]
        predictive = SimpleNamespace(
            discovery_mask=candidate.discovery_mask,
            full_cfa=candidate.conditional_null_cfa[direction] + observed,
            conditional_null_cfa=candidate.conditional_null_cfa[direction : direction + 1],
            variance_cfa=candidate.variance_cfa,
            unit_keys=((direction, 0),),
        )
        operators.append(operator)
        increments.append(increment)
        scores.append(predictive)
    assert np.asarray(increments).shape == (2, 3, h, w)
    return operators, increments, scores


def conditional_null_projection(candidate, values, colors, direction):
    """Project values onto the same A-only weighted null used by validation.

    Called on the parent innovation only after all RAW-only scores are fixed.
    The operator uses the fixed design/noise proxy and discovery sites only;
    projecting parent values does not reselect geometry or validation support.
    """
    values, colors = np.asarray(values, np.float64), np.asarray(colors)
    if values.shape != candidate.discovery_mask.shape or colors.shape != values.shape:
        raise ValueError("Require the fixed native candidate grid")
    if direction not in (0, 1):
        raise ValueError("Require one of the two discovered directions")
    start, stop = candidate.wave_slices[direction]
    keep = np.ones(candidate.design.shape[1], bool)
    keep[start:stop] = False
    design = candidate.design[:, keep]
    projected = np.empty(values.size)
    for color in range(3):
        selected = candidate.selected_indices[color]
        value = values.ravel()[selected]
        if not np.isfinite(value).all():
            raise ValueError("Require finite discovery values")
        inverse_sigma = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
        coefficient = np.linalg.lstsq(
            design[selected] * inverse_sigma[:, None], value * inverse_sigma, rcond=1e-10
        )[0]
        destination = (colors == color).ravel()
        projected[destination] = design[destination] @ coefficient
    return projected.reshape(values.shape)


def restore_phase_aggregation(
    parent,
    packed,
    colors,
    *,
    shot,
    read,
    thresholds=(0.0, 2.0, 4.0),
    geometry_config=_DEFAULT_GEOMETRY,
    aggregation_config=_DEFAULT_AGGREGATION,
):
    """Matched H1 and measurement-aggregation corrections from identical A/B fits."""
    parent, packed, colors = np.asarray(parent), np.asarray(packed), np.asarray(colors)
    config = geometry_config
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
        raise ValueError("Require H1/cardinality geometry, valid native axes and physical noise")
    if not thresholds or len(set(thresholds)) != len(thresholds):
        raise ValueError("Require nonempty distinct fixed thresholds")
    for threshold in thresholds:
        support_weight(0, threshold)
    modes = ("H1-global", "H1-local", "global", "local")
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
        for length in (h, w)
    ]
    records = []
    for y in positions[0]:
        for x in positions[1]:
            region = np.s_[y : y + n, x : x + n]
            tile, layout = raw[region], cfa[region]
            split = stratified_split(tile.shape, config.split_seed + int(y) * w + int(x))
            candidates = [
                fit_local_candidate(tile, layout, mask, shot=shot, read=read, config=config)
                for mask in (split, ~split)
            ]
            aggregate = [
                aggregate_candidate(c, tile, layout, aggregation_config) for c in candidates
            ]
            aggregate_scores = [
                [
                    conditional_scores(
                        predictive,
                        tile,
                        layout,
                        ~c.discovery_mask,
                        window=config.validation_window,
                        stride=config.validation_stride,
                    )
                    for predictive in group[2]
                ]
                for c, group in zip(candidates, aggregate, strict=True)
            ]
            reference_scores = [
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
            # Parent access is deliberately after all geometry and validation scores.
            rgb = parent[:, y : y + n, x : x + n]
            yy, xx = np.indices(tile.shape)
            innovation = tile - rgb[layout, yy, xx]
            components = [
                [
                    operator.apply(
                        innovation - conditional_null_projection(c, innovation, layout, direction)
                        if aggregation_config.parent_projection == "conditional_null"
                        else innovation
                    )
                    for direction, operator in enumerate(group[0])
                ]
                for c, group in zip(candidates, aggregate, strict=True)
            ]
            reference = [replacement_components(c, rgb) for c in candidates]
            maxima = []
            for a, b, _distance in matched:
                for reference_mode in (False, True):
                    component = (
                        (reference[0][a] + reference[1][b]) / 2
                        if reference_mode
                        else (components[0][a] + components[1][b]) / 2
                    )
                    if reference_mode:
                        local = np.minimum(reference_scores[0][0][a], reference_scores[1][0][b])
                        glob = np.minimum(reference_scores[0][1][a], reference_scores[1][1][b])
                    else:
                        local = np.minimum(
                            aggregate_scores[0][a][0][0], aggregate_scores[1][b][0][0]
                        )
                        glob = np.minimum(
                            aggregate_scores[0][a][1][0], aggregate_scores[1][b][1][0]
                        )
                        maxima.append(float(local.max()))
                    prefix = "H1-" if reference_mode else ""
                    for threshold in thresholds:
                        totals[prefix + "local", float(threshold)][:, region[0], region[1]] += (
                            component * support_weight(local, threshold) * blend
                        )
                        totals[prefix + "global", float(threshold)][:, region[0], region[1]] += (
                            component * support_weight(glob, threshold)[:, None, None] * blend
                        )
            denominator[region] += blend
            records.append(
                {
                    "xy": [int(x), int(y)],
                    "frequencies": [c.frequencies_xy for c in candidates],
                    "edges": [c.edge_geometry for c in candidates],
                    "matched": matched,
                    "aggregation_local_max": maxima,
                }
            )
    for key in outputs:
        outputs[key] = (parent.astype(np.float64) + totals[key] / denominator).astype(parent.dtype)
    return outputs, {
        "patches": len(records),
        "records": records,
        "identity_zero_noise": False,
        "geometry_config": config.to_dict(),
        "aggregation_config": aggregation_config.to_dict(),
        "parent_used_for_discovery_or_validation": False,
        "scope": "Same A-only H1 geometry/variance/competing null, fixed phase/local same-color averaging, A/B per-color conditional validation, edge stopping. Difference of normalized averages is signed; empirical scores are not calibrated confidence. Parent projection/correction only after support scores. Final RGB uses both folds and full-input parent, not an independent prediction.",
    }
