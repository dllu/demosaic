"""Learned, phase-preserving spectral innovation after a frozen RGB parent.

Research component: soft frequency gains and a local support gate, without a
hard signal-selection threshold or a second pass through the RGB denoiser.
Neither gain is a calibrated probability. No target/reference enters forward.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import malvar, mosaic
from .precision import ieee_fp32
from .raw_frequency_features import _geometry, frequency_descriptor, validate_frequency_window


def _box(values, size=17):
    return F.avg_pool2d(F.pad(values, (size // 2,) * 4, mode="replicate"), size, stride=1)


class LateSpectralDetail(nn.Module):
    """Zero-initialized correction of a supplied, frozen parent's camera RGB.

    Frequency descriptors use observed and innovation Gram/SNR coordinates.
    A circular3×3 frequency convolution sees peak neighborhoods. The signed
    shared gain multiplies the actual four-phase observed-minus-parent spectrum.
    Its observed-power factor makes every per-phase constant exactly inactive,
    even after learning and even if the parent itself is nonconstant.

    A packed-grid dilated CNN gates local support before fixed signed Malvar
    interpolation. This is not an assurance about noisy flats or mixed scenes;
    both require actual held-out evaluation.
    """

    def __init__(self, max_window=256):
        super().__init__()
        self.max_window = validate_frequency_window(max_window)
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(14701).get_state())
            self.frequency_in = nn.Conv2d(48, 32, 3, padding=1, padding_mode="circular", device="cpu")
            self.frequency_out = nn.Conv2d(32, 1, 1, device="cpu")
            self.local_in = nn.Conv2d(28, 24, 3, padding=1, device="cpu")
            self.local_middle = nn.Conv2d(24, 24, 3, padding=4, dilation=4, device="cpu")
            self.local_wide = nn.Conv2d(24, 24, 3, padding=16, dilation=16, device="cpu")
            self.local_out = nn.Conv2d(24, 1, 1, device="cpu")
        nn.init.zeros_(self.frequency_out.weight)
        nn.init.zeros_(self.frequency_out.bias)
        nn.init.zeros_(self.local_out.weight)
        nn.init.zeros_(self.local_out.bias)
        size = 4
        while size <= max_window:
            window, basis, inverse = _geometry(size)
            self.register_buffer(f"window_{size}", window, persistent=False)
            self.register_buffer(f"basis_{size}", basis, persistent=False)
            self.register_buffer(f"inverse_{size}", inverse, persistent=False)
            frequency = torch.fft.fftfreq(size, device="cpu", dtype=torch.float32)
            radius = torch.hypot(frequency[:, None], frequency[None, :])
            # Packed frequencies are twice native frequencies. Smooth support
            # spans native periods~4.4–64px; DC/very coarse color stay excluded.
            lower, upper = 1 / 32, 0.45
            rise = ((radius - lower) / lower).clamp(0, 1)
            fall = ((upper - radius) / 0.05).clamp(0, 1)
            band = torch.sin(math.pi * rise / 2).square() * torch.sin(math.pi * fall / 2).square()
            self.register_buffer(f"band_{size}", band, persistent=False)
            size *= 2

    def analysis(self, values, size=None):
        """Weighted affine removal and tapered orthonormal full FFT frames."""
        batch, channels, height, width = values.shape
        size = size or min(self.max_window, 1 << int(math.log2(min(height, width))))
        hop = size // 2
        padding = (hop, hop + (-width % hop), hop, hop + (-height % hop))
        centered = values - values[..., :1, :1]
        padded = F.pad(centered, padding, mode="replicate")
        columns = F.unfold(padded, size, stride=hop)
        count = columns.shape[-1]
        frames = columns.transpose(1, 2).reshape(batch * count, channels, size, size)
        frames = frames - frames[..., :1, :1]
        window, basis, inverse = (getattr(self, f"{name}_{size}") for name in ("window", "basis", "inverse"))
        beta = torch.einsum("nchw,hwk,hw->nck", frames, basis, window.square()) @ inverse
        residual = window * (frames - torch.einsum("nck,hwk->nchw", beta, basis))
        spectrum = torch.fft.fft2(residual, norm="ortho")
        non_dc = torch.ones_like(window)
        non_dc[0, 0] = 0
        return spectrum * non_dc, (batch, channels, height, width, size, count, padded.shape[-2:], padding)

    def noise_power(self, variance, geometry):
        batch, channels, _, _, size, count, _, padding = geometry
        frames = F.unfold(F.pad(variance.clamp_min(0), padding, mode="replicate"), size, stride=size // 2)
        frames = frames.transpose(1, 2).reshape(batch * count, channels, size, size)
        return (frames * getattr(self, f"window_{size}").square()).mean((-2, -1))

    def frequency_gain(self, observed, innovation, noise, colors):
        observed_descriptor = frequency_descriptor(observed, noise, colors)
        innovation_descriptor = frequency_descriptor(innovation, noise, colors)
        descriptor = torch.cat((observed_descriptor, innovation_descriptor[:, :17]), 1)
        gain = self.frequency_out(F.silu(self.frequency_in(descriptor))).tanh()
        size = observed.shape[-1]
        reverse = (-torch.arange(size, device=gain.device)) % size
        gain = (gain + gain.index_select(-2, reverse).index_select(-1, reverse)) * 0.5
        observed_power = observed_descriptor[:, :4].sum(1, keepdim=True)
        return gain * observed_power * getattr(self, f"band_{size}")

    def synthesis(self, spectrum, geometry):
        batch, channels, height, width, size, count, shape, _ = geometry
        window = getattr(self, f"window_{size}")
        frames = torch.fft.ifft2(spectrum, norm="ortho").real * window
        columns = frames.reshape(batch, count, channels * size * size).transpose(1, 2)
        numerator = F.fold(columns, shape, size, stride=size // 2)
        weights = window.square().reshape(1, size * size, 1).expand(1, -1, count)
        denominator = F.fold(weights, shape, size, stride=size // 2)
        hop = size // 2
        selected = (..., slice(hop, hop + height), slice(hop, hop + width))
        return numerator[selected] / denominator[selected]

    def apply_frequency_gain(self, gain, innovation):
        """Shared scalar innovation operator; subclasses may mix CFA phases."""
        return gain * innovation

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        if packed.ndim != 4 or packed.shape[1] != 4 or packed.shape != variance.shape:
            raise ValueError("Late spectral detail needs matching four-phase RAW and variance")
        batch, _, height, width = packed.shape
        if min(batch, height, width) < 1 or min(height, width) < 4:
            raise ValueError("Late spectral detail needs at least4 packed pixels per axis")
        if base.shape != (batch, 3, 2 * height, 2 * width):
            raise ValueError("Late spectral detail needs matching native camera RGB")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Late spectral detail needs one CFA layout per image")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            base, packed, variance = base.float(), packed.float(), variance.float()
            parent = mosaic(base, colors)
            observed, geometry = self.analysis(packed)
            parent_spectrum, _ = self.analysis(parent, geometry[4])
            noise = self.noise_power(variance, geometry)
            count = geometry[5]
            layouts = colors[:, None].expand(-1, count, -1).reshape(batch * count, 4)
            innovation = observed - parent_spectrum
            gain = self.frequency_gain(observed, innovation, noise, layouts)
            spectral_delta = self.apply_frequency_gain(gain, innovation)
            proposal = self.synthesis(spectral_delta, geometry)
            sigma = _box(variance.clamp_min(0)).sqrt().clamp_min(1 / 65535)
            placement = F.one_hot(colors, 3).flatten(1).to(packed.dtype)
            placement = placement[:, :, None, None].expand(-1, -1, height, width)
            local = torch.cat(((packed - _box(packed)) / sigma, (parent - _box(parent)) / sigma,
                               proposal / sigma, torch.log1p(variance.clamp_min(0) / sigma.square()), placement), 1)
            local = F.silu(self.local_in(local))
            local = F.silu(self.local_middle(local))
            local = F.silu(self.local_wide(local))
            support = self.local_out(local).sigmoid()
            correction = malvar(proposal * support, colors, wb)
            result = base + correction
            if return_aux:
                return result, {"spectral_delta": spectral_delta, "parent_spectrum": parent_spectrum,
                                "noise_power": noise, "geometry": geometry,
                                "gain": gain, "support": support, "correction": correction}
            return result

    def spectral_supervision(self, target, colors, aux):
        """Training-only coefficient error; target is never a forward input."""
        with torch.autocast(target.device.type, enabled=False), ieee_fp32():
            clean, _ = self.analysis(mosaic(target.float(), colors), aux["geometry"][4])
            desired = clean - aux["parent_spectrum"]
            band = getattr(self, f"band_{aux['geometry'][4]}")
            variance = aux["noise_power"][:, :, None, None].clamp_min((2 / 65535) ** 2)
            return ((aux["spectral_delta"] - desired).abs().square() / variance * band).sum() / (
                band.sum().clamp_min(1) * clean.shape[0] * 4
            )
