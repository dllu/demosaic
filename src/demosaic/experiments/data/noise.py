"""Training-data Poisson/read-noise coupling for aligned clean counterfactuals.

Each member has the existing sensor model's marginal distribution. The members
are deliberately dependent: common Poisson counts use min(clean_a,clean_b),
with independent positive increments, and their Gaussian read draw is shared.
Before ADC, difference variance is shot*abs(clean_a-clean_b) for nonnegative
signals and positive shot at least 1e-12 (the inherited numerical floor).
This is a data-construction primitive, not a restoration algorithm or
evidence that a paired-response objective improves weak detail or flat regions.
"""

import torch


@torch.no_grad()
def coupled_sensor_noise(
    clean_a,
    clean_b,
    shot,
    read,
    *,
    bit_depth=16,
    black_level=0.0,
    generator=None,
    return_pre_ADC=False,
):
    """Return an aligned pair; coefficients and ADC calibration are shared.

    Inputs must be finite FP32 tensors of the same nonempty shape/device.
    Overexposure counts before ADC clipping, matching demosaic.noise.add_noise.
    For positive shot, negative clean samples clamp to zero before counting;
    zero-shot samples retain their signed signal before the ADC. The 1e-12
    shot floor matches the existing implementation. RNG streams differ from
    two independent add_noise calls; only marginal distributions are matched.
    Optional pre-ADC values support physical moment checks without clip bias.
    """
    if (
        clean_a.dtype != torch.float32
        or clean_b.dtype != torch.float32
        or clean_a.device != clean_b.device
        or clean_a.shape != clean_b.shape
        or clean_a.numel() == 0
    ):
        raise ValueError("Expected same-device, same-shape nonempty FP32 clean tensors")
    if not torch.isfinite(clean_a).all() or not torch.isfinite(clean_b).all():
        raise ValueError("Clean tensors must be finite")
    if type(bit_depth) is not int or not 8 <= bit_depth <= 16:
        raise ValueError("ADC bit depth must be an integer in [8,16]")
    coefficients = [
        torch.as_tensor(v, device=clean_a.device, dtype=torch.float32)
        for v in (shot, read, black_level)
    ]
    try:
        shot, read, black = [torch.broadcast_to(v, clean_a.shape) for v in coefficients]
    except RuntimeError as error:
        raise ValueError("Sensor coefficients must broadcast to the clean shape") from error
    if not all(torch.isfinite(v).all() for v in (shot, read, black)):
        raise ValueError("Sensor coefficients must be finite")
    if (shot < 0).any() or (read < 0).any() or (black < 0).any() or (black >= 1).any():
        raise ValueError("Nonnegative noise coefficients and black in [0,1) required")
    safe_shot = shot.clamp_min(1e-12)
    a, b = clean_a.clamp_min(0), clean_b.clamp_min(0)
    shared = torch.minimum(a, b)
    positive = shot > 0
    rate_common = torch.where(positive, shared / safe_shot, 0)
    rate_a = torch.where(positive, (a - shared) / safe_shot, 0)
    rate_b = torch.where(positive, (b - shared) / safe_shot, 0)
    common = torch.poisson(rate_common, generator=generator)
    extra_a = torch.poisson(rate_a, generator=generator)
    extra_b = torch.poisson(rate_b, generator=generator)
    gaussian = (
        torch.randn(clean_a.shape, device=clean_a.device, dtype=torch.float32, generator=generator)
        * read.sqrt()
    )
    before_a = torch.where(positive, (common + extra_a) * safe_shot, clean_a) + gaussian
    before_b = torch.where(positive, (common + extra_b) * safe_shot, clean_b) + gaussian
    levels = (1 << bit_depth) - 1

    def ADC(signal):
        value = (signal * (1 - black) + black).clamp(0, 1)
        return ((value * levels).round() / levels - black) / (1 - black)

    pair = (ADC(before_a), ADC(before_b))
    return (pair, (before_a, before_b)) if return_pre_ADC else pair
