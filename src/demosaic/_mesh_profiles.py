"""Phase profiles and disjoint Bayer prediction for experimental mesh inference."""

import math
from dataclasses import dataclass, replace

import numpy as np

from .isolated_line import coordinates, native_sites


@dataclass(frozen=True)
class Carrier:
    frequency: tuple[float, float]
    offset: float
    width: float


def ribbon(x, y, carrier):
    f = carrier.frequency
    phase = f[0] * x + f[1] * y - carrier.offset
    distance = (phase - np.rint(phase)) / carrier.width
    return np.exp(-0.5 * distance * distance)


def projected_fit(background, profile, raw, weights):
    """Fit the linear null and a residualized one-column wire profile."""
    root = np.sqrt(weights)
    design = root[:, None] * background
    target = root * raw
    column = root[:, None] * profile
    fit = np.linalg.solve(design.T @ design, design.T @ np.column_stack((target, column)))
    wire = column - design @ fit[:, 1:]
    amplitude = np.linalg.solve(wire.T @ wire, wire.T @ (target - design @ fit[:, 0]))
    return fit[:, 0], fit[:, 1:], amplitude


def split_scores(background, profiles, raw, colors, fold, shot, read):
    """Estimate the null and profile on A and forecast B, then reverse."""
    scores = []
    for a in (0, 1):
        train = fold == a
        select = [(train & (colors == k), ~train & (colors == k)) for k in range(3)]
        if any(min(int(v.sum()), int(t.sum())) < 64 for v, t in select):
            return []
        weights = [1 / (max(np.median(raw[v]), 1e-4) * shot + max(read, 1e-10)) for v, _ in select]
        checks = []
        for profile in profiles:
            overlap = power = 0.0
            for (train_sites, test_sites), weight in zip(select, weights, strict=True):
                base, projection, gain = projected_fit(
                    background[train_sites],
                    profile[train_sites],
                    raw[train_sites],
                    np.full(train_sites.sum(), weight),
                )
                increment = (profile[test_sites] - background[test_sites] @ projection) @ gain
                residual = raw[test_sites] - background[test_sites] @ base
                power += (increment @ increment) * weight
                overlap += (increment @ residual) * weight
            checks.append((2 * overlap - power, overlap / math.sqrt(max(power, 1e-20))))
        scores.append(checks)
    return scores


def supported_profile(scores):
    if not scores:
        return 0, 0.0
    occluded = len(scores[0]) > 1 and all(row[1][0] > row[0][0] + 1 for row in scores)
    column = int(occluded)
    if not all(row[column][0] > 0 and row[column][1] > 1.75 for row in scores):
        return column, 0.0
    strength = min(row[column][1] for row in scores)
    return column, float(np.clip((strength - 1.75) / 2, 0, 1))


def fit_direction(parent, packed, variance, colors, carriers, reserve, shot, read, *, occlusion):
    """Return one globally fitted direction and its sixteen local support scores."""
    height, width = parent.shape[-2:]
    origin = (-(width - 1) / 2, -(height - 1) / 2)
    xn, yn = native_sites(packed.shape[-2:], origin)
    x, y = coordinates(height, width, origin=origin)
    cfa = np.broadcast_to(np.asarray(colors)[:, None, None], packed.shape)
    fold = np.broadcast_to(np.indices(packed.shape[-2:]).sum(0) % 2, packed.shape)
    p, q = (ribbon(xn, yn, carrier) for carrier in carriers)
    p_rgb, q_rgb = (ribbon(x, y, carrier) for carrier in carriers)
    basis = [q[..., None]]
    display = [q_rgb[..., None]]
    if occlusion:
        basis.append((q * (1 - p))[..., None])
        display.append((q_rgb * (1 - p_rgb))[..., None])
    background = np.stack((np.ones_like(xn), xn / 128, yn / 128, p), axis=-1)
    parent_sites = parent[cfa, (yn - origin[1]).astype(int), (xn - origin[0]).astype(int)]

    def score(keep):
        return supported_profile(
            split_scores(
                background[keep],
                [a[keep] for a in basis],
                packed[keep].astype(float),
                cfa[keep],
                fold[keep],
                shot,
                read,
            )
        )

    available = np.broadcast_to(~reserve[None], packed.shape)
    option, strength = score(available)
    if not strength:
        return parent, None
    weights = 1 / np.maximum(variance, 1e-12)
    result = np.zeros_like(parent, dtype=float)
    for k in range(3):
        keep = available & (cfa == k)
        args = background[keep], basis[option][keep]
        _, _, measured = projected_fit(*args, packed[keep].astype(float), weights[keep])
        _, _, old = projected_fit(*args, parent_sites[keep], weights[keep])
        result[k] = (display[option] @ (measured - old)) * strength
    support = []
    for cx in (-96, -32, 32, 96):
        for cy in (-96, -32, 32, 96):
            keep = (np.abs(xn - cx) <= 56) & (np.abs(yn - cy) <= 56) & available
            _, local_strength = score(keep)
            support.append((cx, cy, local_strength))
    return (parent + result).astype(parent.dtype), support


