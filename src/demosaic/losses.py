"""Reconstruction losses that explicitly measure edge and highlight chroma errors."""

import torch
from torch.nn import functional as F

from .cfa import mosaic
from .color import render


def charbonnier(error):
    return (error.square() + 1e-6).sqrt().mean()


def noise_normalized_sensor_loss(prediction, batch, rendered_reference):
    """Measure observed-CFA error in units of the *clean* sensor standard deviation.

    Absolute reconstruction errors can give weak gradients to deep shadows.
    Clean-target variance avoids weighting by positive noisy tails. Exclude
    reconstructed/clipped highlights and ADC-only draws; keep their original
    reconstruction losses. The variance floor bounds near-zero-noise gradients.
    """
    target = batch["target"].float()
    colors = batch["colors"]
    sampled = mosaic(target, colors)
    variance = batch["shot"] * sampled.clamp_min(0) + batch["read"]
    valid = (target >= 0) & (target < 0.98) & (rendered_reference.amax(1, keepdim=True) < 0.98)
    valid = mosaic(valid, colors) & ((batch["shot"] > 0) | (batch["read"] > 0))
    error = (mosaic(prediction.float(), colors) - sampled) / variance.clamp_min(1e-8).sqrt()
    penalty = (error.square() + 1e-6).sqrt()
    return penalty.masked_fill(~valid, 0).sum() / valid.sum().clamp_min(1)


def reconstruction_loss(
    prediction, batch, auxiliary=None, *, physical_fp32=True, normalized_sensor_weight=0.0
):
    if normalized_sensor_weight < 0:
        raise ValueError("Normalized sensor loss weight must be nonnegative")
    target = batch["target"]
    linear = charbonnier(prediction - target)
    display = render(prediction, batch["wb"], batch["matrix"], fp32=physical_fp32)
    truth = render(target, batch["wb"], batch["matrix"], fp32=physical_fp32)
    rendered = charbonnier(display - truth)
    gradient = (
        sum(charbonnier(torch.diff(display, dim=d) - torch.diff(truth, dim=d)) for d in (-1, -2))
        / 2
    )
    # Dilate the saturation region; penalize wrong chroma, including its boundary.
    saturated = (truth.amax(1, keepdim=True) > 0.98).float()
    boundary = F.max_pool2d(saturated, 7, 1, 3)
    chroma_error = (display - display.mean(1, keepdim=True)) - (truth - truth.mean(1, keepdim=True))
    highlight = (chroma_error.abs() * boundary).sum() / (boundary.sum() * 3).clamp_min(1)
    sensor = prediction.new_zeros(())
    if auxiliary is not None:
        sensor = charbonnier(auxiliary - mosaic(target, batch["colors"]))
    loss = linear + 0.5 * rendered + 0.1 * gradient + 0.1 * highlight + 0.1 * sensor
    terms = {
        "linear": linear,
        "rendered": rendered,
        "gradient": gradient,
        "highlight": highlight,
        "sensor": sensor,
    }
    if normalized_sensor_weight:
        normalized = noise_normalized_sensor_loss(prediction, batch, truth)
        loss = loss + normalized_sensor_weight * normalized
        terms["normalized_sensor"] = normalized
    return loss, terms


def psnr(prediction, target):
    mse = (prediction.float() - target.float()).square().flatten(1).mean(1)
    return -10 * mse.clamp_min(1e-12).log10()
