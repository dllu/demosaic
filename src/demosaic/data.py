"""Clean linear images, antialiased synthetic detail and optical augmentation."""

import json
import math
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch.nn import functional as F
from torch.utils.data import Dataset

from .cfa import PATTERNS, color_indices, mosaic
from .noise import add_noise, sample_coefficients, variance_map
from .precision import ieee_fp32
from .textures import weak_texture


def synthetic(size: int, rng: random.Random) -> torch.Tensor:
    """Fourfold supersampled lines/shapes, chirps and continuous color ramps."""
    ss = 4
    high = size * ss
    image = Image.new("RGB", (high, high), tuple(rng.randrange(256) for _ in range(3)))
    draw = ImageDraw.Draw(image)
    for _ in range(rng.randint(15, 60)):
        xy = [rng.randrange(high) for _ in range(4)]
        color = tuple(rng.randrange(256) for _ in range(3))
        if rng.random() < 0.6:
            draw.line(xy, fill=color, width=rng.randint(1, 5 * ss))
        else:
            x0, x1 = sorted(xy[::2])
            y0, y1 = sorted(xy[1::2])
            draw.ellipse((x0, y0, x1, y1), fill=color)
    # Synthetic colors are scene-linear values, not encoded photographic sRGB.
    rgb = torch.from_numpy(np.asarray(image).copy()).permute(2, 0, 1).float() / 255
    rgb = F.avg_pool2d(rgb, ss)
    if rng.random() < 0.5:
        yy, xx = torch.meshgrid(
            torch.linspace(0, 1, size), torch.linspace(0, 1, size), indexing="ij"
        )
        phase = (
            2
            * math.pi
            * (rng.uniform(5, 45) * xx + rng.uniform(5, 45) * yy + rng.uniform(0, 50) * xx.square())
        )
        wave = (phase.sin() + 1) / 2
        tint = torch.tensor([rng.random() for _ in range(3)])[:, None, None]
        rgb = 0.4 * rgb + 0.6 * wave * tint
    return rgb


def validate_flat_chroma_stops(value) -> float:
    """Bound the optional smooth-field log tint span; zero keeps legacy draws."""
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 16:
        raise ValueError("Flat chroma stops must be finite and within [0,16]")
    return value


def smooth_scene(size: int, rng: random.Random, *, chroma_stops=0.0) -> torch.Tensor:
    """Continuous-precision flat fields/ramps, including deep shadows.

    These deliberately lack texture: a restoration model should not retain
    sensor noise or introduce a color offset into an otherwise uniform scene.
    They complement detailed shapes and real photos rather than replace them.
    Positive chroma_stops remaps the existing colored tint draws to a log
    palette, preserving their mean before clipping. Neutral fields and RNG
    consumption stay unchanged. Zero preserves the original tensors exactly.
    """
    chroma_stops = validate_flat_chroma_stops(chroma_stops)
    intensity = 2 ** rng.uniform(-13, -1)
    neutral = rng.random() < 0.5
    tint = [1.0] * 3 if neutral else [rng.uniform(0.3, 1.5) for _ in range(3)]
    if chroma_stops and not neutral:
        logarithmic = [2 ** (chroma_stops * ((t - 0.3) / 1.2 - 1)) for t in tint]
        scale = sum(tint) / sum(logarithmic)
        tint = [t * scale for t in logarithmic]
    rgb = torch.tensor(tint, dtype=torch.float32)[:, None, None] * intensity
    rgb = rgb.expand(-1, size, size).clone()
    if rng.random() < 0.5:
        y, x = torch.meshgrid(
            torch.linspace(-1, 1, size), torch.linspace(-1, 1, size), indexing="ij"
        )
        rgb *= 1 + rng.uniform(-0.4, 0.4) * x + rng.uniform(-0.4, 0.4) * y
    return rgb.clamp(0, 1)


