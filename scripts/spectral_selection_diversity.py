"""Input-only pooled spectral allocation; diagnostic fractions are not recovery bounds."""

import math

import numpy as np
from frequency_coverage import eligible_bins, footprint, power_fraction
from green_phase_spectrum import tapered_spectrum


def sector_map(shape, *, offset=0):
    if len(shape) != 2 or min(shape) < 8 or not math.isfinite(offset):
        raise ValueError("Expected axes>=8 and finite angle offset")
    fy, fx = [np.fft.fftfreq(n) / 2 for n in shape]
    angle = np.mod(np.arctan2(fy[:, None], fx[None, :]) - offset, math.pi)
    return np.minimum((angle / (math.pi / 4)).astype(np.int64), 3)


def pooled_score(packed, variance, colors):
    packed, variance, colors = map(np.asarray, (packed, variance, colors))
    if (
        packed.ndim != 3
        or packed.shape[0] != 4
        or variance.shape != packed.shape
        or colors.shape != (4,)
        or tuple(colors) not in {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
        or not np.isfinite(packed).all()
        or not np.isfinite(variance).all()
        or (variance < 0).any()
    ):
        raise ValueError("Expected finite four-phase RAW/variance and a Bayer layout")
    greens = np.flatnonzero(colors == 1)
    fields = [tapered_spectrum(packed[g], variance[g]) for g in greens]
    powers = np.stack(
        [
            abs(f["spectrum"]) ** 2 / np.maximum(f["noise_variance"], (1 / 65535) ** 2)
            for f in fields
        ]
    )
    mean = powers.mean(0)
    score = sum(np.roll(mean, (dy, dx), (0, 1)) for dy in [-1, 0, 1] for dx in [-1, 0, 1]) / 9
    return score, powers, greens


def select_pooled(score, *, count=8, radius=1, quota=None, offset=0):
    """Greedy pooled ranking, optionally larger NMS or at most two slots per sector.

    Full/no-quota reproduces V187's FP64 reference. Four fixed principal angular
    sectors with quota2 use no target. A quota can force noise-only selections;
    no output field represents confidence. Ties use original row-major order.
    """
    score = np.asarray(score)
    if (
        score.ndim != 2
        or not np.isfinite(score).all()
        or (score < 0).any()
        or type(count) is not int
        or not 1 <= count <= 16
        or type(radius) is not int
        or radius < 1
        or quota not in (None, 2)
        or (quota == 2 and count != 8)
    ):
        raise ValueError(
            "Expected nonnegative finite power, count1..16, radius>=1 and optional quota2"
        )
    available = eligible_bins(score.shape, 1 / 16, 1 / 3)
    sectors = sector_map(score.shape, offset=offset)
    used = np.zeros(4, dtype=np.int64)
    bins, values = [], []
    h, w = score.shape
    for _ in range(count):
        allowed = available if quota is None else available & (used[sectors] < quota)
        ranked = np.where(allowed, score, -np.inf)
        flat = int(np.argmax(ranked))
        if not np.isfinite(ranked.flat[flat]):
            break
        y, x = divmod(flat, w)
        bins.append([y, x])
        values.append(float(score[y, x]))
        used[sectors[y, x]] += 1
        for cy, cx in [(y, x), ((-y) % h, (-x) % w)]:
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    available[(cy + dy) % h, (cx + dx) % w] = False
    return {"bins": bins, "scores": values, "sector_counts": used.tolist(), "radius": radius}


def selection_geometry(shape, bins, radius):
    bins = np.asarray(bins, dtype=np.int64).reshape(-1, 2)
    mask = footprint(shape, bins, radius)
    # Conjugate neighborhoods can overlap, including at the Nyquist boundary.
    independent_area = len(bins) * 2 * (2 * radius + 1) ** 2
    return {
        "slots": len(bins),
        "unique_bins": len(set(map(tuple, bins))),
        "footprint_cells": int(mask.sum()),
        "overlap_fraction_of_unclipped_sum": 1 - float(mask.sum()) / independent_area,
        "occupied_sectors": len(set(sector_map(shape)[tuple(bins.T)])) if len(bins) else 0,
    }


def template_proximity(power, bins, radius):
    """Descriptive clean principal-CFA spectral proximity, never amplitude recovery."""
    power = np.asarray(power)
    mask = footprint(power.shape, bins, radius)
    fraction = power_fraction(power, mask)
    principal = eligible_bins(power.shape, 1e-12, math.sqrt(2) / 4)
    # Principal half-plane partitions exclude self-conjugate/DC boundary bins.
    # Sector summaries are restricted to that fixed half-plane, not all energy.
    sectors = {}
    for degrees in [0, 22.5]:
        labels = sector_map(power.shape, offset=math.radians(degrees))
        energy, covered, captured = [], [], []
        total = float(power[principal].sum())
        for s in range(4):
            cells = principal & (labels == s)
            e = float(power[cells].sum())
            energy.append(e / total if total else 0)
            v = float(power[cells & mask].sum())
            captured.append(v / total if total else 0)
            covered.append(v / e if e else None)
        substantial = [v for v, e in zip(covered, energy, strict=True) if e >= 0.05]
        sectors[str(degrees)] = {
            "principal_energy_fractions": energy,
            "captured_principal_energy_fractions": captured,
            "within_sector_proximity": covered,
            "minimum_proximity_among_sectors_with_at_least_5percent_power": min(substantial)
            if substantial
            else None,
        }
    return {"all_template_fraction": fraction, "sectors": sectors}
