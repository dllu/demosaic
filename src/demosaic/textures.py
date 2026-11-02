"""Continuous-precision weak textures with explicit final-pixel frequency profiles."""

import math
import random

import torch


def crossed_line_texture(size: int, rng: random.Random, *, pixel_scale=1, present=None):
    """Continuous weak crossed wires with matched empty backgrounds.

    Final-pixel periods/widths are evaluated on the caller's2x canvas, then
    receive the ordinary geometry/area reduction. A compact visibility mask
    leaves exactly empty regions inside a present sample. No photograph, noise,
    quantization, display transform or global RNG is used here.
    """
    if (
        type(size) is not int
        or size < 32
        or type(pixel_scale) is not int
        or pixel_scale not in (1, 2)
    ):
        raise ValueError("Crossed lines need size>=32 and pixel scale1 or2")
    if present is not None and type(present) is not bool:
        raise ValueError("Crossed-line presence must be boolean or None")
    seed = rng.getrandbits(63)
    chooser = random.Random(seed)
    sampled_presence = chooser.random() < 0.5
    present = sampled_presence if present is None else present
    level = 2 ** chooser.uniform(-10, -1)
    contrast = 2 ** chooser.uniform(math.log2(0.005), math.log2(0.2))
    tint = torch.tensor([chooser.uniform(0.45, 1) for _ in range(3)], dtype=torch.float32)
    tint /= tint.max()
    direction = tint * chooser.choice((-1, 1))
    if chooser.random() < 0.35:
        direction = torch.tensor([chooser.uniform(-1, 1) for _ in range(3)], dtype=torch.float32)
        direction /= direction.abs().max().clamp_min(1e-6)
    slope = (
        [chooser.uniform(-0.03, 0.03) for _ in range(2)] if chooser.random() < 0.5 else [0.0, 0.0]
    )
    angle = chooser.uniform(0, math.pi)
    angles = [angle, angle + chooser.uniform(math.pi * 35 / 180, math.pi * 145 / 180)]
    periods = [2 ** chooser.uniform(math.log2(6), math.log2(32)) for _ in range(2)]
    widths = [chooser.uniform(0.4, 1.2) for _ in range(2)]
    phases = [chooser.uniform(0, 1) for _ in range(2)]
    extent = size / pixel_scale
    center = [chooser.uniform(0.3, 0.7) * extent for _ in range(2)]
    radii = [chooser.uniform(0.2, 0.5) * extent for _ in range(2)]
    coordinates = (torch.arange(size, dtype=torch.float32) + 0.5) / pixel_scale
    y, x = torch.meshgrid(coordinates, coordinates, indexing="ij")
    background = (
        level
        * tint[:, None, None]
        * (1 + slope[0] * (x / extent - 0.5) + slope[1] * (y / extent - 0.5))
    )
    wires = []
    for angle, period, width, phase in zip(angles, periods, widths, phases, strict=True):
        distance = (
            torch.remainder(
                x * math.cos(angle) + y * math.sin(angle) + phase * period + period / 2, period
            )
            - period / 2
        )
        wires.append(torch.exp(-0.5 * (distance / width) ** 2))
    lattice = 1 - (1 - wires[0]) * (1 - wires[1])
    radius = ((x - center[0]) / radii[0]).square() + ((y - center[1]) / radii[1]).square()
    mask = torch.where(radius < 1, 0.5 * (1 + torch.cos(math.pi * radius.clamp_max(1))), 0)
    mean = (lattice * mask).sum() / mask.sum().clamp_min(1)
    field = mask * (lattice - mean)
    # Do not amplify negligible Gaussian tails when no wire crosses a small mask.
    field /= field.abs().max().clamp_min(0.1)
    if not present:
        field = torch.zeros_like(field)
    rgb = background + level * contrast * direction[:, None, None] * field
    recipe = {
        "kind": "crossed-lines",
        "present": present,
        "seed": seed,
        "size": size,
        "pixel_scale": pixel_scale,
        "level": level,
        "requested_peak_relative_contrast": contrast,
        "peak_relative_contrast": float(field.abs().max()) * contrast,
        "tint": tint.tolist(),
        "contrast_direction": direction.tolist(),
        "background_slope": slope,
        "angles_radians": angles,
        "periods_final_pixels": periods,
        "wire_sigma_final_pixels": widths,
        "phases_cycles": phases,
        "mask_center_final_pixels": center,
        "mask_radii_final_pixels": radii,
        "rms_relative_contrast": float(field.square().mean().sqrt()) * contrast,
        "space": "scene-linear-sRGB",
        "absence_probability": 0.5,
    }
    return rgb, recipe


