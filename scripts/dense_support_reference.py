"""Independent QR rows and integer-phase synthetic fields for support auditing."""

import numpy as np


def reference(case):
    labels = {
        "rect65_grid256": (65, False, 256),
        "hann65_grid65": (65, True, 65),
        "hann129_grid129": (129, True, 129),
    }
    n, taper, g = labels[case["method"]]
    r = (n - 1) // 2
    cy, cx = case["center_yx"]
    height, width = case["image_shape"]
    y, x = np.mgrid[-r : r + 1, -r : r + 1]
    inside = (y + cy >= 0) & (y + cy < height) & (x + cx >= 0) & (x + cx < width)
    one = np.hanning(n) if taper else np.ones(n)
    window = one[:, None] * one[None, :] * inside
    design = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3).astype(float)
    q = np.linalg.qr(window.reshape(-1, 1) * design, mode="reduced")[0]
    fy, fx = case["frequency"]["native_fyx"]
    if case["mode"] == "nearest_available_carrier":
        ky, kx = [round(v * 2 * g) for v in [fy, fx]]
        my, mx = ky / (2 * g), kx / (2 * g)
    else:
        my, mx = fy, fx
    dft = np.exp(-2j * np.pi * (my * (2 * y) + mx * (2 * x))).ravel() / n
    row = (dft - (dft @ q) @ q.T) * window.ravel()
    variance = np.ones_like(x, dtype=float)
    if case["noise"] == "graded":
        variance = 0.7 + 0.2 * (y + cy) / (height - 1) + 0.4 * (x + cx) / (width - 1)
    phase = 2 * np.pi * (fy * (2 * y) + fx * (2 * x))
    a = np.sum(row * np.cos(phase).ravel())
    b = np.sum(row * np.sin(phase).ravel())
    noise = float(np.vdot(row, variance.ravel() * row).real)
    signal = float((abs(a) ** 2 + abs(b) ** 2) / 2)
    return {
        "measured_native_fyx": [my, mx],
        "cos_response_real_imag": [float(a.real), float(a.imag)],
        "sin_response_real_imag": [float(b.real), float(b.imag)],
        "noise_trace_variance": noise,
        "phase_averaged_signal_power": signal,
        "phase_averaged_signal_to_noise_power": signal / noise,
        "observed_pixels": int(np.count_nonzero(window)),
        "raw_taper_effective_sample_count_without_affine": float(
            window.sum() ** 2 / (window**2).sum()
        ),
    }
