"""Training-only coherent pair response above the unchanged V181 objective."""

import math

import torch
from flat_spatial_objective import objective as previous_objective


def paired_coherent_response_loss(output, target, pairs, *, floor_DN16=1):
    """Bounded response pressure along each pair's actual spatial target change.

    Let t be the clean pair difference after removing each channel's spatial
    mean. The projection error is mean((restored_difference-clean_difference)*t)
    divided by mean(t²)+(floor_DN16/65535)². Apply unit pseudo-Huber per pair,
    then average pairs equally. FP64 reductions avoid weak/DC cancellation.

    The positive energy floor bounds sensitivity as target differences vanish;
    there is no target-amplitude cutoff. Constant pair-color errors and errors
    orthogonal to t remain invisible to this term. All original absolute,
    common, difference and flat terms remain necessary. Targets/pair labels
    enter only after inference; this is not confidence or a noisy-flat guarantee.
    """
    if (
        output.ndim != 4
        or output.shape[1] != 3
        or min(output.shape) < 1
        or target.shape != output.shape
        or not output.is_floating_point()
        or not target.is_floating_point()
        or output.device != target.device
        or not torch.isfinite(output).all()
        or not torch.isfinite(target).all()
    ):
        raise ValueError("Expected matching finite floating-point N x 3 x H x W RGB")
    if isinstance(floor_DN16, bool) or not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("Coherent response floor must be positive and finite")
    indices = torch.as_tensor(pairs, device=output.device)
    if indices.dtype != torch.int64 or indices.ndim != 2 or indices.shape[1] != 2:
        raise ValueError("Expected P x 2 int64 pair indices")
    if len(indices) == 0:
        zero = output.reshape(-1)[0] * 0
        return zero.to(torch.float64 if output.dtype == torch.float64 else torch.float32)
    if (
        indices.min() < 0
        or indices.max() >= len(output)
        or indices.unique().numel() != indices.numel()
    ):
        raise ValueError("Pairs must be disjoint and in range")
    with torch.autocast(output.device.type, enabled=False):
        value, clean = output.double(), target.detach().double()
        first, second = indices.unbind(1)
        delta = clean[first] - clean[second]
        template = delta - delta.mean((-2, -1), keepdim=True)
        error = value[first] - value[second] - delta
        error = error - error.mean((-2, -1), keepdim=True)
        energy = template.square().mean((1, 2, 3)) + (floor_DN16 / 65535) ** 2
        residual = (error * template).mean((1, 2, 3)) / energy
        power = residual.square()
        loss = (power / ((power + 1).sqrt() + 1)).mean()
        return loss.to(torch.float64 if output.dtype == torch.float64 else torch.float32)


def objective(output, frozen, batch, pair_units, domain_weight):
    """Keep all eight V181 terms; add coherent response at weight0.25 per domain."""
    loss, terms, mask = previous_objective(output, frozen, batch, pair_units, domain_weight)
    response = paired_coherent_response_loss(
        output, batch["target"], batch["pair_indices"], floor_DN16=1
    )
    return loss + (0.25 * domain_weight) * response, dict(terms, coherent_response=response), mask
