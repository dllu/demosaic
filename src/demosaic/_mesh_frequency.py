"""Infer a local frequency prior from several donor windows, without their phase."""

import itertools
from dataclasses import dataclass

import numpy as np

from ._mesh_profiles import Carrier


@dataclass
class Peak:
    frequency: tuple[float, float]
    scores: tuple[float, float]


def residual_sensor(raw, colors, noise, mask, window):
    """Fit phase-wise affine null and normalization only on discovery sites."""
    grid = raw.shape[-2:]
    y, x = np.indices(grid, dtype=float)
    x = (x - (grid[1] - 1) / 2) / max(grid[1], 1)
    y = (y - (grid[0] - 1) / 2) / max(grid[0], 1)
    design = np.stack((np.ones_like(x), x, y), axis=-1)
    result = []
    for plane in np.flatnonzero(np.asarray(colors) == 1):
        values = raw[plane].astype(float)
        weights = (window[mask])[:, None]
        coefficients = np.linalg.lstsq(
            weights * design[mask], weights[:, 0] * values[mask], rcond=None
        )[0]
        residual = values - design @ coefficients
        variance = noise["shot"] * max(np.median(values[mask]), 1e-4) + noise["read"]
        sigma = np.sqrt(max(variance, 1e-12))
        # Fit scale from A, and use it unchanged on B.
        sigma = max(sigma, 1.4826 * np.median(np.abs(residual[mask])))
        result.append((plane, (residual / sigma).clip(-10, 10)))
    return result


