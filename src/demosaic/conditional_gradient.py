"""Cross-fitted output-gradient projections from retained independent draws."""

from itertools import combinations

import numpy as np


def gradient_projections(predictions, target, single_gradients, pair_mean_gradients, weight=0.25):
    """Separate held-out error alignment from same-draw gradient covariance.

    Gradients are derivatives of one image's loss. The pair-mean gradient is
    dL(mean(pred_i,pred_j))/d(mean), in canonical unordered-pair order. Other
    draws estimate error independently of the two draws producing a gradient.
    These are output-space diagnostics, not neural parameter updates.
    """
    predictions, target, single, pair = (
        np.asarray(value, dtype=np.float64)
        for value in (predictions, target, single_gradients, pair_mean_gradients)
    )
    if (
        predictions.ndim < 2
        or predictions.shape[0] < 3
        or predictions.shape[1:] != target.shape
        or not target.size
        or single.shape != predictions.shape
    ):
        raise ValueError("Need at least three finite draws and matching targets/gradients")
    count = len(predictions)
    pairs = np.array(list(combinations(range(count), 2)))
    if pair.shape != (len(pairs), *target.shape):
        raise ValueError("Pair gradients must follow all canonical unordered pairs")
    if any(not np.isfinite(value).all() for value in (predictions, target, single, pair)):
        raise ValueError("Gradient projections require finite arrays")
    if isinstance(weight, bool) or not np.isfinite(weight) or not 0 <= weight <= 1:
        raise ValueError("Mean-gradient weight must be finite and in [0,1]")
    error = predictions - target
    a, b = pairs.T
    pair_error = (error[a] + error[b]) * 0.5
    heldout_error = (error.sum(axis=0) - error[a] - error[b]) / (count - 2)
    control_common = (single[a] + single[b]) * 0.5
    control_bias = float(np.mean(control_common * heldout_error))
    mean_bias = float(np.mean(pair * heldout_error))
    control_self = float(np.mean(single * error))
    mean_self = float(np.mean(pair * pair_error))
    target_energy = float(np.mean(target**2))
    control_force = -float(np.mean(single.mean(axis=0) * target))
    mean_force = -float(np.mean(pair.mean(axis=0) * target))
    control_noise = control_self - control_bias
    mean_noise = mean_self - mean_bias
    pressure = {}
    for name, mix in (("control", 0.0), ("mean", 1.0), ("mixture", float(weight))):
        bias = (1 - mix) * control_bias + mix * mean_bias
        noise = (1 - mix) * control_noise + mix * mean_noise
        same_view = (1 - mix) * control_self + mix * mean_self
        force = (1 - mix) * control_force + mix * mean_force
        pressure[name] = {
            "heldout_bias_projection": bias,
            "noise_covariance_projection": noise,
            "same_view_error_projection": same_view,
            "negative_gradient_target_projection": force,
            "target_coefficient_gain_slope": force / target_energy if target_energy else None,
            "decomposition_error": abs(same_view - bias - noise),
        }
    return {
        "draws": count,
        "unordered_pairs": len(pairs),
        "heldout_draws_per_pair": count - 2,
        "coordinates": target.size,
        "mean_loss_weight": float(weight),
        "target_mean_squared_coefficient": target_energy,
        "projections": pressure,
        "bias_projection_change": pressure["mixture"]["heldout_bias_projection"] - control_bias,
        "noise_projection_change": pressure["mixture"]["noise_covariance_projection"]
        - control_noise,
    }
