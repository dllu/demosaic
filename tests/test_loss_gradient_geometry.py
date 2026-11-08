"""Analytic counterexamples and local directional-derivative contracts."""

import numpy as np
import pytest
from loss_gradient_geometry import adam_diagonal, geometry, gram


def test_positive_diagonal_can_reverse_unweighted_conflict():
    vectors = np.array([[1, 1], [2, -1], [0, 0], [0, 0], [1, 0]], float)
    ordinary = gram(vectors)
    weighted = gram(vectors, [1, 10])
    assert ordinary[0, 1] == 1
    assert weighted[0, 1] == -8
    assert geometry(ordinary)["cosines"][0][1] > 0
    assert geometry(weighted)["cosines"][0][1] < 0
    assert geometry(weighted)["cosines"][2][2] is None


def test_known_directional_derivatives_and_sum_without_normalizing():
    vectors = np.array([[1, 2, 3], [-2, 1, 1], [1, 0, 2], [0, 0, 0], [2, -3, 1]], float)
    weights = np.array([0.25, 4, 2])
    actual = geometry(gram(vectors, weights))
    for name, direction in [
        ("negative_baseline", -weights * vectors[0]),
        ("negative_spatial", -weights * vectors[1]),
        ("negative_sum", -weights * (vectors[0] + vectors[1])),
    ]:
        for field, row in [
            ("pair_difference_loss_slope", 2),
            ("spatial_loss_slope", 1),
            ("pair_response_slope", 4),
        ]:
            assert actual["directions"][name][field] == pytest.approx(vectors[row] @ direction)
    # A positive response derivative is beneficial for this response functional,
    # whereas a negative paired-loss derivative reduces that loss.
    assert actual["directions"]["negative_spatial"]["pair_response_slope"] > 0


def test_adam_denominator_bias_correction_and_zero_variance():
    np.testing.assert_array_equal(adam_diagonal([0, 3 / 4], 2, 0.5, 1), [1, 0.5])
    assert adam_diagonal([0], 1800, 0.999, 1e-8)[0] == 1e8


@pytest.mark.parametrize(
    "second,step,beta,eps",
    [
        ([-1], 1, 0.9, 1e-8),
        ([np.nan], 1, 0.9, 1e-8),
        ([1], 0, 0.9, 1e-8),
        ([1], True, 0.9, 1e-8),
        ([1], 1.5, 0.9, 1e-8),
        ([1], 1, 1, 1e-8),
        ([1], 1, 0.9, 0),
    ],
)
def test_invalid_adam_state_rejected(second, step, beta, eps):
    with pytest.raises(ValueError):
        adam_diagonal(second, step, beta, eps)


@pytest.mark.parametrize(
    "matrix,weights",
    [
        ([], None),
        ([[np.inf]], None),
        ([[1, 2]], [1]),
        ([[1]], [0]),
        ([[1]], [-1]),
        ([[1]], [np.nan]),
    ],
)
def test_invalid_gradient_or_metric_rejected(matrix, weights):
    with pytest.raises(ValueError):
        gram(matrix, weights)


def test_scaling_changes_norms_and_slopes_without_changing_cosines():
    vectors = np.arange(15).reshape(5, 3) - 7
    a, b = geometry(gram(vectors)), geometry(gram(3 * vectors))
    np.testing.assert_allclose(a["cosines"], b["cosines"])
    for key in a["norms"]:
        assert b["norms"][key] == pytest.approx(3 * a["norms"][key])
    for key in a["directions"]["negative_sum"]:
        assert b["directions"]["negative_sum"][key] == pytest.approx(
            9 * a["directions"]["negative_sum"][key]
        )


def test_invalid_gram_rejected_instead_of_hiding_impossible_cosines():
    g = np.eye(5)
    g[0, 1] = g[1, 0] = 2
    with pytest.raises(ValueError):
        geometry(g)


def test_training_pair_response_normalizes_each_pair_and_detaches_targets():
    import torch
    from loss_gradient_geometry import paired_target_response

    target = torch.zeros((4, 3, 2, 3), dtype=torch.float32)
    target[0] = 2
    target[2] = 0.25
    target.requires_grad_()
    output = torch.zeros_like(target)
    output[0] = 1
    output[2] = 0.375
    output.requires_grad_()
    response, energies = paired_target_response(output, target, torch.tensor([[0, 1], [2, 3]]))
    assert response.dtype == torch.float64 and response.item() == 1
    np.testing.assert_array_equal(energies.numpy(), [72, 1.125])
    derivative, clean = torch.autograd.grad(response, (output, target), allow_unused=True)
    expected = torch.empty_like(output)
    expected[0], expected[1], expected[2], expected[3] = 1 / 72, -1 / 72, 1 / 9, -1 / 9
    torch.testing.assert_close(derivative, expected)
    assert clean is None


@pytest.mark.parametrize("pairs", [[[0, 1]], [[0, 1], [1, 2]]])
def test_zero_energy_or_overlapping_pairs_rejected(pairs):
    import torch
    from loss_gradient_geometry import paired_target_response

    a = torch.zeros((3, 3, 2, 2))
    with pytest.raises(ValueError):
        paired_target_response(a, a, torch.tensor(pairs))


def test_actual_checked_gram_entry_matches_cancellation_and_diagonal():
    from probe_flat_spatial_loss_geometry import checked_gram

    a = np.array([[1e8, 1, 1e8], [1e8, 2, -1e8], [0, 0, 0]], dtype=np.float32)
    actual, ratio = checked_gram(a, np.array([1, 4, 1]))
    assert actual[0, 1] == 8 and ratio <= 1
