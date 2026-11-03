"""Experimental local periodic-detail refinement from measured Bayer evidence.

Frequency selection and noise proxies reuse the observation and are not calibrated
confidence. Use explicitly: partial texture can leak into neighbouring flat regions.
"""

import time

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


def fit_patch_harmonics(packed, variance, colors, base):
    packed, variance, base = [np.asarray(v, dtype=np.float64) for v in (packed, variance, base)]
    colors = np.asarray(colors)
    if (
        packed.shape != (4, 128, 128)
        or variance.shape != packed.shape
        or base.shape != (3, 256, 256)
    ):
        raise ValueError("Require native256 RGB and matching four128x128 packed phases")
    if (
        colors.shape != (4,)
        or not np.issubdtype(colors.dtype, np.integer)
        or tuple(colors)
        not in {
            (0, 1, 1, 2),
            (2, 1, 1, 0),
            (1, 0, 2, 1),
            (1, 2, 0, 1),
        }
    ):
        raise ValueError("Require a standard Bayer phase layout")
    if not all(np.isfinite(v).all() for v in (packed, variance, base)) or np.any(variance < 0):
        raise ValueError("Require finite inputs and nonnegative variance")
    if not np.any(variance > 0):
        return {"base": base, "peaks": [], "ADC_only_bypass": True}
    g = green_pair(packed, variance, colors)
    if g["noise_units_signed_cross"] is None:
        return {"base": base, "peaks": [], "green_variance_unavailable": True}
    fx, fy = g["native_fx"], g["native_fy"]
    radius = np.hypot(fx, fy)
    valid = (radius >= 0.03) & (radius <= 0.22) & (fy > 0) & (g["signed_coherence"] > 0.8)
    score = np.where(valid, g["noise_units_signed_cross"], -np.inf).copy()
    peaks = []
    iy, ix = np.indices(score.shape)
    for _ in range(4):
        p = np.unravel_index(np.argmax(score), score.shape)
        if score[p] < 5:
            break
        peaks.append((float(fx[p]), float(fy[p]), float(score[p])))
        dy = np.minimum(abs(iy - p[0]), 128 - abs(iy - p[0]))
        dx = np.minimum(abs(ix - p[1]), 128 - abs(ix - p[1]))
        score[dx * dx + dy * dy <= 16] = -np.inf
    if not peaks:
        return {"base": base, "peaks": []}
    yy, xx = np.mgrid[:128, :128]
    plane = np.stack([np.ones_like(xx), xx / 127, yy / 127], -1).reshape(-1, 3)
    cols = 12 + 6 * len(peaks)
    design = np.zeros((65536, cols))
    residual = np.empty((4, 128, 128))
    for phase, color in enumerate(colors):
        s = slice(phase * 16384, (phase + 1) * 16384)
        design[s, phase * 3 : phase * 3 + 3] = plane
        y, x = 2 * yy + phase // 2, 2 * xx + phase % 2
        residual[phase] = packed[phase] - base[color, phase // 2 :: 2, phase % 2 :: 2]
        for k, (fx, fy, _) in enumerate(peaks):
            a = 2 * np.pi * (fx * x + fy * y)
            c = 12 + 6 * k + 2 * int(color)
            design[s, c] = np.cos(a).ravel()
            design[s, c + 1] = np.sin(a).ravel()
    window = np.hanning(128)[:, None] * np.hanning(128)[None]
    weights = (window[None] / np.sqrt(variance.clip(1e-10))).ravel()
    a = design * weights[:, None]
    b = residual.ravel() * weights
    gram = a.T @ a
    covariance = np.linalg.inv(gram)
    beta = np.linalg.solve(gram, a.T @ b)
    return {
        "base": base,
        "packed": packed,
        "variance": variance,
        "colors": colors,
        "peaks": peaks,
        "beta": beta,
        "covariance": covariance,
        "residual": residual,
        "plane": plane,
    }


def separable_sum(values, ky, kx):
    """Zero extension avoids reflecting one noisy sample into multiple positions."""
    result = np.asarray(values, dtype=np.float64)
    for axis, kernel in ((0, ky), (1, kx)):
        padding = [(0, 0), (0, 0)]
        padding[axis] = (len(kernel) // 2, len(kernel) // 2)
        result = np.apply_along_axis(
            lambda row, kernel=kernel: np.convolve(row, kernel, mode="valid"),
            axis,
            np.pad(result, padding, mode="constant"),
        )
    return result


def envelope_terms(
    residual, variance, colors, phase_planes, green_coefficients, frequency, sigma_native=32
):
    """Conditional local matched sums at physical packed-cell centers.

    The squared kernels propagate independent input variance with fixed global
    coefficients. Selection, coefficient fitting and variance estimation use
    the same noisy input, so this is not unconditional calibrated confidence.
    """
    if sigma_native <= 0 or not np.isfinite(sigma_native):
        raise ValueError("Local envelope scale must be finite and positive")
    height, width = residual.shape[-2:]
    yy, xx = np.mgrid[:height, :width]
    numerator = np.zeros((height, width))
    denominator, noise = np.zeros_like(numerator), np.zeros_like(numerator)
    sigma = sigma_native / 2
    radius = int(np.ceil(4 * sigma))
    coordinates = np.arange(-radius, radius + 1)
    fx, fy = frequency
    for phase in np.flatnonzero(np.asarray(colors) == 1):
        oy, ox = divmod(int(phase), 2)
        angle = 2 * np.pi * (fx * (2 * xx + ox) + fy * (2 * yy + oy))
        template = green_coefficients[0] * np.cos(angle) + green_coefficients[1] * np.sin(angle)
        var = np.asarray(variance[phase], dtype=np.float64).clip(1e-10)
        # Output cell center is(2*y+.5,2*x+.5); each measured phase has its own offset.
        ky = np.exp(-0.5 * ((coordinates - (oy - 0.5) / 2) / sigma) ** 2)
        kx = np.exp(-0.5 * ((coordinates - (ox - 0.5) / 2) / sigma) ** 2)
        ky, kx = ky / ky.sum(), kx / kx.sum()
        numerator += separable_sum((residual[phase] - phase_planes[phase]) * template / var, ky, kx)
        denominator += separable_sum(template**2 / var, ky, kx)
        noise += separable_sum(template**2 / var, ky**2, kx**2)
    return numerator, denominator, noise


def native_envelope(values):
    """Interpolate the smooth envelope; native harmonic/crop samples are retained."""
    height, width = values.shape
    ys, xs = (np.arange(2 * height) - 0.5) / 2, (np.arange(2 * width) - 0.5) / 2
    result = np.apply_along_axis(lambda row: np.interp(ys, np.arange(height), row), 0, values)
    return np.apply_along_axis(lambda row: np.interp(xs, np.arange(width), row), 1, result)


def correct_local_patch(packed, variance, colors, base):
    fitted = fit_patch_harmonics(packed, variance, colors, base)
    base, peaks = fitted["base"], fitted["peaks"]
    if not peaks:
        return base.copy(), {k: v for k, v in fitted.items() if k != "base"}
    beta, covariance = fitted["beta"], fitted["covariance"]
    residual, variance, colors = fitted["residual"], fitted["variance"], fitted["colors"]
    planes = np.stack(
        [(fitted["plane"] @ beta[3 * p : 3 * p + 3]).reshape(128, 128) for p in range(4)]
    )
    yy, xx = np.mgrid[:256, :256]
    field, diagnostics = np.zeros_like(base), []
    for k, (fx, fy, _) in enumerate(peaks):
        indices = [12 + 6 * k + 2, 12 + 6 * k + 3]
        coefficients = beta[indices]
        power = float(
            coefficients @ np.linalg.solve(covariance[np.ix_(indices, indices)], coefficients)
        )
        gate = max(0, 1 - 9 / max(power, 1e-12))
        if gate == 0:
            diagnostics.append({"power": power, "gate": 0})
            continue
        n, d, v = envelope_terms(residual, variance, colors, planes, coefficients, (fx, fy))
        shrink = np.maximum(0, 1 - 4 * v / np.maximum(n**2, 1e-32))
        envelope = native_envelope(np.clip(n / np.maximum(d, 1e-16), 0, 3) * shrink)
        angle = 2 * np.pi * (fx * xx + fy * yy)
        for color in range(3):
            i = 12 + 6 * k + 2 * color
            field[color] += (
                gate * envelope * (beta[i] * np.cos(angle) + beta[i + 1] * np.sin(angle))
            )
        diagnostics.append(
            {
                "power": power,
                "gate": gate,
                "envelope_min": float(envelope.min()),
                "envelope_max": float(envelope.max()),
                "envelope_mean": float(envelope.mean()),
                "active_fraction": float(np.mean(envelope > 0)),
            }
        )
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    return base + field * taper[None], {
        "peaks": peaks,
        "local": diagnostics,
        "sigma_native": 32,
        "variance_shrink": 4,
        "envelope_cap": 3,
        "border_apron_native": 32,
    }


def _origins(length, stride):
    starts = list(range(0, length - 255, stride))
    if starts[-1] != length - 256:
        starts.append(length - 256)
    return starts


def refine_phase_harmonics(
    raw, colors, base, *, shot, read, stride=128, envelope="edge", tv_device="cpu"
):
    """Return CPU float32 camera RGB and diagnostics for an arbitrary Bayer image.

    Fixed native256 patches overlap on even sensor coordinates. Normalize their
    tapered corrections, including inactive patches, and retain the outer-image
    fade. Only incomplete CFA cells/small images need phase-preserving extension.
    Edge-preserving complex envelopes are current; ``complex``/``scalar`` retain
    earlier Gaussian-envelope modes. The optional TV solver uses local CUDA
    buffers when requested; complete image accumulators remain on the CPU.
    Large accumulators are float32; spectral selection/fits remain float64.
    No clipping, color conversion, reference image, RNG or neural calls occur.
    """
    started = time.perf_counter()
    raw, base = np.asarray(raw), np.asarray(base)
    colors = np.asarray(colors)
    if raw.ndim != 2 or min(raw.shape) < 2 or base.shape != (3, *raw.shape):
        raise ValueError("Require a >=2x2 Bayer image and matching 3xHxW camera RGB")
    if not np.isfinite(raw).all() or not np.isfinite(base).all():
        raise ValueError("RAW and RGB must be finite")
    if not np.isfinite([shot, read]).all() or min(shot, read) < 0:
        raise ValueError("Require finite nonnegative shot/read variance coefficients")
    if not isinstance(stride, (int, np.integer)) or stride % 2 or not 2 <= stride <= 192:
        raise ValueError("Stride must be even and between 2 and 192 native pixels")
    if envelope not in ("scalar", "complex", "edge"):
        raise ValueError("Envelope must be scalar, complex or edge")
    if envelope == "edge":
        from functools import partial

        from .phase_tv import correct_edge_phase_patch

        corrector = partial(correct_edge_phase_patch, device=tv_device)
    elif envelope == "complex":
        from .phase_envelope import correct_complex_patch

        corrector = correct_complex_patch
    else:
        corrector = correct_local_patch
    if (
        colors.shape != (4,)
        or not np.issubdtype(colors.dtype, np.integer)
        or tuple(colors) not in {(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)}
    ):
        raise ValueError("Require a standard integer Bayer phase layout")
    result = np.array(base, dtype=np.float32, copy=True)
    metadata = {
        "method": {
            "scalar": "local-phase-harmonic-v1",
            "complex": "local-phase-harmonic-v2",
            "edge": "local-phase-harmonic-v3",
        }[envelope],
        "envelope": envelope,
        "enabled": True,
        "stride_native": int(stride),
        "tile_native": 256,
        "working_precision": "float64 fits; float32 full-image accumulation/output",
        "noise": "max(observed RAW,0)*shot+read; same convention as neural inference",
        "confidence_calibrated": False,
        "patches": 0,
        "selected_patches": 0,
        "active_patches": 0,
        "selected_frequencies": 0,
        "new_model_calls": 0,
    }
    if envelope == "edge":
        metadata["TV"] = {
            "device": str(tv_device),
            "solves": 0,
            "iterations": 0,
            "capped": 0,
            "maximum_relative_primal_dual_gap": 0.0,
        }
    if shot == read == 0:
        metadata.update(ADC_only_bypass=True, seconds=time.perf_counter() - started)
        return result, metadata
    height, width = raw.shape
    padded_h, padded_w = max(256, height + height % 2), max(256, width + width % 2)
    # These indices repeat the final complete cell with the requested phase.
    rows, cols = np.arange(padded_h), np.arange(padded_w)
    rows = np.where(rows < height, rows, 2 * ((height - 2) // 2) + rows % 2)
    cols = np.where(cols < width, cols, 2 * ((width - 2) // 2) + cols % 2)
    add = np.zeros((3, height, width), dtype=np.float32)
    weights = np.zeros((height, width), dtype=np.float32)
    apron = np.sin(np.pi * np.arange(32) / 64) ** 2
    one = np.ones(256)
    one[:32], one[-32:] = apron, apron[::-1]
    taper = one[:, None] * one[None, :]
    for y in _origins(padded_h, stride):
        for x in _origins(padded_w, stride):
            tile_rows, tile_cols = rows[y : y + 256], cols[x : x + 256]
            mosaic = np.asarray(raw[np.ix_(tile_rows, tile_cols)], dtype=np.float32)
            packed = np.stack([mosaic[p // 2 :: 2, p % 2 :: 2] for p in range(4)])
            variance = np.maximum(packed, 0) * shot + read
            parent = base[:, tile_rows[:, None], tile_cols]
            corrected, diagnostic = corrector(packed, variance, colors, parent)
            delta = corrected - parent
            h, w = min(256, height - y), min(256, width - x)
            add[:, y : y + h, x : x + w] += delta[:, :h, :w]
            weights[y : y + h, x : x + w] += taper[:h, :w]
            metadata["patches"] += 1
            metadata["selected_patches"] += bool(diagnostic.get("peaks"))
            metadata["active_patches"] += bool(np.any(delta))
            metadata["selected_frequencies"] += len(diagnostic.get("peaks", []))
            if envelope == "edge":
                for local in diagnostic.get("local", []):
                    solver = local.get("solver", {}).get("edge")
                    if solver:
                        metadata["TV"]["solves"] += 1
                        metadata["TV"]["iterations"] += solver["iterations"]
                        metadata["TV"]["capped"] += not solver["converged"]
                        metadata["TV"]["maximum_relative_primal_dual_gap"] = max(
                            metadata["TV"]["maximum_relative_primal_dual_gap"],
                            solver["relative_primal_dual_gap"],
                        )
    np.maximum(weights, 1, out=weights)
    np.divide(add, weights[None], out=add)
    result += add
    energy = sum(
        float(np.sum(add[:, y : y + 256].astype(np.float64) ** 2)) for y in range(0, height, 256)
    )
    metadata.update(
        seconds=time.perf_counter() - started,
        extension="Repeat complete Bayer cells only beyond odd/small image boundaries",
        blend="sum tapered deltas / max(sum tapers,1), including inactive patches",
        added_field_rms_DN16=float(np.sqrt(energy / add.size) * 65535),
        max_abs_added_field_DN16=float(np.max(np.abs(add)) * 65535),
    )
    return result, metadata
