"""Fixed-wave readout interventions; no learned weights, targets or confidence."""

import numpy as np

POLICIES = (
    "actual",
    "shared-spatial",
    "shared-spatial-RMS",
    "color-constant",
    "shared-constant",
    "shared-constant-RMS",
    "positive-only",
)


def native_basis(waves, bins):
    """Transport each measured complex RGB mode to all native subpixels.

    This independent NumPy path keeps the modes separate rather than summing
    them inside a neural module. Canonical RGB already has actual CFA offsets
    removed. The returned real basis has shape N,K,3,2H,2W.
    """
    waves, bins = np.asarray(waves), np.asarray(bins)
    if (
        waves.ndim != 6
        or waves.shape[2:4] != (3, 2)
        or waves.dtype not in [np.dtype("float32"), np.dtype("float64")]
        or not np.isfinite(waves).all()
    ):
        raise ValueError("Expected finite N,K,3,2,H,W floating complex wave coordinates")
    n, count, _, _, h, w = waves.shape
    if count < 2 or count % 2 or bins.shape != (n, 2, count // 2, 2) or bins.dtype != np.int64:
        raise ValueError("Expected matching int64 N,2,peaks,2 bins")
    if not ((bins >= 0) & (bins < [h, w])).all():
        raise ValueError("FFT bins outside packed image")
    y, x = np.moveaxis(bins.reshape(n, count, 2), -1, 0)
    ky, kx = np.where(y <= (h - 1) // 2, y, y - h), np.where(x <= (w - 1) // 2, x, x - w)
    output = np.empty((n, count, 3, h * 2, w * 2), dtype=waves.dtype)
    real, imag = waves[:, :, :, 0], waves[:, :, :, 1]
    for dy in [0, 1]:
        for dx in [0, 1]:
            angle = np.pi * (ky.astype(np.float64) * dy / h + kx.astype(np.float64) * dx / w)
            cosine, sine = [
                f(angle).astype(waves.dtype)[..., None, None, None] for f in [np.cos, np.sin]
            ]
            output[..., dy::2, dx::2] = real * cosine - imag * sine
    return output


def policy_gate(gates, policy):
    gates = np.asarray(gates)
    if (
        gates.ndim != 5
        or gates.shape[2] != 3
        or gates.dtype not in [np.dtype("float32"), np.dtype("float64")]
        or not np.isfinite(gates).all()
        or (abs(gates) > 1 + 1e-7).any()
    ):
        raise ValueError("Expected finite bounded N,K,3,H,W gates")
    if policy not in POLICIES:
        raise ValueError("Unknown predeclared gate intervention")
    if policy == "actual":
        return gates
    if policy.startswith("shared-spatial"):
        return gates.mean(2, keepdims=True, dtype=gates.dtype)
    if policy == "color-constant":
        return gates.mean((-2, -1), keepdims=True, dtype=gates.dtype)
    if policy.startswith("shared-constant"):
        return gates.mean((2, 3, 4), keepdims=True, dtype=gates.dtype)
    return gates.clip(0, 1)


def synthesize(basis, gate, mask=None):
    basis, gate = np.asarray(basis), np.asarray(gate)
    if basis.ndim != 5 or basis.shape[2] != 3 or not np.isfinite(basis).all():
        raise ValueError("Expected finite native N,K,3,H,W real basis")
    if gate.ndim != 5 or gate.shape[:2] != basis.shape[:2] or gate.shape[2] not in [1, 3]:
        raise ValueError("Expected same N,K and one or three gate channels")
    if gate.dtype != basis.dtype or not np.isfinite(gate).all():
        raise ValueError("Expected finite same-dtype gates")
    if gate.shape[-2:] not in [(1, 1), (basis.shape[-2] // 2, basis.shape[-1] // 2)]:
        raise ValueError("Expected constant or packed-resolution gates")
    native = gate if gate.shape[-2:] == (1, 1) else gate.repeat(2, -2).repeat(2, -1)
    value = (basis * native).sum(1, dtype=basis.dtype)
    if mask is not None:
        if mask.shape != (basis.shape[0], 1, *basis.shape[-2:]) or mask.dtype != np.bool_:
            raise ValueError("Expected native N,1,H,W boolean mask")
        value = np.where(mask, value, 0)
    return value


def rms(value):
    value = np.asarray(value, dtype=np.float64)
    return float(np.linalg.norm(value.ravel()) / np.sqrt(value.size))


def amplitude_match(value, reference):
    """Match whole-context camera-RGB correction RMS without reading a target.

    This is a diagnostic scalar, not a bounded-gate architecture. A resulting
    effective gain may exceed one. Exact zero cannot match a nonzero reference.
    """
    before, desired = rms(value), rms(reference)
    possible = before > 0 or desired == 0
    scale = desired / before if before else (1.0 if desired == 0 else 0.0)
    return (value * scale).astype(value.dtype), {
        "scale": scale,
        "possible": possible,
        "before_RMS_DN16": before * 65535,
        "reference_RMS_DN16": desired * 65535,
        "bounded_gate_architecture": False,
    }


def crop_gates(gates, roi):
    x, y, w, h = roi
    return np.take(np.take(gates, np.arange(y, y + h) // 2, -2), np.arange(x, x + w) // 2, -1)


def correction_stats(value):
    value = np.asarray(value, dtype=np.float64)
    if value.ndim != 4 or value.shape[1] != 3 or not np.isfinite(value).all():
        raise ValueError("Expected finite N,3,H,W camera-RGB corrections")
    return {
        "RMS_DN16": rms(value) * 65535,
        "spatial_RMS_DN16": rms(value - value.mean((-2, -1), keepdims=True)) * 65535,
        "equal_RGB_orthogonal_RMS_DN16": rms(value - value.mean(1, keepdims=True)) * 65535,
        "channel_RMS_DN16": [rms(value[:, c]) * 65535 for c in range(3)],
        "scope": "Correction amplitude only; equal-camera-RGB orthogonal norm is not perceptual chroma, GT error or quality.",
    }


def local_intervention(bundle, endpoint, policy, constants, scale=1):
    """Reconstruct a native crop using saved gates and whole-image constants.

    Constant gates use recorded whole-context means, never means of the crop.
    The saved gate crop already repeats the actual packed gate at each native
    pixel, including odd-coordinate ROIs.
    """
    basis, gate = bundle["basis"], bundle["gate_" + endpoint]
    if policy.startswith("shared-spatial"):
        gate = gate.mean(2, keepdims=True, dtype=gate.dtype)
    elif policy == "color-constant":
        gate = np.asarray(constants["color"], dtype=basis.dtype)
    elif policy.startswith("shared-constant"):
        gate = np.asarray(constants["shared"], dtype=basis.dtype)
    elif policy == "positive-only":
        gate = gate.clip(0, 1)
    elif policy != "actual":
        raise ValueError("Unknown intervention")
    value = np.where(bundle["mask"], (basis * gate).sum(1, dtype=basis.dtype), 0)
    return (value * scale).astype(basis.dtype)
