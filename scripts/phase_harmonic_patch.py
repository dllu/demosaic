"""Phase-aware harmonic innovation for saved native256 RAW/RGB patches."""

import argparse
from pathlib import Path

import numpy as np
from green_phase_spectrum import green_pair
from train_directional_bank_trial import ref, save

from demosaic.safety import writable_path


def correct_patch(packed, variance, colors, base):
    packed, variance, base = [np.asarray(v, dtype=np.float64) for v in (packed, variance, base)]
    colors = np.asarray(colors)
    if (
        packed.shape != (4, 128, 128)
        or variance.shape != packed.shape
        or base.shape != (3, 256, 256)
    ):
        raise ValueError("Require native256 RGB and matching four128x128 packed phases")
    if colors.shape != (4,) or tuple(colors) not in {
        (0, 1, 1, 2),
        (2, 1, 1, 0),
        (1, 0, 2, 1),
        (1, 2, 0, 1),
    }:
        raise ValueError("Require a standard Bayer phase layout")
    if not all(np.isfinite(v).all() for v in (packed, variance, base)) or np.any(variance < 0):
        raise ValueError("Require finite inputs and nonnegative variance")
    if not np.any(variance > 0):
        return base.copy(), {"peaks": [], "ADC_only_bypass": True}
    g = green_pair(packed, variance, colors)
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
        return base.copy(), {"peaks": []}
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
    Y, X = np.mgrid[:256, :256]
    field = np.zeros_like(base)
    gates = []
    for k, (fx, fy, score) in enumerate(peaks):
        indices = [12 + 6 * k + 2, 12 + 6 * k + 3]
        c = beta[indices]
        v = covariance[np.ix_(indices, indices)]
        power = float(c @ np.linalg.solve(v, c))
        gate = max(0, 1 - 9 / max(power, 1e-12))
        gates.append({"power": power, "gate": gate})
        angle = 2 * np.pi * (fx * X + fy * Y)
        for color in range(3):
            index = 12 + 6 * k + 2 * color
            field[color] += gate * (beta[index] * np.cos(angle) + beta[index + 1] * np.sin(angle))
    # Smooth finite-window localization; this can still extend wires into empty areas.
    taper = np.hanning(256)[:, None] * np.hanning(256)[None]
    return base + field * taper[None], {
        "peaks": peaks,
        "gates": gates,
        "field_RMS": float(np.sqrt(np.mean(field * field))),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, help="Retained NPZ with packed,variance,colors")
    parser.add_argument("prediction", type=Path, help="Linear camera-RGB NPY,shape1x3x256x256")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Declared source checkpoint; recorded without model execution",
    )
    args = parser.parse_args()
    with np.load(args.inputs, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("packed", "variance", "colors")}
    base = np.load(args.prediction, allow_pickle=False)
    if base.shape != (1, 3, 256, 256) or arrays["packed"].shape != (1, 4, 128, 128):
        raise ValueError("One native256 patch required")
    value, diagnostic = correct_patch(
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
            "scope": "Fixed exploratory harmonic correction,CPU float64,linear cameraRGB retained without8-bit quantization. Native256 only; not a fullframe implementation. Positive input variance; exactADC bypass. Thresholds/shrink power are uncalibrated. Can extend a periodic field into blank parts of textured patches; see phase-harmonic-patch.md. No GT or reference enters correction.",
        },
    )