class CleanDataset(Dataset):
    def __init__(
        self,
        manifest: str | Path,
        split="train",
        patch_size=256,
        synthetic_fraction=0.2,
        seed=42,
        records=None,
        native_crop=False,
        flat_fraction=0.0,
        augmentation_downsample=1,
        weak_texture_fraction=0.0,
        flat_chroma_stops=0.0,
    ):
        self.flat_chroma_stops = validate_flat_chroma_stops(flat_chroma_stops)
        self.manifest = Path(manifest)
        if records is None:
            records = [json.loads(line) for line in self.manifest.read_text().splitlines()]
        self.rows = [row for row in records if row["split"] == split]
        if not self.rows:
            raise ValueError(f"No {split} images in {manifest}")
        if patch_size % 16 or patch_size < 32:
            raise ValueError("Patch size must be >=32 and divisible by 16")
        self.split, self.size, self.seed = split, patch_size, seed
        if not 0 <= synthetic_fraction <= 1 or not 0 <= flat_fraction <= 1 - synthetic_fraction:
            raise ValueError("Procedural sample fractions must be nonnegative and sum to <=1")
        self.synthetic_fraction = synthetic_fraction if split == "train" else 0
        self.flat_fraction = flat_fraction if split == "train" else 0
        if not 0 <= weak_texture_fraction <= synthetic_fraction:
            raise ValueError("Weak texture fraction must be within the existing synthetic fraction")
        self.weak_texture_fraction = weak_texture_fraction if split == "train" else 0
        if self.weak_texture_fraction and augmentation_downsample != 2:
            raise ValueError("Weak texture training requires augmentation before final downsample2")
        self.native_crop = native_crop
        if augmentation_downsample not in (1, 2) or (
            augmentation_downsample != 1 and split != "train"
        ):
            raise ValueError("Augmentation downsample must be 1, or 2 for training")
        if augmentation_downsample == 2 and any(row.get("bin_factor") != 4 for row in self.rows):
            raise ValueError(
                "Pre-downsample augmentation requires linear 4x-binned training caches"
            )
        self.augmentation_downsample = augmentation_downsample

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        # Validation always uses a fixed crop; training uses worker-seeded RNG.
        rng = random.Random(self.seed + index)
        size = self.size * self.augmentation_downsample
        draw = rng.random()
        if draw < self.flat_fraction:
            rgb = smooth_scene(size, rng, chroma_stops=self.flat_chroma_stops)
        elif draw < self.flat_fraction + self.synthetic_fraction:
            if draw < self.flat_fraction + self.weak_texture_fraction:
                rgb, _ = weak_texture(size, rng, pixel_scale=self.augmentation_downsample)
            else:
                rgb = synthetic(size, rng)
        else:
            record = self.rows[
                rng.randrange(len(self.rows)) if self.split == "train" else index % len(self.rows)
            ]
            array = np.load(self.manifest.parent / record["cache"], mmap_mode="r")
            h, w = array.shape[:2]
            if min(h, w) < size:
                raise ValueError(f"Cached image {record['id']} smaller than patch")
            # Only shrink cached images, never stretch away the binning benefit.
            crop_h = size if self.native_crop else rng.randint(size, min(h, int(size * 1.4)))
            crop_w = size if self.native_crop else rng.randint(size, min(w, int(size * 1.4)))
            y, x = rng.randrange(h - crop_h + 1), rng.randrange(w - crop_w + 1)
            rgb = (
                torch.from_numpy(
                    array[y : y + crop_h, x : x + crop_w].copy().astype(np.float32)
                ).permute(2, 0, 1)
                / 65535
            )
            if self.augmentation_downsample == 1:
                rgb = F.interpolate(rgb[None], size=(size, size), mode="area")[0]
        if self.augmentation_downsample == 2:
            rgb = augment_before_downsample(rgb, self.size, rng)
        elif self.split == "train":
            rgb = torch.rot90(rgb, rng.randrange(4), (-2, -1))
            if rng.random() < 0.5:
                rgb = rgb.flip(-1)
            if rng.random() < 0.25:
                rgb = optical_blur(rgb, rng)
            if rng.random() < 0.2:
                rgb = homography(rgb, rng)
        return {"rgb": rgb.contiguous(), "index": index}


def augment_before_downsample(rgb, size, rng):
    """Compose geometry at 2x target resolution, then average linear 2x2 cells.

    Photographs start as 4x-binned linear uint16 caches. D4 transforms are exact;
    projective sampling also handles the anisotropic crop-to-output scaling in
    one interpolation. Optical PSFs use final-pixel units at this higher scale.
    No geometric interpolation follows the final reduction.
    """
    rgb = torch.rot90(rgb, rng.randrange(4), (-2, -1))
    if rng.random() < 0.5:
        rgb = rgb.flip(-1)
    if rng.random() < 0.2:
        rgb = homography(rgb, rng, output_size=2 * size)
    elif rgb.shape[-2:] != (2 * size, 2 * size):
        rgb = F.interpolate(rgb[None], size=(2 * size, 2 * size), mode="area")[0]
    if rng.random() < 0.25:
        rgb = optical_blur(rgb, rng, pixel_scale=2)
    return F.avg_pool2d(rgb, 2)


