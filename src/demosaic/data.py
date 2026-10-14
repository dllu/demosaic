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


class CleanDataset(Dataset):
    def __init__(
        self, manifest: str | Path, split="train", patch_size=256, synthetic_fraction=0.2, seed=42
    ):
        self.manifest = Path(manifest)
        self.rows = [
            r
            for line in self.manifest.read_text().splitlines()
            if (r := json.loads(line))["split"] == split
        ]
        if not self.rows:
            raise ValueError(f"No {split} images in {manifest}")
        if patch_size % 16 or patch_size < 32:
            raise ValueError("Patch size must be >=32 and divisible by 16")
        self.split, self.size, self.seed = split, patch_size, seed
        self.synthetic_fraction = synthetic_fraction if split == "train" else 0

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        # Validation always uses a fixed crop; training uses worker-seeded RNG.
        rng = random.Random(self.seed + index)
        size = self.size
        if rng.random() < self.synthetic_fraction:
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
            crop_h = rng.randint(size, min(h, int(size * 1.4)))
            crop_w = rng.randint(size, min(w, int(size * 1.4)))
            y, x = rng.randrange(h - crop_h + 1), rng.randrange(w - crop_w + 1)
            rgb = (
                torch.from_numpy(
                    array[y : y + crop_h, x : x + crop_w].copy().astype(np.float32)
                ).permute(2, 0, 1)
                / 65535
            )
            rgb = F.interpolate(rgb[None], size=(size, size), mode="area")[0]
        if self.split == "train":
            rgb = torch.rot90(rgb, rng.randrange(4), (-2, -1))
            if rng.random() < 0.5:
                rgb = rgb.flip(-1)
            if rng.random() < 0.25:
                rgb = optical_blur(rgb, rng)
            if rng.random() < 0.2:
                rgb = homography(rgb, rng)
        return {"rgb": rgb.contiguous(), "index": index}


def homography(rgb, rng):
    """Small projective rotations/shears with an inward sampling margin."""
    size = rgb.shape[-1]
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


def optical_blur(rgb, rng):
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
    yy, xx = torch.meshgrid(torch.arange(-3, 4).float(), torch.arange(-3, 4).float(), indexing="ij")
    angle = rng.uniform(0, math.pi)
    u, v = xx * math.cos(angle) + yy * math.sin(angle), -xx * math.sin(angle) + yy * math.cos(angle)
    sx, sy = rng.uniform(0.35, 1.0), rng.uniform(0.35, 0.8)
    if kind in ("motion", "astigmatism"):
        sx, sy = rng.uniform(0.7, 1.5), 0.3
    kernel = torch.exp(-0.5 * ((u / sx).square() + (v / sy).square()))
    if kind == "coma":
        kernel += 0.35 * torch.exp(-0.5 * (((u - 1) / 0.9).square() + (v / 0.5).square()))
    kernel = (kernel / kernel.sum())[None, None].expand(3, 1, -1, -1)
    return F.conv2d(F.pad(rgb[None], (3, 3, 3, 3), mode="reflect"), kernel, groups=3)[0]


def camera_pair(exposed_rgb, inverse, wb, *, reconstruct_highlights=False):
    """Keep physical sensor clipping separate from the bounded reference white.

    Independent sensor-channel clipping can turn an overexposed neutral scene
    magenta after WB/color conversion. Reference-white clipping occurs in
    linear sRGB before camera transport; it does not alter the noisy input.
    """
    clean = torch.einsum("bij,bjhw->bihw", inverse, exposed_rgb) / wb[..., None, None]
    target = torch.einsum("bij,bjhw->bihw", inverse, exposed_rgb.clamp(0, 1)) / wb[..., None, None]
    return clean, target if reconstruct_highlights else clean.clamp(0, 1)


def degrade(
    rgb,
    *,
    training=True,
    generator=None,
    reconstruct_highlights=False,
    preserve_negative_read_noise=False,
):
    """Convert clean linear sRGB to randomized camera RGB, then mosaic/noise.

    The target is clipped linear camera RGB before white balance. A mild,
    invertible camera-to-sRGB matrix and WB gains are retained for display loss.
    """
    batch, _, _, _ = rgb.shape
    device = rgb.device
    if training:
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
    else:
        wb = rgb.new_tensor([2.0, 1.0, 1.5])[None].expand(batch, -1)
        inverse = torch.eye(3, device=device)[None].expand(batch, -1, -1)
        matrix = inverse
        exposure = 1
        colors = color_indices("RGGB", device=device)[None].expand(batch, -1)
        shot, read = rgb.new_full((batch, 1, 1, 1), 0.001), rgb.new_full((batch, 1, 1, 1), 1e-6)
    clean, target = camera_pair(
        rgb * exposure, inverse, wb, reconstruct_highlights=reconstruct_highlights
    )
    black = (
        torch.empty(batch, 1, 1, 1, device=device).uniform_(0.002, 0.06)
        if (training and preserve_negative_read_noise)
        else 0.0
    )
    observed = add_noise(mosaic(clean, colors), shot, read, black_level=black, generator=generator)
    return {
        "packed": observed,
        "variance": variance_map(observed, shot, read),
        "colors": colors,
        "target": target,
        "wb": wb,
        "matrix": matrix,
        "shot": shot,
        "read": read,
    }
