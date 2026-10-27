"""Native-band parameter-precision diagnostics; no restoration or noise code."""

import numpy as np
from feature_probe_math import annulus, basis, blocks, coefficients


def valid_reference_blocks(target, wb, matrix):
    rgb = np.einsum(
        "bij,bjhw->bihw", matrix.astype(np.float64), target.astype(np.float64) * wb[..., None, None]
    )
    color = blocks(rgb)
    luma = np.sum(color * np.array([0.2126, 0.7152, 0.0722])[None, :, None, None], axis=1)
    c = basis()
    frequency = (c @ luma @ c.T)[..., annulus()]
    means = luma.mean((-1, -2))
    rms = np.sqrt(np.sum(frequency * frequency, -1) / 256)
    mask = (
        ((color >= 0) & (color <= 1)).all((1, 2, 3))
        & (means >= 0.02)
        & (means <= 0.9)
        & (rms >= 1e-5)
    )
    if not mask.any():
        raise ValueError("No eligible reference blocks")
    return mask


def relative_band_error(prediction, target, mask):
    """One-half relative camera-RGB band MSE on reference-selected native blocks."""
    import torch

    c = torch.as_tensor(basis(), device=prediction.device, dtype=torch.float64)
    selected = torch.as_tensor(annulus(), device=prediction.device)
    valid = torch.as_tensor(mask, device=prediction.device)

    def band(value):
        if tuple(value.shape) != (1, 3, 256, 256):
            raise ValueError("Use a native256 camera-RGB context")
        central = value.double()[..., 48:208, 48:208]
        values = (
            central.reshape(1, 3, 10, 16, 10, 16).permute(0, 2, 4, 1, 3, 5).reshape(100, 3, 16, 16)
        )
        return (c @ values @ c.T)[..., selected][valid]

    truth = band(target.detach())
    return 0.5 * (band(prediction) - truth).square().sum() / truth.square().sum()


def gradient_summary(gram):
    """Vectors: FP32 training gradient, BF16 training gradient, FP32 band gradient."""
    gram = np.asarray(gram, np.float64)
    norms = np.sqrt(np.diag(gram))
    return {
        "gradient_cosine_BF16_FP32": float(gram[0, 1] / (norms[0] * norms[1])),
        "BF16_gradient_relative_L2_difference": float(
            np.sqrt(max(gram[0, 0] + gram[1, 1] - 2 * gram[0, 1], 0)) / norms[0]
        ),
        "gradient_norm_BF16_over_FP32": float(norms[1] / norms[0]),
        "FP32_training_band_gradient_cosine": float(gram[0, 2] / (norms[0] * norms[2])),
        "BF16_training_FP32_band_gradient_cosine": float(gram[1, 2] / (norms[1] * norms[2])),
        "FP32_unit_step_band_error_derivative": float(-gram[0, 2] / norms[0]),
        "BF16_unit_step_band_error_derivative": float(-gram[1, 2] / norms[1]),
    }


def numpy_band_error(prediction, target, mask):
    p, t = [coefficients(v)[mask] for v in (prediction, target)]
    return float(0.5 * np.sum((p - t) ** 2) / np.sum(t * t))
