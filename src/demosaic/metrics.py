"""Per-image, float32 metrics for 16-bit linear and rendered restoration."""

import torch
from torch.nn import functional as F

from .color import render
from .losses import psnr
from .precision import ieee_fp32


def ssim(prediction, target):
    """RGB SSIM, Gaussian 11×11 / sigma 1.5, valid windows, data range 1."""
    axis = torch.arange(-5, 6, device=prediction.device, dtype=torch.float32)
    kernel = torch.exp(-axis.square() / (2 * 1.5**2))
    kernel /= kernel.sum()
    horizontal = kernel[None, None, None].expand(3, 1, 1, 11)
    vertical = kernel[None, None, :, None].expand(3, 1, 11, 1)

    def smooth(x):
        # Reduced-precision TF32 convolution biases small local variances.
        with ieee_fp32():
            return F.conv2d(F.conv2d(x, horizontal, groups=3), vertical, groups=3)

    p, t = prediction.float(), target.float()
    mean_p, mean_t = smooth(p), smooth(t)
    var_p = (smooth(p.square()) - mean_p.square()).clamp_min(0)
    var_t = (smooth(t.square()) - mean_t.square()).clamp_min(0)
    covariance = smooth(p * t) - mean_p * mean_t
    # Enforce Cauchy bounds in numerically flat windows.
    limit = (var_p * var_t).sqrt()
    covariance = torch.maximum(torch.minimum(covariance, limit), -limit)
    score = ((2 * mean_p * mean_t + 0.01**2) * (2 * covariance + 0.03**2)) / (
        (mean_p.square() + mean_t.square() + 0.01**2) * (var_p + var_t + 0.03**2)
    )
    return score.flatten(1).mean(1)


def _masked_mean(values, mask):
    denominator = mask.flatten(1).sum(1) * values.shape[1]
    result = (values * mask).flatten(1).sum(1) / denominator.clamp_min(1)
    return torch.where(denominator > 0, result, result.new_full((), float("nan")))


def quality_metrics(prediction, target, wb, matrix):
    linear = prediction.float().clamp(0, 1)
    sensor_target = target.float().clamp(0, 1)
    display, truth = render(prediction.float(), wb, matrix), render(target, wb, matrix)
    error = display - truth
    chroma = error - error.mean(1, keepdim=True)
    clipped = (truth.amax(1, keepdim=True) >= 0.98).float()
    dilated = F.max_pool2d(clipped, 7, 1, 3)
    eroded = 1 - F.max_pool2d(1 - clipped, 7, 1, 3)
    ring = dilated - eroded
    shadow = (target.mean(1, keepdim=True) < 0.02).float()
    shadow_mse = _masked_mean((linear - sensor_target).square(), shadow)
    return {
        "linear_psnr": psnr(linear, sensor_target),
        "srgb_psnr": psnr(display, truth),
        "srgb_ssim": ssim(display, truth),
        "chroma_mae": chroma.abs().flatten(1).mean(1),
        "gradient_mae": sum(
            (torch.diff(display, dim=d) - torch.diff(truth, dim=d)).abs().flatten(1).mean(1)
            for d in (-1, -2)
        )
        / 2,
        "highlight_boundary_chroma_mae": _masked_mean(chroma.abs(), ring),
        "highlight_boundary_rgb_mae": _masked_mean(error.abs(), ring),
        "shadow_linear_psnr": -10 * shadow_mse.clamp_min(1e-12).log10(),
    }
