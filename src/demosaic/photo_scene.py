"""Whole noisy photo context around an unchanged canonical benchmark crop."""

import hashlib
from dataclasses import dataclass

import torch

from .cfa import PATTERNS
from .scene_data import SceneRecipe, observe_scene


@dataclass(frozen=True)
class PhotoSceneContext:
    packed: torch.Tensor
    variance: torch.Tensor
    colors: torch.Tensor
    wb: torch.Tensor
    matrix: torch.Tensor
    box_xywh: tuple[int, int, int, int]
    source_origin_xy: tuple[int, int]
    noise_seed: int


def benchmark_photo_context(linear_rgb, legacy_xywh, canonical, condition, *, identity, seed):
    """Simulate only the surrounding context, retaining every scored input bit.

    `linear_rgb` is the complete cached binned source used by the benchmark.
    The five canonical inputs are a single native crop from that source. Its
    measured packed RAW and variance overwrite the same region of a separately
    declared full-scene noisy observation. Targets are neither read nor returned.

    A crop with an odd source origin defines a CFA frame shifted by at most one
    source pixel. Trim at most one pixel per side, leaving the crop unchanged.
    Thus its existing CFA label/phase remains correct without relocating or
    resampling the scored crop. The full scene is input context only; retain
    the original canonical five tensors for the actual restoration forward.
    """
    if (
        linear_rgb.ndim != 3
        or linear_rgb.shape[0] != 3
        or linear_rgb.device.type != "cpu"
        or linear_rgb.dtype != torch.float32
        or not torch.isfinite(linear_rgb).all()
        or len(legacy_xywh) != 4
        or any(type(v) is not int for v in legacy_xywh)
    ):
        raise ValueError("Require an explicit complete CPU RGB field and integer source box")
    x, y, w, h = legacy_xywh
    if min(x, y) < 0 or min(w, h) < 4 or w % 2 or h % 2:
        raise ValueError("Require an even-sized native crop inside the source")
    if x + w > linear_rgb.shape[2] or y + h > linear_rgb.shape[1]:
        raise ValueError("Legacy crop leaves the cached source")
    inputs = {
        k: canonical[k].detach().cpu() for k in ["packed", "variance", "colors", "wb", "matrix"]
    }
    if (
        inputs["packed"].shape != (1, 4, h // 2, w // 2)
        or inputs["variance"].shape != inputs["packed"].shape
        or inputs["colors"].shape != (1, 4)
        or inputs["wb"].shape != (1, 3)
        or inputs["matrix"].shape != (1, 3, 3)
        or any(not torch.isfinite(v).all() for v in inputs.values())
        or inputs["packed"].dtype != torch.float32
        or inputs["variance"].dtype != torch.float32
    ):
        raise ValueError("Require one finite canonical FP32 crop with matching calibration")
    labels = tuple(inputs["colors"][0].tolist())
    pattern = next((p for p, values in PATTERNS.items() if values == labels), None)
    if pattern is None:
        raise ValueError("Require the actual canonical CFA pattern")
    key = f"scene-surround-v1:{seed}:{identity}:{condition['name']}:{pattern}"
    noise_seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % 2**62
    recipe = SceneRecipe(
        pattern,
        tuple(inputs["wb"][0].tolist()),
        tuple(tuple(row) for row in torch.linalg.inv(inputs["matrix"][0].float()).tolist()),
        float(condition["exposure"]),
        float(condition["shot"]),
        float(condition["read"]),
        0.03,
        noise_seed,
    )
    ox, oy = x % 2, y % 2
    nh = (linear_rgb.shape[1] - oy) // 2 * 2
    nw = (linear_rgb.shape[2] - ox) // 2 * 2
    rgb = linear_rgb[:, oy : oy + nh, ox : ox + nw]
    observation = observe_scene(rgb, recipe)
    packed, variance = observation.packed, observation.variance
    px, py = (x - ox) // 2, (y - oy) // 2
    packed[:, py : py + h // 2, px : px + w // 2] = inputs["packed"][0]
    variance[:, py : py + h // 2, px : px + w // 2] = inputs["variance"][0]
    return PhotoSceneContext(
        packed,
        variance,
        inputs["colors"][0],
        inputs["wb"][0],
        inputs["matrix"][0],
        (x - ox, y - oy, w, h),
        (ox, oy),
        noise_seed,
    )
