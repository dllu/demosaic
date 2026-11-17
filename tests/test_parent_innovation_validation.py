"""Validate the delivered fine innovation on A-only RGB, including signed colour."""

from types import SimpleNamespace

import numpy as np
import pytest

from demosaic.experiments.evaluation.withheld import stratified_split
from demosaic.joint_colour_evidence import joint_conditional_scores
from demosaic.local_validated_waves import _wave_columns
from demosaic.neural_nuisance import WithheldBackground
from demosaic.spatial_carrier_amplitudes import SpatialCarrierOperator


def operator_fixture(phases):
    yy, xx = np.indices((64, 64))
    colors = np.tile(np.array(phases).reshape(2, 2), (32, 32))
    mask = stratified_split(colors.shape, 71)
    waves = np.column_stack([_wave_columns(xx, yy, f) for f in [(0.13, 0.08), (-0.09, 0.11)]])
    design = np.column_stack([np.ones(4096), xx.ravel() / 64, yy.ravel() / 64, waves])
    candidate = SimpleNamespace(
        discovery_mask=mask,
        design=design,
        variance_cfa=np.full(colors.shape, 4e-6),
        operators=tuple(np.linalg.pinv(design[(mask & (colors == c)).ravel()]) for c in range(3)),
        wave_slices=((3, 5), (5, 7)),
        unit_slices=((3, 5), (5, 7)),
        unit_keys=((0, 0), (1, 0)),
    )
    amplitudes = np.array(
        [
            [0.003, 0.0002, 0.0018, 0.0001],
            [0.002, -0.0003, -0.00054, -0.00003],
            [0.001, 0.0001, 0.00126, 0.00007],
        ]
    )
    fine = (amplitudes @ waves.T).reshape(3, 64, 64)
    broad = np.array([0.04, 0.05, 0.035])[:, None, None] + np.zeros_like(fine)
    truth = broad + fine
    raw = truth[colors, yy, xx]
    op = SpatialCarrierOperator(candidate, colors, window=33, stride=8, nuisance_mode="global")
    return op, raw, colors, broad, truth


@pytest.mark.parametrize("phases", [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
@pytest.mark.parametrize("perfect_teacher", [False, True])
def test_actual_signed_RGB_innovation_and_nulls_ignore_withheld_values(phases, perfect_teacher):
    op, raw, colors, broad, truth = operator_fixture(phases)
    background = WithheldBackground(truth if perfect_teacher else broad, op.mask)
    predicted = op.predict_parent_innovation(raw, background)
    yy, xx = np.indices(raw.shape)
    delivered = op.components(raw, background.rgb)[1]
    np.testing.assert_allclose(predicted.full_cfa, truth[colors, yy, xx], atol=1e-14)
    np.testing.assert_array_equal(predicted.innovation_cfa, delivered[:, colors, yy, xx])
    for unit in range(2):
        np.testing.assert_array_equal(
            predicted.conditional_null_cfa[unit],
            predicted.full_cfa - delivered[unit, colors, yy, xx],
        )
    if perfect_teacher:
        np.testing.assert_array_equal(predicted.innovation_cfa, 0)
        local, glob = joint_conditional_scores(
            predicted, raw, colors, ~op.mask, window=33, stride=8
        )
        assert not local.any() and not glob.any()
        # A good standalone nuisance predictor can have strong evidence even
        # when the delivered innovation is exactly zero on a good parent.
        _, old = joint_conditional_scores(
            op.predict(raw), raw, colors, ~op.mask, window=33, stride=8
        )
        assert (old > 0).all()
    else:
        np.testing.assert_allclose(delivered.sum(axis=0), truth - broad, atol=1e-14)
        _, glob = joint_conditional_scores(predicted, raw, colors, ~op.mask, window=33, stride=8)
        assert (glob > 0).all()
    damaged = raw.copy()
    damaged[~op.mask] = np.nan
    repeated = op.predict_parent_innovation(damaged, background)
    for name in ["full_cfa", "conditional_null_cfa", "innovation_cfa"]:
        np.testing.assert_array_equal(getattr(predicted, name), getattr(repeated, name))
    with pytest.raises(ValueError, match="matching finite A-only"):
        op.predict_parent_innovation(raw, WithheldBackground(background.rgb, ~op.mask))
