"""Analytical coherent-tone support and carrier-grid mismatch, not RGB recovery."""

import math

import numpy as np

METHODS = {
    "rect65_grid256": (65, "rect", 256),
    "hann65_grid65": (65, "hann", 65),
    "hann129_grid129": (129, "hann", 129),
}
OFFSETS = [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (-0.25, 0.25)]


def target_frequencies():
    k = np.rint(np.fft.fftfreq(65) * 65).astype(int)
    y, x = np.meshgrid(k, k, indexing="ij")
    radius = np.hypot(y, x) / 130
    mask = (
        (radius >= 0.09)
        & (radius <= 0.29)
        & (abs(x) / 130 <= 0.225)
        & (abs(y) / 130 <= 0.225)
        & ((y > 0) | ((y == 0) & (x > 0)))
    )
    bins = np.stack([y[mask], x[mask]], -1)
    bases = bins[np.linspace(0, len(bins) - 1, 12, dtype=int)]
    return [
        {
            "base_bin_yx": [int(y), int(x)],
            "offset_in_65_grid_bins": list(offset),
            "native_fyx": [(float(y) + offset[0]) / 130, (float(x) + offset[1]) / 130],
        }
        for y, x in bases
        for offset in OFFSETS
    ]


def cases():
    return [
        dict(
            id=f"tone{index:02d}-{position}-{noise}-{method}-{mode}",
            target=index,
            frequency=frequency,
            position=position,
            center_yx=[128, 128] if position == "interior" else [0, 0],
            noise=noise,
            method=method,
            mode=mode,
            image_shape=[256, 256],
        )
        for index, frequency in enumerate(target_frequencies())
        for position in ["interior", "corner"]
        for noise in ["uniform", "graded"]
        for method in METHODS
        for mode in ["exact_frequency", "nearest_available_carrier"]
    ]


def geometry(case):
    length, taper, grid = METHODS[case["method"]]
    y, x = np.indices((length, length), dtype=float)
    r = length // 2
    dy, dx = y - r, x - r
    cy, cx = case["center_yx"]
    h, w = case["image_shape"]
    gy, gx = dy + cy, dx + cx
    valid = (gy >= 0) & (gy < h) & (gx >= 0) & (gx < w)
    weight = (
        np.ones((length, length))
        if taper == "rect"
        else np.outer(np.hanning(length), np.hanning(length))
    )
    weight *= valid
    design = np.stack([np.ones_like(x), dx / r, dy / r], -1).reshape(-1, 3)
    noise = (
        np.ones_like(x)
        if case["noise"] == "uniform"
        else 0.7 + 0.2 * gy / (h - 1) + 0.4 * gx / (w - 1)
    )
    target = np.asarray(case["frequency"]["native_fyx"])
    frequency = (
        target if case["mode"] == "exact_frequency" else np.rint(target * 2 * grid) / (2 * grid)
    )
    carrier = np.exp(-4j * np.pi * (frequency[0] * dy + frequency[1] * dx)).ravel() / length
    angle = 4 * np.pi * (target[0] * dy + target[1] * dx)
    return (
        design,
        weight.ravel(),
        noise.ravel(),
        carrier,
        np.cos(angle).ravel(),
        np.sin(angle).ravel(),
        frequency,
    )


def measure(case):
    design, weight, noise, carrier, cosine, sine, frequency = geometry(case)
    gram = design.T @ (weight[:, None] ** 2 * design)
    h = (carrier @ (weight[:, None] * design)) @ np.linalg.inv(gram)
    row = carrier * weight - h @ (design.T * weight**2)
    response = np.array([row @ cosine, row @ sine])
    variance = float((noise * abs(row) ** 2).sum())
    signal = float((abs(response) ** 2).mean())
    snr = signal / variance
    return {
        "id": case["id"],
        "measured_native_fyx": frequency.tolist(),
        "cos_response_real_imag": [float(response[0].real), float(response[0].imag)],
        "sin_response_real_imag": [float(response[1].real), float(response[1].imag)],
        "noise_trace_variance": variance,
        "phase_averaged_signal_power": signal,
        "phase_averaged_signal_to_noise_power": snr,
        "maximum_affine_annihilation_error": float(abs(row @ design).max()),
        "observed_pixels": int(np.count_nonzero(weight)),
        "raw_taper_effective_sample_count_without_affine": float(
            weight.sum() ** 2 / (weight**2).sum()
        ),
    }


def ratios(rows, specifications):
    lookup = {r["id"]: r for r in rows}
    groups = {}
    for case in specifications:
        key = tuple(case[k] for k in ["target", "position", "noise", "mode"])
        groups.setdefault(key, {})[case["method"]] = lookup[case["id"]]
    output = []
    for key, group in groups.items():
        baseline = group["rect65_grid256"]["phase_averaged_signal_to_noise_power"]
        for method in ["hann65_grid65", "hann129_grid129"]:
            output.append(
                dict(
                    zip(["target", "position", "noise", "mode"], key, strict=True),
                    method=method,
                    ratio_to_rect65=group[method]["phase_averaged_signal_to_noise_power"]
                    / baseline,
                )
            )
    return output
