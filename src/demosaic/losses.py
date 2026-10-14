"""Reconstruction losses that explicitly measure edge and highlight chroma errors."""

import torch
from torch.nn import functional as F

from .cfa import mosaic
from .color import render


def charbonnier(error):
    return (error.square() + 1e-6).sqrt().mean()


def reconstruction_loss(prediction, batch, auxiliary=None):
    target = batch["target"]
    linear = charbonnier(prediction - target)
    display = render(prediction, batch["wb"], batch["matrix"])
    truth = render(target, batch["wb"], batch["matrix"])
    rendered = charbonnier(display - truth)
    gradient = (
        sum(charbonnier(torch.diff(display, dim=d) - torch.diff(truth, dim=d)) for d in (-1, -2))
        / 2
    )
    # Dilate the saturation region; penalize wrong chroma, including its boundary.
    saturated = (target.amax(1, keepdim=True) > 0.95).float()
    boundary = F.max_pool2d(saturated, 7, 1, 3)
    chroma_error = (display - display.mean(1, keepdim=True)) - (truth - truth.mean(1, keepdim=True))
    highlight = (chroma_error.abs() * boundary).sum() / (boundary.sum() * 3).clamp_min(1)
    sensor = prediction.new_zeros(())
    if auxiliary is not None:
        sensor = charbonnier(auxiliary - mosaic(target, batch["colors"]))
    loss = linear + 0.5 * rendered + 0.1 * gradient + 0.1 * highlight + 0.1 * sensor
    return loss, {
        "linear": linear,
        "rendered": rendered,
        "gradient": gradient,
        "highlight": highlight,
        "sensor": sensor,
    }


def psnr(prediction, target):
    mse = (prediction.float() - target.float()).square().flatten(1).mean(1)
    return -10 * mse.clamp_min(1e-12).log10()
