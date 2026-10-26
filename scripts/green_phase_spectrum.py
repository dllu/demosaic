"""NumPy diagnostics of separately measured green CFA planes, not restoration.

Phase compensation describes the principal packed-grid band. Aliases can reverse
the signed cross-spectrum; a four-native-pixel carrier can even vanish in one
green phase. Agreement is therefore neither an all-frequency signal detector
nor a calibrated photographic confidence measure.
"""

import numpy as np


def _geometry(shape):
    height, width = shape
    if min(shape) < 8:
        raise ValueError("Spectral fields need at least eight samples per axis")
    y, x = np.meshgrid(np.linspace(-1, 1, height), np.linspace(-1, 1, width), indexing="ij")
    basis = np.stack((np.ones(shape), x, y), axis=-1)
    window = np.hanning(height)[:, None] * np.hanning(width)[None, :]
    gram = np.einsum("hwi,hwj,hw->ij", basis, basis, window**2)
    return basis, window, np.linalg.inv(gram)


def tapered_spectrum(image, variance=None):
    """Hann-taper a weighted-plane residual and propagate independent noise.

    For Q=[1,x,y], W=diag(Hann), beta=(Q'W²Q)^-1 Q'W²image.
    The Fourier operator is F W (I-Q(Q'W²Q)^-1 Q'W²). Its per-coefficient
    noise variance includes the fitted-plane terms, not just mean input noise.
    This is conditional linear propagation for supplied independent variances;
    observed-signal variance proxies are not established camera-noise truth.
    """
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 2 or not np.isfinite(image).all():
        raise ValueError("Expected one finite real image plane")
    basis, window, inverse = _geometry(image.shape)
    beta = inverse @ np.einsum("hwi,hw,hw->i", basis, window**2, image)
    residual = window * (image - np.einsum("hwi,i->hw", basis, beta))
    spectrum = np.fft.fft2(residual, norm="ortho")
    noise = None
    if variance is not None:
        variance = np.asarray(variance, dtype=np.float64)
        if variance.shape != image.shape or not np.isfinite(variance).all() or (variance < 0).any():
            raise ValueError("Variance must be finite, nonnegative and match the image")
        # t_k = a_k - h_k (W² Q)', with a_k the tapered Fourier row.
        transformed_basis = np.fft.fft2(window[..., None] * basis, axes=(0, 1), norm="ortho")
        h = transformed_basis @ inverse
        cross = np.fft.fft2((variance * window**3)[..., None] * basis, axes=(0, 1), norm="ortho")
        covariance = np.einsum("hwi,hwj,hw->ij", basis, basis, variance * window**4)
        base = float(np.mean(variance * window**2))
        noise = (
            base
            - 2 * np.real(np.sum(np.conj(h) * cross, axis=-1))
            + np.real(np.einsum("hwi,ij,hwj->hw", h, covariance, np.conj(h)))
        )
        if np.min(noise) < -1e-10 * max(base, np.finfo(np.float64).tiny):
            raise ArithmeticError("Propagated spectral noise variance became negative")
        noise = np.maximum(noise, 0)
    return {"spectrum": spectrum, "noise_variance": noise, "plane": beta}


def _average3(values):
    return sum(np.roll(values, (y, x), axis=(0, 1)) for y in (-1, 0, 1) for x in (-1, 0, 1)) / 9


