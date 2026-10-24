"""Independent NumPy64 reductions of retained native predictions (no Torch)."""

import numpy as np


def linear_rgb(value, supervision):
    return np.einsum("bij,bjhw->bihw", supervision["matrix"].astype(np.float64),
                     value.astype(np.float64)*supervision["wb"].astype(np.float64)[..., None, None])


def display(value, supervision, exposure=1):
    value = np.clip(linear_rgb(value*exposure, supervision), 0, 1)
    return np.where(value <= .0031308, 12.92*value, 1.055*value**(1/2.4)-.055)


def _psnr(mse):
    return -10*np.log10(np.maximum(mse, 1e-12))


def photometry(prediction, supervision, *, border=8, camera=False):
    """Per-image scores; camera references are auxiliary except measured CFA."""
    if border < 0 or min(prediction.shape[-2:])-2*border < 2:
        raise ValueError("Border leaves no metric region")
    region = (..., slice(border, -border or None), slice(border, -border or None))
    p = prediction[region].astype(np.float64)
    target = supervision["reference_rgb" if camera else "target"][region].astype(np.float64)
    a, b = (display(v, supervision) for v in (p, target))
    error = a-b
    result = {"linear_psnr": _psnr(np.mean((np.clip(p, 0, 1)-np.clip(target, 0, 1))**2, axis=(1, 2, 3))),
              "srgb_psnr": _psnr(np.mean(error**2, axis=(1, 2, 3))),
              "chroma_mae": np.mean(np.abs(error-error.mean(1, keepdims=True)), axis=(1, 2, 3)),
              "gradient_mae": sum(np.mean(np.abs(np.diff(a, axis=d)-np.diff(b, axis=d)), axis=(1, 2, 3)) for d in (-1, -2))/2}
    if camera:
        reference = supervision["sensor_reference"][region].astype(np.float64)
        mask = supervision["sensor_mask"][region]
        if mask.shape != p.shape or np.any((mask != 0) & (mask != 1)):
            raise ValueError("Measured CFA mask must be binary at native RGB shape")
        count = mask.sum((1, 2, 3))
        mse = np.sum((np.clip(p, 0, 1)-reference)**2*mask, axis=(1, 2, 3))/np.maximum(count, 1)
        result = {"sensor_psnr": np.where(count >= 1024, _psnr(mse), np.nan),
                  "reference_samples": count,
                  **{"ahd_"+k: result[k] for k in ("srgb_psnr", "chroma_mae", "gradient_mae")}}
    return result


def texture(prediction, supervision, *, period=None, roi=(48, 48, 160, 160)):
    """Orthogonal Fourier sums for carriers; exact FFT bands for neutral flats."""
    x, y, w, h = roi
    a, b = (linear_rgb(v, supervision)[..., y:y+h, x:x+w] for v in (prediction, supervision["target"]))
    if a.shape[-2:] != (h, w):
        raise ValueError("Texture ROI exceeds the retained context")
    rmse = np.sqrt(np.mean((a-b)**2, axis=(1, 2, 3)))
    if period is None:
        weights = np.array([.2126, .7152, .0722])
        luma, truth = (np.einsum("c,bchw->bhw", weights, v) for v in (a, b))
        centered = luma-luma.mean((-2, -1), keepdims=True)
        spectrum = np.abs(np.fft.fft2(centered))
        # Match the evaluator's FP32 frequency-bin boundary definition.
        fy, fx = np.fft.fftfreq(h).astype(np.float32), np.fft.fftfreq(w).astype(np.float32)
        radius = np.sqrt(fy[:, None]**2+fx[None, :]**2)
        band = (radius >= 1/48) & (radius <= .22)
        level = np.maximum(np.abs(truth.mean((-2, -1))), 1e-12)
        return {"dc_bias_abs_rgb": np.abs(a.mean((-2, -1))-b.mean((-2, -1))).mean(1),
                "linear_srgb_rmse": rmse, "spatial_luma_rms": np.sqrt(np.mean(centered**2, axis=(-2, -1))),
                "relative_band_rms": np.sqrt(np.sum(spectrum**2*band, axis=(-2, -1)))/(h*w)/level,
                "relative_peak_band_contrast": 2*np.max(spectrum*band, axis=(-2, -1))/(h*w)/level}
    if period not in (4, 8, 16) or w % period:
        raise ValueError("Carrier period must divide the ROI and be 4, 8 or 16")
    angle = np.arange(x, x+w)*2*np.pi/period
    cosine, sine = np.cos(angle)[None, None, None], np.sin(angle)[None, None, None]
    def coefficients(v):
        return np.stack([v.mean((-2, -1)), 2*(v*cosine).mean((-2, -1)), 2*(v*sine).mean((-2, -1))], axis=-1)
    ca, cb = coefficients(a), coefficients(b)
    u, v = ca[..., 1:], cb[..., 1:]
    power = np.maximum(np.sum(v*v, axis=-1), 1e-24)
    gain = np.sum(u*v, axis=-1)/power
    residual = a-(ca[..., 0, None, None]+ca[..., 1, None, None]*cosine+ca[..., 2, None, None]*sine)
    return {"in_phase_gain": gain.mean(1), "gain_channel_std": gain.std(1),
            "quadrature_gain": ((v[..., 0]*u[..., 1]-u[..., 0]*v[..., 1])/power).mean(1),
            "amplitude_ratio": np.sqrt(np.sum(u*u, axis=-1)/power).mean(1),
            "dc_bias_abs": np.abs(ca[..., 0]-cb[..., 0]).mean(1), "noncarrier_rms": np.sqrt(np.mean(residual**2, axis=(1, 2, 3))),
            "linear_srgb_rmse": rmse}


