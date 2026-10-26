import numpy as np
import pytest

from demosaic.conditional_bias import error_moments


def test_conditional_decomposition_matches_independent_cross_draw_products():
    samples = np.array([[1.0, 2.0, 3.0], [2.0, -1.0, 4.0], [-1.0, 3.0, 5.0], [3.0, 0.0, 1.0]])
    target = np.array([0.5, 1.0, 2.0])
    result = error_moments(samples, target)
    errors = samples - target
    pairs = [
        float(np.mean(a * b)) for i, a in enumerate(errors) for j, b in enumerate(errors) if i != j
    ]
    assert result["unbiased_squared_conditional_bias"] == pytest.approx(np.mean(pairs), abs=1e-14)
    assert result["MSE_decomposition_error"] < 1e-14
    assert result["empirical_per_draw_MSE"] == pytest.approx(np.mean(errors**2))


def test_symmetric_finite_sample_bias_estimate_is_not_clamped():
    result = error_moments(np.array([[1.0], [-1.0]]), np.array([0.0]))
    assert result["squared_mean_error"] == 0
    assert result["unbiased_output_variance"] == 2
    assert result["unbiased_squared_conditional_bias"] == -1
    assert result["empirical_per_draw_MSE"] == 1


def test_deterministic_bias_and_exact_target_have_zero_variance():
    target = np.arange(6).reshape(2, 3) / 10
    for bias in [0.0, 0.03]:
        result = error_moments(np.stack([target + bias] * 8), target)
        assert result["unbiased_output_variance"] < 1e-30
        assert result["unbiased_squared_conditional_bias"] == pytest.approx(bias**2)


@pytest.mark.parametrize(
    "samples,target",
    [
        (np.zeros((1, 3)), np.zeros(3)),
        (np.zeros((2, 3)), np.zeros(2)),
        (np.zeros((2, 0)), np.zeros(0)),
        (np.array([[np.nan], [0]]), np.zeros(1)),
        (np.zeros((2, 1)), np.array([np.inf])),
    ],
)
def test_invalid_draw_groups_rejected(samples, target):
    with pytest.raises(ValueError):
        error_moments(samples, target)
