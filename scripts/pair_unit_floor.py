"""Training-unit reconstruction from retained pre-ADC pair-increment variance."""

import math

import torch


@torch.no_grad()
def pair_units_from_increment_variance(mean_variance, *, floor_DN16):
    """CPU FP32 sqrt/clamp, matching the original cached-unit arithmetic.

    The retained values are original FP32 mean shot-increment variances, before
    the old 16 DN16 clamp. Shared read noise cancels before ADC. These units
    normalize a training loss; they are not restored-RGB covariance, confidence
    or an inference input. A smaller floor changes relative pair weighting.
    Empty sequences represent ordinary unpaired batches. No sampling occurs.
    """
    if not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("Pair-unit floor must be positive and finite")
    value = torch.as_tensor(mean_variance, dtype=torch.float32, device="cpu").detach()
    if value.ndim != 1 or not torch.isfinite(value).all() or (value < 0).any():
        raise ValueError("Expected a finite nonnegative vector of mean increment variances")
    return value.sqrt().clamp_min(floor_DN16 / 65535).reshape(-1, 1, 1, 1)
