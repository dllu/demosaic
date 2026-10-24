"""Continuous-precision weak textures with explicit final-pixel frequency profiles."""

import math
import random

import torch


def weak_texture(size: int, rng: random.Random, *, pixel_scale=1, kind=None, frequency_profile="legacy"):
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
        low, high = ((1 / 6, rng.uniform(.34, .40)) if frequency_profile == "fine-v1"
                     else (1 / 48, rng.uniform(1 / 8, 0.22)))
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
