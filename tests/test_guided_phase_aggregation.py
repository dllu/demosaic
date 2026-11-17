"""Actual measurement-weight parity and cross-object isolation for range guidance."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.guided_phase_aggregation import GuidedPhaseOperator
from demosaic.phase_aggregation import PhaseAggregateConfig, PhaseAggregateOperator

LAYOUTS = ([0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1])
CONFIG = PhaseAggregateConfig(bins=16, window=17, query_stride=8)
SHOT, READ = 1e-4, 1e-8


def scene(layout):
    yy, xx = np.indices((32, 32))
    colors = np.tile(np.asarray(layout).reshape(2, 2), (16, 16))
    candidate = SimpleNamespace(
        discovery_mask=stratified_split(colors.shape, 71),
        frequencies_xy=((3 / 32, 2 / 32), (-2 / 32, 4 / 32)),
        variance_cfa=1e-6 * (1 + (xx + yy) / 32),
        edge_geometry=(0.0, 0.0),
    )
    guide = np.stack(
        [0.01 + (xx + 2 * yy) / 10000, 0.012 + (2 * xx + yy) / 12000, 0.009 + (xx + yy) / 11000]
    )
    raw = (
        0.03
        + 0.001 * np.cos(2 * np.pi * (3 * xx + 2 * yy) / 32)
        + 0.0003 * np.sin(xx * 0.7 + yy * 0.6)
    )
    return candidate, colors, guide, raw


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("direction", [0, 1])
def test_guided_kernel_matches_independent_nonnegative_measurement_weights(layout, direction):
    candidate, colors, guide, raw = scene(layout)
    operator = GuidedPhaseOperator(
        candidate, colors, direction, guide, shot=SHOT, read=READ, config=CONFIG
    )
    actual = operator.apply(raw)
    yy, xx = np.indices(raw.shape)
    y, x = 16, 16
    f = candidate.frequencies_xy[direction]
    phase = np.remainder(xx * f[0] + yy * f[1], 1) * CONFIG.bins

    def assignment(q, sample, kernel):
        qbin, sbin = np.floor(q), np.floor(sample)
        qf, sf = q - qbin, sample - sbin
        return sum(
            (qf if a else 1 - qf) * (sf if b else 1 - sf) * kernel(qbin + a - sbin - b)
            for a in (0, 1)
            for b in (0, 1)
        )

    def pk(delta):
        delta = (delta + CONFIG.bins / 2) % CONFIG.bins - CONFIG.bins / 2
        return np.maximum(0, 3 - np.abs(delta)) / 9

    phase_weight = assignment(phase[y, x], phase, pk)
    for color in range(3):
        # Independent square-root formula, rather than the implementation's
        # cancellation-free equivalent, in two physical noise units per bin.
        g = (np.sqrt(SHOT * guide[color] + READ) - np.sqrt(READ)) / SHOT
        range_weight = assignment(g[y, x], g, lambda d: np.maximum(0, 2 - np.abs(d)) / 4)
        selected = (
            candidate.discovery_mask
            & (colors == color)
            & (xx >= 16)
            & (np.abs(yy - y) <= 8)
            & (np.abs(xx - x) <= 8)
        )
        local = range_weight[selected] / candidate.variance_cfa[selected]
        joint = local * phase_weight[selected]
        assert np.min(local) >= 0 and np.min(joint) >= 0
        expected = (
            np.dot(raw[selected], joint) / joint.sum() - np.dot(raw[selected], local) / local.sum()
        )
        np.testing.assert_allclose(actual[color, y, x], expected, atol=5e-16, rtol=1e-10)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_constant_guide_reduces_to_original_phase_kernel_and_withholding_is_exact(layout):
    candidate, colors, guide, raw = scene(layout)
    guide[:] = 0.03
    guided = GuidedPhaseOperator(candidate, colors, 0, guide, shot=SHOT, read=READ, config=CONFIG)
    original = PhaseAggregateOperator(candidate, colors, 0, CONFIG)
    actual = guided.apply(raw)
    np.testing.assert_allclose(actual, original.apply(raw), atol=2e-15, rtol=1e-10)
    damaged = raw.copy()
    damaged[~candidate.discovery_mask] = np.nan
    np.testing.assert_array_equal(guided.apply(damaged), actual)
    constants = np.array([0.1, 0.3, -0.2])[colors]
    np.testing.assert_allclose(guided.apply(constants), 0, atol=3e-15)
    np.testing.assert_allclose(
        guided.apply(2 * raw - raw**2), 2 * actual - guided.apply(raw**2), atol=3e-15
    )


def test_guide_excludes_different_object_profile_without_tying_color_amplitudes():
    candidate, colors, guide, raw = scene(LAYOUTS[0])
    yy, xx = np.indices(raw.shape)
    guide[:] = np.where(yy < 16, 0.01, 0.2)
    wave = np.cos(2 * np.pi * (3 * xx + 2 * yy) / 32)
    signal = np.where(yy < 16, 0.002 * wave, 0) * np.array([0.7, 1, 1.4])[colors]
    guided = GuidedPhaseOperator(candidate, colors, 0, guide, shot=SHOT, read=READ, config=CONFIG)
    original = PhaseAggregateOperator(candidate, colors, 0, CONFIG)
    result = guided.apply(signal)
    np.testing.assert_allclose(result[:, 16:], 0, atol=1e-16)
    assert np.max(np.abs(original.apply(signal)[:, 16:])) > 1e-4
    assert np.max(np.abs(result[:, :16])) > 1e-4
