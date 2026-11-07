"""Stateless fresh paired/ordinary training observations; no restoration model."""

import hashlib
import json
import math
import random

import numpy as np
import torch
from coupled_sensor_noise import coupled_sensor_noise
from paired_response_objective import paired_sensor_increment_units

from demosaic.cfa import color_indices, mosaic
from demosaic.data import augment_before_downsample, camera_pair, sample_broad_cameras
from demosaic.noise import variance_map
from demosaic.prediction_archive import fingerprint
from demosaic.suite import observation


def batch_spec(config, step):
    """Return domain/noise/geometry and a local RNG, without sampling pixels."""
    if type(step) is not int or step < 1 or step > config["steps"]:
        raise ValueError("Step outside the fixed schedule")
    rng = random.Random(f"paired-response:{config['seed']}:{step}")
    if step <= 10:
        domain = config["first_ten_domains"][step - 1]
    else:
        draw, cumulative = rng.random(), 0.0
        for domain, fraction in config["domains"].items():
            cumulative += fraction
            if draw < cumulative:
                break
    if step == 3 or rng.random() < 0.1:
        shot, read = 0.0, 0.0
    elif step == 8 or rng.random() < 0.45:
        shot, read = 0.00128, 6.5536e-6
    elif rng.random() < 0.5:
        shot, read = 0.00256, 2.62144e-5
    else:
        shot = 2 ** rng.uniform(math.log2(0.00008), math.log2(0.00256))
        read = 2 ** rng.uniform(math.log2(2e-8), math.log2(2.62144e-5))
    return (
        domain,
        {"name": f"V160-train-step{step}", "shot": shot, "read": read, "exposure": 1.0},
        config["domain_sizes"][domain],
        rng,
    )


def _seed(text):
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little") % (2**63)


def _cameras(count, seed):
    with torch.random.fork_rng(devices=[]):
        torch.set_rng_state(torch.Generator().manual_seed(seed).get_state())
        wb, inverse = sample_broad_cameras(count, "cpu")
    return wb, inverse


def _interleave(first, second):
    return torch.stack((first, second), 1).reshape(-1, *first.shape[1:])


@torch.no_grad()
def paired_observation(rgb_a, rgb_b, condition, patterns, wb, inverse, seed, *, floor_DN16=16):
    """Camera/Bayer transport with shared coupling for each aligned target pair.

    Return P0,E0,P1,E1,... layout. Camera calibration and CFA must be shared
    inside each pair. Every forward later receives only its own physical fields.
    Scene targets and pair units are training-only. No source/reference lookup.
    """
    if rgb_a.dtype != torch.float32 or rgb_a.shape != rgb_b.shape or rgb_b.dtype != torch.float32:
        raise ValueError("Expected matching FP32 RGB pair tensors")
    if rgb_a.ndim != 4 or rgb_a.shape[1] != 3 or min(rgb_a.shape) < 1:
        raise ValueError("Expected nonempty P x 3 x H x W RGB")
    count = len(rgb_a)
    if len(patterns) != count or wb.shape != (count, 3) or inverse.shape != (count, 3, 3):
        raise ValueError("One shared camera/CFA calibration required per pair")
    colors = torch.stack([color_indices(pattern) for pattern in patterns])
    clean_a, target_a = camera_pair(
        rgb_a * condition["exposure"], inverse, wb, reconstruct_highlights=True
    )
    clean_b, target_b = camera_pair(
        rgb_b * condition["exposure"], inverse, wb, reconstruct_highlights=True
    )
    sensor_a, sensor_b = [mosaic(v.clamp_min(0), colors) for v in [clean_a, clean_b]]
    noisy_a, noisy_b = coupled_sensor_noise(
        sensor_a,
        sensor_b,
        condition["shot"],
        condition["read"],
        black_level=0.03,
        generator=torch.Generator().manual_seed(seed),
    )
    units = paired_sensor_increment_units(
        sensor_a, sensor_b, condition["shot"], floor_DN16=floor_DN16
    )
    packed = _interleave(noisy_a, noisy_b)
    transform = torch.linalg.inv(inverse)
    arrays = {
        "packed": packed,
        "variance": variance_map(packed, condition["shot"], condition["read"]),
        "colors": _interleave(colors, colors),
        "wb": _interleave(wb, wb),
        "matrix": _interleave(transform, transform),
        "target": _interleave(target_a, target_b),
        "pair_indices": torch.arange(2 * count, dtype=torch.int64).reshape(count, 2),
        "pair_units": units,
    }
    sensor_metadata = {
        "seed": seed,
        "black_level": 0.03,
        "bit_depth": 16,
        "clean_packed_a": fingerprint(sensor_a.numpy()),
        "clean_packed_b": fingerprint(sensor_b.numpy()),
        "increment_mean_variance": (condition["shot"] * (sensor_a - sensor_b).abs())
        .mean((1, 2, 3))
        .tolist(),
        "units_DN16": (units.flatten() * 65535).tolist(),
        "identical_sensor_pixels": [int(v.sum()) for v in (sensor_a == sensor_b)],
        "sensor_pixels_per_pair": sensor_a[0].numel(),
        "sampler_calls": {"Poisson": 3, "Gaussian": 1},
        "scope": "Shared counts/read noise;each marginal physical. Increment units are pre-ADC training proxies,not restored RGB covariance.",
    }
    return {k: v.numpy() for k, v in arrays.items()}, sensor_metadata