def green_pair(packed, variance, colors):
    """Describe both greens on an even-origin four-phase packed RAW field.

    The 3×3 frequency average is not nine independent observations. Its signed
    coherence is bounded by Cauchy-Schwarz, but is not a test probability.
    Noise-normalized cross power has no calibrated false-discovery threshold.
    """
    packed = np.asarray(packed, dtype=np.float64)
    variance = np.asarray(variance, dtype=np.float64)
    colors = np.asarray(colors)
    allowed = {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
    if (
        packed.ndim != 3
        or packed.shape[0] != 4
        or variance.shape != packed.shape
        or colors.shape != (4,)
        or tuple(colors) not in allowed
    ):
        raise ValueError("Expected matching 4×H×W RAW/variance and a standard Bayer layout")
    indices = np.flatnonzero(colors == 1)
    first, second = [tapered_spectrum(packed[i], variance[i]) for i in indices]
    height, width = packed.shape[-2:]
    fy = np.fft.fftfreq(height)[:, None] / 2
    fx = np.fft.fftfreq(width)[None, :] / 2
    y0, x0 = divmod(int(indices[0]), 2)
    y1, x1 = divmod(int(indices[1]), 2)
    alignment = np.exp(2j * np.pi * ((y1 - y0) * fy + (x1 - x0) * fx))
    cross = first["spectrum"] * np.conj(second["spectrum"]) * alignment
    power = np.stack([np.abs(item["spectrum"]) ** 2 for item in (first, second)])
    averaged_cross = _average3(cross)
    averaged_power = np.stack([_average3(p) for p in power])
    denominator = np.sqrt(averaged_power[0] * averaged_power[1])
    coherence = np.divide(
        averaged_cross,
        denominator,
        out=np.zeros_like(averaged_cross),
        where=denominator > np.finfo(np.float64).tiny,
    )
    if np.max(np.abs(coherence)) > 1 + 1e-12:
        raise ArithmeticError("Smoothed cross-spectrum violates Cauchy-Schwarz")
    noise = np.stack([item["noise_variance"] for item in (first, second)])
    averaged_noise = np.stack([_average3(v) for v in noise])
    scale = np.sqrt(averaged_noise[0] * averaged_noise[1])
    normalized_cross = None
    normalized_power = None
    if np.all(scale > 0) and np.all(averaged_noise > 0):
        normalized_cross = np.real(averaged_cross) / scale
        normalized_power = np.mean(averaged_power / averaged_noise, axis=0)
    return {
        "green_phase_indices": indices,
        "spectra": np.stack([first["spectrum"], second["spectrum"]]),
        "noise_variance": noise,
        "power": power,
        "aligned_cross": cross,
        "average_cross": averaged_cross,
        "signed_coherence": np.real(coherence),
        "complex_coherence": coherence,
        "noise_units_signed_cross": normalized_cross,
        "noise_units_mean_phase_power": normalized_power,
        "native_fx": np.broadcast_to(fx, (height, width)).copy(),
        "native_fy": np.broadcast_to(fy, (height, width)).copy(),
        "removed_planes": np.stack([first["plane"], second["plane"]]),
    }


def cross_decomposition(packed, reference, variance, colors):
    """Separate reference, residual and mixed terms in observed green cross-power.

    This is an algebraic diagnostic, not an independence or unbiasedness claim.
    The residual can include added noise, ADC quantization/clipping and reference
    mismatch. A low-noise camera estimate must not be called noiseless GT.
    """
    observed = green_pair(packed, variance, colors)
    target = green_pair(reference, variance, colors)
    if np.shape(reference) != np.shape(packed):
        raise ValueError("Reference must match packed observation geometry")
    signal = target["spectra"]
    residual = observed["spectra"] - signal
    first, second = observed["green_phase_indices"]
    y0, x0 = divmod(int(first), 2)
    y1, x1 = divmod(int(second), 2)
    alignment = np.exp(
        2j * np.pi * ((y1 - y0) * observed["native_fy"] + (x1 - x0) * observed["native_fx"])
    )
    products = {
        "reference": signal[0] * np.conj(signal[1]),
        "residual": residual[0] * np.conj(residual[1]),
        "mixed": signal[0] * np.conj(residual[1]) + residual[0] * np.conj(signal[1]),
    }
    cross = {name: _average3(value * alignment) for name, value in products.items()}
    total = sum(cross.values())
    scale = max(float(np.max(np.abs(observed["average_cross"]))), np.finfo(float).tiny)
    if np.max(np.abs(total - observed["average_cross"])) > 64 * np.finfo(float).eps * scale:
        raise ArithmeticError("Reference/residual/mixed cross-power identity failed")
    noise_scale = np.sqrt(
        np.prod(np.stack([_average3(v) for v in observed["noise_variance"]]), axis=0)
    )
    normalized = None
    if np.all(noise_scale > 0):
        normalized = {name: value.real / noise_scale for name, value in cross.items()}
    return {
        "observed": observed,
        "reference": target,
        "component_cross": cross,
        "noise_units_components": normalized,
    }
