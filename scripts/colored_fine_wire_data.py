"""New exact coloured finite-wire scenes; no photographs or model outputs."""

import numpy as np

PATTERNS = {"RGGB": [0, 1, 1, 2], "BGGR": [2, 1, 1, 0], "GRBG": [1, 0, 2, 1], "GBRG": [1, 2, 0, 1]}
SEED = 202611162200
WB = np.array([1.55, 1.0, 1.7], np.float32)
MATRIX = np.array([[1.08, -0.06, -0.02], [-0.03, 1.28, -0.25], [-0.01, -0.12, 1.13]], np.float32)
PRIORS = {
    "iso1600": {"shot": 0.00032, "read": 4.096e-7, "exposure": 1.0},
    "iso6400": {"shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0},
}


def render(source, *, size=512, supersample=8):
    if (
        source not in (0, 1)
        or size < 64
        or size % 4
        or type(supersample) is not int
        or not 1 <= supersample <= 8
    ):
        raise ValueError("Require source0/1, native axes divisible by4 and1..8 area samples")
    rng = np.random.default_rng(np.random.SeedSequence([SEED, source]))
    angles = np.array([rng.uniform(0.4, 0.75), rng.uniform(2.25, 2.6)])
    radii = rng.uniform(0.105, 0.145, 2)
    fine = np.column_stack([np.cos(angles), np.sin(angles)]) * radii[:, None]
    coarse_angles = np.array([rng.uniform(-0.15, 0.15), rng.uniform(1.4, 1.7)])
    coarse_radii = rng.uniform(1 / 48, 1 / 34, 2)
    coarse = np.column_stack([np.cos(coarse_angles), np.sin(coarse_angles)]) * coarse_radii[:, None]
    phases = rng.uniform(0, 1, 4)
    widths = rng.uniform(0.4, 0.55, 2)
    colours = (
        np.array([[0.75, 1.0, 0.85], [0.75, 1.0, 0.85]])
        if source == 0
        else np.array([[0.25, 1.0, 0.4], [1.0, -0.3, 0.7]])
    )
    amplitudes = np.array([0.0016, 0.0008])
    yy, xx = np.indices((size, size), dtype=np.float64)
    background = np.zeros((3, size, size))
    profiles = np.zeros((2, size, size))
    center = (size - 1) / 2
    for dy in (np.arange(supersample) + 0.5) / supersample - 0.5:
        for dx in (np.arange(supersample) + 0.5) / supersample - 0.5:
            x, y = xx + dx, yy + dy
            edge = y - 0.18 * size - 0.08 * (x - center)
            base = 0.0062 + 0.0007 * x / size + 0.0003 * y / size
            slow = sum(
                a * np.cos(2 * np.pi * (f[0] * x + f[1] * y + p))
                for a, f, p in zip([0.0014, 0.0011], coarse, phases[:2], strict=True)
            )
            background += (base + slow)[None] * np.array([0.85, 1.0, 0.9])[:, None, None] + 0.12 * (
                edge < 0
            )[None] * np.array([0.7, 1.0, 0.9])[:, None, None]
            radius = np.hypot(x - center, y - center)
            taper = np.clip((radius - 0.30 * size) / (0.08 * size), 0, 1)
            envelope = 0.5 + 0.5 * np.cos(np.pi * taper)
            for direction, (f, width, phase) in enumerate(
                zip(fine, widths, phases[2:], strict=True)
            ):
                distance = ((f[0] * x + f[1] * y + phase + 0.5) % 1 - 0.5) / np.linalg.norm(f)
                profiles[direction] += envelope * np.exp(-0.5 * (distance / width) ** 2)
    background /= supersample**2
    profiles /= supersample**2
    increments = amplitudes[:, None, None, None] * colours[:, :, None, None] * profiles[:, None]
    target = np.stack(
        [background, background + increments[0], background + increments.sum(axis=0)]
    ).astype(np.float32)
    edge_distance = yy - 0.18 * size - 0.08 * (xx - center)
    quiet = (np.hypot(xx - center, yy - center) > 0.42 * size) & (abs(edge_distance) > 0.04 * size)
    edge_band = abs(edge_distance) < 0.025 * size
    assert target.min() > 0 and target.max() < 1 and quiet.any() and edge_band.any()
    recipe = {
        "source": source,
        "seed": SEED,
        "size": size,
        "area_reduction": supersample,
        "optical_blur": 0.0,
        "fine_frequencies_xy": fine.tolist(),
        "coarse_frequencies_xy": coarse.tolist(),
        "phases_cycles": phases.tolist(),
        "widths_native_pixels": widths.tolist(),
        "increment_colours_sensor_RGB": colours.tolist(),
        "peak_amplitudes": amplitudes.tolist(),
        "colour_case": "neutral" if source == 0 else "green_strong_magenta_weak",
        "placement": "far",
        "display_exposure": 16.0,
        "ROI_xywh": [size // 2 - 80, size // 2 - 80, 160, 160],
        "calibration": "Fixed fictional sensor WB/matrix; no camera/reference pixels or fitted camera calibration.",
    }
    return {"target": target, "quiet": quiet, "edge_band": edge_band}, recipe


def observe(target, pattern, prior, *, source):
    target = np.asarray(target)
    if (
        target.ndim != 4
        or target.shape[:2] != (3, 3)
        or target.shape[-1] != target.shape[-2]
        or target.shape[-1] % 4
        or not np.isfinite(target).all()
        or target.min() < 0
    ):
        raise ValueError("Require nonnegative zero/one/two-direction sensor RGB")
    if pattern not in PATTERNS or prior not in PRIORS or source not in (0, 1):
        raise ValueError("Unknown declared CFA/prior/source")
    noise = PRIORS[prior]
    phases = np.array(PATTERNS[pattern], np.int64)
    size = target.shape[-1]
    colors = np.tile(phases.reshape(2, 2), (size // 2, size // 2))
    yy, xx = np.indices(colors.shape)
    packed = []
    true_variance = []
    identities = []
    for role in range(3):
        keys = [SEED, source, list(PATTERNS).index(pattern), list(PRIORS).index(prior), role]
        rng = np.random.default_rng(np.random.SeedSequence(keys))
        clean = target[role, colors, yy, xx].astype(np.float64)
        raw = rng.poisson(clean / noise["shot"]) * noise["shot"] + rng.normal(
            0, np.sqrt(noise["read"]), clean.shape
        )
        packed.append(
            np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)]).astype(np.float32)
        )
        variance = clean * noise["shot"] + noise["read"]
        true_variance.append(
            np.stack([variance[y::2, x::2] for y in range(2) for x in range(2)]).astype(np.float32)
        )
        identities.append(
            {"key": keys, "id": f"coloured-fine:{source}:{pattern}:{prior}:role{role}"}
        )
    packed = np.stack(packed)
    return {
        "packed": packed,
        "variance": packed.clip(0) * noise["shot"] + noise["read"],
        "true_sensor_variance": np.stack(true_variance),
        "colors": np.repeat(phases[None], 3, axis=0),
        "wb": np.repeat(WB[None], 3, axis=0),
        "matrix": np.repeat(MATRIX[None], 3, axis=0),
    }, identities
