"""Training-only response supervision on physically coupled counterfactual pairs."""

import math

import torch


@torch.no_grad()
def paired_sensor_increment_units(clean_a, clean_b, shot, *, floor_DN16=16):
    """Nominal std of the coupled sensor difference, with a fixed DN16 floor.

    Common Poisson counts and Gaussian read noise cancel before ADC; the
    remaining variance is effective_shot*abs(clean_a-clean_b). These are
    sensor-increment training units, not restored RGB covariance/confidence.
    The inherited positive-shot floor is 1e-12. Targets/units never enter forward.
    """
    if clean_a.ndim != 4 or clean_a.shape != clean_b.shape or min(clean_a.shape) < 1:
        raise ValueError("Expected matching nonempty N x C x H x W sensor tensors")
    if not all(v.is_floating_point() and torch.isfinite(v).all() for v in (clean_a, clean_b)):
        raise ValueError("Sensor values must be finite floating-point tensors")
    if clean_a.device != clean_b.device or (clean_a < 0).any() or (clean_b < 0).any():
        raise ValueError("Sensor values must be nonnegative on the same device")
    if not math.isfinite(floor_DN16) or floor_DN16 <= 0:
        raise ValueError("Noise-unit floor must be positive and finite")
    dtype = torch.float64 if clean_a.dtype == torch.float64 else torch.float32
    a, b = clean_a.to(dtype), clean_b.to(dtype)
    coefficient = torch.as_tensor(shot, device=a.device, dtype=dtype)
    if not torch.isfinite(coefficient).all() or (coefficient < 0).any():
        raise ValueError("Shot coefficient must be finite and nonnegative")
    try:
        coefficient = torch.broadcast_to(coefficient, a.shape)
    except RuntimeError as error:
        raise ValueError("Shot coefficient must broadcast within the sensor shape") from error
    coefficient = torch.where(coefficient > 0, coefficient.clamp_min(1e-12), coefficient)
    variance = coefficient * (a - b).abs()
    if variance.shape != a.shape:
        raise ValueError("Shot coefficient must broadcast within the sensor shape")
    return variance.mean((1, 2, 3), keepdim=True).sqrt().clamp_min(floor_DN16 / 65535)


def paired_response_loss(output, target, units, pairs, *, epsilon=0.003):
    """Stable Charbonnier of restored-minus-target pair differences.

    Each model forward sees one noisy image and its supplied parent. This loss
    operates afterwards on disjoint aligned pairs, including exactly unchanged
    target regions. It is blind to RGB errors shared by both members, so ordinary
    RGB/local/DC losses remain necessary. No inference gate or flat guarantee.
    """
    if output.ndim != 4 or output.shape[1] != 3 or min(output.shape) < 1:
        raise ValueError("Expected nonempty N x 3 x H x W output")
    if target.shape != output.shape or not all(v.is_floating_point() for v in (output, target)):
        raise ValueError("Output and target must be matching floating-point RGB")
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("Charbonnier epsilon must be positive and finite")
    indices = torch.as_tensor(pairs, device=output.device)
    if (
        indices.dtype != torch.int64
        or indices.ndim != 2
        or indices.shape[1] != 2
        or len(indices) < 1
    ):
        raise ValueError("Expected nonempty P x 2 int64 pair indices")
    if (
        indices.min() < 0
        or indices.max() >= len(output)
        or indices.unique().numel() != indices.numel()
    ):
        raise ValueError("Pair members must be distinct and in range")
    if units.shape != (len(indices), 1, 1, 1) or not units.is_floating_point():
        raise ValueError("Expected one floating-point unit per pair")
    if not torch.isfinite(units).all() or (units <= 0).any():
        raise ValueError("Pair units must be positive and finite")
    dtype = torch.float64 if output.dtype == torch.float64 else torch.float32
    with torch.autocast(output.device.type, enabled=False):
        value, clean = output.to(dtype), target.detach().to(device=output.device, dtype=dtype)
        scale = units.detach().to(device=output.device, dtype=dtype)
        first, second = indices.unbind(1)
        residual = ((value[first] - value[second]) - (clean[first] - clean[second])) / scale
        power = residual.square()
        return (power / ((power + epsilon**2).sqrt() + epsilon)).mean()
