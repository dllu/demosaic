"""Training-only robust delivered-RGB spectral errors in RAW-proxy units."""

import math

from delivered_spectral_objective import spectral_loss as delivered_loss


def charbonnier_power(power, epsilon):
    """Stable sqrt(power + epsilon**2) - epsilon, with finite zero derivatives.

    Rationalization avoids cancellation for tiny powers. For a complex error
    normalized by sqrt(variance), its gradient relative to squared error is
    1 / (2 * sqrt(power + epsilon**2)). Weak nonzero errors gain relative
    pressure, including errors in flat targets; no target-power mask is used.
    """
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("Charbonnier epsilon must be finite and positive")
    return power / ((power + epsilon**2).sqrt() + epsilon)


def spectral_loss(module, output, target, colors, aux, floor, penalty, epsilon):
    """Keep V153 RGB MSE arithmetic exact, or change only its penalty shape.

    Twelve C-major RGB phases, original analysis/band, and the repeated RAW
    frame-noise scales match V153. These scales define training units, not
    calibrated post-demosaic covariance. Targets never enter model forward.
    """
    if penalty == "mse":
        if epsilon != 0:
            raise ValueError("MSE control must use epsilon zero")
        return delivered_loss(module, output, target, colors, aux, floor, "delivered-RGB")
    if penalty != "charbonnier":
        raise ValueError("Unknown delivered spectral penalty")
    if output.shape != target.shape or output.ndim != 4 or output.shape[1] != 3:
        raise ValueError("Expected matching delivered RGB and target")
    import torch
    from torch.nn import functional as F

    from demosaic.precision import ieee_fp32

    with torch.autocast(output.device.type, enabled=False), ieee_fp32():
        error = F.pixel_unshuffle(output.float() - target.float(), 2)
        spectrum, _ = module.analysis(error, aux["geometry"][4])
        noise = aux["noise_power"].repeat(1, 3)
        assert noise.shape == spectrum.shape[:2]
        variance = noise[:, :, None, None].clamp_min((floor / 65535) ** 2)
        power = spectrum.abs().square() / variance
        band = getattr(module, f"band_{aux['geometry'][4]}")
        return (charbonnier_power(power, epsilon) * band).sum() / (
            band.sum().clamp_min(1) * spectrum.shape[0] * spectrum.shape[1]
        )
