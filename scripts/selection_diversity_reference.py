"""Separate sorted-list selection, toroidal geometry and QR template reference."""

import math

import numpy as np
from frequency_coverage_reference import independent_footprint, qr_spectrum


def sorted_pooled(score, radius, quota=None):
    h, w = score.shape
    fy, fx = [np.fft.fftfreq(n) / 2 for n in (h, w)]
    y, x = np.indices((h, w))
    rad = np.hypot(fy[:, None], fx[None, :])
    valid = (
        (rad >= 1 / 16)
        & (rad <= 1 / 3)
        & ((fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0)))
    )
    ys, xs = y[valid], x[valid]
    order = np.lexsort((xs, ys, -score[valid]))
    chosen = []
    counts = [0] * 4
    for q in order:
        a, b = int(ys[q]), int(xs[q])
        sector = min(int((math.atan2(fy[a], fx[b]) % math.pi) / (math.pi / 4)), 3)
        if quota is not None and counts[sector] >= quota:
            continue
        reject = False
        for cy, cx in chosen:
            for dy, dx in [(cy, cx), ((-cy) % h, (-cx) % w)]:
                if (
                    min(abs(a - dy), h - abs(a - dy)) <= radius
                    and min(abs(b - dx), w - abs(b - dx)) <= radius
                ):
                    reject = True
        if not reject:
            chosen.append([a, b])
            counts[sector] += 1
        if len(chosen) == 8:
            break
    return chosen


def qr_pooled(raw, variance, greens):
    fields = [qr_spectrum(raw[g], variance[g]) for g in greens]
    powers = np.stack([abs(f[0]) ** 2 / np.maximum(f[1], (1 / 65535) ** 2) for f in fields])
    m = (powers[0] + powers[1]) / 2
    score = np.zeros_like(m)
    # Separate padded slicing instead of the primary rolling-sum expression.
    padded = np.pad(m, 1, mode="wrap")
    for y in range(3):
        for x in range(3):
            score += padded[y : y + m.shape[0], x : x + m.shape[1]] / 9
    return score, powers


def qr_template_power(signal, greens):
    return sum(abs(qr_spectrum(signal[g], np.ones(signal.shape[-2:]))[0]) ** 2 for g in greens)


def reference_proximity(power, bins, radius):
    mask = independent_footprint(power.shape, bins, radius)
    fy, fx = [np.fft.fftfreq(n) / 2 for n in power.shape]
    half = np.broadcast_to(
        (fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0)), power.shape
    )
    angle = np.arctan2(fy[:, None], fx[None, :])
    details = {}
    for degrees in [0, 22.5]:
        a = (angle - math.radians(degrees)) % math.pi
        values = []
        energies = []
        captured = []
        total = float(power[half].sum())
        for s in range(4):
            cell = half & (a >= s * math.pi / 4) & (a < (s + 1) * math.pi / 4)
            e = float(power[cell].sum())
            v = float(power[cell & mask].sum())
            energies.append(e / total if total else 0)
            captured.append(v / total if total else 0)
            values.append(v / e if e else None)
        details[str(degrees)] = {
            "principal_energy_fractions": energies,
            "captured_principal_energy_fractions": captured,
            "within_sector_proximity": values,
            "minimum_proximity_among_sectors_with_at_least_5percent_power": min(
                v for v, e in zip(values, energies, strict=True) if e >= 0.05
            ),
        }
    return float(power[mask].sum() / power.sum()), details
