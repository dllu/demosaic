"""Independent window enumeration and corruption rejection for the native audit."""

import copy

import numpy as np
import pytest
from audit_flat_spatial_loss_geometry import flat_fields, inspect_geometry
from loss_gradient_geometry import geometry, gram


@pytest.mark.parametrize("window", [3, 17])
def test_prefix_sums_and_separable_extrema_match_explicit_windows(window):
    rng = np.random.default_rng(18201)
    target = (0.002 + rng.normal(0, 0.025 / 65535, (2, 3, 5, 7))).astype(np.float32)
    if window == 3:
        target[0, 2, 1, 2] += 4 / 65535
    output = (target + rng.normal(3 / 65535, 2 / 65535, target.shape)).astype(np.float32)
    expected_mask = np.zeros((2, 1, 5, 7), bool)
    expected_loss = 0.0
    for b in range(2):
        for y in range(5):
            for x in range(7):
                ys = slice(max(0, y - window // 2), min(5, y + window // 2 + 1))
                xs = slice(max(0, x - window // 2), min(7, x + window // 2 + 1))
                clean = target[b, :, ys, xs]
                selected = np.all(
                    np.max(clean, axis=(1, 2)) - np.min(clean, axis=(1, 2)) <= np.float32(1 / 65535)
                )
                expected_mask[b, 0, y, x] = selected
                error = (output[b, :, ys, xs].astype(np.float64) - clean.astype(np.float64)) / (
                    4 / 65535
                )
                variance = np.mean(
                    (error - error.mean(axis=(1, 2), keepdims=True)) ** 2, axis=(1, 2)
                )
                expected_loss += selected * np.sum(np.sqrt(1 + variance) - 1) / output.size
    mask, loss = flat_fields(output, target, window)
    np.testing.assert_array_equal(mask, expected_mask)
    assert loss == pytest.approx(expected_loss, rel=1e-12, abs=1e-14)
    assert loss > 0 and mask.any()
    if window == 3:
        assert not mask.all()


def test_independent_spatial_measurement_removes_per_channel_constant_error():
    target = np.zeros((1, 3, 4, 7), np.float32)
    output = target + np.array([0.125, -0.25, 0.0625], np.float32)[None, :, None, None]
    mask, loss = flat_fields(output, target)
    assert mask.all() and loss == 0


def test_auditor_rejects_wrong_signed_derivative():
    vectors = np.arange(15).reshape(5, 3) - 7
    g = gram(vectors)
    correct = geometry(g)
    inspect_geometry(g, correct)
    corrupted = copy.deepcopy(correct)
    corrupted["directions"]["negative_spatial"]["pair_response_slope"] *= -1
    with pytest.raises(AssertionError):
        inspect_geometry(g, corrupted)
