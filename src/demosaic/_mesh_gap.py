"""Detect a deficit in an already admitted rear mesh direction."""

import math
from dataclasses import dataclass
from itertools import product

import numpy as np

from .isolated_line import coordinates, native_sites


@dataclass(frozen=True)
class _Region:
    is_band: bool
    u: float
    v: float
    center: float
    radius: float

    def mask(self, x, y):
        if self.is_band:
            distance = np.abs(self.u * x + self.v * y - self.center)
        else:
            distance = np.hypot(x - self.u, y - self.v)
        taper = np.clip((self.radius + 12 - distance) / 12, 0, 1)
        return taper * taper * (3 - 2 * taper)


_REGIONS = tuple(
    _Region(True, math.cos(angle), math.sin(angle), center, radius)
    for angle, center, radius in product(
        np.arange(12) * np.pi / 12, range(-48, 49, 16), (20, 30, 40)
    )
) + tuple(
    _Region(False, x, y, 0.0, radius)
    for x, y, radius in product(range(-48, 49, 24), range(-48, 49, 24), (24, 36, 48))
)


@dataclass
class _Observation:
    coordinates: tuple[np.ndarray, np.ndarray]
    colors: np.ndarray
    raw: np.ndarray
    rear: np.ndarray
    nuisance: np.ndarray
    shot: float
    read: float

    def variance(self, sensor):
        return self.shot * max(1e-4, float(np.median(sensor))) + self.read


def _fit(design, target):
    return np.linalg.solve(design.T @ design, design.T @ target)


def _propose(observation, train):
    """Rank candidate cuts only on the supplied discovery samples."""
    x, y = (axis[train] for axis in observation.coordinates)
    colors = observation.colors[train]
    waves = observation.rear[train]
    regressors = observation.nuisance[train]
    raw = observation.raw[train]
    vote = np.zeros(len(x))
    power = np.zeros(len(x))
    for color in range(3):
        select = colors == color
        wave = waves[select]
        nuisance = regressors[select]
        sensor = raw[select]
        sigma = math.sqrt(observation.variance(sensor))
        wave = wave - nuisance @ _fit(nuisance, wave)
        sensor = sensor - nuisance @ _fit(nuisance, sensor)
        gain = float(wave @ sensor / max(wave @ wave, 1e-16))
        removal = -(gain / sigma) * wave
        vote[select] = removal * (sensor / sigma + removal)
        power[select] = removal * removal

    best_score = -np.inf
    best = None
    for start in range(0, len(_REGIONS), 24):
        chunk = _REGIONS[start : start + 24]
        masks = np.stack([region.mask(x, y) for region in chunk], axis=1)
        norm = power @ (masks * masks)
        contrast = (vote @ masks - 0.5 * norm) / np.sqrt(np.maximum(norm, 1e-12))
        contrast[norm < 4] = -np.inf
        index = int(np.argmax(contrast))
        if contrast[index] > best_score:
            best_score = contrast[index]
            best = chunk[index]
    return best


def _forecast_gain(observation, train, test, region):
    """Forecast on the held-out samples with and without the nominated cut."""
    cut = region.mask(*observation.coordinates)
    background = np.column_stack((observation.nuisance, cut))
    whole = np.column_stack((background, observation.rear))
    gap = np.column_stack((background, observation.rear * (1 - cut)))
    overlap = power = 0.0
    for color in range(3):
        learn = train & (observation.colors == color)
        check = test & (observation.colors == color)
        sensor = observation.raw[learn]
        precise = 1 / observation.variance(sensor)
        uniform = whole[check] @ _fit(whole[learn], sensor)
        interrupted = gap[check] @ _fit(gap[learn], sensor)
        removal = interrupted - uniform
        overlap += precise * float((observation.raw[check] - uniform) @ removal)
        power += precise * float(removal @ removal)
    return (overlap - 0.5 * power) / math.sqrt(max(power, 1e-12))


def confirmed_gap(raw, colors, front_profile, rear_profile, shot, read):
    """Return a native attenuation mask for an interrupted rear profile.

    Profiles evaluate both directions at each packed Bayer sample using phase
    estimated from column slot 0. The gap score uses columns 1 and 2 to find
    candidates. Each fold must predict the other better with its proposed cut.
    A pooled candidate is checked once on slot 3. A failed or degenerate fit
    yields ``None``. The predictive margins are empirical.
    """
    packed_height, packed_width = raw.shape[-2:]
    width, height = 2 * packed_width, 2 * packed_height
    origin = (-(width - 1) / 2, -(height - 1) / 2)
    x, y = native_sites(raw.shape[-2:], origin)
    slots = np.broadcast_to(np.indices(raw.shape[-2:])[1] % 4, raw.shape).ravel()
    color = np.broadcast_to(np.asarray(colors)[:, None, None], raw.shape).ravel()
    u, v = x / 128, y / 128
    nuisance = np.stack((np.ones_like(x), u, v, u * u, u * v, v * v, front_profile), axis=-1)
    observation = _Observation(
        (x.ravel(), y.ravel()),
        color,
        raw.ravel().astype(float),
        (rear_profile * (1 - front_profile)).ravel(),
        nuisance.reshape((-1, nuisance.shape[-1])),
        shot,
        read,
    )
    a, b = slots == 1, slots == 2
    try:
        for train, test in ((a, b), (b, a)):
            candidate = _propose(observation, train)
            if candidate is None or _forecast_gain(observation, train, test, candidate) <= 0.75:
                return None
        candidate = _propose(observation, a | b)
        if candidate is None or _forecast_gain(observation, a | b, slots == 3, candidate) <= 1.5:
            return None
    except np.linalg.LinAlgError:
        return None
    return candidate.mask(*coordinates(height, width, origin=origin))
