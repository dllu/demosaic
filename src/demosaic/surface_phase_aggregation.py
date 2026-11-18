"""Phase-conditioned RAW averages stratified by the fitted query surface."""

from types import SimpleNamespace

import numpy as np

from .local_validated_waves import conditional_scores
from .phase_aggregation import (
    PhaseAggregateConfig,
    PhaseAggregateOperator,
    conditional_null_projection,
)

SURFACE_AGGREGATION = PhaseAggregateConfig(bins=24, window=97, query_stride=24)


def bound_phase_average(parent, refit, average):
    """Limit each emitted color correction to the paired wave refit's norm."""
    parent, refit, average = (np.asarray(a) for a in (parent, refit, average))
    if (
        parent.ndim != 3
        or parent.shape[0] != 3
        or not np.issubdtype(parent.dtype, np.floating)
        or refit.shape != parent.shape
        or average.shape != parent.shape
        or any(not np.isfinite(a).all() for a in (parent, refit, average))
    ):
        raise ValueError("Require finite matching camera RGB")
    origin = parent.astype(np.float64)
    delta = average - origin
    allowable = np.linalg.norm((refit - origin).reshape(3, -1), axis=1)
    observed = np.linalg.norm(delta.reshape(3, -1), axis=1)
    scale = np.divide(allowable, observed, out=np.ones_like(observed), where=observed > allowable)
    return (origin + scale[:, None, None] * delta).astype(parent.dtype)


class SurfacePhaseOperator(PhaseAggregateOperator):
    """Keep phase pooling within the same color and fitted step region."""

    def __init__(self, candidate, colors, direction, config=SURFACE_AGGREGATION, *, tangent=False):
        self.tangent = tangent
        frequency = np.asarray(candidate.frequencies_xy[direction])
        length = np.linalg.norm(frequency)
        if not np.isfinite(length) or length == 0:
            raise ValueError("Require a nonzero finite phase normal")
        self.normal = frequency / length
        super().__init__(candidate, colors, direction, config)

    def _regions(self, candidate, x, y, angle, offset):
        parallel = getattr(candidate, "parallel_edges", None)
        if not self.config.edge_stopping or parallel is None:
            return super()._regions(candidate, x, y, angle, offset)
        normal, first, second = parallel
        pos = x * np.cos(normal) + y * np.sin(normal)
        return (pos > first).astype(np.uint8) + (pos > second)

    def _histogram(self, group, values):
        if not self.tangent:
            return super()._histogram(group, values)
        bins = self.config.bins
        if "ellipse" not in group:
            iy, ix = np.unravel_index(group["indices"], self.shape)
            u, v = self.normal
            # Equal continuous area to the square, with a 2:1 tangent axis.
            short = self.config.window / np.sqrt(2 * np.pi)
            long = 2 * short
            group["ellipse"] = []
            for y in self.ay:
                for x in self.ax:
                    dx, dy = ix - x, iy - y
                    across, along = (u * dx + v * dy) / short, (v * dx - u * dy) / long
                    group["ellipse"].append(np.flatnonzero(across**2 + along**2 <= 1))
        lower, fraction = group["lower"], group["fraction"]
        weighted = values * group["weight"]
        result = np.empty((len(group["ellipse"]), bins))
        for i, keep in enumerate(group["ellipse"]):
            floor, part, weight = lower[keep], fraction[keep], weighted[keep]
            result[i] = np.bincount(floor, weight * (1 - part), minlength=bins)
            result[i] += np.bincount((floor + 1) % bins, weight * part, minlength=bins)
        return result.T.reshape(bins, len(self.ay), len(self.ax))


class SurfacePhaseProposal:
    """A fitted phase kernel and the test scores from its fixed RAW prediction."""

    def __init__(self, candidate, raw, cfa, validation, reliability, direction, cfg, *, tangent):
        self.operator = SurfacePhaseOperator(candidate, cfa, direction, tangent=tangent)
        self.candidate = candidate
        self.direction = direction
        null = candidate.conditional_null_cfa[direction]
        self.raw_residual = raw - null
        yy, xx = np.indices(raw.shape)
        wave = self.operator.apply(self.raw_residual)[cfa, yy, xx]
        predictor = SimpleNamespace(
            full_cfa=null + wave,
            conditional_null_cfa=null[None],
            discovery_mask=candidate.discovery_mask,
            variance_cfa=candidate.variance_cfa,
            phase_bright_side=candidate.phase_bright_side,
            phase_side_profiles=False,
            unit_keys=((direction, 0),),
        )
        self.scores = conditional_scores(
            predictor,
            raw,
            cfa,
            validation,
            window=cfg.validation_window,
            stride=cfg.validation_stride,
            reliability=reliability[direction : direction + 1],
        )[0][0]

    def correction(self, parent_cfa, colors):
        # Applying the same conditional-null projector to both images keeps
        # the actual validation operator in the parent replacement path.
        parent_null = conditional_null_projection(
            self.candidate, parent_cfa, colors, self.direction
        )
        return self.operator.apply(self.raw_residual - (parent_cfa - parent_null))
