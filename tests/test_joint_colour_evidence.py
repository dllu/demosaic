"""Actual CFA pooled gains, adverse colours, withholding and zero-energy null."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.joint_colour_evidence import joint_conditional_scores
from demosaic.local_validated_waves import conditional_scores


@pytest.mark.parametrize("phases", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
def test_joint_scores_match_direct_pooled_CFA_RSS_and_ignore_nonvalidation_values(phases):
    yy, xx = np.indices((64, 64))
    colors = np.tile(np.array(phases).reshape(2, 2), (32, 32))
    discovery = stratified_split(colors.shape, 107)
    variance = np.array([0.01, 0.025, 0.04])[colors] * (1 + xx / 100)
    full = 0.02 * np.sin(0.23 * xx + 0.13 * yy) * np.array([0.8, 1.2, -0.7])[colors]
    nulls = np.stack([np.zeros_like(full), full * 0.4])
    raw = full + np.random.default_rng(25).normal(size=colors.shape) * np.sqrt(variance)
    candidate = SimpleNamespace(
        full_cfa=full,
        conditional_null_cfa=nulls,
        variance_cfa=variance,
        discovery_mask=discovery,
        unit_keys=((0, 0), (1, 0)),
    )
    local, glob = joint_conditional_scores(candidate, raw, colors, ~discovery, window=33, stride=16)
    for unit in range(2):
        for y, x in [(0, 0), (16, 32), (32, 48), (63, 63)]:
            mask = ~discovery & (abs(yy - y) <= 16) & (abs(xx - x) <= 16)
            gain = (
                ((raw[mask] - nulls[unit, mask]) ** 2 - (raw[mask] - full[mask]) ** 2)
                / variance[mask]
            ).sum()
            energy = (((full[mask] - nulls[unit, mask]) ** 2) / variance[mask]).sum()
            np.testing.assert_allclose(
                local[unit, :, y, x], gain / (2 * np.sqrt(energy)), atol=1e-12
            )
        mask = ~discovery
        gain = (
            ((raw[mask] - nulls[unit, mask]) ** 2 - (raw[mask] - full[mask]) ** 2) / variance[mask]
        ).sum()
        energy = (((full[mask] - nulls[unit, mask]) ** 2) / variance[mask]).sum()
        np.testing.assert_allclose(glob[unit], gain / (2 * np.sqrt(energy)), atol=1e-12)
    damaged = raw.copy()
    damaged[discovery] = np.nan
    repeated = joint_conditional_scores(
        candidate, damaged, colors, ~discovery, window=33, stride=16
    )
    np.testing.assert_array_equal(repeated[0], local)
    np.testing.assert_array_equal(repeated[1], glob)
    relabeled = joint_conditional_scores(
        candidate, raw, 2 - colors, ~discovery, window=33, stride=16
    )
    np.testing.assert_array_equal(relabeled[0], local)
    np.testing.assert_array_equal(relabeled[1], glob)
    np.testing.assert_array_equal(local[:, 0], local[:, 1])
    np.testing.assert_array_equal(local[:, 1], local[:, 2])


def test_adverse_red_prediction_can_reject_a_positive_green_direction():
    colors = np.tile([[0, 1], [1, 2]], (16, 16))
    mask = stratified_split(colors.shape, 19)
    full = np.where(colors == 0, 10.0, 1.0)
    raw = np.where(colors == 0, 0.0, 1.0)
    candidate = SimpleNamespace(
        full_cfa=full,
        conditional_null_cfa=np.zeros((1, *colors.shape)),
        variance_cfa=np.ones_like(raw),
        discovery_mask=mask,
        unit_keys=((0, 0),),
    )
    _, independent = conditional_scores(candidate, raw, colors, ~mask, window=17, stride=8)
    _, joint = joint_conditional_scores(candidate, raw, colors, ~mask, window=17, stride=8)
    assert independent[0, 1] > 0 and independent[0, 0] < 0
    assert (joint < 0).all()


def test_zero_prediction_difference_has_zero_support():
    colors = np.tile([[0, 1], [1, 2]], (16, 16))
    mask = stratified_split(colors.shape, 19)
    candidate = SimpleNamespace(
        full_cfa=np.ones(colors.shape),
        conditional_null_cfa=np.ones((1, *colors.shape)),
        variance_cfa=np.ones(colors.shape),
        discovery_mask=mask,
        unit_keys=((0, 0),),
    )
    local, glob = joint_conditional_scores(
        candidate, np.ones(colors.shape), colors, ~mask, window=17, stride=8
    )
    assert not local.any() and not glob.any()


def test_joint_scores_apply_each_colors_shrinkage_before_pooling():
    colors = np.tile([[0, 1], [1, 2]], (16, 16))
    mask = stratified_split(colors.shape, 21)
    y, x = np.indices(colors.shape)
    null = 0.1 + y / 1000
    full = null + 0.02 * np.cos((x + y) / 3) * np.array([-1.0, 0.5, 1.4])[colors]
    raw = full + 0.005 * np.sin(x)
    raw[mask] = np.nan
    variance = np.array([1e-5, 2e-5, 3e-5])[colors]
    candidate = SimpleNamespace(
        full_cfa=full,
        conditional_null_cfa=null[None],
        variance_cfa=variance,
        discovery_mask=mask,
        unit_keys=((0, 0),),
    )
    reliability = np.array([[0.0, 0.35, 0.8]])
    local, global_scores = joint_conditional_scores(
        candidate,
        raw,
        colors,
        ~mask,
        reliability=reliability,
        window=17,
        stride=8,
    )
    for subset in [~mask, ~mask & (np.abs(y - 16) <= 8) & (np.abs(x - 8) <= 8)]:
        change = (full[subset] - null[subset]) * reliability[0, colors[subset]]
        sigma = np.sqrt(variance[subset])
        whitened = change / sigma
        expected = ((raw[subset] - null[subset]) / sigma) @ whitened / np.linalg.norm(whitened)
        expected -= np.linalg.norm(whitened) / 2
        observed = global_scores[0] if subset.sum() == (~mask).sum() else local[0, :, 16, 8]
        np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-12)