def extra_query_check(raw, colors, carriers, shot, read, packed_offset):
    """Check both directions and a shifted rear profile on separate Bayer sites."""
    height, width = raw.shape[-2:]
    x, y = native_sites((height, width), (-(2 * width - 1) / 2, -(2 * height - 1) / 2))
    slot = np.broadcast_to((np.indices((height, width))[1] + packed_offset) % 4, raw.shape)
    cfa = np.broadcast_to(np.asarray(colors)[:, None, None], raw.shape)
    front, rear = (ribbon(x, y, carrier) for carrier in carriers)
    shifted = ribbon(x, y, replace(carriers[1], offset=(carriers[1].offset + 0.31) % 1))
    affine = np.stack((np.ones_like(x), x / 128, y / 128), axis=-1)
    checks = []
    for other, trial in ((rear, front), (front, rear), (front, shifted)):
        background = np.concatenate((affine, other[..., None]), axis=-1)
        gains = []
        for training_slots, test_slot in (((1,), 2), ((2,), 1), ((1, 2), 3)):
            improvement = 0.0
            for color in range(3):
                train = (cfa == color) & np.isin(slot, training_slots)
                test = (cfa == color) & (slot == test_slot)
                variance = shot * max(1e-4, float(np.median(raw[train]))) + read
                base, projection, gain = projected_fit(
                    background[train],
                    trial[train, None],
                    raw[train],
                    np.full(train.sum(), 1 / variance),
                )
                delta = (trial[test, None] - background[test] @ projection) @ gain
                residual = raw[test] - background[test] @ base
                improvement += float(np.sum(delta * (2 * residual - delta)) / variance)
            gains.append(improvement)
        checks.append(gains)
    return min(checks[0] + checks[1]) > 0 and checks[1][-1] > checks[2][-1]


def supported_patch(parent, raw, variance, colors, carriers, reserve, shot, read):
    front, front_support = fit_direction(
        parent, raw, variance, colors, carriers[::-1], reserve, shot, read, occlusion=False
    )
    if front_support is None:
        return parent
    rear, rear_support = fit_direction(
        parent, raw, variance, colors, carriers, reserve, shot, read, occlusion=True
    )
    if rear_support is None:
        return parent
    height, width = parent.shape[-2:]
    x, y = coordinates(height, width, origin=(-(width - 1) / 2, -(height - 1) / 2))
    mask = np.zeros_like(x)
    normalization = np.zeros_like(x)
    for (cx, cy, a), (_, _, b) in zip(front_support, rear_support, strict=True):
        taper = np.maximum(0, 1 - np.abs(x - cx) / 64) * np.maximum(0, 1 - np.abs(y - cy) / 64)
        normalization += taper
        mask += taper * min(a, b)
    mask /= np.maximum(normalization, 1e-8)
    combined = front.astype(float) + rear.astype(float) - parent
    return (parent + mask[None] * (combined - parent)).astype(parent.dtype)
