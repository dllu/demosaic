"""Electron-domain Poisson-Gaussian sensor model, including ADC quantization."""

from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass(frozen=True)
class Sensor:
    # Representative priors, NOT measured profiles of a particular camera.
    full_well_e: float = 50000
    read_noise_e: float = 2.0
    iso: float = 100
    base_iso: float = 100
    bit_depth: int = 16

    def coefficients(self) -> tuple[float, float]:
        if min(self.full_well_e, self.iso, self.base_iso) <= 0 or self.read_noise_e < 0:
            raise ValueError("Invalid physical sensor parameters")
        if not 8 <= self.bit_depth <= 16:
            raise ValueError("ADC bit depth must be in [8, 16]")
        capacity = self.full_well_e * self.base_iso / self.iso
        return 1 / capacity, (self.read_noise_e / capacity) ** 2


def sample_coefficients(batch: int, device) -> tuple[Tensor, Tensor]:
    """Random 3–6 µm-class photosites, ISO 50–12800, read noise 0.7–5 e-."""
    area = torch.empty(batch, 1, 1, 1, device=device).uniform_(3, 6).square()
    full_well = area * torch.empty_like(area).uniform_(1400, 2400)
    iso_gain = 2 ** torch.empty_like(area).uniform_(-1, 7)
    read_e = torch.empty_like(area).uniform_(0.7, 5)
    capacity = full_well / iso_gain
    return capacity.reciprocal(), (read_e / capacity).square()


def add_noise(clean: Tensor, shot, read, *, bit_depth=16, generator=None) -> Tensor:
    """Var(y|x)=shot*x+read before clipping. Saturation happens AFTER noise.

    `clean` may exceed 1 for overexposed scenes. Counting before the ADC clip
    preserves the different statistics of clipped pixels and their boundaries.
    """
    shot = torch.as_tensor(shot, device=clean.device, dtype=torch.float32)
    read = torch.as_tensor(read, device=clean.device, dtype=torch.float32)
    if bool((shot < 0).any() or (read < 0).any()):
        raise ValueError("Noise coefficients must be nonnegative")
    safe_shot = shot.clamp_min(1e-12)
    poisson = torch.poisson(clean.clamp_min(0) / safe_shot, generator=generator) * safe_shot
    signal = torch.where(shot > 0, poisson, clean)
    signal = (
        signal
        + torch.randn(clean.shape, device=clean.device, dtype=torch.float32, generator=generator)
        * read.sqrt()
    )
    levels = (1 << bit_depth) - 1
    return (signal.clamp(0, 1) * levels).round() / levels


def variance_map(noisy: Tensor, shot, read) -> Tensor:
    return noisy.clamp_min(0) * shot + read
