"""CPU Fourier measurements for the experimental Bayer phase witness heads.

Queries contain 256 native pixels per side. Fourier support and phase transport
use native-pixel coordinates, while the input has four packed Bayer planes in
spatial phase order. The four donor windows share no samples with their center.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.fft import rfft2

from .cfa import PATTERNS

NATIVE = 32
PACKED = NATIVE // 2
PAD = 64
STEP = 1 / (2 * PAD)
STRIDE = PACKED // 2
SIDE = 1 + (128 - PACKED) // STRIDE
YI, XI = (index.ravel() * STRIDE for index in np.indices((SIDE, SIDE)))
axis = np.fft.fftfreq(PACKED, d=2)
fx, fy = np.meshgrid(axis, axis)
band = (np.hypot(fx, fy) >= 0.066) & (np.hypot(fx, fy) < 0.244)
half = (fx > 0) | ((fx == 0) & (fy > 0))
supported = band & half
radius = PAD // PACKED // 2
OFFSETS = np.asarray(
    [(0, 0)]
    + sorted(
        [(y, x) for y in range(-radius, radius + 1) for x in range(-radius, radius + 1) if y or x],
        key=lambda v: (v[0] ** 2 + v[1] ** 2, *v),
    )
)
BINS = np.rint(np.stack((fy[supported], fx[supported]), axis=-1) / STEP).astype(np.int64)[
    :, None, :
]
BINS = BINS + OFFSETS[None]
FREQ = BINS * STEP
ALLOWED = (np.linalg.norm(FREQ, axis=-1) <= 0.251) & (abs(FREQ).max(axis=-1) < 0.25)
PENALTY = 0.18 * np.sum(OFFSETS**2, axis=-1)[None, None, :]
BAYER_OFFSETS = np.stack((np.arange(4) // 2, np.arange(4) % 2), axis=-1)

window_1d = np.sin(np.pi * (np.arange(PACKED) + 0.5) / PACKED)
WEIGHT = (window_1d[:, None] * window_1d).astype(np.float32)
native_taper = np.sin(np.pi * (np.arange(NATIVE) + 0.5) / NATIVE)
taper = native_taper[:, None] * native_taper
POSITION = np.arange(NATIVE)
MEAN_RESPONSE = (
    np.einsum(
        "oy,op,yp->o",
        np.exp(2j * np.pi * OFFSETS[:, :1] * STEP * POSITION[None]),
        np.exp(2j * np.pi * OFFSETS[:, 1:] * STEP * POSITION[None]),
        taper,
    )
    / taper.sum()
)

NORM = WEIGHT.sum()
VARIANCE_SCALE = (WEIGHT**2).mean()
UNIQUE, MAP = np.unique(BINS.reshape(-1, 2), axis=0, return_inverse=True)
INDEX = MAP.reshape(ALLOWED.shape)
BASE = INDEX[:, 0]
GRID = np.exp(2j * np.pi * NATIVE * UNIQUE * STEP).astype(np.complex64)
SHIFT = np.exp(-2j * np.pi * np.einsum("ck,fk->cf", BAYER_OFFSETS, UNIQUE * STEP)).astype(
    np.complex64
)
MIRROR = UNIQUE[:, 1] < 0
# Negative horizontal frequencies are mirrored in both axes before gathering.
# Conjugation restores their signed complex coefficient.
COORDINATES = ((UNIQUE[:, 0] * np.where(MIRROR, -1, 1)) % PAD) * (PAD // 2 + 1) + abs(UNIQUE[:, 1])


def _transform(raw, shot, read):
    windows = np.lib.stride_tricks.sliding_window_view(raw, (PACKED, PACKED), axis=(-2, -1))
    pixels = np.moveaxis(windows[:, YI, XI], 0, 1)
    average = (pixels * WEIGHT).sum(axis=(-1, -2)) / NORM
    tapered = (pixels - average[..., None, None]) * WEIGHT
    transform = rfft2(tapered, s=(PAD, PAD), workers=1)
    transform /= PACKED
    variance = (shot * average.clip(min=0) + read).clip(min=2e-11)
    variance *= VARIANCE_SCALE
    return transform.reshape(len(XI), 4, -1), variance


def _gather(transform, plane, frequency=None):
    values = transform[:, plane]
    if frequency is None:
        sampled = values[:, COORDINATES]
        sampled[:, MIRROR] = sampled[:, MIRROR].conj()
        return sampled * SHIFT[plane]
    sampled = np.take_along_axis(values, COORDINATES[frequency], axis=-1)
    reflected = MIRROR[frequency]
    sampled[reflected] = sampled[reflected].conj()
    return sampled * SHIFT[plane, frequency]


def _unit(value):
    return value / np.maximum(abs(value), 1e-12)


def _neighborhood(vector, variance, phase_grid):
    """Transport the four disjoint neighboring windows to the center origin."""
    shape = (SIDE, SIDE, *vector.shape[1:])
    grid = vector.reshape(shape)
    variance = variance.reshape(SIDE, SIDE)
    total = np.zeros_like(grid)
    var = np.zeros_like(variance)
    # Preserve the original contribution order because a near-tied search can
    # select a different bin after even one rounding step.
    for axis in (0, 1):
        g = np.swapaxes(grid, 0, axis)
        v = np.swapaxes(variance, 0, axis)
        out = np.swapaxes(total, 0, axis)
        ns = np.swapaxes(var, 0, axis)
        transport = phase_grid[..., axis]
        out[2:] += g[:-2] * transport
        out[:-2] += g[2:] * transport.conj()
        ns[2:] += v[:-2]
        ns[:-2] += v[2:]
    return total.reshape(vector.shape), var.ravel()


def _neighboring_pair(values, variance, axis):
    grid = values.reshape(SIDE, SIDE, -1).swapaxes(0, axis)
    sigma = variance.reshape(SIDE, SIDE).swapaxes(0, axis)
    total = np.zeros((SIDE, SIDE, grid.shape[-1]), dtype=values.dtype).swapaxes(0, axis)
    combined = np.zeros((SIDE, SIDE), dtype=variance.dtype).swapaxes(0, axis)
    phase = GRID[:, axis]
    total[2:] += grid[:-2] * phase
    total[:-2] += grid[2:] * phase.conj()
    combined[2:] += sigma[:-2]
    combined[:-2] += sigma[2:]
    return total.swapaxes(0, axis).reshape(values.shape), combined.swapaxes(0, axis).ravel()


def _choose_by_power(values, variance, refine):
    selection = INDEX if refine else INDEX[:, :1]
    # The penalties are float64 in the source policy.
    power = abs(values) ** 2 / variance[:, None].clip(min=4e-10)
    options = selection.shape[-1]
    where = np.where(
        ALLOWED[None, :, :options], power[:, selection] - PENALTY[..., :options], -np.inf
    ).argmax(axis=-1)
    chosen = INDEX[np.arange(len(BASE))[None], where]
    return where, chosen


def _consistency(vertical, horizontal, vv, hv, selected, refine):
    """Nominate with each pair separately and evaluate the other pair."""
    _, vertical_best = _choose_by_power(vertical, vv, refine)
    _, horizontal_best = _choose_by_power(horizontal, hv, refine)
    v_donor = np.take_along_axis(vertical, vertical_best, axis=-1)
    h_donor = np.take_along_axis(horizontal, horizontal_best, axis=-1)
    v_target = np.take_along_axis(vertical, horizontal_best, axis=-1)
    h_target = np.take_along_axis(horizontal, vertical_best, axis=-1)
    v_sigma = np.sqrt(vv[:, None]).clip(min=2e-5)
    h_sigma = np.sqrt(hv[:, None]).clip(min=2e-5)
    v_support = (v_target * _unit(h_donor).conj()).real / v_sigma
    h_support = (h_target * _unit(v_donor).conj()).real / h_sigma
    v_field = np.take_along_axis(vertical, selected, axis=-1)
    h_field = np.take_along_axis(horizontal, selected, axis=-1)
    match = (_unit(v_field) * _unit(h_field).conj()).real
    tune = (UNIQUE[vertical_best] - UNIQUE[horizontal_best]) / 4
    features = np.stack(
        (
            np.arcsinh(v_support),
            np.arcsinh(h_support),
            np.log1p(abs(v_field) / v_sigma),
            np.log1p(abs(h_field) / h_sigma),
            match,
            tune[..., 0],
            tune[..., 1],
            np.arcsinh(abs(v_field - h_field) / np.hypot(v_sigma, h_sigma)),
        ),
        axis=-1,
    )
    return np.ascontiguousarray(features.clip(-6, 6), dtype=np.float32)


@dataclass(frozen=True)
class PhaseWitness:
    """Selected phase, center evidence and waveform proposal for each tile and bin."""

    features: np.ndarray
    frequency: np.ndarray
    phase: np.ndarray
    exterior_z: np.ndarray
    offsets: np.ndarray
    carrier: np.ndarray
    amplitude: np.ndarray
    confidence: np.ndarray
    noise: np.ndarray
    pair_features: np.ndarray | None = None

    def proposal(self, parent, scale=1.0):
        """Return the bounded head's extra basis in the original output bins."""
        deficit = self.amplitude / scale - (parent * self.carrier.conj()).real
        return (self.carrier * self.confidence * deficit).astype(np.complex64)