def _paired_scene(config, dataset, step, pair, domain, size, rng):
    from demosaic.textures import crossed_line_texture, weak_texture

    source_seed, geometry_seed = rng.getrandbits(63), rng.getrandbits(63)
    level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.05))
    if domain == "photo":
        if dataset is None:
            raise ValueError("Photographic pairs require the frozen Commons dataset")
        item = dataset[(step - 1) * 2 + pair]
        rgb = item["rgb"]
        mean = rgb.mean((-2, -1), keepdim=True)
        contrast = 2 ** rng.uniform(math.log2(0.005), math.log2(0.2)) if rng.random() < 0.5 else 1.0
        level = 2 ** rng.uniform(math.log2(0.001), math.log2(0.1))
        scale = level / float(rgb.mean().clamp_min(1e-6))
        a = (mean + contrast * (rgb - mean)) * scale
        b = mean.expand_as(rgb) * scale
        metadata = {
            "kind": domain,
            "source": json.loads(item["source"]),
            "contrast": contrast,
            "scene_mean": level,
            "counterfactual": "Exact constant channel means of the augmented free-photo patch;constructed target,not a real empty capture.",
        }
    else:
        if domain == "mesh":
            a, recipe_a = crossed_line_texture(
                2 * size, random.Random(source_seed), pixel_scale=2, present=True
            )
            b, recipe_b = crossed_line_texture(
                2 * size, random.Random(source_seed), pixel_scale=2, present=False
            )
            assert recipe_a["seed"] == recipe_b["seed"]
        else:
            a, recipe_a = weak_texture(2 * size, random.Random(source_seed), pixel_scale=2)
            b = a.mean((-2, -1), keepdim=True).expand_as(a).clone()
            recipe_b = {"kind": "constant-counterfactual", "of_seed": recipe_a["seed"]}
        a, b = [v * (level / recipe_a["level"]) for v in [a, b]]
        a, b = [
            augment_before_downsample(
                v, size, random.Random(geometry_seed), optical_blur_probability=0.0
            )
            for v in [a, b]
        ]
        metadata = {
            "kind": domain,
            "present_recipe": recipe_a,
            "background_recipe": recipe_b,
            "source_seed": source_seed,
            "geometry_seed": geometry_seed,
            "scene_level_after_rescale": level,
            "augmentation_downsample": 2,
            "optical_blur_probability": 0.0,
        }
    assert a.shape == b.shape == (3, size, size) and a.dtype == b.dtype == torch.float32
    return a, b, metadata


