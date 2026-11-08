"""NumPy real spatial subtemplates and analytic output derivatives for audit."""

import math

import numpy as np


def independent(output, target, pairs, floor):
    derivative = np.zeros_like(output, dtype=np.float64)
    if not len(pairs):
        return 0.0, derivative
    height, width = output.shape[-2:]
    y, x = np.meshgrid(np.fft.fftfreq(height), np.fft.fftfreq(width), indexing="ij")
    iy, ix = np.mgrid[:height, :width]
    partner = ((-iy) % height) * width + ((-ix) % width)
    representative = np.minimum(iy * width + ix, partner)
    # Half-open angular comparisons, instead of production Cartesian tests.
    angles = np.mod(np.arctan2(y, x), math.pi).reshape(-1)[representative]
    masks = []
    for offset in [0.0, math.pi / 8]:
        shifted = np.mod(angles - offset, math.pi)
        labels = sum(shifted >= k * math.pi / 4 for k in [1, 2, 3])
        for sector in range(4):
            mask = labels == sector
            mask[0, 0] = False
            masks.append(mask)
    loss = 0.0
    for a, b in pairs:
        delta = target[a] - target[b]
        template = delta - delta.mean((1, 2), keepdims=True)
        error = output[a] - output[b] - delta
        error -= error.mean((1, 2), keepdims=True)
        spectrum = np.fft.fft2(template)
        for mask in masks:
            value = np.fft.ifft2(spectrum * mask)
            assert abs(value.imag).max() < 1e-12
            component = value.real
            unit = np.mean(component * component) + (floor / 65535) ** 2
            residual = np.mean(error * component) / unit
            loss += (math.sqrt(1 + residual * residual) - 1) / (8 * len(pairs))
            centered = component - component.mean((1, 2), keepdims=True)
            grad = (
                residual
                / math.sqrt(1 + residual * residual)
                * centered
                / (unit * template.size * 8 * len(pairs))
            )
            derivative[a] += grad
            derivative[b] -= grad
    return loss, derivative
