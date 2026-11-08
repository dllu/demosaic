"""Expose separately measured RAW frequency evidence to local-unit matching.

Experimental variant; initialization/CPU checks do not establish trained quality
or noisy-flat safety. No target, clean template or paired metadata enters forward.
"""

import math

import torch
from torch import nn
from torch.nn import functional as F

from .late_local_noise_matching import LateLocalNoiseMatchingDetail, local_noise_features
from .nonlocal_autograd import enable_sampler_autograd
from .precision import ieee_fp32


def _green_spectra(packed, variance, green):
    """Hann/weighted-affine FFT and complete conditional coefficient variance."""
    _batch, _, height, width = packed.shape
    index = green[:, :, None, None].expand(-1, -1, height, width)
    # Subtraction makes exactly constant phase inputs exactly zero before fitting.
    values = packed.gather(1, index)
    values = values - values[..., :1, :1]
    noise = variance.clamp_min(0).gather(1, index)
    device, dtype = packed.device, packed.dtype
    y, x = torch.meshgrid(
        torch.linspace(-1, 1, height, device=device, dtype=dtype),
        torch.linspace(-1, 1, width, device=device, dtype=dtype),
        indexing="ij",
    )
    basis = torch.stack((torch.ones_like(x), x, y), -1)
    window = (
        torch.hann_window(height, periodic=False, device=device, dtype=dtype)[:, None]
        * torch.hann_window(width, periodic=False, device=device, dtype=dtype)[None, :]
    )
    gram = torch.einsum("hwi,hwj,hw->ij", basis, basis, window.square())
    inverse = torch.linalg.inv(gram)
    beta = torch.einsum("nphw,hwi,hw->npi", values, basis, window.square()) @ inverse
    spectrum = torch.fft.fft2(
        window * (values - torch.einsum("npi,hwi->nphw", beta, basis)), norm="ortho"
    )
    transformed = torch.fft.fft2(window[..., None] * basis, dim=(0, 1), norm="ortho")
    h = transformed @ inverse.to(transformed.dtype)
    cross = torch.fft.fft2((noise * window.pow(3))[..., None] * basis, dim=(-3, -2), norm="ortho")
    covariance = torch.einsum("hwi,hwj,nphw->npij", basis, basis, noise * window.pow(4))
    propagated = (
        (noise * window.square()).mean((-2, -1))[..., None, None]
        - 2 * (h.conj() * cross).sum(-1).real
        + torch.einsum("hwi,npij,hwj->nphw", h, covariance.to(h.dtype), h.conj()).real
    )
    return spectrum, propagated.clamp_min(0)


