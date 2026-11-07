"""Expose bounded cross-frequency phase products to the late detail estimator."""

import torch
from torch import nn
from torch.nn import functional as F

from .late_harmonic_context import LateHarmonicContextDetail, dyadic_frequency_context
from .late_spectral_matrix import bounded_real_image_mixing
from .late_spectral_relative import relative_spectrum_features
from .raw_frequency_features import frequency_descriptor, validate_frequency_window


def harmonic_phase_features(observed, innovation, noise):
    """16 real coordinates: Re/Im of u(w)^2 conj(u(2w)), for RAW then innovation.

    u=F/sqrt(sum_phase |F|^2 + sum_phase noise), with the inherited 1e-12
    arithmetic floor. Each complex product has magnitude at most one in exact
    arithmetic. Doubling indexes the full periodic grid, without interpolation.
    Integer circular-shift phase ramps cancel algebraically. This does not make
    the tapered/detrended full network translation invariant, or turn one noisy
    third-order product into calibrated confidence or an unbiased signal estimate.
    """
    if (
        observed.shape != innovation.shape
        or observed.ndim != 4
        or observed.shape[1] != 4
        or min(observed.shape) < 1
        or observed.shape[-2] != observed.shape[-1]
    ):
        raise ValueError("Expected matching nonempty N x 4 x S x S spectra")
    validate_frequency_window(observed.shape[-1])
    if (
        observed.dtype not in (torch.complex64, torch.complex128)
        or innovation.dtype != observed.dtype
    ):
        raise ValueError("Expected matching complex64 or complex128 spectra")
    if noise.shape != observed.shape[:2] or not noise.is_floating_point():
        raise ValueError("Expected floating-point N x 4 frame-noise proxies")
    if innovation.device != observed.device or noise.device != observed.device:
        raise ValueError("Spectra and noise must share a device")
    noise_sum = noise.to(observed.real.dtype).clamp_min(0).sum(1)[:, None, None, None]
    features = []
    for spectrum in (observed, innovation):
        power = spectrum.real.square() + spectrum.imag.square()
        scale = (power.sum(1, keepdim=True) + noise_sum).clamp_min(1e-12).sqrt()
        carrier = spectrum / scale
        doubled = carrier[..., ::2, ::2].repeat(1, 1, 2, 2)
        product = carrier.square() * doubled.conj()
        features.extend((product.real, product.imag))
    return torch.cat(features, 1)


class LateHarmonicPhaseDetail(LateHarmonicContextDetail):
    """One zero 16-to-32 projection adds 512 parameters before inherited SiLU.

    A zero adapter embeds any trained harmonic-context head. Existing matrix
    bounds, conjugate projection, band, support and direct RGB path remain.
    The new input carries information discarded by same-bin Gram/relative
    descriptors; extra capacity and compute are also part of this intervention.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(16301).get_state())
            self.phase_in = nn.Conv2d(16, 32, 1, bias=False, device="cpu")
        nn.init.zeros_(self.phase_in.weight)

    def frequency_gain(self, observed, innovation, noise, colors):
        descriptor = frequency_descriptor(observed, noise, colors)
        innovation_descriptor = frequency_descriptor(innovation, noise, colors)
        relative = relative_spectrum_features(observed, innovation, noise)
        features = torch.cat((descriptor, innovation_descriptor[:, :17]), 1)
        hidden = self.frequency_in(features) + self.relative_in(relative)
        distant = dyadic_frequency_context(
            torch.cat((descriptor[:, :17], innovation_descriptor[:, :17], relative), 1)
        )
        hidden = hidden + self.harmonic_in(distant)
        hidden = hidden + self.phase_in(harmonic_phase_features(observed, innovation, noise))
        logits = self.frequency_out(F.silu(hidden))
        values = logits.reshape(len(observed), 4, 4, 2, *observed.shape[-2:])
        real = (values[:, :, :, 0] + self.frequency_real_bias[None, :, :, None, None]).tanh()
        imaginary = values[:, :, :, 1].tanh()
        mixing = bounded_real_image_mixing(torch.complex(real, imaginary))
        observed_power = descriptor[:, :4].sum(1, keepdim=True)
        return mixing * observed_power[:, None] * getattr(self, f"band_{observed.shape[-1]}")
