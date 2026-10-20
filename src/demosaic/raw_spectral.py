"""Input-only Fourier evidence for an optional measured-CFA residual.

The shared phase mask keeps Fourier evidence separate from a learned RGB
estimate. It is a conservative coherent-signal descriptor, not a calibrated
posterior probability or a replacement for photographic quality evaluation.
"""

import math

import torch
from torch import nn

from .cfa import malvar, mosaic
from .precision import ieee_fp32


def spectral_mask(packed, variance, *, alpha=0.01):
    """Return orthonormal RAW spectra and one shared non-DC shrinkage mask.

    Per-phase mean variance is the marginal coefficient variance for independent
    pixel noise, including spatially varying variance. With *known independent
    Gaussian* noise, the four-phase real quadratic form has trace4 and spectral
    norm at most1. A conservative Gaussian quadratic/union bound motivates
    T=4+4*sqrt(log(HW/alpha))+2*log(HW/alpha). HW counts the full transform,
    preserving rotations of rectangular inputs; it is not the rFFT array size.
    Poisson/ADC noise and input-derived variance do not inherit this bound.

    No measured samples, innovation, spectral power or RGB values are clipped.
    The1e-12 variance floor makes ADC-only arithmetic finite; it is an explicit
    numerical convention, not a claim of an ADC noise calibration.
    """
    if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
        raise ValueError("Spectral evidence requires matching four-phase RAW and variance")
    if not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("Spectral alpha must be finite and between zero and one")
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed, variance = packed.float(), variance.float()
        spectrum = torch.fft.rfft2(packed, norm="ortho")
        scale = variance.clamp_min(0).mean((-2, -1), keepdim=True).clamp_min(1e-12)
        power = (spectrum.real.square() + spectrum.imag.square()) / scale
        power = power.sum(1, keepdim=True)
        t = math.log(packed.shape[-2] * packed.shape[-1] / alpha)
        threshold = 4 + 4 * math.sqrt(t) + 2 * t
        weight = (1 - threshold / power.clamp_min(1e-12)).clamp_min(0)
        # Out-of-place multiplication keeps autograd's saved mask intact.
        non_dc = torch.ones_like(weight)
        non_dc[..., 0, 0] = 0
        return spectrum, weight * non_dc


def spectral_innovation(base, packed, variance, colors, wb=None):
    """Map the shared-mask RAW innovation back to signed camera RGB.

    Evidence is computed from observations, never from the base/target error.
    The base is used only in the innovation. Each phase has zero DC before
    linear Malvar interpolation. Border interpolation does not guarantee exact
    zero mean in every interpolated RGB channel.
    """
    batch, _, height, width = packed.shape
    if base.shape != (batch, 3, 2 * height, 2 * width):
        raise ValueError("Spectral innovation requires matching native RGB and RAW")
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        observed, weight = spectral_mask(packed, variance)
        predicted = torch.fft.rfft2(mosaic(base.float(), colors), norm="ortho")
        residual = torch.fft.irfft2(
            weight * (observed - predicted), s=(height, width), norm="ortho"
        )
        return malvar(residual, colors, wb)


class RawSpectralResidual(nn.Module):
    """A signed scalar gate conditioned on pooled frozen-DINO/decoder features.

    A zero head preserves the parent output and common RNG, while allowing its
    first backward to learn the gate. Shared scalar mixing avoids a learned
    per-pixel modulation reintroducing DC into the phase innovation. The gate
    can reject the descriptor; no downstream improvement is assumed.
    """

    def __init__(self, channels=67):
        super().__init__()
        self.weight = nn.Parameter(torch.zeros(1, channels))
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, base, packed, variance, colors, features, wb=None):
        if features.shape != (len(packed), self.weight.shape[1], *base.shape[-2:]):
            raise ValueError("Spectral residual needs matching native decoder features")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            pooled = features.float().mean((-2, -1))
            gate = torch.nn.functional.linear(pooled, self.weight, self.bias).tanh()
            residual = spectral_innovation(base, packed, variance, colors, wb)
            return base.float() + gate[..., None, None] * residual
