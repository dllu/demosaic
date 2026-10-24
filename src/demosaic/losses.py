"""Reconstruction losses that explicitly measure edge and highlight chroma errors."""

import math
from functools import partial

import torch
from torch.nn import functional as F

from .cfa import mosaic
from .color import render
from .detail_loss import normalized_band_loss, validate_normalized_band_weight
from .precision import ieee_fp32

DEFAULT_RECONSTRUCTION_EPSILON = 1e-3


def validate_reconstruction_epsilon(value):
    try:
        epsilon = float(value)
    except (TypeError, ValueError):
        raise ValueError("Reconstruction epsilon must be finite and positive") from None
    limits = torch.finfo(torch.float32)
    squared = epsilon * epsilon
    if (
        isinstance(value, bool)
        or not math.isfinite(epsilon)
        or epsilon <= 0
        or not limits.tiny <= squared <= limits.max
    ):
        raise ValueError("Reconstruction epsilon must be positive with a finite normal FP32 square")
    return epsilon


def charbonnier(error, *, epsilon=DEFAULT_RECONSTRUCTION_EPSILON):
    return (error.square() + epsilon**2).sqrt().mean()


def validate_reconstruction_objective(value):
    if value not in ("charbonnier-v1", "image-log-mse-v1"):
        raise ValueError("Unknown reconstruction objective")
    return value


def validate_camera_supervision(value):
    if value not in ("reference-white-v1", "sensor-valid-v1"):
        raise ValueError("Unknown camera supervision convention")
    return value


def masked_reconstruction(error, valid, objective, *, epsilon=DEFAULT_RECONSTRUCTION_EPSILON):
    if objective == "image-log-mse-v1":
        return image_log_mse(error, valid)
    valid = valid.expand_as(error)
    error = error.float().masked_fill(~valid, 0)
    return (error.square() + epsilon**2).sqrt().masked_fill(
        ~valid, 0
    ).sum() / valid.sum().clamp_min(1)


def reference_white_interval_loss(prediction, batch):
    """Keep training gradients before display clipping without fitting latent white.

    Interior linear-sRGB reference values are exact; clipped black/white encode
    upper/lower bounds. The ordinary preview/display transform stays unchanged.
    """
    with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
        wb, matrix = batch["wb"].float(), batch["matrix"].float()
        value = torch.einsum("bij,bjhw->bihw", matrix, prediction.float() * wb[..., None, None])
        reference = torch.einsum(
            "bij,bjhw->bihw", matrix, batch["target"].float() * wb[..., None, None]
        )
        error = torch.where(
            reference >= 1 - 1e-6,
            (value - 1).clamp_max(0),
            torch.where(reference <= 1e-6, value.clamp_min(0), value - reference),
        )
        return charbonnier(error)


def image_log_mse(error, valid=None):
    """Mean negative PSNR, with a fixed 100dB floor and per-image mask counts.

    Images with no valid samples contribute neither value nor gradient. The
    mask is observation/reference validity, never derived from prediction error.
    """
    with torch.autocast(device_type=error.device.type, enabled=False), ieee_fp32():
        if valid is None:
            mse = error.float().square().flatten(1).mean(1)
            return (10 * mse.clamp_min(1e-10).log10()).mean()
        valid = valid.expand_as(error)
        count = valid.flatten(1).sum(1)
        mse = error.float().masked_fill(~valid, 0).square().flatten(1).sum(1) / count.clamp_min(1)
        values = 10 * mse.clamp_min(1e-10).log10()
        return values.masked_fill(count == 0, 0).sum() / (count > 0).sum().clamp_min(1)


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


def multiscale_sensor_loss(prediction, batch, rendered_reference=None):
    """Measure pooled CFA error in input-noise units at 8/32/64 sensor pixels.

    A block sums independent *input* variances, not posterior restoration
    covariance. Real targets contain measured reference CFA samples only;
    synthetic targets are sampled at the same CFA phases. Reject blocks with
    any invalid reference samples and omit ADC-only observations. Reference
    shot/read noise remains a limitation of real pairs.
    """
    with torch.autocast(device_type=prediction.device.type, enabled=False), ieee_fp32():
        colors = batch["colors"]
        if "sensor_reference" in batch:
            reference = mosaic(batch["sensor_reference"].float(), colors)
            valid = mosaic(batch["sensor_mask"].bool(), colors)
        else:
            target = batch["target"].float()
            reference = mosaic(target, colors)
            truth = rendered_reference
            if truth is None:
                truth = render(target, batch["wb"], batch["matrix"])
            valid = mosaic(
                (target >= 0) & (target < 0.98) & (truth.amax(1, keepdim=True) < 0.98),
                colors,
            )
        variance = batch["shot"] * reference.clamp_min(0) + batch["read"]
        valid = valid & ((batch["shot"] > 0) | (batch["read"] > 0))
        error = (mosaic(prediction.float(), colors) - reference).masked_fill(~valid, 0)
        terms = []
        for side in (4, 16, 32):
            if side > min(error.shape[-2:]):
                continue
            count = side**2
            pooled_error = F.avg_pool2d(error, side, side) * count
            summed_variance = F.avg_pool2d(variance.masked_fill(~valid, 0), side, side) * count
            complete = F.avg_pool2d(valid.float(), side, side) == 1
            standardized = pooled_error / summed_variance.clamp_min(1e-12).sqrt()
            penalty = (standardized.square() + 1e-6).sqrt() - 1e-3
            terms.append(penalty.masked_fill(~complete, 0).sum() / complete.sum().clamp_min(1))
        return torch.stack(terms).mean() if terms else error.sum() * 0