def source_batch(config, dataset, step):
    """Four fresh observations;two coupled pairs on mesh/weak/photo domains."""
    if config["batch_size"] != 4:
        raise ValueError("The fixed paired-response recipe requires batch_size4")
    domain, condition, size, rng = batch_spec(config, step)
    patterns = ["RGGB", "BGGR", "GRBG", "GBRG"]
    rng.shuffle(patterns)
    paired = domain in ["mesh", "weak", "photo"]
    wb, inverse = _cameras(2 if paired else 4, _seed(f"V160-camera:{config['seed']}:{step}"))
    cases = []
    if paired:
        present, background = [], []
        for pair in range(2):
            a, b, source = _paired_scene(config, dataset, step, pair, domain, size, rng)
            present.append(a)
            background.append(b)
            for role in ["present", "background"]:
                cases.append(
                    {
                        "id": f"V160-train-{step:04d}-{len(cases)}",
                        "pattern": patterns[pair],
                        "pair": pair,
                        "role": role,
                        "source": source,
                    }
                )
        arrays, sensor = paired_observation(
            torch.stack(present),
            torch.stack(background),
            condition,
            patterns[:2],
            wb,
            inverse,
            _seed(f"V160-coupled-noise:{config['seed']}:{step}"),
            floor_DN16=config["pair_unit_floor_DN16"],
        )
    else:
        yy, xx = torch.meshgrid(
            (torch.arange(2 * size) + 0.5) / 2, (torch.arange(2 * size) + 0.5) / 2, indexing="ij"
        )
        matrices = torch.linalg.inv(inverse)
        members = []
        for index in range(4):
            level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.05))
            tint = torch.tensor([2 ** rng.uniform(-3, 0) for _ in range(3)])
            tint /= tint.max()
            if domain == "flat":
                level = 2 ** rng.uniform(math.log2(0.002), math.log2(0.9))
                sx, sy = (
                    (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05))
                    if rng.random() < 0.5
                    else (0.0, 0.0)
                )
                rgb = (
                    level
                    * tint[:, None, None]
                    * (1 + sx * (xx / size - 0.5) + sy * (yy / size - 0.5))
                )
                source = {"kind": domain, "level": level, "tint": tint.tolist(), "slopes": [sx, sy]}
            elif domain == "mixed":
                angle = rng.uniform(0, math.pi)
                coordinate = xx * math.cos(angle) + yy * math.sin(angle)
                center = rng.uniform(0.2, 0.8) * size * (math.cos(angle) + math.sin(angle))
                width = rng.uniform(2, 20)
                bar = ((coordinate - center).abs() < width).float()
                side = (
                    (xx > rng.uniform(0.2, 0.8) * size).float()
                    if rng.random() < 0.5
                    else torch.zeros_like(xx)
                )
                stripe = torch.tensor([rng.uniform(0.2, 1) for _ in range(3)])
                rgb = level * (
                    tint[:, None, None]
                    + rng.uniform(0.25, 4) * stripe[:, None, None] * bar
                    + rng.uniform(0.1, 1) * side
                )
                source = {
                    "kind": domain,
                    "level": level,
                    "angle": angle,
                    "width": width,
                    "center": center,
                    "quiet_background": True,
                }
            else:
                raise ValueError("Unknown source domain")
            rgb = augment_before_downsample(rgb, size, rng, optical_blur_probability=0.0)
            identity = f"V160-train-{step:04d}-{index}"
            arrays = observation(
                rgb[None],
                [identity],
                condition,
                patterns[index],
                wb[index].tolist(),
                matrices[index].tolist(),
                16003,
            )
            members.append({k: v.numpy() for k, v in arrays.items()})
            cases.append({"id": identity, "pattern": patterns[index], "source": source})
        arrays = {k: np.concatenate([a[k] for a in members], 0) for k in members[0]}
        arrays.update(
            pair_indices=np.empty((0, 2), dtype=np.int64),
            pair_units=np.empty((0, 1, 1, 1), dtype=np.float32),
        )
        sensor = {
            "sampler_calls": {"Poisson": 4, "Gaussian": 4},
            "black_level": 0.03,
            "bit_depth": 16,
        }
    assert len(cases) == 4 and all(np.isfinite(v).all() for v in arrays.values())
    return arrays, {
        "step": step,
        "domain": domain,
        "noise": condition,
        "cases": cases,
        "native_size": size,
        "coupled_pairs": 2 if paired else 0,
        "sensor": sensor,
    }
