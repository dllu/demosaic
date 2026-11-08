"""Local linear Fourier measurements with exact supplied-noise propagation.

Frequency selection is external. Each clipped rectangular window removes its
own affine plane. No target, threshold, RGB restoration or learned model enters
these measurements. Observed-intensity variance proxies are not calibrated
confidence, and native CFA aliases remain unresolved.
"""

import math

import numpy as np


def box_sums(values, boxes):
    values, boxes = np.asarray(values), np.asarray(boxes)
    if (
        values.ndim != 2
        or boxes.ndim != 2
        or boxes.shape[1] != 4
        or not np.issubdtype(boxes.dtype, np.integer)
    ):
        raise ValueError("Expected a 2D field and integer Nx4 xywh boxes")
    x, y, width, height = boxes.T
    if not (
        (x >= 0)
        & (y >= 0)
        & (width > 0)
        & (height > 0)
        & (x + width <= values.shape[1])
        & (y + height <= values.shape[0])
    ).all():
        raise ValueError("Boxes must lie inside the field")
    integral = np.pad(values.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (
        integral[y + height, x + width]
        - integral[y, x + width]
        - integral[y + height, x]
        + integral[y, x]
    )


def local_phase_projection(image, variance, bin_yx, *, window, centers_yx):
    """Return complex box coefficients and their conditional variance.

    For local Q=[1,x-cx,y-cy], a=carrier-Q(Q'Q)^-1Q'carrier and c=a'image.
    The variance is sum(variance*abs(a)^2), including the fitted-plane terms.
    Summed-area moments evaluate these rows without constructing every patch.
    Partial edge windows use actual clipped support, without padding data.
    """
    image = np.asarray(image, dtype=np.float64)
    variance = np.asarray(variance, dtype=np.float64)
    centers = np.asarray(centers_yx)
    frequency = np.asarray(bin_yx)
    if image.ndim != 2 or min(image.shape) < 8 or variance.shape != image.shape:
        raise ValueError("Expected matching image/variance with axes at least eight")
    if not np.isfinite(image).all() or not np.isfinite(variance).all() or (variance < 0).any():
        raise ValueError("Expected finite image and nonnegative finite variance")
    if type(window) is not int or window < 3 or window % 2 != 1:
        raise ValueError("Window must be an odd integer at least three")
    if (
        centers.ndim != 2
        or centers.shape[1] != 2
        or not len(centers)
        or not np.issubdtype(centers.dtype, np.integer)
    ):
        raise ValueError("Expected nonempty integer Nx2 yx centers")
    height, width = image.shape
    if not ((centers >= 0) & (centers < [height, width])).all():
        raise ValueError("Centers must lie inside the field")
    if (
        frequency.shape != (2,)
        or not np.issubdtype(frequency.dtype, np.integer)
        or not ((frequency >= 0) & (frequency < [height, width])).all()
    ):
        raise ValueError("Expected an in-range integer Fourier bin")
    radius = window // 2
    start = np.maximum(centers - radius, 0)
    end = np.minimum(centers + radius + 1, [height, width])
    boxes = np.stack(
        (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
    )
    x0, y0, nx, ny = boxes.T
    cx, cy = x0 + (nx - 1) / 2, y0 + (ny - 1) / 2
    count = nx * ny
    xx = ny * nx * (nx**2 - 1) / 12
    yy = nx * ny * (ny**2 - 1) / 12
    y, x = np.mgrid[:height, :width]
    ky, kx = [
        int(k if k <= (size - 1) // 2 else k - size)
        for k, size in zip(frequency, image.shape, strict=True)
    ]
    period = math.lcm(height, width)
    phase = (ky * y * (period // height) + kx * x * (period // width)) % period
    phase = np.where(phase > period // 2, phase - period, phase)
    carrier = np.exp(-2j * np.pi * phase / period)

    def total(field):
        return box_sums(field, boxes)

    m0 = total(carrier)
    mx = total(x * carrier) - cx * m0
    my = total(y * carrier) - cy * m0
    k0, kx, ky = m0 / count, mx / xx, my / yy
    centered = image - image[0, 0]
    mean = total(centered)
    coefficient = total(centered * carrier) - k0 * mean
    coefficient -= kx * (total(centered * x) - cx * mean)
    coefficient -= ky * (total(centered * y) - cy * mean)

    v0 = total(variance)
    vx0, vy0 = total(variance * x), total(variance * y)
    vx, vy = vx0 - cx * v0, vy0 - cy * v0
    vxx = total(variance * x**2) - 2 * cx * vx0 + cx**2 * v0
    vyy = total(variance * y**2) - 2 * cy * vy0 + cy**2 * v0
    vxy = total(variance * x * y) - cx * vy0 - cy * vx0 + cx * cy * v0
    vc = total(variance * carrier)
    vxc, vyc = total(variance * x * carrier) - cx * vc, total(variance * y * carrier) - cy * vc
    noise = v0 - 2 * np.real(k0.conj() * vc + kx.conj() * vxc + ky.conj() * vyc)
    noise += abs(k0) ** 2 * v0 + abs(kx) ** 2 * vxx + abs(ky) ** 2 * vyy
    noise += 2 * np.real(k0.conj() * kx * vx + k0.conj() * ky * vy + kx.conj() * ky * vxy)
    if not np.isfinite(coefficient).all() or not np.isfinite(noise).all():
        raise ArithmeticError("Nonfinite projected coefficients or variance")
    if (noise < -2e-9 * np.maximum(v0, np.finfo(float).tiny)).any():
        raise ArithmeticError("Negative propagated variance beyond rounding")
    return {"coefficient": coefficient, "noise_variance": np.maximum(noise, 0), "boxes_xywh": boxes}