def phase_evidence_maps(packed, variance, colors, *, peaks=4):
    """Return 10 channels for each of K selected peaks in each green direction.

    Channels are transported real/imaginary coefficients of A and B (asinh
    Fourier-noise units), log1p power A/B, bounded signed real/imaginary cross
    evidence, and native fx/fy times continuous total-power strength. Selection
    uses A only; B cannot alter its frequency or rank. Both directions reuse the
    observations and are not independent tests. No hard detection gate is used.

    Principal-band transport does not resolve all native aliases. Full-context
    waves are features only; spatial localization must be learned and evaluated.
    A one-DN16-squared Fourier-variance floor provides finite ADC arithmetic,
    not statistical calibration. Exactly constant phase inputs yield zero maps.
    """
    if (
        packed.ndim != 4
        or packed.shape[1] != 4
        or variance.shape != packed.shape
        or packed.shape[0] < 1
        or min(packed.shape[-2:]) < 8
        or max(packed.shape[-2:]) > 512
        or packed.dtype not in (torch.float32, torch.float64)
        or variance.dtype != packed.dtype
        or variance.device != packed.device
        or type(peaks) is not int
        or not 1 <= peaks <= 8
    ):
        raise ValueError("Expected finite matching FP32/FP64 Nx4xHxW,axes8..512,peaks1..8")
    batch, _, height, width = packed.shape
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    colors = colors.to(device=packed.device)
    allowed = torch.tensor(
        [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]], device=packed.device
    )
    if colors.shape != (batch, 4) or not bool((colors[:, None] == allowed).all(-1).any(-1).all()):
        raise ValueError("Expected standard Bayer layouts aligned with the batch")
    if not bool(torch.isfinite(packed).all() & torch.isfinite(variance).all()):
        raise ValueError("Expected finite RAW and variance")
    green = torch.where(colors == 1)[1].reshape(batch, 2)
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        spectra, noise = _green_spectra(packed, variance, green)
        noise = noise.clamp_min((1 / 65535) ** 2)
        fy = torch.fft.fftfreq(height, device=packed.device, dtype=packed.dtype) / 2
        fx = torch.fft.fftfreq(width, device=packed.device, dtype=packed.dtype) / 2
        radius = torch.hypot(fy[:, None], fx[None, :])
        eligible = (radius >= 1 / 16) & (radius <= 1 / 3)
        eligible &= (fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0))
        yy, xx = torch.meshgrid(
            torch.arange(height, device=packed.device),
            torch.arange(width, device=packed.device),
            indexing="ij",
        )
        carrier_period = math.lcm(height, width)
        batch_index = torch.arange(batch, device=packed.device)
        features, bins, powers, agreements, validity = [], [], [], [], []
        for a, b in [(0, 1), (1, 0)]:
            available = eligible[None].expand(batch, -1, -1).clone()
            power_a = spectra[:, a].abs().square() / noise[:, a]
            direction_bins, direction_power, direction_cross, direction_valid = [], [], [], []
            for _ in range(peaks):
                scores = power_a.masked_fill(~available, -torch.inf).flatten(1)
                maximum, flat = scores.max(1)
                valid = torch.isfinite(maximum)
                y, x = flat // width, flat % width
                f_y, f_x = fy[y], fx[x]
                coefficients = []
                for phase in [a, b]:
                    z = spectra[batch_index, phase, y, x] / noise[batch_index, phase, y, x].sqrt()
                    index = green[:, phase]
                    offset = 2 * math.pi * (f_y * (index // 2) + f_x * (index % 2))
                    coefficients.append(z * torch.polar(torch.ones_like(offset), -offset))
                first, second = coefficients
                p_a, p_b = first.abs().square(), second.abs().square()
                cross = first * second.conj() / ((1 + p_a) * (1 + p_b)).sqrt()
                # Integer FFT-bin phase is exactly periodic. Reduce it before
                # radians to avoid FP32 large-angle error at zero crossings.
                ky = torch.where(y <= (height - 1) // 2, y, y - height)
                kx = torch.where(x <= (width - 1) // 2, x, x - width)
                phase = (
                    ky[:, None, None] * yy * (carrier_period // height)
                    + kx[:, None, None] * xx * (carrier_period // width)
                ).remainder(carrier_period)
                phase = torch.where(phase > carrier_period // 2, phase - carrier_period, phase)
                angle = phase.to(packed.dtype) * (2 * math.pi / carrier_period)
                carrier = torch.polar(torch.ones_like(angle), angle)
                first_wave, second_wave = (
                    first[:, None, None] * carrier,
                    second[:, None, None] * carrier,
                )
                strength = (p_a + p_b) / (1 + p_a + p_b)
                constants = torch.stack(
                    (
                        p_a.log1p(),
                        p_b.log1p(),
                        cross.real,
                        cross.imag,
                        f_x * strength,
                        f_y * strength,
                    ),
                    1,
                )[:, :, None, None].expand(-1, -1, height, width)
                maps = torch.cat(
                    (
                        torch.stack(
                            (
                                first_wave.real.asinh(),
                                first_wave.imag.asinh(),
                                second_wave.real.asinh(),
                                second_wave.imag.asinh(),
                            ),
                            1,
                        ),
                        constants,
                    ),
                    1,
                )
                features.append(
                    torch.where(valid[:, None, None, None], maps, torch.zeros_like(maps))
                )
                direction_bins.append(torch.stack((y, x), -1))
                direction_power.append(torch.stack((p_a, p_b), -1))
                direction_cross.append(torch.stack((cross.real, cross.imag), -1))
                direction_valid.append(valid)
                # Suppression depends on the A-selected indices only.
                for cy, cx in [(y, x), ((-y) % height, (-x) % width)]:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            available[batch_index, (cy + dy) % height, (cx + dx) % width] = False
            bins.append(torch.stack(direction_bins, 1))
            powers.append(torch.stack(direction_power, 1))
            agreements.append(torch.stack(direction_cross, 1))
            validity.append(torch.stack(direction_valid, 1))
        return torch.cat(features, 1), {
            "green_phase_indices": green,
            "bin_yx": torch.stack(bins, 1),
            "nominal_power": torch.stack(powers, 1),
            "bounded_cross": torch.stack(agreements, 1),
            "valid": torch.stack(validity, 1),
        }


class LatePhaseEvidenceMatchingDetail(LateLocalNoiseMatchingDetail):
    """Zero adapter adds 80 measured-wave coordinates to 39 matching features.

    The existing matching network and frozen V169 component are inherited. At
    zero adapter weights the added coordinates contribute zero; real CUDA parity
    and training/quality admission remain necessary. No hard spectral support or
    direct wave-to-RGB output is added. Local zero variance retains the frozen
    component exactly, including mixed noisy/ADC cells.
    """

    def __init__(self, width=16, max_search=9.0, evidence_peaks=4):
        if type(evidence_peaks) is not int or not 1 <= evidence_peaks <= 8:
            raise ValueError("Expected evidence_peaks1..8")
        super().__init__(width, max_search)
        self.evidence_peaks = evidence_peaks
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(17801).get_state())
            self.phase_evidence_in = nn.Conv2d(20 * evidence_peaks, 39, 1, bias=False, device="cpu")
        nn.init.zeros_(self.phase_evidence_in.weight)

    def initialize_from_local_matching(self, state):
        """Strict old-component load; new adapter is zero, optimizer is separate."""
        expected = set(self.state_dict()) - {"phase_evidence_in.weight"}
        if set(state) != expected:
            raise ValueError("Expected exactly the local-noise matching component tensors")
        with torch.no_grad():
            self.phase_evidence_in.weight.zero_()
        self.load_state_dict(
            dict(
                state,
                **{"phase_evidence_in.weight": self.phase_evidence_in.weight.detach().clone()},
            ),
            strict=True,
        )
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        with torch.autocast(base.device.type, enabled=False), ieee_fp32():
            with torch.no_grad():
                restored = self.frozen(base, packed, variance, colors, wb)
                features, sigma = local_noise_features(restored, packed, variance, colors, wb)
            evaluated = bool(torch.any(sigma > 0))
            evidence_aux = None
            if evaluated:
                with torch.no_grad():
                    evidence, evidence_aux = phase_evidence_maps(
                        packed.float(), variance.float(), colors, peaks=self.evidence_peaks
                    )
                features = features + self.phase_evidence_in(evidence)
                if torch.is_grad_enabled():
                    enable_sampler_autograd()
                correction = F.pixel_shuffle(self.network(features), 2) * sigma
                output = torch.where(sigma > 0, restored + correction, restored)
            else:
                correction = torch.zeros_like(restored)
                output = restored
            if return_aux:
                return output, {
                    "frozen_output": restored,
                    "correction": correction,
                    "sigma": sigma,
                    "matching_evaluated": evaluated,
                    "phase_evidence": evidence_aux,
                }
            return output