def homography(rgb, rng, *, output_size=None):
    """Small projective rotations/shears with an inward sampling margin."""
    size = rgb.shape[-1] if output_size is None else output_size
    yy, xx = torch.meshgrid(
        torch.linspace(-0.85, 0.85, size), torch.linspace(-0.85, 0.85, size), indexing="ij"
    )
    angle = rng.uniform(-0.12, 0.12)
    denom = 1 + rng.uniform(-0.03, 0.03) * xx + rng.uniform(-0.03, 0.03) * yy
    x = (math.cos(angle) * xx - math.sin(angle) * yy + rng.uniform(-0.03, 0.03) * yy) / denom
    y = (math.sin(angle) * xx + math.cos(angle) * yy) / denom
    return F.grid_sample(
        rgb[None],
        torch.stack((x, y), -1)[None],
        mode="bilinear",
        padding_mode="reflection",
        align_corners=True,
    )[0]


def optical_blur(rgb, rng, *, pixel_scale=1):
    """Small Gaussian, motion, coma/astigmatism PSFs or radial integration."""
    kind = rng.choice(("gaussian", "motion", "coma", "astigmatism", "radial"))
    if kind == "radial":
        result = rgb.clone()
        for scale in (1.002, 1.005, 1.008):
            theta = torch.tensor([[[scale, 0, 0], [0, scale, 0]]], dtype=rgb.dtype)
            grid = F.affine_grid(theta, (1, *rgb.shape), align_corners=False)
            result += F.grid_sample(
                rgb[None], grid, padding_mode="reflection", align_corners=False
            )[0]
        return result / 4
    radius = 3 * pixel_scale
    coordinates = torch.arange(-radius, radius + 1).float() / pixel_scale
    yy, xx = torch.meshgrid(coordinates, coordinates, indexing="ij")
    angle = rng.uniform(0, math.pi)
    u, v = xx * math.cos(angle) + yy * math.sin(angle), -xx * math.sin(angle) + yy * math.cos(angle)
    sx, sy = rng.uniform(0.35, 1.0), rng.uniform(0.35, 0.8)
    if kind in ("motion", "astigmatism"):
        sx, sy = rng.uniform(0.7, 1.5), 0.3
    kernel = torch.exp(-0.5 * ((u / sx).square() + (v / sy).square()))
    if kind == "coma":
        kernel += 0.35 * torch.exp(-0.5 * (((u - 1) / 0.9).square() + (v / 0.5).square()))
    kernel = (kernel / kernel.sum())[None, None].expand(3, 1, -1, -1)
    return F.conv2d(F.pad(rgb[None], (radius,) * 4, mode="reflect"), kernel, groups=3)[0]


def camera_pair(exposed_rgb, inverse, wb, *, reconstruct_highlights=False, physical_fp32=True):
    """Keep physical sensor clipping separate from the bounded reference white.

    Independent sensor-channel clipping can turn an overexposed neutral scene
    magenta after WB/color conversion. Reference-white clipping occurs in
    linear sRGB before camera transport; it does not alter the noisy input.
    """
    if physical_fp32:
        with torch.autocast(device_type=exposed_rgb.device.type, enabled=False), ieee_fp32():
            return _camera_pair(
                exposed_rgb.float(), inverse.float(), wb.float(), reconstruct_highlights
            )
    return _camera_pair(exposed_rgb, inverse, wb, reconstruct_highlights)


def _camera_pair(exposed_rgb, inverse, wb, reconstruct_highlights):
    clean = torch.einsum("bij,bjhw->bihw", inverse, exposed_rgb) / wb[..., None, None]
    target = torch.einsum("bij,bjhw->bihw", inverse, exposed_rgb.clamp(0, 1)) / wb[..., None, None]
    return clean, target if reconstruct_highlights else clean.clamp(0, 1)


