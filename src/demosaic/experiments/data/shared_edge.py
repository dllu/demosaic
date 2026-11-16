"""Training-only faint mesh increments on a shared strong-edge background.

Paired targets preserve the broad scene. All recipes are procedural; no image
or held-out reference is read. Geometry precedes 2x area reduction, and the
existing coupled physical sensor sampler supplies the two noisy marginals.
"""

import copy
import math
import random

import numpy as np
import torch
from demosaic.experiments.data.mesh import render_recipe
from demosaic.experiments.data.paired import _cameras, _seed, paired_observation

from demosaic.cfa import PATTERNS
from demosaic.data import augment_before_downsample

PROFILE = "shared-edge-faint-mesh-v1"
SEED = 202611080202


def pair_recipe(size, step, ordinal, pair, *, seed=SEED):
    if type(size) is not int or size < 32 or size % 2:
        raise ValueError("Expected even native size>=32")
    if type(step) is not int or step < 1 or type(ordinal) is not int or ordinal < 0:
        raise ValueError("Expected positive step and nonnegative mixed ordinal")
    if type(pair) is not int or pair not in (0, 1):
        raise ValueError("Expected pair0 or1")
    rng = random.Random(_seed(f"{PROFILE}:{seed}:{step}:{pair}"))
    index = 2 * ordinal + pair
    level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.08))
    bright = 2 ** rng.uniform(math.log2(max(0.02, 2 * level)), math.log2(0.8))
    colors = [[rng.uniform(0.25, 1) for _ in range(3)] for _ in range(2)]
    colors = [[v / max(c) for v in c] for c in colors]
    kind = ("vertical-step", "bar", "slanted-step", "corner")[index % 4]
    angle = 0.0 if kind == "vertical-step" else rng.uniform(0.1, math.pi - 0.1)
    offset = rng.uniform(-0.15, 0.15) * size
    center = size / 2 * (math.cos(angle) + math.sin(angle)) + offset
    placement = (-0.18, 0.0, 0.18)[index % 3] * size
    mesh_center = [
        size / 2 + (offset + placement) * math.cos(angle),
        size / 2 + (offset + placement) * math.sin(angle),
    ]
    direction_kind = rng.random()
    if direction_kind < 0.45:
        direction, color_role = [-0.2, -1.0, -0.35], "dark-green"
    elif direction_kind < 0.75:
        direction, color_role = [-1.0, -1.0, -1.0], "dark-neutral"
    else:
        direction = [rng.uniform(-1, 1) for _ in range(3)]
        scale = max(abs(v) for v in direction)
        direction = [v / max(scale, 1e-6) for v in direction]
        color_role = "signed-chromatic"
    wire_angle = rng.uniform(0, math.pi)
    period_bounds = (6.0, 10.0) if index % 2 else (6.0, 32.0)
    mesh = {
        "kind": "crossed-lines",
        "present": index % 5 != 0,
        "seed": rng.getrandbits(63),
        "size": 2 * size,
        "pixel_scale": 2,
        "level": level,
        "requested_peak_relative_contrast": 2 ** rng.uniform(math.log2(0.005), math.log2(0.2)),
        "tint": [1.0, 1.0, 1.0],
        "contrast_direction": direction,
        "background_slope": [0.0, 0.0],
        "angles_radians": [wire_angle, wire_angle + rng.uniform(math.pi * 0.25, math.pi * 0.75)],
        "periods_final_pixels": [
            2 ** rng.uniform(math.log2(period_bounds[0]), math.log2(period_bounds[1]))
            for _ in range(2)
        ],
        "wire_sigma_final_pixels": [rng.uniform(0.4, 1.2) for _ in range(2)],
        "phases_cycles": [rng.random(), rng.random()],
        "mask_center_final_pixels": mesh_center,
        "mask_radii_final_pixels": [rng.uniform(0.22, 0.38) * size for _ in range(2)],
        "space": "scene-linear-sRGB",
    }
    return {
        "kind": PROFILE,
        "size": size,
        "step": step,
        "mixed_ordinal": ordinal,
        "pair": pair,
        "background": {
            "kind": kind,
            "level": level,
            "bright_level": bright,
            "colors": colors,
            "angle": angle,
            "center": center,
            "half_width": rng.uniform(0.5, 12),
            "slopes": [rng.uniform(-0.02, 0.02) for _ in range(2)],
        },
        "mesh": mesh,
        "mesh_color_role": color_role,
        "placement_relative_to_edge": ("negative-side", "at-edge", "positive-side")[index % 3],
        "geometry_seed": rng.getrandbits(63),
        "optical_blur_probability": 0.0,
        "augmentation_downsample": 2,
        "counterfactual": "Identical broad scene, geometry and camera;only the compact mesh increment is absent.",
    }


