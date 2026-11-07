"""Training-only absolute supervision of error shared by a counterfactual pair."""

import math

import torch


def paired_common_error_loss(output, target, pairs, *, unit_DN16=16):
    """Pseudo-Huber of the average RGB error of disjoint aligned pair members.

    The difference loss cannot see e_a=e_b. This term supervises (e_a+e_b)/2
    against zero, retaining the actual, potentially different targets. Conversely
    it cannot see e_a=-e_b; difference and ordinary reconstruction losses stay
    necessary. Fixed DN16 units are training weights, not covariance estimates.
    Shared sensor noise need not cancel in this average. No target or pair label
    enters inference, and this empirical loss gives no flat-field guarantee.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape) < 1
        or target.shape != output.shape
        or not output.is_floating_point()
        or not target.is_floating_point()
    ):
        raise ValueError("Expected matching nonempty floating-point N x 3 x H x W RGB")
    if output.device != target.device:
        raise ValueError("Output and target must share a device")
    if not math.isfinite(unit_DN16) or unit_DN16 <= 0:
        raise ValueError("Common-error units must be positive and finite")
    indices = torch.as_tensor(pairs, device=output.device)
    if indices.dtype != torch.int64 or indices.ndim != 2 or indices.shape[1] != 2 or len(indices) < 1:
        raise ValueError("Expected nonempty P x 2 int64 pair indices")
    if indices.min() < 0 or indices.max() >= len(output) or indices.unique().numel() != indices.numel():
        raise ValueError("Pair members must be distinct and in range")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        error = output.to(dtype) - target.detach().to(dtype)
        first, second = indices.unbind(1)
        residual = (error[first] + error[second]) / (2 * unit_DN16 / 65535)
        power = residual.square()
        return (power / ((power + 1).sqrt() + 1)).mean()
