"""Expose RAW/residual relative phase to the native late spectral estimator."""

import torch
from torch import nn
from torch.nn import functional as F

from .late_spectral_matrix import LateSpectralMatrixDetail, bounded_real_image_mixing
from .raw_frequency_features import frequency_descriptor


def relative_spectrum_features(observed, innovation, noise):
    """Eight normalized same-site cross-spectrum coordinates, real4 then imag4.

    The previous two marginal Gram descriptors discard the relative complex
    phase between observed RAW and observed-minus-parent innovation. Their
    cross-spectrum retains that phase while remaining invariant to a common
    phase rotation. The noise proxy supplies units, not calibrated coherence
    or detection probability. No target/reference is an argument.
    """
    if observed.shape != innovation.shape or observed.ndim != 4 or observed.shape[1] != 4:
        raise ValueError("Expected matching N x 4 x H x W complex spectra")
    if (
        not observed.is_complex()
        or not innovation.is_complex()
        or noise.shape != observed.shape[:2]
    ):
        raise ValueError("Expected complex spectra and N x 4 noise proxies")
    noise_sum = noise.clamp_min(0).sum(1)[:, None, None, None]
    first = (observed.abs().square().sum(1, keepdim=True) + noise_sum).clamp_min(1e-12)
    second = (innovation.abs().square().sum(1, keepdim=True) + noise_sum).clamp_min(1e-12)
    denominator = (first * second).sqrt()
    cross = observed * innovation.conj()
    return torch.cat((cross.real / denominator, cross.imag / denominator), 1)


class LateSpectralRelativeDetail(LateSpectralMatrixDetail):
    """Native matrix head plus a zero-initialized 8-to-32 frequency adapter.

    The original twelve tensors and their arithmetic stay intact. One new
    bias-free circular3x3 convolution adds 2,304 parameters before the existing
    SiLU. A zero adapter exactly embeds any trained native matrix head. The
    per-bin norm projection, band, physical inputs and spatial support are
    unchanged; this does not establish flat safety or useful recoverability.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(15201).get_state())
            self.relative_in = nn.Conv2d(
                8, 32, 3, padding=1, padding_mode="circular", bias=False, device="cpu"
            )
        nn.init.zeros_(self.relative_in.weight)

    def frequency_gain(self, observed, innovation, noise, colors):
        descriptor = frequency_descriptor(observed, noise, colors)
        innovation_descriptor = frequency_descriptor(innovation, noise, colors)
        features = torch.cat((descriptor, innovation_descriptor[:, :17]), 1)
        hidden = self.frequency_in(features) + self.relative_in(
            relative_spectrum_features(observed, innovation, noise)
        )
        logits = self.frequency_out(F.silu(hidden))
        values = logits.reshape(len(observed), 4, 4, 2, *observed.shape[-2:])
        real = (values[:, :, :, 0] + self.frequency_real_bias[None, :, :, None, None]).tanh()
        imaginary = values[:, :, :, 1].tanh()
        mixing = bounded_real_image_mixing(torch.complex(real, imaginary))
        observed_power = descriptor[:, :4].sum(1, keepdim=True)
        return mixing * observed_power[:, None] * getattr(self, f"band_{observed.shape[-1]}")