def weak_texture(
    size: int, rng: random.Random, *, pixel_scale=1, kind=None, frequency_profile="legacy"
):
    """Return a bounded scene-linear RGB texture and its generation recipe.

    Coordinates/frequencies use final sensor-pixel units. A caller preparing a
    2x augmentation canvas must supply pixel_scale=2 and perform the final area
    reduction afterwards. This routine has no camera mosaic, noise, display
    encoding, 8-bit rasterization or global random-state dependency.

    The legacy profile is used by current quality recipes. Peak
    relative contrast is .005--.2; measured RMS contrast is recorded separately.
    Band-limited fields and curved fibers complement flat/strong-shape sources.
    """
    if type(size) is not int or size < 32:
        raise ValueError("Texture size must be an integer >=32")
    if pixel_scale not in (1, 2):
        raise ValueError("Texture pixel scale must be1 or2")
    if frequency_profile not in ("legacy", "fine-v1"):
        raise ValueError("Unknown weak texture frequency profile")
    kind = rng.choice(("bandlimited", "fibers")) if kind is None else kind
    if kind not in ("bandlimited", "fibers"):
        raise ValueError("Unknown weak texture kind")
    seed = rng.getrandbits(63)
    generator = torch.Generator(device="cpu").manual_seed(seed)
    level = 2 ** rng.uniform(-8, -1)
    contrast = 2 ** rng.uniform(math.log2(0.005), math.log2(0.2))
    tint = torch.tensor([rng.uniform(0.45, 1) for _ in range(3)], dtype=torch.float32)
    tint /= tint.max()
    recipe = {
        "kind": kind,
        "size": size,
        "pixel_scale": pixel_scale,
        "seed": seed,
        "level": level,
        "peak_relative_contrast": contrast,
        "tint": tint.tolist(),
        "space": "scene-linear-sRGB",
    }
    if frequency_profile != "legacy":
        recipe["frequency_profile"] = frequency_profile
    if kind == "bandlimited":
        # Low/high limits are safely below final Nyquist even on the 2x canvas.
        low, high = (
            (1 / 6, rng.uniform(0.34, 0.40))
            if frequency_profile == "fine-v1"
            else (1 / 48, rng.uniform(1 / 8, 0.22))
        )
        exponent = rng.uniform(0, 1.5)
        fy = torch.fft.fftfreq(size, d=1 / pixel_scale)[:, None]
        fx = torch.fft.rfftfreq(size, d=1 / pixel_scale)[None]
        radius = (fx.square() + fy.square()).sqrt()
        # Smooth compact support avoids a hard annulus ringing profile.
        position = ((radius - low) / (high - low)).clamp(0, 1)
        window = torch.sin(math.pi * position).square()
        window = torch.where((radius > low) & (radius < high), window, 0)
        spectrum = torch.fft.rfft2(torch.randn(size, size, generator=generator))
        field = torch.fft.irfft2(
            spectrum * window / radius.clamp_min(low).pow(exponent), s=(size, size)
        )
        recipe.update(
            {"frequency_band_cycles_per_final_pixel": [low, high], "amplitude_exponent": exponent}
        )
    else:
        coordinates = (torch.arange(size, dtype=torch.float32) + 0.5) / pixel_scale
        y, x = torch.meshgrid(coordinates, coordinates, indexing="ij")
        angle = rng.uniform(0, math.pi)
        period = rng.uniform(3.5, 6) if frequency_profile == "fine-v1" else rng.uniform(6, 32)
        along = x * math.cos(angle) + y * math.sin(angle)
        across = -x * math.sin(angle) + y * math.cos(angle)
        bend_period, bend = rng.uniform(32, 96), rng.uniform(0.1, 0.7)
        phase = 2 * math.pi * along / period + bend * torch.sin(2 * math.pi * across / bend_period)
        offset = rng.uniform(-math.pi, math.pi)
        field = (
            (phase + offset).cos()
            + 0.35 * (1.37 * phase + 0.3).cos()
            + 0.2 * (0.63 * phase - 0.4).sin()
        )
        recipe.update(
            {
                "angle_radians": angle,
                "carrier_period_final_pixels": period,
                "bend_period_final_pixels": bend_period,
                "bend_radians": bend,
                "phase_offset": offset,
            }
        )
    field = field - field.mean()
    field = field / field.abs().amax().clamp_min(1e-12)
    rgb = level * tint[:, None, None] * (1 + contrast * field[None])
    recipe["rms_relative_contrast"] = float(field.square().mean().sqrt()) * contrast
    return rgb.contiguous(), recipe
