"""Bounded-memory, phase-preserving, overlapping tiled inference."""

import time
from contextlib import nullcontext

import numpy as np
import torch
from torch.nn import functional as F

from .cfa import pack


def positions(length, tile, stride):
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile + 1, stride))
    if starts[-1] != length - tile:
        starts.append(length - tile)
    return starts


@torch.inference_mode()
def restore_tiled(
    model,
    raw,
    colors,
    *,
    shot,
    read,
    tile=256,
    overlap=64,
    batch_size=4,
    device="cuda",
    wb=None,
    matrix=None,
    amp=True,
):
    """Return CPU float32 RGB and timing. `tile`/`overlap` use sensor pixels.

    Only the raw image and float32 RGB accumulators persist on the CPU. Tile
    feature maps live on CUDA. No full-image CUDA copy, duplicated CPU/CUDA
    outputs or full-resolution feature tensors are retained on UMA systems.
    Even tile coordinates preserve the original CFA phase for every pattern.
    """
    if tile < 32 or tile % 16 or overlap < 0 or overlap % 2 or overlap >= tile:
        raise ValueError("Tile must be >=32 and divisible by 16; overlap must be even and <tile")
    if batch_size < 1 or min(shot, read) < 0:
        raise ValueError("Invalid batch size or noise coefficients")
    device = torch.device(device)
    if isinstance(raw, np.ndarray):
        raw = torch.from_numpy(np.ascontiguousarray(raw, dtype=np.float32))
    raw = raw.detach().cpu().float()
    if raw.ndim != 2 or not torch.isfinite(raw).all():
        raise ValueError("Raw must be a finite H×W normalized mosaic")
    original_h, original_w = raw.shape
    h = max(tile, original_h + original_h % 2)
    w = max(tile, original_w + original_w % 2)
    # Extend CFA values by whole 2×2 cells; replication of individual edge
    # pixels would assign a red measurement to a green phase on odd borders.
    raw = F.pad(raw[None, None], (0, original_w % 2, 0, original_h % 2), mode="replicate")
    if original_h % 2 and original_h > 1:
        raw[..., -1, :] = raw[..., original_h - 2, :]
    if original_w % 2 and original_w > 1:
        raw[..., :, -1] = raw[..., :, original_w - 2]
    packed = pack(raw)
    packed = F.pad(
        packed, (0, w // 2 - packed.shape[-1], 0, h // 2 - packed.shape[-2]), mode="replicate"
    )
    stride = tile - overlap
    coords = [(y, x) for y in positions(h, tile, stride) for x in positions(w, tile, stride)]
    # Positive weights avoid division by zero at the exterior image boundaries.
    edge = torch.hann_window(tile, periodic=False).clamp_min(0.02)
    weight = edge[:, None] * edge[None, :]
    accum = torch.zeros(3, h, w, dtype=torch.float32)
    norm = torch.zeros(h, w, dtype=torch.float32)
    colors = torch.as_tensor(colors, device=device, dtype=torch.long)
    model.eval()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    for start in range(0, len(coords), batch_size):
        current = coords[start : start + batch_size]
        tiles = torch.cat(
            [packed[..., y // 2 : (y + tile) // 2, x // 2 : (x + tile) // 2] for y, x in current]
        ).to(device)
        variance = tiles.clamp_min(0) * shot + read
        batch_colors = (
            colors[None].expand(len(current), -1)
            if colors.ndim == 1
            else colors.expand(len(current), -1)
        )
        batch_wb = (
            None
            if wb is None
            else torch.as_tensor(wb, device=device, dtype=torch.float32)
            .reshape(1, 3)
            .expand(len(current), -1)
        )
        batch_matrix = (
            None
            if matrix is None
            else torch.as_tensor(matrix, device=device, dtype=torch.float32)
            .reshape(1, 3, 3)
            .expand(len(current), -1, -1)
        )
        context = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if (amp and device.type == "cuda")
            else nullcontext()
        )
        with context:
            outputs = model(tiles, variance, batch_colors, batch_wb, batch_matrix)
        outputs = outputs.float().cpu()
        for output, (y, x) in zip(outputs, current):
            accum[:, y : y + tile, x : x + tile].add_(output * weight)
            norm[y : y + tile, x : x + tile].add_(weight)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    seconds = time.perf_counter() - started
    accum.div_(norm.clamp_min_(1e-12))
    return accum[:, :original_h, :original_w], {
        "seconds": seconds,
        "megapixels": original_h * original_w / 1e6,
        "tiles": len(coords),
        "tile": tile,
        "overlap": overlap,
        "batch_size": batch_size,
        "peak_cuda_gb": torch.cuda.max_memory_allocated(device) / 1e9
        if device.type == "cuda"
        else 0,
    }


def load_checkpoint(path, device="cpu"):
    from .model import JointDemosaic, ModelConfig

    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = JointDemosaic(ModelConfig(**checkpoint["model_config"]))
    weights = checkpoint.get("ema", checkpoint["model"])
    missing, unexpected = model.load_state_dict(weights, strict=False)
    if unexpected or any(not key.startswith("context.backbone.") for key in missing):
        raise ValueError(f"Incompatible checkpoint: missing={missing}, unexpected={unexpected}")
    return model.to(device), checkpoint