def native_modulation(shape, green, mask, weighted, frequencies):
    yz, xz = np.indices(shape, dtype=float)
    x = (2 * xz - (2 * shape[1] - 1) / 2)[mask]
    y = (2 * yz - (2 * shape[0] - 1) / 2)[mask]
    points = np.stack((x, y), axis=1)
    w = weighted[mask]
    result = np.zeros(len(frequencies), dtype=complex)
    z = np.sqrt(len(green) * np.sum(w * w) / 2)
    for i in range(0, len(result), 8):
        f = np.asarray(frequencies[i : i + 8])
        angles = 2 * np.pi * (points @ f.T)
        exp = np.cos(angles) + 1j * np.sin(angles)
        for plane, val in green:
            phase = 2 * np.pi * ((plane % 2) * f[:, 0] + (plane // 2) * f[:, 1])
            result[i : i + len(f)] += (w * val[mask]) @ exp * np.exp(1j * phase)
    return result / z


def donor_peaks(raw, colors, noise):
    from scipy.ndimage import maximum_filter

    height, width = raw.shape[-2:]
    window = np.outer(np.hanning(height), np.hanning(width))
    a = np.indices((height, width)).sum(0) % 2 == 0
    prepared = residual_sensor(raw, colors, noise, a, window)
    # First propose spectral peaks on the discovery sites.
    pad = 128
    bins = np.fft.fftfreq(pad, d=2)
    fx, fy = np.meshgrid(bins, bins)
    power = np.zeros_like(fx, dtype=complex)
    for plane, values in prepared:
        e = np.exp(-2j * np.pi * ((plane % 2) * fx + (plane // 2) * fy))
        power += e * np.fft.fft2(values * window * a, s=(pad, pad))
    r = np.hypot(fx, fy)
    shape = (r >= 0.035) & (r <= 0.205) & ((fx > 0) | ((fx == 0) & (fy > 0)))
    score = np.abs(power) / np.sqrt(np.sum((window * a) ** 2))
    peaks = shape & (score >= 3.5) & (score == maximum_filter(score, 3, mode="wrap"))
    located = np.argwhere(peaks)
    tops = sorted(located, key=lambda ij: score[tuple(ij)], reverse=True)[:10]
    search = np.asarray(list(itertools.product((-0.00195, 0, 0.00195), repeat=2)))
    choices = []
    for i, j in tops:
        candidates = search + (fx[i, j], fy[i, j])
        discover = native_modulation((height, width), prepared, a, window, candidates)
        best = int(np.argmax(abs(discover)))
        frequency = candidates[best]
        estimate = discover[best]
        held_out = native_modulation((height, width), prepared, ~a, window, [frequency])[0]
        valid = float(np.real(held_out * np.conjugate(estimate)) / max(abs(estimate), 1e-20))
        if valid < 3:
            continue
        if any(np.linalg.norm(frequency - k.frequency) < 0.007 for k in choices):
            continue
        choices.append(Peak(tuple(frequency), (float(abs(estimate)), valid)))
    return choices


def signed_alignment(f, g):
    f, g = np.asarray(f), np.asarray(g)
    if np.dot(f, g) < 0:
        g = -g
    return g, np.linalg.norm(f - g)


def separation(first, second):
    a, b = np.asarray(first.frequency), np.asarray(second.frequency)
    return abs(np.linalg.det(np.stack((a, b))) / np.linalg.norm(a) / np.linalg.norm(b))


def contained_tiles(packed, box, span, *, gap=32):
    left, top, width, height = box
    xx, yy = packed.shape[2] * 2, packed.shape[1] * 2
    row = (yy % span) // 4 * 2
    column = (xx % span) // 4 * 2
    for y in range(row, yy - span + 1, span):
        for x in range(column, xx - span + 1, span):
            if (
                x + span > left - gap
                and y + span > top - gap
                and x < left + width + gap
                and y < top + height + gap
            ):
                continue
            yield x, y


def infer_prior(packed, colors, box, noise, *, span):
    observations = []
    for lx, ly in contained_tiles(packed, box, span):
        region = packed[:, ly // 2 : (ly + span) // 2, lx // 2 : (lx + span) // 2]
        observed = donor_peaks(region, colors, noise)
        observations.append(((lx + span / 2, ly + span / 2), observed))
    scores = []
    for _, peaks in observations:
        for p, q in itertools.combinations(peaks, 2):
            if not 0.5 < separation(p, q):
                continue
            both = []
            for position, other in observations:
                u = [(w, signed_alignment(p.frequency, w.frequency)) for w in other]
                v = [(w, signed_alignment(q.frequency, w.frequency)) for w in other]
                if not u:
                    continue
                w1, k1 = min(u, key=lambda pair: pair[1][1])
                w2, k2 = min(v, key=lambda pair: pair[1][1])
                if w1 is not w2 and k1[1] <= 0.011 and k2[1] <= 0.011:
                    both.append((position, w1, w2, k1[0], k2[0]))
            score = sum(min(w1.scores[1], w2.scores[1], 10) for _, w1, w2, _, _ in both)
            scores.append((score, both))
    if not scores:
        return None
    _, both = max(scores, key=lambda item: item[0])
    if len(both) < 2:
        return None
    # Move only frequency, not phase; local Bayer data must establish phase.
    center = np.array([box[0] + 127.5, box[1] + 127.5])
    distances = np.linalg.norm(np.asarray([p[0] for p in both]) - center, axis=1)
    weights = 1 / (1 + (distances / 180) ** 2)
    result = [tuple(np.average([p[k] for p in both], weights=weights, axis=0)) for k in (3, 4)]
    return result


def query_phases(raw, colors, frequencies, noise, *, packed_offset=0):
    h, w = raw.shape[-2:]
    reserved = (np.indices((h, w))[1] + packed_offset) % 4 == 0
    win = np.outer(np.hanning(h), np.hanning(w))
    green = residual_sensor(raw, colors, noise, reserved, win)
    steps = np.arange(-2, 3) / 384
    deltas = np.array(list(itertools.product(steps, repeat=2)))
    answer = []
    for frequency in frequencies:
        bank = frequency + deltas
        amps = native_modulation((h, w), green, reserved, win, bank)
        score = np.abs(amps)
        j = int(np.argmax(score))
        closer = np.array(list(itertools.product(np.arange(-2, 3) / 1536, repeat=2)))
        bank = bank[j] + closer
        amps = native_modulation((h, w), green, reserved, win, bank)
        score = np.abs(amps)
        j = int(np.argmax(score))
        answer.append(
            (
                float(score[j]),
                Carrier(tuple(bank[j]), float(np.angle(amps[j]) / (2 * np.pi) % 1), 0.08),
            )
        )
    answer.sort(key=lambda t: t[0], reverse=True)
    return [line for _, line in answer], reserved, [s for s, _ in answer]
