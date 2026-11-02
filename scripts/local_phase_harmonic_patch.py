"""Local RAW evidence limits phase-aware harmonics to supported patch regions."""

import argparse
from pathlib import Path

import numpy as np
from green_phase_spectrum import green_pair
from train_directional_bank_trial import ref, save

from demosaic.safety import writable_path


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("prediction", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.inputs, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("packed", "variance", "colors")}
    base = np.load(args.prediction, allow_pickle=False)
    if base.shape != (1, 3, 256, 256) or arrays["packed"].shape != (1, 4, 128, 128):
        raise ValueError("One native256 patch required")
    value, diagnostic = correct_local_patch(
        arrays["packed"][0], arrays["variance"][0], arrays["colors"][0], base[0]
    )
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    target = output / "prediction.npy"
    np.save(target, value[None], allow_pickle=False)
    save(
        output / "receipt.json",
        {
            "operator": ref(__file__),
            "inputs": ref(args.inputs),
            "parent_prediction": ref(args.prediction),
            "declared_checkpoint": ref(args.checkpoint),
            "prediction": ref(target),
            "diagnostic": diagnostic,
            "new_model_calls": 0,
            "scope": "Fixed local phase-harmonic correction,CPUfloat64/native256. Globalinput-only phase/frequency selection and fit retained; localGaussian32native,positive-part variance shrink4,cap3,32pxborderapron. No GT/reference or8-bitquantization in correction. Conditionalnoise proxy is uncalibrated; not a fullframe method or broad flatsafety proof.",
        },
    )
