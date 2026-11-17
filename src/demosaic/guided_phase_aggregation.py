"""A-only neural range guidance for same-color native phase measurements.

The extra range coordinate is a physical variance-stabilized own-color neural
prediction. Nonnegative linear bin assignment and fixed range smoothing retain
normalized measurement averages; their phase-minus-local difference is signed.
"""

import numpy as np
from scipy.ndimage import convolve1d, map_coordinates

from .phase_aggregation import PhaseAggregateConfig, PhaseAggregateOperator

_DEFAULT = PhaseAggregateConfig()


class GuidedPhaseOperator(PhaseAggregateOperator):
    """Fixed phase/range/spatial histogram, reading only declared A measurements."""

    def __init__(self, candidate, colors, direction, guide_rgb, *, shot, read, config=_DEFAULT):
        guide = np.asarray(guide_rgb, np.float64)
        if (
            guide.shape != (3, *candidate.discovery_mask.shape)
            or not np.isfinite(guide).all()
            or not np.isfinite([shot, read]).all()
            or min(shot, read) < 0
            or shot + read == 0
        ):
            raise ValueError("Require a finite A-only RGB guide and positive physical noise")
        # The primitive builds groups through virtual histogram/query methods.
        # Initialize guidance before calling it; no RAW or parent enters here.
        guide = np.clip(guide, 0, 1)
        if shot:
            denominator = np.sqrt(shot * guide + read) + np.sqrt(read)
            transformed = np.divide(
                2 * guide, denominator, out=np.zeros_like(guide), where=denominator > 0
            )
        else:
            transformed = guide / np.sqrt(read)
        self.range_coordinate = transformed / 2  # Fixed two physical noise units per bin.
        self.range_bins = int(np.ceil(self.range_coordinate.max())) + 2
        if self.range_bins > 512:
            raise ValueError("Range guidance supports at most512 bins at the fixed noise spacing")
        super().__init__(candidate, colors, direction, config)

    def _histogram(self, group, values):
        self._active_group = group
        if "query_indices" not in group:
            indices = group["indices"]
            yy, xx = np.unravel_index(indices, self.shape)
            radius = self.config.window // 2
            group["query_indices"] = [
                np.flatnonzero((np.abs(yy - y) <= radius) & (np.abs(xx - x) <= radius))
                for y in self.ay
                for x in self.ax
            ]
            range_value = self.range_coordinate[group["color"]].ravel()[indices]
            lower, fraction = np.floor(range_value).astype(np.int64), range_value % 1
            phase, phase_fraction = group["lower"], group["fraction"]
            group["joint_bins"] = np.stack(
                [
                    ((phase + p) % self.config.bins) * self.range_bins + lower + g
                    for p in (0, 1)
                    for g in (0, 1)
                ]
            )
            group["joint_weights"] = np.stack(
                [
                    (phase_fraction if p else 1 - phase_fraction)
                    * (fraction if g else 1 - fraction)
                    for p in (0, 1)
                    for g in (0, 1)
                ]
            )
            group["coordinates"] = np.concatenate(
                [
                    self.coordinates[:1],
                    self.range_coordinate[group["color"]][None],
                    self.spatial_coordinates,
                ]
            )
        value = np.asarray(values) * group["weight"]
        bins, weights = group["joint_bins"], group["joint_weights"]
        histogram = np.empty((self.config.bins * self.range_bins, len(self.ay) * len(self.ax)))
        for column, selected in enumerate(group["query_indices"]):
            histogram[:, column] = np.bincount(
                bins[:, selected].ravel(),
                weights=(weights[:, selected] * value[selected]).ravel(),
                minlength=self.config.bins * self.range_bins,
            )
        return histogram.reshape(self.config.bins, self.range_bins, len(self.ay), len(self.ax))

    def _phase_query(self, histogram):
        # Called during base initialization, where only the current group owns
        # this histogram. Its guide coordinate differs by CFA color only.
        smooth = (
            sum(
                weight * np.roll(histogram, offset, axis=0)
                for offset, weight in zip(range(-2, 3), (1, 2, 3, 2, 1), strict=True)
            )
            / 9
        )
        smooth = convolve1d(smooth, [0.25, 0.5, 0.25], axis=1, mode="constant", cval=0)
        periodic = np.concatenate([smooth, smooth[:1]], axis=0)
        return map_coordinates(
            periodic, self._active_group["coordinates"], order=1, prefilter=False, mode="nearest"
        )

    def _spatial_query(self, histogram):
        smooth = convolve1d(histogram, [0.25, 0.5, 0.25], axis=0, mode="constant", cval=0)
        return map_coordinates(
            smooth, self._active_group["coordinates"][1:], order=1, prefilter=False, mode="nearest"
        )
