"""Fresh physical sensor noise on retained, preflighted camera-RGB scenes.

This does not treat an arbitrary restoration target as an unclipped sensor
signal. Paired clean-sensor fingerprints must match their original construction;
unpaired scenes need a separate preflight proving reference-white clipping was
inactive. Targets/calibration/pair units stay fixed and never enter inference.
"""

import hashlib
import math

import numpy as np
import torch
from coupled_sensor_noise import coupled_sensor_noise

from demosaic.cfa import mosaic
from demosaic.noise import add_noise, variance_map
from demosaic.prediction_archive import fingerprint


class SensorSignalUnavailable(ValueError):
    """A valid cached target cannot prove the original unclipped sensor signal."""


def noise_seed(row, cache_step, *, seed=17501):
    if any(type(v) is not int or v < 1 for v in [row, cache_step, seed]):
        raise ValueError("Positive integer row, cache step and seed required")
    token = f"V175-fresh-sensor:{seed}:{row}:{cache_step}".encode()
    return int.from_bytes(hashlib.sha256(token).digest()[:8], "little") % 2**63


def clean_sensor(arrays, metadata):
    """Recover only the exact unclipped sensor cases admitted by preflight."""
    names = {"packed", "variance", "colors", "wb", "matrix", "target", "pair_indices", "pair_units"}
    if set(arrays) != names:
        raise ValueError("Unexpected cached observation fields")
    if any(not isinstance(v, np.ndarray) or not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError("Cached fields must be finite NumPy arrays")
    target, packed, colors, pairs = [
        arrays[k] for k in ["target", "packed", "colors", "pair_indices"]
    ]
    if (
        target.dtype != np.float32
        or target.ndim != 4
        or target.shape[1] != 3
        or min(target.shape) < 1
        or target.shape[-2] % 2
        or target.shape[-1] % 2
        or packed.dtype != np.float32
        or packed.shape != (len(target), 4, target.shape[-2] // 2, target.shape[-1] // 2)
        or colors.dtype != np.int64
        or colors.shape != (len(target), 4)
        or (colors < 0).any()
        or (colors > 2).any()
        or arrays["variance"].shape != packed.shape
        or arrays["variance"].dtype != np.float32
        or (arrays["variance"] < 0).any()
        or arrays["wb"].shape != (len(target), 3)
        or arrays["wb"].dtype != np.float32
        or arrays["matrix"].shape != (len(target), 3, 3)
        or arrays["matrix"].dtype != np.float32
        or (arrays["wb"] <= 0).any()
        or pairs.dtype != np.int64
        or pairs.ndim != 2
        or pairs.shape[1] != 2
        or arrays["pair_units"].shape != (len(pairs), 1, 1, 1)
        or arrays["pair_units"].dtype != np.float32
        or (arrays["pair_units"] <= 0).any()
    ):
        raise ValueError("Invalid cached observation shape, dtype or calibration")
    if len(pairs) and (
        pairs.min() < 0
        or pairs.max() >= len(target)
        or len(np.unique(pairs)) != pairs.size
        or pairs.size != len(target)
    ):
        raise ValueError("Expected disjoint pairs covering every member")
    sensor = metadata["sensor"]
    if sensor["black_level"] != 0.03 or sensor["bit_depth"] != 16:
        raise ValueError("Only the retained 16-bit, 0.03-black sensor is admitted")
    noise = metadata["noise"]
    if any(not math.isfinite(noise[k]) or noise[k] < 0 for k in ["shot", "read"]):
        raise ValueError("Invalid sensor coefficients")
    clean = mosaic(torch.from_numpy(target).clamp_min(0), torch.from_numpy(colors))
    if len(pairs):
        first, second = pairs.T
        if any(
            not np.array_equal(arrays[k][first], arrays[k][second])
            for k in ["colors", "wb", "matrix"]
        ):
            raise ValueError("Paired calibration must match")
        if (
            fingerprint(clean[first].numpy()) != sensor["clean_packed_a"]
            or fingerprint(clean[second].numpy()) != sensor["clean_packed_b"]
        ):
            raise SensorSignalUnavailable("Target does not reproduce the original unclipped sensor")
    else:
        # Reference-white clipping would place at least one scene-linear RGB
        # channel at one. Require a generous interior margin instead of trying
        # to invert a clipped target. The full retained bank is preflighted too.
        scene = np.einsum(
            "bij,bjhw->bihw",
            arrays["matrix"].astype(np.float64),
            target.astype(np.float64) * arrays["wb"][:, :, None, None],
        )
        if scene.max() >= 0.999 or scene.min() < -1e-6:
            raise SensorSignalUnavailable("Unpaired reference-white clipping cannot be excluded")
    return clean


def renoise(arrays, metadata, row, cache_step, *, seed=17501):
    """Change only noisy RAW and its noisy-intensity variance conditioning.

    A stateless CPU generator supplies a new realization for every continuation
    row. Paired members keep common Poisson counts/read noise. Global CPU/CUDA
    generators are untouched. ADC-only rows are reused and skipped by training.
    """
    selected_seed = noise_seed(row, cache_step, seed=seed)
    clean = clean_sensor(arrays, metadata)
    noise = metadata["noise"]
    if noise["shot"] == noise["read"] == 0:
        return dict(arrays), {
            "seed": None,
            "Poisson_calls": 0,
            "Gaussian_calls": 0,
            "ADC_reused": True,
        }
    generator = torch.Generator(device="cpu").manual_seed(selected_seed)
    pairs = arrays["pair_indices"]
    if len(pairs):
        first, second = pairs.T
        a, b = coupled_sensor_noise(
            clean[first],
            clean[second],
            noise["shot"],
            noise["read"],
            black_level=0.03,
            generator=generator,
        )
        packed = torch.empty_like(clean)
        packed[first], packed[second] = a, b
        poisson = 3
    else:
        packed = add_noise(
            clean, noise["shot"], noise["read"], black_level=0.03, generator=generator
        )
        poisson = 1
    result = dict(arrays)
    result["packed"] = packed.numpy()
    result["variance"] = variance_map(packed, noise["shot"], noise["read"]).numpy()
    return result, {
        "seed": selected_seed,
        "Poisson_calls": poisson,
        "Gaussian_calls": 1,
        "ADC_reused": False,
    }
