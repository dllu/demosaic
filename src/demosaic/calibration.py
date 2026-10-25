"""Conservative single-RAW Poisson/read-noise diagnostics from flat patches.

This is a statistical estimate, not a substitute for measured flat/dark frames.
Texture indistinguishable from noise can bias estimates upward. Narrow signal
ranges cannot identify shot and read terms separately and are reported as such.
"""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class NoiseEstimate:
    shot: float | None
    read: float | None
    reliable: bool
    reason: str
    candidate_patches: int
    accepted_patches: int
    intensity_span: float
    reference_intensity: float | None
    reference_variance: float | None
    shot_interval: list[float] | None
    read_interval: list[float] | None
    bins: list[dict]
    lower_clip_levels: list[float] | None = None
    lower_clip_tolerances: list[float] | None = None

    def to_dict(self):
        return asdict(self)


def _nonnegative_fit(x, y, weights):
    """Two-variable weighted NNLS, including both boundary solutions."""
    design = np.stack((x, np.ones_like(x)), axis=1)
    root = np.sqrt(weights)
    unconstrained = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)[0]
    candidates = [
        np.array([0.0, np.average(y, weights=weights)]),
        np.array([np.sum(weights * x * y) / max(np.sum(weights * x * x), 1e-30), 0.0]),
    ]
    if np.all(unconstrained >= 0):
        candidates.append(unconstrained)
    return min(candidates, key=lambda p: np.sum(weights * (design @ p - y) ** 2))


