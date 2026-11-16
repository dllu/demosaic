"""Competing orientation proposals from the same measured innovation spectrum.

Two angular families receive equal proposal slots. This is candidate allocation,
not evidence that two structures exist; the learned readout must still reject
unsupported proposals. Both greens and the parent reuse RAW noise, so scores
are empirical features, never independent validation or confidence.
"""

import math

import torch

from .late_phase_evidence_matching import _green_spectra
from .late_pooled_phase_wave import _green_layout
from .precision import ieee_fp32


def exclude_nearby_bins(bins, valid, inherited_bins, inherited_valid, shape, *, radius=1):
    """Remove duplicate/conjugate proposals on the periodic packed DFT lattice.

    This only reserves the inherited carriers' neighborhoods. It neither detects
    a structure nor bounds overlap of spatially modulated wave estimates.
    """
    if type(radius) is not int or radius < 0:
        raise ValueError("Expected a nonnegative integer exclusion radius")
    size = bins.new_tensor(shape)
    new, old = bins.flatten(1, 2), inherited_bins.flatten(1, 2)
    occupied = inherited_valid.flatten(1, 2)
    duplicate = torch.zeros(new.shape[:2], dtype=torch.bool, device=bins.device)
    for sign in [-1, 1]:
        delta = (new[:, :, None] - sign * old[:, None]).remainder(size)
        distance = torch.minimum(delta, size - delta).amax(-1)
        duplicate |= ((distance <= radius) & occupied[:, None]).any(-1)
    return valid & ~duplicate.reshape(valid.shape)


@torch.no_grad()
def competing_phase_bins(field, variance, colors, *, peaks=4, lower=1 / 64, family_degrees=20.0):
    if type(peaks) is not int or not 1 <= peaks <= 8:
        raise ValueError("Expected peaks1..8")
    if not math.isfinite(family_degrees) or not 0 < family_degrees < 45:
        raise ValueError("Expected angular family radius between0 and45degrees")
    if not math.isfinite(lower) or not 0 < lower < 1 / 3:
        raise ValueError("Expected positive lower native frequency below1/3")
    green = _green_layout(field, variance, colors)
    batch, _, height, width = field.shape
    with torch.autocast(field.device.type, enabled=False), ieee_fp32():
        spectrum, noise = _green_spectra(field, variance, green)
        power = spectrum.abs().square() / noise.clamp_min((1 / 65535) ** 2)
        mean = power.mean(1)
        score = (
            sum(torch.roll(mean, (dy, dx), (-2, -1)) for dy in [-1, 0, 1] for dx in [-1, 0, 1]) / 9
        )
        if not torch.isfinite(score).all():
            raise ArithmeticError("Nonfinite spectral proposal score")
        fy, fx = [
            torch.fft.fftfreq(n, device=field.device, dtype=torch.float64) / 2
            for n in (height, width)
        ]
        yy, xx = torch.meshgrid(fy, fx, indexing="ij")
        radius2 = yy.square() + xx.square()
        eligible = (
            (radius2 >= lower**2) & (radius2 <= (1 / 3) ** 2) & ((yy > 0) | ((yy == 0) & (xx > 0)))
        )
        available = eligible[None].expand(batch, -1, -1).clone()
        items = torch.arange(batch, device=field.device)
        roots, root_valid = [], []
        selected, validities, selected_scores = [], [], []
        cosine2 = math.cos(math.radians(family_degrees)) ** 2

        def angular_mask(root):
            ry, rx = root
            dot = yy[None] * ry[:, None, None] + xx[None] * rx[:, None, None]
            return (
                dot.square() >= cosine2 * radius2[None] * (ry.square() + rx.square())[:, None, None]
            )

        for rank in range(2 * peaks):
            candidate = available.clone()
            if rank == 1:
                candidate &= ~angular_mask(roots[0])
            elif rank >= 2:
                family = rank % 2
                candidate &= angular_mask(roots[family]) & root_valid[family][:, None, None]
            maximum, flat = score.masked_fill(~candidate, -torch.inf).flatten(1).max(1)
            valid = torch.isfinite(maximum)
            y, x = flat // width, flat % width
            if rank < 2:
                roots.append((fy[y], fx[x]))
                root_valid.append(valid)
            selected.append(torch.stack((y, x), -1))
            validities.append(valid)
            selected_scores.append(torch.where(valid, maximum, torch.zeros_like(maximum)))
            for cy, cx in ((y, x), ((-y) % height, (-x) % width)):
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        available[items, (cy + dy) % height, (cx + dx) % width] = False
        bins = torch.stack(selected, 1).reshape(batch, peaks, 2, 2).transpose(1, 2).contiguous()
        valid = torch.stack(validities, 1).reshape(batch, peaks, 2).transpose(1, 2).contiguous()
        scores = (
            torch.stack(selected_scores, 1).reshape(batch, peaks, 2).transpose(1, 2).contiguous()
        )
        powers = []
        for family, (a, b) in enumerate([(0, 1), (1, 0)]):
            y, x = bins[:, family].unbind(-1)
            powers.append(torch.stack([power[items[:, None], p, y, x] for p in (a, b)], -1))
        return (
            bins,
            valid,
            {
                "green_phase_indices": green,
                "bin_yx": bins,
                "valid": valid,
                "rank": torch.arange(2 * peaks, device=field.device)
                .reshape(peaks, 2)
                .T[None]
                .expand(batch, -1, -1),
                "pooled_score": scores,
                "global_nominal_power": torch.stack(powers, 1),
                "family_degrees": float(family_degrees),
                "scope": "Two proposed angular families; not detected structures or calibrated confidence.",
            },
        )
