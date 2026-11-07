"""Training-only fine crossed-wire distribution from retained procedural recipes.

No photograph or held-out reference supplies pixels. Half the mesh batches are
retained exactly; selected batches change both wire periods and contrast bands.
Camera, geometry, background, exposure and physical noise coefficients match.
Noise seeds match, but changed Poisson rates do not imply identical noise draws.
"""

import copy
import math

import numpy as np
import torch
from paired_response_data import _cameras, _seed, paired_observation

from demosaic.cfa import PATTERNS
from demosaic.data import augment_before_downsample

CONTRAST_EDGES = (0.02, 0.05, 0.125, 0.25, 0.4)
PROFILE = "fine-mesh-ladder-v1"


def selected_mesh_batch(ordinal):
    if type(ordinal) is not int or ordinal < 0:
        raise ValueError("Expected nonnegative mesh-batch ordinal")
    return ordinal % 2 == 0


def edit_recipe(recipe, ordinal, pair):
    """Deterministic quantile transport; keep all other continuous recipe fields."""
    if not selected_mesh_batch(ordinal) or type(pair) is not int or pair not in (0, 1):
        raise ValueError("Expected a selected batch and pair0 or1")
    old_periods = recipe["periods_final_pixels"]
    old_contrast = recipe["requested_peak_relative_contrast"]
    if len(old_periods) != 2 or not all(6 <= v <= 32 for v in old_periods):
        raise ValueError("Expected legacy6--32 pixel wire periods")
    if not 0.005 <= old_contrast <= 0.2:
        raise ValueError("Expected legacy.005--.2 relative contrast")
    band = ((ordinal // 2) * 2 + pair) % 4
    quantile = math.log(old_contrast / 0.005) / math.log(0.2 / 0.005)
    lo, hi = CONTRAST_EDGES[band : band + 2]
    result = copy.deepcopy(recipe)
    result.update(
        periods_final_pixels=[
            6 * (10 / 6) ** (math.log(v / 6) / math.log(32 / 6)) for v in old_periods
        ],
        requested_peak_relative_contrast=lo * (hi / lo) ** quantile,
        training_distribution=PROFILE,
        contrast_band=band,
        contrast_band_edges=[lo, hi],
    )
    # These two fields describe pixels and must be measured after rendering.
    result.pop("rms_relative_contrast", None)
    result.pop("peak_relative_contrast", None)
    return result


def render_recipe(recipe):
    """Replay the existing FP32 construction order without RNG or resampling.

    A legacy recipe must reproduce crossed_line_texture pixel-for-pixel. Area
    reduction and geometry remain the original separate augmentation operation.
    """
    size, pixel_scale = recipe["size"], recipe["pixel_scale"]
    if type(size) is not int or size < 32 or pixel_scale not in (1, 2):
        raise ValueError("Expected legacy crossed-line canvas dimensions")
    level, contrast = recipe["level"], recipe["requested_peak_relative_contrast"]
    tint = torch.tensor(recipe["tint"], dtype=torch.float32)
    direction = torch.tensor(recipe["contrast_direction"], dtype=torch.float32)
    sx, sy = recipe["background_slope"]
    extent = size / pixel_scale
    coordinates = (torch.arange(size, dtype=torch.float32) + 0.5) / pixel_scale
    y, x = torch.meshgrid(coordinates, coordinates, indexing="ij")
    background = level * tint[:, None, None] * (
        1 + sx * (x / extent - 0.5) + sy * (y / extent - 0.5)
    )
    wires = []
    for angle, period, width, phase in zip(
        recipe["angles_radians"], recipe["periods_final_pixels"],
        recipe["wire_sigma_final_pixels"], recipe["phases_cycles"], strict=True,
    ):
        distance = torch.remainder(
            x * math.cos(angle) + y * math.sin(angle) + phase * period + period / 2,
            period,
        ) - period / 2
        wires.append(torch.exp(-0.5 * (distance / width) ** 2))
    lattice = 1 - (1 - wires[0]) * (1 - wires[1])
    center, radii = recipe["mask_center_final_pixels"], recipe["mask_radii_final_pixels"]
    radius = ((x - center[0]) / radii[0]).square() + ((y - center[1]) / radii[1]).square()
    mask = torch.where(radius < 1, 0.5 * (1 + torch.cos(math.pi * radius.clamp_max(1))), 0)
    mean = (lattice * mask).sum() / mask.sum().clamp_min(1)
    field = mask * (lattice - mean)
    field /= field.abs().max().clamp_min(0.1)
    if not recipe["present"]:
        field = torch.zeros_like(field)
    rgb = background + level * contrast * direction[:, None, None] * field
    measured = copy.deepcopy(recipe)
    measured["rms_relative_contrast"] = float(field.square().mean().sqrt()) * contrast
    measured["peak_relative_contrast"] = float(field.abs().max()) * contrast
    return rgb, measured


@torch.no_grad()
def edited_observation(item, original_arrays, ordinal, *, seed=160):
    """Build one selected mesh batch; no restoration model or image-file reads."""
    metadata = copy.deepcopy(item["metadata"])
    if metadata["domain"] != "mesh" or not selected_mesh_batch(ordinal):
        raise ValueError("Only selected mesh batches may be reconstructed")
    size, step = metadata["native_size"], item["step"]
    wb, inverse = _cameras(2, _seed(f"V160-camera:{seed}:{step}"))
    matrix = torch.linalg.inv(inverse)
    np.testing.assert_array_equal(wb.numpy(), original_arrays["wb"][::2])
    np.testing.assert_array_equal(matrix.numpy(), original_arrays["matrix"][::2])
    patterns = [next(k for k, v in PATTERNS.items() if list(v) == list(c))
                for c in original_arrays["colors"][::2]]
    first, second, cases = [], [], []
    for pair in range(2):
        source = copy.deepcopy(metadata["cases"][2 * pair]["source"])
        recipe = edit_recipe(source["present_recipe"], ordinal, pair)
        a, present_recipe = render_recipe(recipe)
        empty_recipe = dict(recipe, present=False)
        b, empty_recipe = render_recipe(empty_recipe)
        a, b = [v * (source["scene_level_after_rescale"] / recipe["level"]) for v in (a, b)]
        a, b = [augment_before_downsample(
            v, size, __import__("random").Random(source["geometry_seed"]),
            optical_blur_probability=0.0,
        ) for v in (a, b)]
        assert torch.isfinite(a).all() and torch.isfinite(b).all() and a.min() >= 0
        first.append(a)
        second.append(b)
        source.update(
            previous_present_recipe=source["present_recipe"],
            present_recipe=present_recipe, background_recipe=empty_recipe,
            training_distribution=PROFILE, mesh_batch_ordinal=ordinal,
        )
        for role in ("present", "background"):
            cases.append(dict(metadata["cases"][2 * pair + (role == "background")],
                              id=f"V168-fine-mesh-{step:04d}-{len(cases)}", source=source))
    arrays, sensor = paired_observation(
        torch.stack(first), torch.stack(second), metadata["noise"], patterns, wb, inverse,
        metadata["sensor"]["seed"], floor_DN16=16,
    )
    for key in ("wb", "matrix", "colors", "pair_indices"):
        np.testing.assert_array_equal(arrays[key], original_arrays[key])
    np.testing.assert_array_equal(arrays["target"][1::2], original_arrays["target"][1::2])
    assert all(np.isfinite(v).all() for v in arrays.values())
    metadata.update(cases=cases, sensor=sensor, training_distribution=PROFILE)
    return arrays, metadata
