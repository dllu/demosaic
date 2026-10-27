from itertools import combinations

import numpy as np
import pytest

from demosaic.conditional_bias import error_moments
from demosaic.conditional_gradient import gradient_projections


@pytest.mark.parametrize("draws", [3, 4, 8])
def test_squared_loss_preserves_bias_and_reduces_variance_weight_by_half_alpha(draws):
    rng = np.random.default_rng(2026)
    target = rng.uniform(0.1, 0.8, (3, 5))
    values = target + rng.normal(0.1, 0.3, (draws, 3, 5))
    errors = values - target
    means = np.stack([(errors[i] + errors[j]) / 2 for i, j in combinations(range(draws), 2)])
    result = gradient_projections(values, target, errors, means)
    moments = error_moments(values, target)
    control = result["projections"]["control"]
    mixture = result["projections"]["mixture"]
    np.testing.assert_allclose(
        control["heldout_bias_projection"], moments["unbiased_squared_conditional_bias"], atol=1e-16
    )
    np.testing.assert_allclose(
        control["noise_covariance_projection"], moments["unbiased_output_variance"], atol=1e-16
    )
    np.testing.assert_allclose(
        mixture["heldout_bias_projection"], control["heldout_bias_projection"], atol=1e-16
    )
    np.testing.assert_allclose(
        mixture["noise_covariance_projection"],
        0.875 * moments["unbiased_output_variance"],
        atol=1e-16,
    )


def test_negative_finite_sample_bias_projection_is_preserved():
    values = np.array([[-1.0], [-1.0], [1.0], [1.0]])
    pairs = np.stack([(values[i] + values[j]) / 2 for i, j in combinations(range(4), 2)])
    result = gradient_projections(values, np.zeros(1), values, pairs)
    assert result["projections"]["control"]["heldout_bias_projection"] == pytest.approx(-1 / 3)


def test_nonlinear_gradient_crossfit_matches_explicit_independent_heldout_products():
    rng = np.random.default_rng(8)
    values = rng.normal(size=(8, 7))
    target = np.full(7, 0.2)
    single = np.tanh(values - target)
    pair = np.stack(
        [np.tanh((values[i] + values[j]) / 2 - target) for i, j in combinations(range(8), 2)]
    )
    result = gradient_projections(values, target, single, pair)
    control_bias, mean_bias = [], []
    for n, (i, j) in enumerate(combinations(range(8), 2)):
        independent = [k for k in range(8) if k not in (i, j)]
        heldout = (values[independent] - target).mean(axis=0)
        control_bias.append(np.mean((single[i] + single[j]) / 2 * heldout))
        mean_bias.append(np.mean(pair[n] * heldout))
    assert result["projections"]["control"]["heldout_bias_projection"] == pytest.approx(
        np.mean(control_bias)
    )
    assert result["projections"]["mean"]["heldout_bias_projection"] == pytest.approx(
        np.mean(mean_bias)
    )
    for terms in result["projections"].values():
        assert terms["decomposition_error"] < 1e-15


def test_component_projections_are_additive():
    rng = np.random.default_rng(9)
    values = rng.normal(size=(8, 4))
    target = np.ones(4)
    gradients = rng.normal(size=(2, 8, 4))
    means = rng.normal(size=(2, 28, 4))
    parts = [gradient_projections(values, target, gradients[k], means[k]) for k in range(2)]
    total = gradient_projections(values, target, gradients.sum(0), means.sum(0))
    for objective in ["control", "mean", "mixture"]:
        for field in ["heldout_bias_projection", "noise_covariance_projection"]:
            assert total["projections"][objective][field] == pytest.approx(
                sum(p["projections"][objective][field] for p in parts)
            )


@pytest.mark.parametrize("change", ["short", "shape", "pairs", "nan", "weight"])
def test_invalid_groups_are_rejected(change):
    values = np.zeros((8, 3))
    target = np.zeros(3)
    single = np.zeros_like(values)
    pair = np.zeros((28, 3))
    weight = 0.25
    if change == "short":
        values, single = values[:2], single[:2]
    elif change == "shape":
        target = target[:2]
    elif change == "pairs":
        pair = pair[:27]
    elif change == "nan":
        pair[0, 0] = np.nan
    else:
        weight = True
    with pytest.raises(ValueError):
        gradient_projections(values, target, single, pair, weight=weight)
