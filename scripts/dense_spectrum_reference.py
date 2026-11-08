"""Independent QR patch measurements and sliced native overlap-add in NumPy."""

import numpy as np


def patch_geometry(shape, window, stride):
    axes = [sorted(set(range(0, n, stride)) | {n - 1}) for n in shape]
    centers = [(y, x) for y in axes[0] for x in axes[1]]
    y, x = np.meshgrid(np.linspace(-1, 1, window), np.linspace(-1, 1, window), indexing="ij")
    design = np.stack([np.ones_like(x), x, y], -1).reshape(-1, 3)
    fy, fx = np.meshgrid(np.fft.fftfreq(window) / 2, np.fft.fftfreq(window) / 2, indexing="ij")
    return centers, design, fy, fx


def measurements(
    packed, variance, colors, *, window=65, stride=32, support_windows=(33, 17), centers_yx=None
):
    raw, noise = np.asarray(packed, dtype=float), np.asarray(variance, dtype=float)
    colors = np.broadcast_to(colors, (len(raw), 4))
    h, w = raw.shape[-2:]
    centers, design, fy, fx = patch_geometry((h, w), window, stride)
    if centers_yx is not None:
        allowed = set(centers)
        centers = [tuple(map(int, value)) for value in centers_yx]
        if not centers or len(set(centers)) != len(centers) or not set(centers) <= allowed:
            raise ValueError("Expected distinct actual patch centers")
    r = window // 2
    context = np.empty((len(raw), len(centers), 18, window, window))
    spectra = np.empty((len(raw), len(centers), 3, 2, window, window), dtype=complex)
    propagated = np.empty(spectra.shape, dtype=float)
    for p, (cy, cx) in enumerate(centers):
        y, x = np.indices((window, window))
        sy, sx = cy - r + y, cx - r + x
        valid = (sy >= 0) & (sy < h) & (sx >= 0) & (sx < w)
        yi, xi = np.clip(sy, 0, h - 1), np.clip(sx, 0, w - 1)
        for scale_index, scale in enumerate([window, *support_windows]):
            hann = np.pad(np.hanning(scale), (window - scale) // 2)
            taper = hann[:, None] * hann[None, :] * valid
            q = np.linalg.qr(design * taper.reshape(-1, 1), mode="reduced")[0]
            qfield = q.reshape(window, window, 3)
            fq = np.fft.fft2(qfield, axes=(0, 1), norm="ortho")
            for n, layout in enumerate(colors):
                greens = np.flatnonzero(layout == 1)
                for a, g in enumerate(greens):
                    image = raw[n, g, yi, xi]
                    v = noise[n, g, yi, xi]
                    weighted = (image - image[valid][0]).ravel() * taper.ravel()
                    residual = weighted - q @ (q.T @ weighted)
                    coefficient = np.fft.fft2(residual.reshape(window, window), norm="ortho")
                    effective = v * taper**2
                    cross = np.fft.fft2(effective[..., None] * qfield, axes=(0, 1), norm="ortho")
                    covariance = q.T @ (effective.ravel()[:, None] * q)
                    vfft = effective.mean() - 2 * (fq.conj() * cross).sum(-1).real
                    vfft += np.einsum("hwi,ij,hwj->hw", fq, covariance, fq.conj()).real
                    offset = 2 * np.pi * ((int(g) // 2) * fy + (int(g) % 2) * fx)
                    spectra[n, p, scale_index, a] = coefficient * np.exp(-1j * offset)
                    propagated[n, p, scale_index, a] = np.maximum(vfft, 0)
                z = (
                    spectra[n, p, scale_index]
                    / np.maximum(propagated[n, p, scale_index], (1 / 65535) ** 2) ** 0.5
                )
                pa, pb = abs(z) ** 2
                cross_power = z[0] * z[1].conj() / np.sqrt((1 + pa) * (1 + pb))
                strength = (pa + pb) / (1 + pa + pb)
                context[n, p, scale_index * 6 : (scale_index + 1) * 6] = np.stack(
                    [
                        np.log1p(pa),
                        np.log1p(pb),
                        cross_power.real,
                        cross_power.imag,
                        fx * strength,
                        fy * strength,
                    ]
                )
    return (
        context.reshape(-1, 18, window, window),
        spectra[:, :, 0],
        {
            "centers_yx": centers,
            "image_shape": (h, w),
            "window": window,
            "aligned_spectra": spectra,
            "propagated_variance": propagated,
        },
    )


def native_readout(state, context, coefficient, geometry):
    context, coefficient = np.asarray(context, dtype=float), np.asarray(coefficient, dtype=complex)
    n, patches, _, length, _ = coefficient.shape
    h, w = geometry["image_shape"]
    centers = geometry["centers_yx"]
    state = {k: np.asarray(v, dtype=float) for k, v in state.items()}
    hidden = np.einsum("oc,nchw->nohw", state["context.weight"][:, :, 0, 0], context)
    hidden += state["context.bias"][None, :, None, None]
    hidden /= 1 + np.exp(-hidden)
    weights = np.einsum("oc,nchw->nohw", state["mixing.weight"][:, :, 0, 0], hidden)
    weights += state["mixing.bias"][None, :, None, None]
    weights = weights.reshape(n, patches, 3, 4, length, length)
    output = np.zeros((n, 3, 2 * h, 2 * w))
    denominator = np.zeros((h, w))
    fy, fx = np.meshgrid(np.fft.fftfreq(length) / 2, np.fft.fftfreq(length) / 2, indexing="ij")
    radius = np.hypot(fy, fx)
    eligible = (radius >= 1 / 16) & (radius <= 1 / 3)
    hann = np.hanning(length)
    window = hann[:, None] * hann[None, :]
    r = length // 2
    for p, (cy, cx) in enumerate(centers):
        y0, x0 = cy - r, cx - r
        yl, yh, xl, xh = max(y0, 0), min(y0 + length, h), max(x0, 0), min(x0 + length, w)
        wy, wx = slice(yl - y0, yh - y0), slice(xl - x0, xh - x0)
        denominator[yl:yh, xl:xh] += window[wy, wx] ** 2
        for b in range(n):
            weight = weights[b, p]
            spectrum = (weight[:, 0] + 1j * weight[:, 1]) * coefficient[b, p, 0]
            spectrum += (weight[:, 2] + 1j * weight[:, 3]) * coefficient[b, p, 1]
            spectrum *= eligible
            spectrum = (
                spectrum + np.roll(spectrum[:, ::-1, ::-1], (1, 1), axis=(-2, -1)).conj()
            ) / 2
            for dy in range(2):
                for dx in range(2):
                    phase = np.exp(2j * np.pi * (fy * dy + fx * dx))
                    image = np.fft.ifft2(spectrum * phase, norm="ortho").real * window
                    output[b, :, dy::2, dx::2][:, yl:yh, xl:xh] += image[:, wy, wx]
    return output / np.repeat(np.repeat(denominator, 2, 0), 2, 1)