def measure_witnesses(
    raw: np.ndarray,
    layout: np.ndarray,
    noise: Mapping[str, float],
    *,
    refine: bool = True,
    pair_features: bool = False,
) -> PhaseWitness:
    """Measure signed evidence for sub-bin phase on one native 256-pixel query."""
    raw = np.asarray(raw, dtype=np.float32)
    layout = np.asarray(layout)
    if raw.shape != (4, 128, 128) or not np.isfinite(raw).all():
        raise ValueError("Expected a finite 4 × 128 × 128 packed Bayer query")
    if layout.shape != (4,) or tuple(layout) not in PATTERNS.values():
        raise ValueError("Expected four color indices in Bayer spatial phase order")
    shot, read = float(noise["shot"]), float(noise["read"])
    if min(shot, read) < 0 or not np.isfinite([shot, read]).all():
        raise ValueError("Expected finite nonnegative shot and read coefficients")
    transform, variance = _transform(raw, shot, read)
    green = np.flatnonzero(layout == 1)
    red, blue = (np.flatnonzero(layout == shade)[0] for shade in (0, 2))
    g0, g1 = (_gather(transform, plane) for plane in green)
    direct = (g0 + g1) * 0.5
    green_variance = variance[:, green].sum(1) * 0.25
    source, exterior_var = _neighborhood(direct, green_variance, GRID)
    offsets, selected = _choose_by_power(source, exterior_var, refine)
    external = np.take_along_axis(source, selected, axis=-1)
    external_phase = _unit(external)
    direct_phase = _unit(direct[:, BASE])
    refined_unit = _unit(np.take_along_axis(direct, selected, axis=-1))
    per_site = np.sqrt(variance)
    base = np.broadcast_to(BASE, selected.shape)
    local_color = np.stack(
        [
            ((_gather(transform, p, base) / per_site[:, p, None]) * direct_phase.conj()).real
            for p in (red, blue)
        ],
        axis=-1,
    )
    exterior_color = np.stack(
        [
            ((_gather(transform, p, selected) / per_site[:, p, None]) * external_phase.conj()).real
            for p in (red, blue)
        ],
        axis=-1,
    )
    exterior_green = np.stack(
        [
            (
                (np.take_along_axis(g, selected, axis=-1) / per_site[:, p, None])
                * external_phase.conj()
            ).real
            for p, g in zip(green, (g0, g1), strict=True)
        ],
        axis=-1,
    )
    strength = abs(external) / np.sqrt(exterior_var[:, None]).clip(min=2e-5)
    agreement = (refined_unit * external_phase.conj()).real
    features = (
        np.concatenate(
            (
                np.arcsinh(local_color),
                np.arcsinh(exterior_color),
                np.arcsinh(exterior_green),
                np.log1p(strength)[..., None],
                agreement[..., None],
            ),
            axis=-1,
        )
        .clip(-6, 6)
        .astype(np.float32)
    )
    carrier = _unit(external_phase * MEAN_RESPONSE[offsets])
    amplitude = (np.take_along_axis(direct, selected, axis=-1) * external_phase.conj()).real
    amplitude = amplitude.clip(min=0) * abs(MEAN_RESPONSE[offsets])
    evidence = (exterior_color.mean(-1) - 0.4).clip(min=0)
    confidence = np.sqrt(evidence / (1 + evidence))
    local_noise = np.sqrt(variance[:, green].mean(1))[:, None]
    pairs = None
    if pair_features:
        vertical, vv = _neighboring_pair(direct, green_variance, 0)
        horizontal, hv = _neighboring_pair(direct, green_variance, 1)
        pairs = _consistency(vertical, horizontal, vv, hv, selected, refine)
    return PhaseWitness(
        features,
        FREQ[np.arange(len(BASE))[None], offsets],
        external_phase,
        strength,
        offsets,
        carrier,
        amplitude,
        confidence,
        local_noise,
        pairs,
    )
