"""Conditional error moments from independent noisy observations of one target."""

import numpy as np


def error_moments(predictions, target):
    """Separate conditional bias energy and output variance without clipping.

    The first dimension indexes independent input-noise draws. The finite-draw
    squared mean error includes variance/K; subtract that term to estimate
    squared conditional bias. This unbiased estimate can be negative and is
    deliberately retained. These are conditional-noise diagnostics, not source
    population uncertainty or a single-input inference method.
    """
    predictions = np.asarray(predictions, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if predictions.ndim < 2 or predictions.shape[0] < 2 or predictions.shape[1:] != target.shape:
        raise ValueError("Need at least two draws with a common, matching target")
    if not predictions.size or not np.isfinite(predictions).all() or not np.isfinite(target).all():
        raise ValueError("Conditional moments require nonempty finite arrays")
    count = predictions.shape[0]
    error = predictions - target
    mean_error = error.mean(axis=0)
    mean_error_energy = float(np.mean(mean_error**2))
    variance = float(np.mean(np.sum((error - mean_error) ** 2, axis=0) / (count - 1)))
    bias = mean_error_energy - variance / count
    mse = float(np.mean(error**2))
    return {
        "draws": count,
        "empirical_per_draw_MSE": mse,
        "squared_mean_error": mean_error_energy,
        "unbiased_output_variance": variance,
        "finite_draw_variance_correction": variance / count,
        "unbiased_squared_conditional_bias": bias,
        "MSE_decomposition_error": abs(mse - bias - variance),
    }
