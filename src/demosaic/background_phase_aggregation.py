"""Local measurement reconstruction above a fixed global nuisance operator.

The broad-context joint fit supplies only the background coefficients. Each
direction's null adds a global fit of the competing H1 carrier to the remaining
measurements. A fixed local phase kernel reconstructs the null residual. Both
held-out predictions and parent replacement use that identical linear map.
"""

from types import SimpleNamespace

import numpy as np

from .phase_aggregation import PhaseAggregateConfig, PhaseAggregateOperator

_DEFAULT = PhaseAggregateConfig()


class BackgroundPhaseOperator:
    """A-only fixed background, competing direction and signed phase kernel."""

    def __init__(self, candidate, colors, config=_DEFAULT):
        if config.parent_projection != "conditional_null":
            raise ValueError("Require the same global null projection for RAW and parent")
        self.candidate = candidate
        self.mask = np.asarray(candidate.discovery_mask)
        self.colors = np.asarray(colors)
        self.shape = self.mask.shape
        if (
            self.colors.shape != self.shape
            or self.mask.dtype != bool
            or not np.isin(self.colors, (0, 1, 2)).all()
            or len(candidate.wave_slices) != 2
            or any(b - a != 2 for a, b in candidate.wave_slices)
            or candidate.unit_keys != ((0, 0), (1, 0))
            or not np.isfinite(candidate.variance_cfa).all()
            or np.any(candidate.variance_cfa <= 0)
        ):
            raise ValueError("Require two H1 directions and a positive native A-only CFA fit")
        self.nuisance_columns = candidate.wave_slices[0][0]
        self.kernels = [PhaseAggregateOperator(candidate, colors, d, config) for d in (0, 1)]
        self.groups = []
        for color in range(3):
            selected = candidate.selected_indices[color]
            if not np.array_equal(
                selected, np.flatnonzero((self.mask & (self.colors == color)).ravel())
            ):
                raise ValueError("Candidate indices must match the actual discovery CFA sites")
            precision = 1 / np.sqrt(candidate.variance_cfa.ravel()[selected])
            competitors = []
            for direction in (0, 1):
                start, stop = candidate.wave_slices[1 - direction]
                design = candidate.design[:, start:stop]
                operator = np.linalg.pinv(design[selected] * precision[:, None], rcond=1e-10)
                competitors.append((design, operator * precision[None]))
            self.groups.append((selected, candidate.operators[color], competitors))

    def residualize(self, values, direction):
        """Return A residual and native CFA null; never inspect withheld values."""
        values = np.asarray(values, np.float64)
        if (
            values.shape != self.shape
            or direction not in (0, 1)
            or not np.isfinite(values[self.mask]).all()
        ):
            raise ValueError("Require finite A values on the fixed native grid")
        residual = np.zeros(values.size)
        null = np.empty(values.size)
        nuisance = self.candidate.design[:, : self.nuisance_columns]
        for color, (selected, operator, competitors) in enumerate(self.groups):
            observed = values.ravel()[selected]
            coefficient = (operator @ observed)[: self.nuisance_columns]
            background = nuisance @ coefficient
            remaining = observed - background[selected]
            design, competing_operator = competitors[direction]
            competing = design @ (competing_operator @ remaining)
            residual[selected] = remaining - competing[selected]
            destination = (self.colors == color).ravel()
            null[destination] = (background + competing)[destination]
        return residual.reshape(self.shape), null.reshape(self.shape)

    def apply(self, values):
        """Two RGB increments from the identical fixed composite operator."""
        return np.stack(
            [kernel.apply(self.residualize(values, d)[0]) for d, kernel in enumerate(self.kernels)]
        )

    def predict(self, raw):
        yy, xx = np.indices(self.shape)
        predictions = []
        for direction, kernel in enumerate(self.kernels):
            residual, null = self.residualize(raw, direction)
            increment = kernel.apply(residual)[self.colors, yy, xx]
            predictions.append(
                SimpleNamespace(
                    full_cfa=null + increment,
                    conditional_null_cfa=null[None],
                    discovery_mask=self.mask,
                    variance_cfa=self.candidate.variance_cfa,
                    unit_keys=((direction, 0),),
                )
            )
        return predictions

    def components(self, raw, parent):
        raw, parent = np.asarray(raw, np.float64), np.asarray(parent, np.float64)
        if parent.shape != (3, *self.shape) or not np.isfinite(parent).all():
            raise ValueError("Require the matching finite native RGB parent")
        yy, xx = np.indices(self.shape)
        return self.apply(raw - parent[self.colors, yy, xx])