def render_pair(recipe, *, augment=True):
    """Return present/background targets; no clipping or stochastic sensor calls."""
    size = recipe["size"]
    if type(size) is not int or size < 32 or size % 2:
        raise ValueError("Expected even native size>=32")
    b = recipe["background"]
    coordinates = (torch.arange(2 * size, dtype=torch.float32) + 0.5) / 2
    y, x = torch.meshgrid(coordinates, coordinates, indexing="ij")
    angle = b["angle"]
    u = x * math.cos(angle) + y * math.sin(angle) - b["center"]
    if b["kind"] == "bar":
        region = u.abs() < b["half_width"]
    elif b["kind"] in ("vertical-step", "slanted-step"):
        region = u > 0
    elif b["kind"] == "corner":
        v = -(x - size / 2) * math.sin(angle) + (y - size / 2) * math.cos(angle)
        region = (u > 0) & (v > 0)
    else:
        raise ValueError("Unknown background geometry")
    low = b["level"] * torch.tensor(b["colors"][0], dtype=torch.float32)
    high = b["bright_level"] * torch.tensor(b["colors"][1], dtype=torch.float32)
    sx, sy = b["slopes"]
    broad = (low[:, None, None] + (high - low)[:, None, None] * region) * (
        1 + sx * (x / size - 0.5) + sy * (y / size - 0.5)
    )
    wire, measured = render_recipe(recipe["mesh"])
    empty, _ = render_recipe(dict(recipe["mesh"], present=False))
    present = broad + (wire - empty)
    assert torch.isfinite(present).all() and present.min() >= 0 and present.max() < 1
    if augment:
        present, broad = [
            augment_before_downsample(
                v, size, random.Random(recipe["geometry_seed"]), optical_blur_probability=0.0
            )
            for v in (present, broad)
        ]
    return present, broad, measured


@torch.no_grad()
def shared_edge_observation(item, calibration, ordinal, *, seed=SEED):
    metadata = copy.deepcopy(item["metadata"])
    if metadata["domain"] != "mixed":
        raise ValueError("Only mixed training rows may be replaced")
    size, step = metadata["native_size"], item["step"]
    wb, inverse = _cameras(4, _seed(f"V160-camera:160:{step}"))
    np.testing.assert_array_equal(wb.numpy(), calibration["wb"])
    np.testing.assert_array_equal(torch.linalg.inv(inverse).numpy(), calibration["matrix"])
    chosen = [0, 2]
    patterns = [
        next(name for name, colors in PATTERNS.items() if list(colors) == list(c))
        for c in calibration["colors"][chosen]
    ]
    first, second, cases = [], [], []
    for pair in range(2):
        source = pair_recipe(size, step, ordinal, pair, seed=seed)
        a, b, measured = render_pair(source)
        source["measured_mesh"] = measured
        first.append(a)
        second.append(b)
        for role in ("present", "background"):
            cases.append(
                {
                    "id": f"V202-shared-edge-{step:04d}-{len(cases)}",
                    "pattern": patterns[pair],
                    "pair": pair,
                    "role": role,
                    "source": source,
                }
            )
    arrays, sensor = paired_observation(
        torch.stack(first),
        torch.stack(second),
        metadata["noise"],
        patterns,
        wb[chosen],
        inverse[chosen],
        _seed(f"V202-coupled-noise:{seed}:{step}"),
        floor_DN16=16,
    )
    assert all(np.isfinite(v).all() for v in arrays.values())
    metadata.update(
        cases=cases,
        coupled_pairs=2,
        sensor=sensor,
        training_distribution=PROFILE,
        mixed_batch_ordinal=ordinal,
        replaced_calibration_members=chosen,
        changed="Shared edge/background plus weak mesh increment;pair coupling,geometry/content/noise draws change together. Original mixed noise coefficients and domain schedule retained.",
    )
    return arrays, metadata
