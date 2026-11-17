"""One noisy complete observation shared by scene context and native crops."""

import math
import random
from dataclasses import dataclass

import torch

from .cfa import PATTERNS, mosaic
from .data import camera_pair
from .noise import add_noise, variance_map


@dataclass(frozen=True)
class SceneRecipe:
    pattern: str
    wb: tuple[float, float, float]
    camera_inverse: tuple[tuple[float, float, float], ...]
    exposure: float
    shot: float
    read: float
    black: float
    noise_seed: int

    def __post_init__(self):
        inverse = torch.as_tensor(self.camera_inverse, dtype=torch.float64)
        if (
            self.pattern not in PATTERNS
            or len(self.wb) != 3
            or any(not math.isfinite(x) or x <= 0 for x in self.wb)
            or inverse.shape != (3, 3)
            or not torch.isfinite(inverse).all()
            or abs(torch.linalg.det(inverse)) < 1e-5
            or not all(math.isfinite(v) for v in [self.exposure, self.shot, self.read, self.black])
            or self.exposure <= 0
            or min(self.shot, self.read, self.black) < 0
            or self.black >= 1
            or type(self.noise_seed) is not int
            or self.noise_seed < 0
        ):
            raise ValueError("Require explicit finite camera, noise, exposure and seed")


def sample_scene_recipe(seed):
    """CPU counter-keyed broad camera/noise priors, independent of pixel values."""
    rng = random.Random(seed)
    wb = (
        2 ** rng.uniform(math.log2(0.65), math.log2(3.6)),
        1.0,
        2 ** rng.uniform(math.log2(0.65), math.log2(3.6)),
    )
    limits = [[0, 0.55, 0.20], [0.18, 0, 0.35], [0.12, 0.40, 0]]
    if rng.random() < 0.25:
        limits = [[0 if i == j else 0.12 for j in range(3)] for i in range(3)]
    off = torch.tensor([[rng.random() * v for v in row] for row in limits], dtype=torch.float64)
    off *= 0.65 / off.sum(-1, keepdim=True).clamp_min(0.65)
    inverse = torch.diag(1 - off.sum(-1)) + off
    if torch.linalg.det(inverse) < 0.08:
        off *= 0.5
        inverse = torch.diag(1 - off.sum(-1)) + off
    capacity = rng.uniform(3, 6) ** 2 * rng.uniform(1400, 2400) / 2 ** rng.uniform(-1, 7)
    shot, read = 1 / capacity, (rng.uniform(0.7, 5) / capacity) ** 2
    if rng.random() < 0.1:
        shot = read = 0.0
    return SceneRecipe(
        rng.choice(tuple(PATTERNS)),
        wb,
        tuple(tuple(r) for r in inverse.tolist()),
        2 ** rng.uniform(-3, 2),
        shot,
        read,
        rng.uniform(0.002, 0.06),
        rng.randrange(2**62),
    )


@dataclass(frozen=True)
class SceneObservation:
    packed: torch.Tensor
    variance: torch.Tensor
    colors: torch.Tensor
    wb: torch.Tensor
    matrix: torch.Tensor
    target: torch.Tensor
    sensor_target: torch.Tensor
    recipe: SceneRecipe

    def crops(self, boxes_xywh):
        """Copy exact phase-preserving crops, without a second sensor draw."""
        h, w = self.target.shape[-2:]
        boxes = [tuple(b) for b in boxes_xywh]
        if (
            not boxes
            or any(
                len(b) != 4
                or any(type(v) is not int for v in b)
                or min(b[:2]) < 0
                or min(b[2:]) < 4
                or any(v % 2 for v in b)
                or b[0] + b[2] > w
                or b[1] + b[3] > h
                for b in boxes
            )
            or len({b[2:] for b in boxes}) != 1
        ):
            raise ValueError("Require equal-size, even native boxes inside the complete scene")
        result = {}
        for name in ["packed", "variance", "target", "sensor_target"]:
            array = getattr(self, name)
            scale = 2 if name in ["packed", "variance"] else 1
            result[name] = torch.stack(
                [
                    array[..., y // scale : (y + bh) // scale, x // scale : (x + bw) // scale]
                    for x, y, bw, bh in boxes
                ]
            )
        for name in ["colors", "wb", "matrix"]:
            array = getattr(self, name)
            result[name] = array[None].expand(len(boxes), *array.shape)
        result["shot"] = self.packed.new_full((len(boxes), 1, 1, 1), self.recipe.shot)
        result["read"] = self.packed.new_full((len(boxes), 1, 1, 1), self.recipe.read)
        return result


def observe_scene(linear_rgb, recipe):
    """Apply the camera, CFA and Poisson/signed-read/ADC model once, globally.

    Clean targets remain separate from context inputs. Input variance is the
    same observed-signal proxy used by the existing restoration model.
    """
    if (
        linear_rgb.ndim != 3
        or linear_rgb.shape[0] != 3
        or linear_rgb.dtype != torch.float32
        or min(linear_rgb.shape[-2:]) < 4
        or any(n % 2 for n in linear_rgb.shape[-2:])
        or not torch.isfinite(linear_rgb).all()
    ):
        raise ValueError("Require finite even native scene-linear RGB FP32")
    device = linear_rgb.device
    wb = linear_rgb.new_tensor(recipe.wb)
    inverse = linear_rgb.new_tensor(recipe.camera_inverse)
    matrix = torch.linalg.inv(inverse)
    colors = torch.tensor(PATTERNS[recipe.pattern], device=device)
    clean, target = camera_pair(
        linear_rgb[None] * recipe.exposure, inverse[None], wb[None], reconstruct_highlights=True
    )
    generator = torch.Generator(device=device).manual_seed(recipe.noise_seed)
    observed = add_noise(
        mosaic(clean, colors),
        recipe.shot,
        recipe.read,
        black_level=recipe.black,
        generator=generator,
    )[0]
    return SceneObservation(
        observed,
        variance_map(observed, recipe.shot, recipe.read),
        colors,
        wb,
        matrix,
        target[0],
        clean[0],
        recipe,
    )


def scene_crop_boxes(native_hw, *, patch_size=256, count=4, seed):
    """Geometry-only deterministic crops; all origins preserve actual CFA phase."""
    h, w = native_hw
    if (
        type(patch_size) is not int
        or patch_size < 4
        or patch_size % 2
        or type(count) is not int
        or count < 1
        or min(h, w) < patch_size
    ):
        raise ValueError("Require positive crop count and fitting even native size")
    rng = random.Random(seed)
    return [
        (
            2 * rng.randrange((w - patch_size) // 2 + 1),
            2 * rng.randrange((h - patch_size) // 2 + 1),
            patch_size,
            patch_size,
        )
        for _ in range(count)
    ]
