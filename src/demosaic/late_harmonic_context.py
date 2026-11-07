"""Condition late spectral mixing on distant dyadic frequency evidence."""

import torch
from torch import nn
from torch.nn import functional as F

from .late_spatial_rgb import LateSpatialRgbDetail
from .late_spectral_matrix import bounded_real_image_mixing
from .late_spectral_relative import relative_spectrum_features
from .raw_frequency_features import frequency_descriptor, validate_frequency_window


def dyadic_frequency_context(values):
    """Concatenate f(2w), then all four alias branches of f(w/2).

    Full unshifted FFT coordinates are periodic. Half coordinates use linear
    interpolation, including the neighbor across each half-branch boundary.
    Branch order is (y,x) offsets (0,0),(0,S/2),(S/2,0),(S/2,S/2).
    Inputs are real N x C x S x S descriptors, not spatial image pixels.
    Slices, rolls and explicit interleaving keep CUDA backward deterministic.
    """
    if values.ndim != 4 or min(values.shape) < 1 or values.shape[-2] != values.shape[-1]:
        raise ValueError("Expected nonempty square N x C x S x S descriptors")
    size = validate_frequency_window(values.shape[-1])
    if values.dtype not in (torch.float32, torch.float64):
        raise ValueError("Expected real FP32 or FP64 descriptors")
    half = size // 2
    outputs = [values[..., ::2, ::2].repeat(1, 1, 2, 2)]
    for y in (0, half):
        for x in (0, half):
            shifted = torch.roll(values, shifts=(-y, -x), dims=(-2, -1))
            left = shifted[..., : half + 1, :half]
            right = shifted[..., : half + 1, 1 : half + 1]
            rows = torch.stack((left, (left + right) * 0.5), dim=-1).flatten(-2)
            top, bottom = rows[..., :half, :], rows[..., 1 : half + 1, :]
            outputs.append(torch.stack((top, (top + bottom) * 0.5), dim=-2).flatten(-3, -2))
    return torch.cat(outputs, 1)


class LateHarmonicContextDetail(LateSpatialRgbDetail):
    """Zero adapter embeds the trained spatial hybrid before learning.

    42 signal/innovation/relative coordinates at five distant locations feed
    one bias-free 210-to-32 projection before the inherited SiLU. All existing
    bounds, band, support and direct RGB path remain. Additional context can
    learn structural evidence but does not guarantee flat-field fidelity.
    """

    def __init__(self, max_window=256):
        super().__init__(max_window)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(16101).get_state())
            self.harmonic_in = nn.Conv2d(210, 32, 1, bias=False, device="cpu")
        nn.init.zeros_(self.harmonic_in.weight)

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
        logits = self.frequency_out(F.silu(hidden))
        values = logits.reshape(len(observed), 4, 4, 2, *observed.shape[-2:])
        real = (values[:, :, :, 0] + self.frequency_real_bias[None, :, :, None, None]).tanh()
        imaginary = values[:, :, :, 1].tanh()
        mixing = bounded_real_image_mixing(torch.complex(real, imaginary))
        observed_power = descriptor[:, :4].sum(1, keepdim=True)
        return mixing * observed_power[:, None] * getattr(self, f"band_{observed.shape[-1]}")
