"""Build scene affinity priors from the donor search's fixed screening sites."""

import numpy as np
import torch
from torch.nn import functional as F

from .cfa import color_indices
from .color import render
from .scene_context import SceneGrid, sample_scene_features
from .search_donor_geometry import screening_mask


def screening_preview(raw, pattern, wb, matrix, *, long_side=1536, exposure=4.0):
    """Compress a Bayer field to one measurement per parity and absolute 4×4 cell."""
    raw = np.asarray(raw)
    if raw.ndim != 2 or min(raw.shape) < 4 or long_side < 1:
        raise ValueError("Require a native Bayer field and a positive preview size")
    h, w = (n // 4 * 4 for n in raw.shape)
    colors = color_indices(pattern).numpy()
    phases = np.empty((4, h // 4, w // 4), np.float32)
    for y in range(0, h, 128):
        stop = min(y + 128, h)
        box = (0, y, w, stop - y)
        scope = screening_mask(box)
        values = np.where(scope, raw[y:stop, :w], 0)
        for phase in range(4):
            dy, dx = divmod(phase, 2)
            cells = values[dy::2, dx::2].reshape((stop - y) // 4, 2, w // 4, 2)
            phases[phase, y // 4 : stop // 4, :] = cells.sum((1, 3))
    rgb = torch.from_numpy(np.stack([phases[colors == c].mean(0) for c in range(3)]))[None]
    if not torch.isfinite(rgb).all():
        raise ValueError("Require finite RAW samples at the screening sites")
    factor = min(0.25, long_side / max(h, w))
    size = tuple(max(1, round(n * factor)) for n in (h, w))
    rgb = F.interpolate(rgb, size=size, mode="area")
    preview = render(
        rgb * exposure,
        torch.as_tensor(wb, dtype=torch.float32).reshape(1, 3),
        torch.as_tensor(matrix, dtype=torch.float32).reshape(1, 3, 3),
    )
    return preview, SceneGrid((h, w), size, tuple(n + -n % 32 for n in size))


def retain_near_preview(preview, grid, box):
    """Preserve the donor/query window at its scene coordinates."""
    x, y, w, h = box
    nh, nw = grid.native_hw
    ph, pw = grid.preview_hw
    x0, x1 = x * pw // nw, ((x + w) * pw + nw - 1) // nw
    y0, y1 = y * ph // nh, ((y + h) * ph + nh - 1) // nh
    near = preview[..., y0:y1, x0:x1]
    neutral = near.mean(dim=(-2, -1), keepdim=True)
    result = neutral.expand_as(preview).clone()
    result[..., y0:y1, x0:x1] = near
    return result


def donor_affinities(features, grid, boxes, query):
    """Compare candidate appearances with the center of the query on spatial maps."""
    x, y, w, h = query
    center = (x + w / 4, y + h / 4, w / 2, h / 2)
    distances = []
    for f, stride in zip(features[:3], (4, 8, 16), strict=True):
        regions = sample_scene_features(f, grid, stride, [center, *boxes], (5, 5))
        vectors = F.normalize(regions.flatten(2).float(), dim=1)
        anchor = F.normalize(vectors[0].mean(dim=1), dim=0)
        similarity = torch.einsum("d,ndp->np", anchor, vectors[1:])
        distances.append(1 - similarity.quantile(0.25, dim=1).clamp(-1, 1))
    distance = 0.40 * distances[0] + 0.35 * distances[1] + 0.25 * distances[2]
    return torch.exp(-6 * distance).cpu().numpy()