def sample_broad_cameras(batch, device):
    """Neutral-preserving camera primaries and warm/cool illuminants.

    The original near-identity transforms and red WB >=1.3 miss ordinary real
    cameras. Broader nonnegative spectral mixing covers much stronger primary
    overlap without sampling unstable inverses. These are augmentations, not
    calibrated camera profiles. No evaluation-camera matrix is copied here.
    """
    wb = torch.ones(batch, 3, device=device)
    wb[:, (0, 2)] = (
        torch.empty(batch, 2, device=device).uniform_(math.log2(0.65), math.log2(3.6)).exp2()
    )
    limits = wb.new_tensor([[0, 0.55, 0.20], [0.18, 0, 0.35], [0.12, 0.40, 0]])
    broad = torch.rand(batch, 3, 3, device=device) * limits
    # Retain near-identity coverage in the same recipe.
    mild = torch.rand_like(broad) * 0.12
    mild.diagonal(dim1=-2, dim2=-1).zero_()
    off = torch.where(torch.rand(batch, 1, 1, device=device) < 0.25, mild, broad)
    off *= 0.65 / off.sum(-1, keepdim=True).clamp_min(0.65)
    eye = torch.eye(3, device=device)[None]
    inverse = eye * (1 - off.sum(-1, keepdim=True)) + off
    off *= torch.where(torch.linalg.det(inverse)[:, None, None] < 0.08, 0.5, 1.0)
    inverse = eye * (1 - off.sum(-1, keepdim=True)) + off
    return wb, inverse


def degrade(
    rgb,
    *,
    training=True,
    generator=None,
    reconstruct_highlights=False,
    preserve_negative_read_noise=False,
    physical_fp32=True,
    noise_free_fraction=0.0,
    broad_camera=False,
    retain_sensor_target=False,
):
    """Convert clean linear sRGB to randomized camera RGB, then mosaic/noise.

    The target is clipped linear camera RGB before white balance. A mild,
    invertible camera-to-sRGB matrix and WB gains are retained for display loss.
    """
    batch, _, _, _ = rgb.shape
    device = rgb.device
    if not 0 <= noise_free_fraction <= 1:
        raise ValueError("Noise-free fraction must be in [0,1]")
    if type(retain_sensor_target) is not bool:
        raise ValueError("Sensor target retention must be a boolean")
    if training:
        if broad_camera:
            wb, inverse = sample_broad_cameras(batch, device)
        else:
            wb = torch.ones(batch, 3, device=device)
            wb[:, 0] = torch.empty(batch, device=device).uniform_(1.3, 2.6)
            wb[:, 2] = torch.empty(batch, device=device).uniform_(1.1, 2.4)
            off = torch.rand(batch, 3, 3, device=device) * 0.12
            off.diagonal(dim1=-2, dim2=-1).zero_()
            inverse = torch.eye(3, device=device)[None] * (1 - off.sum(-1, keepdim=True)) + off
        matrix = torch.linalg.inv(inverse)
        exposure = 2 ** torch.empty(batch, 1, 1, 1, device=device).uniform_(-3, 2)
        colors = torch.stack([color_indices(p, device=device) for p in PATTERNS])[
            torch.randint(4, (batch,), device=device)
        ]
        shot, read = sample_coefficients(batch, device)
        if noise_free_fraction:
            keep = torch.rand_like(shot) >= noise_free_fraction
            shot, read = shot * keep, read * keep
    else:
        wb = rgb.new_tensor([2.0, 1.0, 1.5])[None].expand(batch, -1)
        inverse = torch.eye(3, device=device)[None].expand(batch, -1, -1)
        matrix = inverse
        exposure = 1
        colors = color_indices("RGGB", device=device)[None].expand(batch, -1)
        shot, read = rgb.new_full((batch, 1, 1, 1), 0.001), rgb.new_full((batch, 1, 1, 1), 1e-6)
    clean, target = camera_pair(
        rgb * exposure,
        inverse,
        wb,
        reconstruct_highlights=reconstruct_highlights,
        physical_fp32=physical_fp32,
    )
    black = (
        torch.empty(batch, 1, 1, 1, device=device).uniform_(0.002, 0.06)
        if (training and preserve_negative_read_noise)
        else 0.0
    )
    observed = add_noise(mosaic(clean, colors), shot, read, black_level=black, generator=generator)
    result = {
        "packed": observed,
        "variance": variance_map(observed, shot, read),
        "colors": colors,
        "target": target,
        "wb": wb,
        "matrix": matrix,
        "shot": shot,
        "read": read,
    }
    if retain_sensor_target:
        result["sensor_target"] = clean
    return result
