"""Independent weighted QR, spectral variance and sorted-distance selection."""

import numpy as np


def qr_spectrum(image, variance):
    image, variance = np.asarray(image, dtype=np.float64), np.asarray(variance, dtype=np.float64)
    h, w = image.shape
    yy, xx = np.meshgrid(np.linspace(-1, 1, h), np.linspace(-1, 1, w), indexing="ij")
    window = np.hanning(h)[:, None] * np.hanning(w)[None]
    design = np.stack([np.ones_like(xx), xx, yy], -1) * window[..., None]
    q = np.linalg.qr(design.reshape(-1, 3), mode="reduced")[0].reshape(h, w, 3)
    weighted = (image - image[0, 0]) * window
    residual = weighted - np.einsum("hwi,i->hw", q, np.einsum("hwi,hw->i", q, weighted))
    spectrum = np.fft.fft2(residual, norm="ortho")
    fq = np.fft.fft2(q, axes=(0, 1), norm="ortho")
    cross = np.fft.fft2(q * (variance * window**2)[..., None], axes=(0, 1), norm="ortho")
    covariance = np.einsum("hwi,hwj,hw->ij", q, q, variance * window**2)
    noise = (
        np.mean(variance * window**2)
        - 2 * np.real(np.sum(fq.conj() * cross, -1))
        + np.einsum("hwi,ij,hwj->hw", fq, covariance, fq.conj()).real
    )
    return spectrum, np.maximum(noise, 0)


def reference_score(field, variance, colors):
    power = []
    for phase in range(4):
        if colors[0, phase] == 1:
            spectrum, noise = qr_spectrum(field[0, phase], variance[0, phase])
            power.append(abs(spectrum) ** 2 / np.maximum(noise, (1 / 65535) ** 2))
    mean = (power[0] + power[1]) / 2
    # Sliding windows over explicit wrap padding instead of circular rolls.
    padded = np.pad(mean, 1, mode="wrap")
    return np.lib.stride_tricks.sliding_window_view(padded, (3, 3)).mean((-2, -1))


def reference_selection(score, lower, *, count=8):
    h, w = score.shape
    ys, xs = [np.fft.fftfreq(n) / 2 for n in [h, w]]
    candidates = []
    for y in range(h):
        for x in range(w):
            radius = np.hypot(ys[y], xs[x])
            if lower <= radius <= 1 / 3 and (ys[y] > 0 or (ys[y] == 0 and xs[x] > 0)):
                candidates.append((-float(score[y, x]), y * w + x))
    selected = []
    for _, flat in sorted(candidates):
        y, x = divmod(flat, w)
        blocked = False
        for cy, cx in selected:
            for sign in [-1, 1]:
                dy, dx = (y - sign * cy) % h, (x - sign * cx) % w
                if min(dy, h - dy) <= 1 and min(dx, w - dx) <= 1:
                    blocked = True
        if not blocked:
            selected.append([y, x])
            if len(selected) == count:
                return selected
    raise ValueError("Too few unsuppressed candidates")
