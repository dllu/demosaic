"""Analytic CFA candidate discovery and genuinely withheld predictive checks.

No parent restoration, DINO features, target values or held-out noise enter a
fit. The standardized predictive improvement is an empirical diagnostic, not a
calibrated probability. In particular, an omitted edge can predict across both
subsets and still be mistaken for periodic detail.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np


@dataclass(frozen=True)
class Candidate:
    background: np.ndarray
    prediction: np.ndarray
    frequencies_xy: tuple
    noise_variance: np.ndarray
    edge_index: int | None
    discovery_mask: np.ndarray
    edge_geometry: tuple | None = None


def stratified_split(shape, seed):
    """Exactly half of every native Bayer phase; geometry independent of pixels."""
    h, w = shape
    if h % 4 or w % 4 or min(shape) < 32:
        raise ValueError("Expected native axes divisible by four and at least32")
    rng = np.random.default_rng(seed)
    mask = np.zeros(shape, bool)
    for y in range(2):
        for x in range(2):
            indices = rng.permutation(h * w // 4)[: h * w // 8]
            phase = np.zeros(h * w // 4, bool)
            phase[indices] = True
            mask[y::2, x::2] = phase.reshape(h // 2, w // 2)
    return mask


@lru_cache(maxsize=4)
def geometry(shape):
    h, w = shape
    yy, xx = np.mgrid[:h, :w]
    x, y = 2 * (xx + 0.5) / w - 1, 2 * (yy + 0.5) / h - 1
    basis = np.stack((np.ones(shape), x, y), axis=-1).reshape(-1, 3)
    steps = np.stack(
        [
            (x * np.cos(angle) + y * np.sin(angle) > offset).ravel()
            for angle in np.linspace(0, np.pi, 12, endpoint=False)
            for offset in np.linspace(-0.4, 0.4, 9)
        ],
        axis=-1,
    ).astype(np.float64)
    return xx, yy, basis, steps


def fit_candidate(
    raw,
    colors,
    discovery_mask,
    *,
    shot,
    read,
    nuisance="affine",
    peaks=2,
    edge_refinements=0,
    edge_search="bounded-grid",
):
    """Fit a fixed native-coordinate prediction using only discovery samples.

    Edge geometry and Fourier peaks are selected on this same discovery subset.
    Coefficients jointly fit nuisance and waves; held-out coordinates supply no
    weights, normalization, selection, amplitude, phase or threshold tuning.
    """
    raw = np.asarray(raw, dtype=np.float64)
    colors, discovery_mask = np.asarray(colors), np.asarray(discovery_mask)
    if (
        raw.ndim != 2
        or colors.shape != raw.shape
        or discovery_mask.shape != raw.shape
        or discovery_mask.dtype != bool
        or not np.isin(colors, (0, 1, 2)).all()
        or not np.isfinite(raw[discovery_mask]).all()
        or nuisance not in ("affine", "step")
        or peaks not in (1, 2)
        or not np.isfinite([shot, read]).all()
        or min(shot, read) < 0
        or shot + read <= 0
        or type(edge_refinements) is not int
        or not 0 <= edge_refinements <= 3
        or (edge_refinements and nuisance != "step")
        or edge_search not in ("bounded-grid", "full-frame")
        or (edge_search == "full-frame" and nuisance != "step")
    ):
        raise ValueError("Invalid CFA discovery inputs")
    xx, yy, basis, steps = geometry(raw.shape)
    green = ((colors == 1) & discovery_mask).ravel()
    if any(((colors == c) & discovery_mask).sum() < 16 for c in range(3)):
        raise ValueError("Discovery subset needs samples of every color")
    edge_index = None
    edge_geometry = None
    if nuisance == "step" and edge_search == "full-frame":
        from demosaic.full_frame_edge import search_edge

        angle, offset = search_edge(raw.ravel()[green], basis[green, 1:], edge_refinements)
        x, y = basis[:, 1], basis[:, 2]
        chosen_step = (x * np.cos(angle) + y * np.sin(angle) > offset).astype(np.float64)
        edge_geometry = (angle, offset)
        basis = np.column_stack((basis, chosen_step))
    elif nuisance == "step":
        # Residualize every fixed edge competitor against the A-only affine fit.
        q, _ = np.linalg.qr(basis[green], mode="reduced")
        edges = steps[green]
        edges = edges - q @ (q.T @ edges)
        values = raw.ravel()[green]
        residual = values - q @ (q.T @ values)
        energy = np.sum(edges * edges, axis=0)
        benefit = (residual @ edges) ** 2 / np.maximum(energy, 1e-20)
        edge_index = int(np.argmax(benefit))
        angle = edge_index // 9 * np.pi / 12
        offset = np.linspace(-0.4, 0.4, 9)[edge_index % 9]
        chosen_step = steps[:, edge_index]
        x, y = 2 * (xx + 0.5) / raw.shape[1] - 1, 2 * (yy + 0.5) / raw.shape[0] - 1
        angular_radius, offset_radius = np.pi / 12, 0.1
        for _ in range(edge_refinements):
            candidates = [
                (a, b)
                for a in angle + np.linspace(-angular_radius, angular_radius, 9)
                for b in offset + np.linspace(-offset_radius, offset_radius, 9)
            ]
            search = np.stack(
                [(x * np.cos(a) + y * np.sin(a) > b).ravel() for a, b in candidates], axis=-1
            ).astype(np.float64)
            projected = search[green] - q @ (q.T @ search[green])
            energy = np.sum(projected**2, axis=0)
            benefit = (residual @ projected) ** 2 / np.maximum(energy, 1e-20)
            selected = int(np.argmax(benefit))
            angle, offset = candidates[selected]
            chosen_step = search[:, selected]
            angular_radius /= 4
            offset_radius /= 4
        edge_geometry = (float(angle), float(offset))
        basis = np.column_stack((basis, chosen_step))
    background = np.empty(raw.size, np.float64)
    noise_variance = np.empty(raw.size, np.float64)
    for color in range(3):
        selected = ((colors == color) & discovery_mask).ravel()
        destination = (colors == color).ravel()
        values = raw.ravel()[selected]
        coefficients = np.linalg.lstsq(basis[selected], values, rcond=1e-10)[0]
        background[destination] = basis[destination] @ coefficients
        # One color-wise estimate from A; no oracle variance map or B samples.
        noise_variance[destination] = read + shot * max(float(values.mean()), 1e-6)
    residual = np.zeros(raw.size, np.float64)
    residual[green] = raw.ravel()[green] - background[green]
    power = abs(np.fft.fft2(residual.reshape(raw.shape))) ** 2
    fy, fx = np.meshgrid(np.fft.fftfreq(raw.shape[0]), np.fft.fftfreq(raw.shape[1]), indexing="ij")
    radius = np.hypot(fx, fy)
    # Restrict this prototype below the per-color quarter-cycle Nyquist limit.
    allowed = (radius >= 1 / 64) & (radius <= 0.24) & ((fy > 0) | ((fy == 0) & (fx > 0)))
    frequencies = []
    for _ in range(peaks):
        index = np.unravel_index(np.argmax(np.where(allowed, power, -np.inf)), raw.shape)
        if not allowed[index]:
            raise ValueError("No independent frequency candidates remain")
        frequency = (float(fx[index]), float(fy[index]))
        frequencies.append(frequency)
        separation = min(raw.shape) ** -1 * 2
        allowed &= np.hypot(fx - frequency[0], fy - frequency[1]) >= separation
    waves = []
    for fx_value, fy_value in frequencies:
        phase = 2 * np.pi * (xx * fx_value + yy * fy_value)
        waves.extend((np.cos(phase).ravel(), np.sin(phase).ravel()))
    design = np.column_stack((basis, *waves))
    prediction = np.empty(raw.size, np.float64)
    for color in range(3):
        selected = ((colors == color) & discovery_mask).ravel()
        destination = (colors == color).ravel()
        coefficients = np.linalg.lstsq(design[selected], raw.ravel()[selected], rcond=1e-10)[0]
        prediction[destination] = design[destination] @ coefficients
    return Candidate(
        background.reshape(raw.shape),
        prediction.reshape(raw.shape),
        tuple(frequencies),
        noise_variance.reshape(raw.shape),
        edge_index,
        discovery_mask.copy(),
        edge_geometry,
    )


def validate_candidate(candidate, raw, validation_mask):
    """Assess one fixed prediction on disjoint samples, without refitting it."""
    raw, mask = np.asarray(raw, dtype=np.float64), np.asarray(validation_mask)
    if (
        raw.shape != candidate.prediction.shape
        or mask.shape != raw.shape
        or mask.dtype != bool
        or not mask.any()
        or (mask & candidate.discovery_mask).any()
        or not np.isfinite(raw[mask]).all()
    ):
        raise ValueError("Validation must contain finite, genuinely disjoint samples")
    base, full = candidate.background[mask], candidate.prediction[mask]
    variance = candidate.noise_variance[mask]
    improvement = float(np.sum(((raw[mask] - base) ** 2 - (raw[mask] - full) ** 2) / variance))
    nominal_sd = float(2 * np.sqrt(np.sum((full - base) ** 2 / variance)))
    return {
        "weighted_SSE_improvement": improvement,
        "nominal_noise_sd": nominal_sd,
        "validation_z": improvement / nominal_sd if nominal_sd > 0 else 0.0,
        "samples": int(mask.sum()),
    }
