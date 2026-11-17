"""Whole-observation previews and coordinate-aligned scene feature queries.

These utilities do not replace V120's local encoder or generate native detail.
A scene encoder/adapter needs matched training before a quality claim. Withheld
evidence requires a genuinely A-only packed scene, including its normalization.
"""

from dataclasses import dataclass

import torch
from torch.nn import functional as F

from .color import render


@dataclass(frozen=True)
class SceneGrid:
    native_hw: tuple[int, int]
    preview_hw: tuple[int, int]
    padded_hw: tuple[int, int]

    def __post_init__(self):
        for pair in (self.native_hw, self.preview_hw, self.padded_hw):
            if len(pair) != 2 or any(type(n) is not int or n < 1 for n in pair):
                raise ValueError("Require positive integer scene/preview/padded dimensions")
        if any(p < n for p, n in zip(self.padded_hw, self.preview_hw, strict=True)):
            raise ValueError("Padding cannot shrink the scene preview")


def scene_preview(packed, colors, wb, matrix, *, long_side=1024, exposure=1.0):
    """Area-average each actual CFA phase, then render with one scene exposure.

    Accept only one complete packed observation; no clean image or crop-specific
    normalization enters this function. Average the two green phases. The
    preview keeps aspect ratio (nearest integer height/width), never enlarges
    a packed plane, and retains native scene dimensions separately from padding.
    For A→B tests pass A-only imputed packed data, never the full observation.
    """
    if (
        packed.ndim != 3
        or packed.shape[0] != 4
        or not packed.is_floating_point()
        or not torch.isfinite(packed).all()
        or type(long_side) is not int
        or long_side < 1
        or not isinstance(exposure, (int, float))
        or not 0 < exposure < float("inf")
    ):
        raise ValueError(
            "Require finite four-plane scene RAW and positive preview geometry/exposure"
        )
    colors = torch.as_tensor(colors, device=packed.device)
    allowed = torch.tensor(
        [[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]], device=packed.device
    )
    if colors.shape != (4,) or not (allowed == colors).all(dim=1).any():
        raise ValueError("Require one of the four actual Bayer layouts")
    h, w = packed.shape[-2:]
    ratio = min(1.0, long_side / max(h, w))
    size = (max(1, round(h * ratio)), max(1, round(w * ratio)))
    phases = F.interpolate(packed[None].float(), size=size, mode="area")[0]
    rgb = torch.stack([phases[colors == c].mean(dim=0) for c in range(3)])[None]
    wb = torch.as_tensor(wb, device=packed.device, dtype=torch.float32).reshape(1, 3)
    matrix = torch.as_tensor(matrix, device=packed.device, dtype=torch.float32).reshape(1, 3, 3)
    if not torch.isfinite(wb).all() or not torch.isfinite(matrix).all() or (wb <= 0).any():
        raise ValueError("Require finite scene calibration and positive white balance")
    preview = render(rgb * exposure, wb, matrix)
    grid = SceneGrid((2 * h, 2 * w), size, tuple(n + -n % 32 for n in size))
    return preview, grid


def sample_scene_features(features, grid, stride, boxes_xywh, output_hw):
    """Query a padded scene feature map at native crop pixel-center coordinates.

    Padding is part of the feature-map coordinate system, not squeezed into the
    photograph. Several tile queries share one encoded scene. No donor pixels
    or native RGB texture is synthesized here.
    """
    if (
        features.ndim != 4
        or features.shape[0] != 1
        or not features.is_floating_point()
        or type(stride) is not int
        or stride < 1
        or any(n % stride for n in grid.padded_hw)
        or tuple(features.shape[-2:]) != tuple(n // stride for n in grid.padded_hw)
        or len(output_hw) != 2
        or any(type(n) is not int or n < 1 for n in output_hw)
    ):
        raise ValueError("Require one matching padded scene feature map and query geometry")
    # Native coordinates can exceed10k; BF16 query arithmetic would move a
    # feature by many pixels. Keep coordinates/sampling at least FP32.
    query_dtype = torch.float64 if features.dtype == torch.float64 else torch.float32
    boxes = torch.as_tensor(boxes_xywh, device=features.device, dtype=query_dtype)
    nh, nw = grid.native_hw
    if (
        boxes.ndim != 2
        or boxes.shape[1] != 4
        or len(boxes) < 1
        or not torch.isfinite(boxes).all()
        or (boxes[:, :2] < 0).any()
        or (boxes[:, 2:] <= 0).any()
        or (boxes[:, 0] + boxes[:, 2] > nw).any()
        or (boxes[:, 1] + boxes[:, 3] > nh).any()
    ):
        raise ValueError("Require finite positive native tile boxes inside the scene")
    oh, ow = output_hw
    qy = (torch.arange(oh, device=features.device, dtype=query_dtype) + 0.5) / oh
    qx = (torch.arange(ow, device=features.device, dtype=query_dtype) + 0.5) / ow
    x = boxes[:, 0, None] + boxes[:, 2, None] * qx
    y = boxes[:, 1, None] + boxes[:, 3, None] * qy
    x = 2 * x / nw * grid.preview_hw[1] / grid.padded_hw[1] - 1
    y = 2 * y / nh * grid.preview_hw[0] / grid.padded_hw[0] - 1
    queries = torch.stack((x[:, None].expand(-1, oh, -1), y[:, :, None].expand(-1, -1, ow)), dim=-1)
    return F.grid_sample(
        features.to(query_dtype).expand(len(boxes), -1, -1, -1),
        queries,
        mode="bilinear",
        padding_mode="border",
        align_corners=False,
    ).to(features.dtype)