def color(prediction, supervision):
    """Unclipped camera-space/color/CFA errors on each native 160-pixel ROI."""
    p = prediction[..., 48:208, 48:208].astype(np.float64)
    t = supervision["target"][..., 48:208, 48:208].astype(np.float64)
    if p.shape != (1, 3, 160, 160) or not np.array_equal(t, np.broadcast_to(t[..., :1, :1], t.shape)):
        raise ValueError("Color cases require one native256 constant-target observation")
    error = p-t
    means, mse = error.mean((0, 2, 3)), float(np.mean(error**2))
    phases, observed = [], []
    for phase, channel in enumerate(supervision["colors"][0]):
        y, x = divmod(phase, 2)
        phases.append(float(error[:, channel, y::2, x::2].mean()))
        observed.append(float((supervision["packed"][:, phase, 24:104, 24:104].astype(np.float64)-t[:, channel, y::2, x::2]).mean()))
    return {"camera_RGB_mean_error": means.tolist(), "camera_RGB_MSE": mse,
            "camera_RGB_mean_component_fraction": float(np.mean(means**2)/max(mse, 1e-24)),
            "spatially_centered_camera_RGB_RMS": float(np.sqrt(np.mean((error-means[None, :, None, None])**2))),
            "predicted_minus_GT_CFA_phase_mean": phases, "observed_minus_GT_CFA_phase_mean": observed}


def noisy_malvar(supervision):
    """Independent 5×5 Malvar preview of actual packed CFA, without denoising."""
    packed = supervision["packed"].astype(np.float64)
    colors = supervision["colors"]
    batch, _, h, w = packed.shape
    wb = np.maximum(supervision["wb"].astype(np.float64), 1e-6)
    raw = np.empty((batch, 2*h, 2*w))
    masks = np.zeros((batch, 3, 2*h, 2*w), bool)
    for phase in range(4):
        y, x = divmod(phase, 2)
        raw[:, y::2, x::2] = packed[:, phase]*wb[np.arange(batch), colors[:, phase], None, None]
        masks[np.arange(batch), colors[:, phase], y::2, x::2] = True
    green = np.array([[0, 0, -1, 0, 0], [0, 0, 2, 0, 0], [-1, 2, 4, 2, -1], [0, 0, 2, 0, 0], [0, 0, -1, 0, 0]])/8
    horizontal = np.array([[0, 0, .5, 0, 0], [0, -1, 0, -1, 0], [-1, 4, 5, 4, -1], [0, -1, 0, -1, 0], [0, 0, .5, 0, 0]])/8
    diagonal = np.array([[0, 0, -1.5, 0, 0], [0, 2, 0, 2, 0], [-1.5, 0, 6, 0, -1.5], [0, 2, 0, 2, 0], [0, 0, -1.5, 0, 0]])/8
    padded = np.pad(raw, ((0, 0), (2, 2), (2, 2)), mode="reflect")
    def convolve(kernel):
        return sum(kernel[y, x]*padded[:, y:y+2*h, x:x+2*w] for y, x in zip(*np.nonzero(kernel), strict=True))
    g, horizontal, vertical, diagonal = map(convolve, (green, horizontal, horizontal.T, diagonal))
    parity = np.arange(2*h)[None, :, None] % 2
    red_row, blue_row = (np.argmax(colors == c, axis=1)[:, None, None]//2 for c in (0, 2))
    red = np.where(masks[:, 0], raw, np.where(masks[:, 2], diagonal, np.where(parity == red_row, horizontal, vertical)))
    blue = np.where(masks[:, 2], raw, np.where(masks[:, 0], diagonal, np.where(parity == blue_row, horizontal, vertical)))
    return np.stack([red, np.where(masks[:, 1], raw, g), blue], axis=1)/wb[..., None, None]
