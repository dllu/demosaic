"""Held-out finite wire increments with independent sensor draws per role.

This evaluation-only generator reads no photographs. Geometry precedes area
reduction. Targets have zero, one strong, or strong plus weaker wire families;
noise is deliberately independent between those counterfactual roles.
"""

import math
import random

import numpy as np
import torch
from torch.nn import functional as F

from demosaic.data import camera_pair
from demosaic.suite import observation

from .paired import _cameras

SEED = 202611160500
CONDITION = {"name": "iso6400-prior", "shot": 0.00128, "read": 6.5536e-6, "exposure": 1.0}


def scene_recipe(source, *, size=512):
    if type(source) is not int or not 0 <= source < 100:
        raise ValueError("Expected evaluation source0..99")
    if type(size) is not int or size < 64 or size % 4:
        raise ValueError("Expected native size divisible by four and at least64")
    rng = random.Random(f"heldout-edge-response:{SEED}:{source}")
    angle = rng.uniform(0.25, 1.1)
    level = rng.uniform(0.015, 0.03)
    return {
        "source": source,
        "seed": SEED,
        "size": size,
        "level": level,
        "bright_level": rng.uniform(0.12, 0.3),
        "edge_angle": rng.uniform(0.15, math.pi - 0.15),
        "edge_jitter": rng.uniform(-0.015, 0.015) * size,
        "wire_angles": [angle, angle + rng.uniform(0.85, 1.4)],
        "periods": [rng.uniform(7.0, 11.0), rng.uniform(11.0, 22.0)],
        "widths": [rng.uniform(0.45, 0.8), rng.uniform(0.45, 0.8)],
        "phases": [rng.random(), rng.random()],
        "amplitude": level * rng.uniform(0.04, 0.12),
        "weak_fraction": 0.5,
        "mask_radii": [size * 0.23, size * 0.29],
        "camera_seed": SEED + 1000 + source,
        "optical_blur": 0.0,
        "area_reduction": 2,
    }


def render_scene(recipe, placement):
    if placement not in ("near", "far"):
        raise ValueError("Expected near or far edge placement")
    size = recipe["size"]
    coordinates = (torch.arange(2 * size, dtype=torch.float32) + 0.5) / 2
    y, x = torch.meshgrid(coordinates, coordinates, indexing="ij")
    center = size / 2
    a = recipe["edge_angle"]
    distance = (
        (x - center) * math.cos(a)
        + (y - center) * math.sin(a)
        - recipe["edge_jitter"]
        - (0 if placement == "near" else 0.40 * size)
    )
    low = recipe["level"] * torch.tensor([0.8, 1.0, 0.7])[:, None, None]
    high = recipe["bright_level"] * torch.tensor([1.0, 0.8, 0.6])[:, None, None]
    background = low + (high - low) * (distance > 0)
    rx, ry = recipe["mask_radii"]
    radius = ((x - center) / rx) ** 2 + ((y - center) / ry) ** 2
    envelope = torch.where(radius < 1, 0.5 * (1 + torch.cos(math.pi * radius.clamp_max(1))), 0)
    components = []
    drifts = recipe.get("phase_drifts")
    for i in range(2):
        angle, period, width, phase = (
            recipe[k][i] for k in ("wire_angles", "periods", "widths", "phases")
        )
        cosine, sine = math.cos(angle), math.sin(angle)
        position = x * cosine + y * sine
        if drifts is not None and any(drifts[i]):
            normal = ((x - center) * cosine + (y - center) * sine) / (size / 2)
            tangent = (-(x - center) * sine + (y - center) * cosine) / (size / 2)
            q_normal, q_tangent = drifts[i]
            position += 0.5 * period * (q_normal * normal.square() + q_tangent * tangent.square())
        d = torch.remainder(position + phase * period + period / 2, period) - period / 2
        wire = torch.exp(-0.5 * (d / width) ** 2)
        field = envelope * (wire - (wire * envelope).sum() / envelope.sum())
        field /= field.abs().max().clamp_min(0.1)
        amplitude = recipe["amplitude"] * (1 if i == 0 else recipe["weak_fraction"])
        components.append(-amplitude * torch.tensor([0.2, 1.0, 0.35])[:, None, None] * field)
    # Average the common scene and increments separately, keeping their identities.
    background = F.avg_pool2d(background, 2)
    components = F.avg_pool2d(torch.stack(components), 2)
    rgb = torch.stack(
        (background, background + components[0], background + components[0] + components[1])
    )
    if not torch.isfinite(rgb).all() or rgb.min() < 0 or rgb.max() >= 1:
        raise ValueError("Invalid clean evaluation target")
    edge_band = F.avg_pool2d((distance.abs() < 24).float()[None], 2)[0] > 0.99
    quiet = (components == 0).all((0, 1)) & (
        F.avg_pool2d((distance.abs() > 32).float()[None], 2)[0] > 0.99
    )
    return rgb, components, {"quiet": quiet.numpy(), "edge_band": edge_band.numpy()}


@torch.no_grad()
def edge_observation(recipe, placement, pattern, repeat, *, condition=None):
    if type(repeat) is not int or repeat < 0:
        raise ValueError("Expected nonnegative independent repeat")
    condition = CONDITION if condition is None else condition
    if condition["exposure"] != 1.0:
        raise ValueError("Noise-profile comparisons preserve the exact clean exposure")
    rgb, _, masks = render_scene(recipe, placement)
    wb, inverse = _cameras(1, recipe["camera_seed"])
    clean, _ = camera_pair(rgb, inverse.expand(3, -1, -1), wb.expand(3, -1))
    if clean.min() < 0 or clean.max() >= 1:
        raise ValueError("Camera transport would clip this diagnostic's sensor target")
    identities = [
        f"edge-response:{recipe['source']}:{placement}:{repeat}:role{r}" for r in range(3)
    ]
    arrays = observation(
        rgb,
        identities,
        condition,
        pattern,
        wb[0].tolist(),
        torch.linalg.inv(inverse)[0].tolist(),
        SEED,
    )
    arrays = {k: v.numpy() for k, v in arrays.items()}
    arrays.update(masks)
    # Actual camera-target differences, accumulated in FP64 during scoring.
    assert arrays["target"].dtype == np.float32
    return arrays, {
        "recipe": recipe,
        "placement": placement,
        "pattern": pattern,
        "repeat": repeat,
        "identities": identities,
        "roles": ["background", "one-direction", "two-directions"],
        "noise": condition,
        "noise_coupling": "none: distinct role/repeat keys",
    }
