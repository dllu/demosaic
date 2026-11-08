"""Fixed-metric local loss geometry; no optimizer step or quality prediction."""

import math

import numpy as np

LABELS = ["baseline", "flat_spatial", "pair_difference", "pair_common", "pair_response"]


def paired_target_response(output, target, pairs):
    """Mean full-target response over disjoint training pairs, in FP64.

    Each pair has its own actual target-difference energy. This is not a
    frequency-band score and carries no inference-time target access.
    """
    import torch

    first, second = pairs.unbind(1)
    if len(first) < 1 or pairs.unique().numel() != pairs.numel():
        raise ValueError("Expected nonempty disjoint pairs")
    delta = (target[first].double() - target[second].double()).detach()
    power = delta.square().sum((1, 2, 3))
    if not torch.isfinite(power).all() or not bool((power > 0).all()):
        raise ValueError("Each pair requires positive finite target-difference energy")
    response = (
        ((output[first].double() - output[second].double()) * delta).sum((1, 2, 3)) / power
    ).mean()
    return response, power


def adam_diagonal(second_moment, step, beta2, epsilon):
    """Positive FP64 inverse RMS using saved, bias-corrected Adam moments.

    This fixes the denominator before a hypothetical update. It omits first
    moments, new second moments, clipping, weight decay and finite-step effects.
    It is a diagnostic metric, not the direction of an actual AdamW step.
    """
    value = np.asarray(second_moment, dtype=np.float64)
    if (
        value.size == 0
        or not np.isfinite(value).all()
        or (value < 0).any()
        or isinstance(step, bool)
        or not math.isfinite(step)
        or step < 1
        or int(step) != step
        or not 0 <= beta2 < 1
        or not math.isfinite(epsilon)
        or epsilon <= 0
    ):
        raise ValueError("Expected finite nonnegative moments and valid Adam denominator state")
    return 1 / (np.sqrt(value / (1 - beta2**step)) + epsilon)


def gram(vectors, diagonal=None):
    """Explicit NumPy FP64 dot products, including zero gradient columns."""
    matrix = np.asarray(vectors, dtype=np.float64)
    if matrix.ndim != 2 or min(matrix.shape) < 1 or not np.isfinite(matrix).all():
        raise ValueError("Expected a nonempty finite gradient matrix")
    weight = np.ones(matrix.shape[1]) if diagonal is None else np.asarray(diagonal, np.float64)
    if weight.shape != (matrix.shape[1],) or not np.isfinite(weight).all() or (weight <= 0).any():
        raise ValueError("Expected a finite positive diagonal matching gradient coordinates")
    result = np.empty((len(matrix), len(matrix)))
    for i in range(len(matrix)):
        for j in range(i, len(matrix)):
            result[i, j] = result[j, i] = np.sum(matrix[i] * matrix[j] * weight, dtype=np.float64)
    return result


def geometry(value):
    """Signed first-order changes under negative baseline/new-term directions.

    A positive response slope increases the training-pair response. A negative
    loss slope decreases the specified loss. Neither is a finite training or
    held-out image-quality result. Null cosines retain exact zero directions.
    """
    g = np.asarray(value, np.float64)
    if g.shape != (5, 5) or not np.isfinite(g).all() or not np.array_equal(g, g.T):
        raise ValueError("Expected a finite symmetric five-component Gram matrix")
    if (g.diagonal() < 0).any():
        raise ValueError("Squared gradient norms must be nonnegative")
    norms = np.sqrt(g.diagonal())
    cosine = [
        [float(g[i, j] / (a * b)) if a > 0 and b > 0 else None for j, b in enumerate(norms)]
        for i, a in enumerate(norms)
    ]
    if any(abs(v) > 1 + 1e-10 for row in cosine for v in row if v is not None):
        raise ValueError("Gram matrix violates Cauchy-Schwarz")
    return {
        "labels": LABELS,
        "norms": dict(zip(LABELS, norms.tolist(), strict=True)),
        "cosines": cosine,
        "spatial_to_baseline_norm": float(norms[1] / norms[0]) if norms[0] else None,
        "directions": {
            name: {
                "pair_difference_loss_slope": float(-g[2] @ direction),
                "spatial_loss_slope": float(-g[1] @ direction),
                "pair_response_slope": float(-g[4] @ direction),
            }
            for name, direction in {
                "negative_baseline": np.array([1, 0, 0, 0, 0]),
                "negative_spatial": np.array([0, 1, 0, 0, 0]),
                "negative_sum": np.array([1, 1, 0, 0, 0]),
            }.items()
        },
    }
