"""Independent orthonormal-QR spectral rows and explicit rectangular DFT rows."""

import math

import numpy as np


def qr_spectrum(image, variance):
    image, variance = np.asarray(image, dtype=float), np.asarray(variance, dtype=float)
    h, w = image.shape
    y, x = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    window = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    basis = np.stack((np.ones_like(y), x, y), axis=-1).reshape(-1, 3)
    q = np.linalg.qr(window.ravel()[:, None] * basis, mode="reduced")[0]
    weighted = (image - image[0, 0]).ravel() * window.ravel()
    residual = (weighted - q @ (q.T @ weighted)).reshape(h, w)
    spectrum = np.fft.fft2(residual, norm="ortho")
    qgrid = q.reshape(h, w, 3)
    fq = np.fft.fft2(qgrid, axes=(0, 1), norm="ortho")
    effective = variance * window**2
    cross = np.fft.fft2(effective[..., None] * qgrid, axes=(0, 1), norm="ortho")
    covariance = q.T @ (effective.ravel()[:, None] * q)
    noise = effective.mean() - 2 * (fq.conj() * cross).sum(-1).real
    noise += np.einsum("hwi,ij,hwj->hw", fq, covariance, fq.conj()).real
    return spectrum, np.maximum(noise, 0), q, window


def dense_spectral_row(shape, bin_yx, q, window):
    y, x = np.indices(shape)
    ky, kx = bin_yx
    row = np.exp(-2j * np.pi * (ky * y / shape[0] + kx * x / shape[1])).ravel() / math.sqrt(
        np.prod(shape)
    )
    return (row - (row @ q) @ q.T) * window.ravel()


def sorted_select(spectrum, variance, lower, upper, inclusive=True, count=4):
    h, w = spectrum.shape
    fy, fx = [np.fft.fftfreq(n) / 2 for n in [h, w]]
    y, x = np.indices((h, w))
    r = np.hypot(fy[:, None], fx[None, :])
    allowed = (
        (r >= lower)
        & ((r <= upper) if inclusive else (r < upper))
        & ((fy[:, None] > 0) | ((fy[:, None] == 0) & (fx[None, :] > 0)))
    )
    yy, xx = y[allowed], x[allowed]
    power = abs(spectrum[allowed]) ** 2 / variance[allowed]
    order = np.lexsort((xx, yy, -power))
    result = []
    for i in order:
        cy, cx = int(yy[i]), int(xx[i])
        suppressed = False
        for sy, sx in result:
            for a, b in [(sy, sx), ((-sy) % h, (-sx) % w)]:
                if (
                    min(abs(cy - a), h - abs(cy - a)) <= 1
                    and min(abs(cx - b), w - abs(cx - b)) <= 1
                ):
                    suppressed = True
        if not suppressed:
            result.append([cy, cx])
        if len(result) == count:
            break
    return result


def independent_footprint(shape, bins, radius):
    y, x = np.indices(shape)
    covered = np.zeros(shape, bool)
    for sy, sx in bins:
        for a, b in [(sy, sx), ((-sy) % shape[0], (-sx) % shape[1])]:
            dy = np.abs(y - a)
            dx = np.abs(x - b)
            covered |= (np.minimum(dy, shape[0] - dy) <= radius) & (
                np.minimum(dx, shape[1] - dx) <= radius
            )
    return covered


def direct_local_power(raw, variance, bin_yx, center, window=65):
    h, w = raw.shape
    cy, cx = center
    y0, y1 = max(0, cy - window // 2), min(h, cy + window // 2 + 1)
    x0, x1 = max(0, cx - window // 2), min(w, cx + window // 2 + 1)
    y, x = np.mgrid[y0:y1, x0:x1]
    basis = np.stack((np.ones_like(x), x - x.mean(), y - y.mean()), axis=-1).reshape(-1, 3)
    q = np.linalg.qr(basis.astype(float), mode="reduced")[0]
    ky, kx = [k if k <= (n - 1) // 2 else k - n for k, n in zip(bin_yx, [h, w], strict=True)]
    row = np.exp(-2j * np.pi * (ky * y / h + kx * x / w)).ravel()
    row -= (row @ q) @ q.T
    values = raw[y0:y1, x0:x1].astype(float).ravel()
    values = values - values[0]
    coefficient = row @ values
    noise = (abs(row) ** 2) @ variance[y0:y1, x0:x1].astype(float).ravel()
    return float(abs(coefficient) ** 2 / max(float(noise), (1 / 65535) ** 2))
