"""Optional learned RAW frequency features for the pretrained RGB input stem.

This is not an RGB correction or a signal-detection mask. Signed complex
cross-phase products condition learned complex mixing; no cross-power sign is
discarded. Overlapping, tapered frames bound the context instead of using one
periodic transform of an arbitrarily large inference tile.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .precision import ieee_fp32


def hermitian_projection(values):
    """Project a full square spectrum onto the real-image Fourier subspace."""
    size = values.shape[-1]
    if values.shape[-2] != size or not values.is_complex():
        raise ValueError("Expected square complex spectra")
    reverse = (-torch.arange(size, device=values.device)) % size
    partner = values.index_select(-2, reverse).index_select(-1, reverse).conj()
    return (values + partner) * 0.5


def frequency_descriptor(spectrum, noise_power, colors):
    """31 channels: normalized Hermitian Gram16, log strength1, CFA12, xy2.

    The supplied frame-noise proxy sets descriptor units, not a calibrated
    coefficient variance after detrending. The1e-12 floor is finite ADC-only
    arithmetic. Gram real/imaginary signs and single-phase evidence are retained.
    Common complex phase rotations leave the descriptor invariant.
    """
    if spectrum.ndim != 4 or spectrum.shape[1] != 4 or noise_power.shape != spectrum.shape[:2]:
        raise ValueError("Expected N×4×H×W spectra and per-phase frame-noise power")
    power = spectrum.abs().square()
    total = power.sum(1, keepdim=True)
    noise = noise_power.sum(1)[:, None, None, None].clamp_min(0)
    scale = (total + noise).clamp_min(1e-12)
    channels = [power / scale]
    for first in range(4):
        for second in range(first + 1, 4):
            cross = spectrum[:, first : first + 1] * spectrum[:, second : second + 1].conj()
            channels.extend((cross.real / scale, cross.imag / scale))
    channels.append(torch.log1p(total / noise.clamp_min(1e-12)) / 8)
    height, width = spectrum.shape[-2:]
    placement = F.one_hot(colors, 3).flatten(1).to(power.dtype)
    channels.append(placement[:, :, None, None].expand(-1, -1, height, width))
    fy = torch.fft.fftfreq(height, device=power.device, dtype=power.dtype)[:, None]
    fx = torch.fft.fftfreq(width, device=power.device, dtype=power.dtype)[None, :]
    channels.extend(
        (
            fx.expand(height, width)[None, None].expand(len(power), -1, -1, -1),
            fy.expand(height, width)[None, None].expand(len(power), -1, -1, -1),
        )
    )
    return torch.cat(channels, 1)


def _geometry(size):
    # Deterministic CPU construction; FP64 fitting geometry then FP32 execution.
    axis = torch.arange(size, dtype=torch.float64, device="cpu")
    taper = torch.sin(math.pi * axis / size)
    window = taper[:, None] * taper[None, :]
    y, x = torch.meshgrid(
        torch.linspace(-1, 1, size, dtype=torch.float64, device="cpu"),
        torch.linspace(-1, 1, size, dtype=torch.float64, device="cpu"),
        indexing="ij",
    )
    basis = torch.stack((torch.ones_like(x, device="cpu"), x, y), -1)
    gram = torch.einsum("hwi,hwj,hw->ij", basis, basis, window.square())
    return window.float(), basis.float(), torch.linalg.inv(gram).float()


class RawFrequencyFeatures(nn.Module):
    """Zero-output adapter: packed RAW → complex frame mixing →64 stem offsets.

    Default frames are64 packed pixels with50% overlap (native128px support).
    Smaller inputs use the largest fitting power-of-two frame, at least4.
    Constant CFA colors give exactly zero features, including after learning.
    This does not protect the separately trainable common RGB trunk from drift.
    """

    def __init__(self, max_window=64):
        super().__init__()
        if type(max_window) is not int or max_window < 4 or max_window & (max_window - 1):
            raise ValueError("Maximum frequency frame must be a power of two at least4")
        self.max_window = max_window
        # Preserve the common model's initialization and global RNG state.
        with torch.random.fork_rng(devices=[]):
            # torch.manual_seed also seeds CUDA; only replace CPU RNG here.
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(6501).get_state())
            self.kernel_in = nn.Conv2d(31, 32, 1, device="cpu")
            self.kernel_out = nn.Conv2d(32, 64, 1, device="cpu")
            self.project = nn.Conv2d(2, 64, 1, bias=False, device="cpu")
        nn.init.zeros_(self.kernel_out.weight)
        nn.init.zeros_(self.kernel_out.bias)
        nn.init.zeros_(self.project.weight)
        hadamard = (
            torch.tensor(
                [[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]],
                dtype=torch.float32,
                device="cpu",
            )
            / 2
        )
        self.register_buffer(
            "base_mixing", torch.cat((torch.eye(4, device="cpu"), hadamard)), persistent=False
        )
        size = 4
        while size <= max_window:
            window, basis, inverse = _geometry(size)
            self.register_buffer(f"window_{size}", window, persistent=False)
            self.register_buffer(f"basis_{size}", basis, persistent=False)
            self.register_buffer(f"inverse_{size}", inverse, persistent=False)
            size *= 2

    def mix_spectrum(self, spectrum, noise_power, colors):
        descriptor = frequency_descriptor(spectrum, noise_power, colors)
        delta = self.kernel_out(F.silu(self.kernel_in(descriptor))).tanh()
        delta = delta.reshape(len(spectrum), 8, 4, 2, *spectrum.shape[-2:])
        real = delta[:, :, :, 0] + self.base_mixing[None, :, :, None, None]
        mixing = torch.complex(real, delta[:, :, :, 1])
        mixed = torch.einsum("noihw,nihw->nohw", mixing, spectrum)
        return hermitian_projection(mixed)

    def packed_features(self, packed, variance, colors, span=None):
        """Return eight real latent planes in normalized restoration units."""
        if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
            raise ValueError("Frequency features require matching four-phase RAW and variance")
        batch, _, height, width = packed.shape
        if min(height, width) < 4:
            raise ValueError("Frequency features require at least4 packed pixels per axis")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Frequency features require one CFA layout per image")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            packed, variance = packed.float(), variance.float()
            if span is None:
                span = packed.new_ones(batch, 1, 1, 1)
            if span.shape != (batch, 1, 1, 1):
                raise ValueError("Frequency features require one restoration scale per image")
            span = span.float()
            # Subtract a same-phase value before scaling: constants stay exactly
            # zero even when large stabilized sensor coordinates are involved.
            signal = (packed - packed[..., :1, :1]) / span
            noise = variance.clamp_min(0) / span.square()
            size = min(self.max_window, 1 << int(math.log2(min(height, width))))
            hop = size // 2
            padding = (hop, hop + (-width % hop), hop, hop + (-height % hop))
            padded = F.pad(signal, padding, mode="replicate")
            noise = F.pad(noise, padding, mode="replicate")
            shape = padded.shape[-2:]
            columns = F.unfold(padded, size, stride=hop)
            count = columns.shape[-1]
            patches = columns.transpose(1, 2).reshape(batch * count, 4, size, size)
            noise = F.unfold(noise, size, stride=hop).transpose(1, 2).reshape_as(patches)
            window = getattr(self, f"window_{size}")
            basis = getattr(self, f"basis_{size}")
            inverse = getattr(self, f"inverse_{size}")
            centered = patches - patches[..., :1, :1]
            beta = torch.einsum("nchw,hwk,hw->nck", centered, basis, window.square()) @ inverse
            residual = window * (centered - torch.einsum("nck,hwk->nchw", beta, basis))
            spectrum = torch.fft.fft2(residual, norm="ortho")
            non_dc = torch.ones_like(window)
            non_dc[0, 0] = 0
            spectrum = spectrum * non_dc
            noise_power = (noise * window.square()).mean((-2, -1))
            layouts = colors[:, None].expand(-1, count, -1).reshape(batch * count, 4)
            mixed = self.mix_spectrum(spectrum, noise_power, layouts)
            synthesis = torch.fft.ifft2(mixed, norm="ortho").real * window
            columns = synthesis.reshape(batch, count, 8 * size * size).transpose(1, 2)
            numerator = F.fold(columns, shape, size, stride=hop)
            weight = window.square().reshape(1, size * size, 1).expand(1, -1, count)
            denominator = F.fold(weight, shape, size, stride=hop)
            # Only the guarded interior is returned; its overlap weights are
            # positive. Outer zero-weight padded pixels never enter this divide.
            interior = (..., slice(hop, hop + height), slice(hop, hop + width))
            return numerator[interior] / denominator[interior]

    def forward(self, packed, variance, colors, span=None):
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            features = self.packed_features(packed, variance, colors, span)
            return self.project(F.pixel_shuffle(features, 2))