def reconstruction_loss(
    prediction,
    batch,
    auxiliary=None,
    *,
    physical_fp32=True,
    normalized_sensor_weight=0.0,
    multiscale_sensor_weight=0.0,
    objective="charbonnier-v1",
    camera_supervision="reference-white-v1",
    reference_interval_weight=0.0,
    reconstruction_charbonnier_epsilon=DEFAULT_RECONSTRUCTION_EPSILON,
    normalized_band_weight=0.0,
):
    validate_reconstruction_objective(objective)
    epsilon = validate_reconstruction_epsilon(reconstruction_charbonnier_epsilon)
    validate_camera_supervision(camera_supervision)
    band_weight = validate_normalized_band_weight(normalized_band_weight)
    if band_weight and camera_supervision != "sensor-valid-v1":
        raise ValueError("Normalized band supervision requires sensor-valid clean camera targets")
    if band_weight and "sensor_reference" in batch:
        raise ValueError("Normalized band supervision requires exact synthetic targets, not paired references")
    if not math.isfinite(reference_interval_weight) or reference_interval_weight < 0:
        raise ValueError("Reference interval weight must be finite and nonnegative")
    if reference_interval_weight and camera_supervision != "sensor-valid-v1":
        raise ValueError("Reference interval supervision requires sensor-valid camera targets")
    if normalized_sensor_weight < 0:
        raise ValueError("Normalized sensor loss weight must be nonnegative")
    if not math.isfinite(multiscale_sensor_weight) or multiscale_sensor_weight < 0:
        raise ValueError("Multiscale sensor loss weight must be finite and nonnegative")
    target = batch["target"]
    penalty = (
        image_log_mse if objective == "image-log-mse-v1" else partial(charbonnier, epsilon=epsilon)
    )
    sensor_target, sensor_valid, sensor_batch = None, None, batch
    if camera_supervision == "sensor-valid-v1":
        sensor_target = batch.get("sensor_target")
        if sensor_target is None or sensor_target.shape != target.shape:
            raise ValueError("Sensor-valid supervision needs the retained clean camera target")
        # Target-only validity: unmeasured/clipped sensor signals are not made
        # reliable by a good prediction. Display targets stay reference-white.
        sensor_valid = (sensor_target >= 0) & (sensor_target < 0.98)
        linear = masked_reconstruction(
            prediction - sensor_target, sensor_valid, objective, epsilon=epsilon
        )
        sensor_batch = {**batch, "target": sensor_target}
    else:
        linear = penalty(prediction - target)
    display = render(prediction, batch["wb"], batch["matrix"], fp32=physical_fp32)
    truth = render(target, batch["wb"], batch["matrix"], fp32=physical_fp32)
    rendered = penalty(display - truth)
    gradient = (
        sum(
            charbonnier(torch.diff(display, dim=d) - torch.diff(truth, dim=d), epsilon=epsilon)
            for d in (-1, -2)
        )
        / 2
    )
    # Dilate the saturation region; penalize wrong chroma, including its boundary.
    saturated = (truth.amax(1, keepdim=True) > 0.98).float()
    boundary = F.max_pool2d(saturated, 7, 1, 3)
    chroma_error = (display - display.mean(1, keepdim=True)) - (truth - truth.mean(1, keepdim=True))
    highlight = (chroma_error.abs() * boundary).sum() / (boundary.sum() * 3).clamp_min(1)
    sensor = prediction.new_zeros(())
    if auxiliary is not None:
        if camera_supervision == "sensor-valid-v1":
            sensor = masked_reconstruction(
                auxiliary - mosaic(sensor_target, batch["colors"]),
                mosaic(sensor_valid, batch["colors"]),
                "charbonnier-v1",
                epsilon=epsilon,
            )
        else:
            sensor = charbonnier(auxiliary - mosaic(target, batch["colors"]), epsilon=epsilon)
    loss = linear + 0.5 * rendered + 0.1 * gradient + 0.1 * highlight + 0.1 * sensor
    terms = {
        "linear": linear,
        "rendered": rendered,
        "gradient": gradient,
        "highlight": highlight,
        "sensor": sensor,
    }
    if normalized_sensor_weight:
        normalized = noise_normalized_sensor_loss(prediction, sensor_batch, truth)
        loss = loss + normalized_sensor_weight * normalized
        terms["normalized_sensor"] = normalized
    if multiscale_sensor_weight:
        multiscale = multiscale_sensor_loss(prediction, sensor_batch, truth)
        loss = loss + multiscale_sensor_weight * multiscale
        terms["multiscale_sensor"] = multiscale
    if reference_interval_weight:
        interval = reference_white_interval_loss(prediction, batch)
        loss = loss + reference_interval_weight * interval
        terms["reference_interval"] = interval
    if band_weight:
        detail = normalized_band_loss(prediction, sensor_target)
        loss = loss + band_weight * detail
        terms["normalized_band"] = detail
    return loss, terms


def psnr(prediction, target):
    mse = (prediction.float() - target.float()).square().flatten(1).mean(1)
    return -10 * mse.clamp_min(1e-12).log10()