def estimate_noise(raw, *, patch=32, max_patches=4096, seed=42, metadata=None):
    """Fit Var(y|x)=shot*x+read on black/white-normalized Bayer measurements.

    Sample all four CFA phases independently. Three orthonormal Haar detail
    bands remove smooth intensity trends; a detrended low-pass image rejects
    texture. Clipped/ADC-censored patches are excluded. With read_raw metadata,
    the lower limit is -black/(white-black) for each visible CFA phase: zero
    after black subtraction is not the ADC floor. Half an ADC code of tolerance
    accounts for floating normalization at the floor. Without metadata the legacy
    zero-floor convention applies. Negative read noise stays unmodified.
    Quantile-bin medians
    limit outlier influence, and a bin bootstrap exposes poor identifiability.
    Input arrays are never modified; work is bounded by max_patches*patch².
    """
    raw = np.asarray(raw)
    if raw.ndim != 2 or min(raw.shape) < patch * 2 or patch < 8 or patch % 2:
        raise ValueError("Expected a Bayer image at least twice the even patch size")
    if not 64 <= max_patches <= 32768:
        raise ValueError("max_patches must be in [64, 32768]")
    if metadata is None:
        floors = np.zeros(4, dtype=np.float32)
        tolerance = np.zeros(4, dtype=np.float32)
    else:
        black = np.asarray(metadata.black_levels, dtype=np.float32)
        white = np.asarray(metadata.white_levels, dtype=np.float32)
        if (
            black.shape != (4,)
            or white.shape != (4,)
            or not np.isfinite(black).all()
            or not np.isfinite(white).all()
            or np.any(white <= black)
        ):
            raise ValueError("Noise estimation requires four finite phase black/white levels")
        floors = -black / (white - black)
        tolerance = 0.5 / (white - black)
    side = max(1, int(np.sqrt(max_patches // 4)))
    rows = np.unique(np.linspace(0, raw.shape[0] - 2 * patch, side).astype(int) // 2 * 2)
    cols = np.unique(np.linspace(0, raw.shape[1] - 2 * patch, side).astype(int) // 2 * 2)
    patches = np.stack(
        [
            raw[y + dy : y + 2 * patch : 2, x + dx : x + 2 * patch : 2]
            for y in rows
            for x in cols
            for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))
        ]
    ).astype(np.float32)
    means = patches.mean(axis=(1, 2))
    valid = np.isfinite(patches).all(axis=(1, 2))
    lower = np.tile(floors + tolerance, len(patches) // 4)[:, None, None]
    valid &= ((patches <= lower) | (patches >= 0.99)).mean(axis=(1, 2)) < 0.01
    valid &= (means > 0.001) & (means < 0.9)
    a, b = patches[:, ::2, ::2], patches[:, ::2, 1::2]
    c, d = patches[:, 1::2, ::2], patches[:, 1::2, 1::2]
    bands = np.stack(((a - b - c + d) / 2, (a + b - c - d) / 2, (a - b + c - d) / 2), axis=1)
    centers = np.median(bands, axis=(-2, -1), keepdims=True)
    band_var = (np.median(np.abs(bands - centers), axis=(-2, -1)) / 0.67448975) ** 2
    variances = np.median(band_var, axis=1)
    isotropy = band_var.max(1) / np.maximum(band_var.min(1), 1e-15)
    low = (a + b + c + d) / 4
    axis = np.linspace(-1, 1, low.shape[-1], dtype=np.float32)
    yy, xx = np.meshgrid(axis, axis, indexing="ij")
    residual = low - low.mean(axis=(1, 2), keepdims=True)
    residual -= (residual * xx).mean(axis=(1, 2))[:, None, None] / np.mean(xx**2) * xx
    residual -= (residual * yy).mean(axis=(1, 2))[:, None, None] / np.mean(yy**2) * yy
    texture_ratio = (residual**2).mean(axis=(1, 2)) / np.maximum(variances / 4, 1e-15)
    valid &= (variances > 1e-12) & (isotropy < 2.5) & (texture_ratio < 2.0)
    x, y = means[valid].astype(np.float64), variances[valid].astype(np.float64)
    base = {
        "shot": None,
        "read": None,
        "reliable": False,
        "reason": "insufficient_flat_patches",
        "candidate_patches": len(patches),
        "accepted_patches": len(x),
        "intensity_span": 0.0,
        "reference_intensity": None,
        "reference_variance": None,
        "shot_interval": None,
        "read_interval": None,
        "bins": [],
        "lower_clip_levels": floors.astype(float).tolist(),
        "lower_clip_tolerances": tolerance.astype(float).tolist(),
    }
    if len(x) < 64:
        return NoiseEstimate(**base)
    order = np.argsort(x)
    # Equal-count bins avoid letting a large uniform sky dominate the fit.
    groups = np.array_split(order, min(16, len(x) // 16))
    bins = [
        {"mean": float(np.median(x[g])), "variance": float(np.median(y[g])), "patches": len(g)}
        for g in groups
    ]
    bx = np.array([b["mean"] for b in bins])
    by = np.array([b["variance"] for b in bins])
    weights = 1 / np.maximum(by, 1e-12) ** 2
    span = float(np.quantile(x, 0.95) - np.quantile(x, 0.05))
    base.update(
        intensity_span=span,
        reference_intensity=float(np.median(x)),
        reference_variance=float(np.median(y)),
        bins=bins,
    )
    if span < 0.05 or np.ptp(bx) < 0.01:
        base["reason"] = "insufficient_intensity_span"
        return NoiseEstimate(**base)
    fit = _nonnegative_fit(bx, by, weights)
    rng = np.random.default_rng(seed)
    bootstrap = []
    for _ in range(128):
        indices = rng.integers(len(bx), size=len(bx))
        if np.ptp(bx[indices]) > 0.01:
            bootstrap.append(_nonnegative_fit(bx[indices], by[indices], weights[indices]))
    intervals = np.quantile(bootstrap, (0.025, 0.975), axis=0)
    relative_residual = float(np.median(np.abs(bx * fit[0] + fit[1] - by) / by))
    reliable = (
        relative_residual < 0.25 and fit[0] > 0 and intervals[1, 0] - intervals[0, 0] < 1.5 * fit[0]
    )
    base.update(
        shot=float(fit[0]),
        read=float(fit[1]),
        reliable=bool(reliable),
        reason="fit" if reliable else "unstable_fit",
        shot_interval=intervals[:, 0].tolist(),
        read_interval=intervals[:, 1].tolist(),
    )
    return NoiseEstimate(**base)
