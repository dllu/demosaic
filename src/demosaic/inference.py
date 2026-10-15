"""Bounded-memory, phase-preserving, overlapping tiled inference."""

import hashlib
import time
from pathlib import Path

import numpy as np
import torch

from .cfa import pack
from .precision import COMPUTE_DTYPES, amp_context


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
    precision="bfloat16",
    refinement_precision=None,
):
    """Return CPU float32 RGB and timing. `tile`/`overlap` use sensor pixels.

    Only the raw image and float32 RGB accumulators persist on the CPU. Tile
    feature maps live on CUDA. No full-image CUDA copy, duplicated CPU/CUDA
    outputs or full-resolution feature tensors are retained on UMA systems.
    Even tile coordinates preserve the original CFA phase for every pattern.
    """
    full_started = time.perf_counter()
    if tile < 32 or tile % 16 or overlap < 0 or overlap % 2 or overlap >= tile:
        raise ValueError("Tile must be >=32 and divisible by 16; overlap must be even and <tile")
    if batch_size < 1 or min(shot, read) < 0:
        raise ValueError("Invalid batch size or noise coefficients")
    if precision not in COMPUTE_DTYPES:
        raise ValueError(f"Unknown compute precision {precision!r}")
    if refinement_precision is not None:
        model.set_refinement_precision(refinement_precision)
    device = torch.device(device)
    if isinstance(raw, np.ndarray):
        raw = torch.from_numpy(np.ascontiguousarray(raw, dtype=np.float32))
    raw = raw.detach().cpu().float()
    # NumPy checks the CPU view in one SIMD pass; torch.isfinite materializes
    # several full-image intermediates on this host before the reduction.
    if raw.ndim != 2 or min(raw.shape) < 2 or not np.isfinite(raw.numpy()).all():
        raise ValueError("Raw must be a finite H×W normalized mosaic")
    original_h, original_w = raw.shape
    h = max(tile, original_h + original_h % 2)
    w = max(tile, original_w + original_w % 2)
    # Extend CFA values by whole 2×2 cells; replication of individual edge
    # pixels would assign a red measurement to a green phase on odd borders.
    if (h, w) != (original_h, original_w):
        rows, cols = torch.arange(h), torch.arange(w)
        rows = torch.where(rows < original_h, rows, 2 * ((original_h - 2) // 2) + rows % 2)
        cols = torch.where(cols < original_w, cols, 2 * ((original_w - 2) // 2) + cols % 2)
        raw = raw.index_select(0, rows).index_select(1, cols)
    stride = tile - overlap
    coords = [(y, x) for y in positions(h, tile, stride) for x in positions(w, tile, stride)]
    # Positive weights avoid division by zero at the exterior image boundaries.
    edge = torch.hann_window(tile, periodic=False).clamp_min(0.02)
    weight = edge[:, None] * edge[None, :]
    accum = torch.zeros(3, h, w, dtype=torch.float32)
    norm = torch.zeros(h, w, dtype=torch.float32)
    colors = torch.as_tensor(colors, device=device, dtype=torch.long)
    model.eval()
    if hasattr(model, "set_noise"):
        model.set_noise(shot, read)
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
        torch.cuda.synchronize(device)
        torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    compute_seconds, blend_seconds = 0.0, 0.0
    for start in range(0, len(coords), batch_size):
        compute_started = time.perf_counter()
        current = coords[start : start + batch_size]
        # Pack only each active batch on the device, avoiding a second 100 MP
        # host allocation and a full-image pixel-unshuffle pass.
        tiles = pack(
            torch.stack([raw[y : y + tile, x : x + tile] for y, x in current])[:, None].to(device)
        )
        if device.type == "cuda":
            tiles = tiles.contiguous(memory_format=torch.channels_last)
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
        with amp_context(device, amp, dtype=precision):
            outputs = model(tiles, variance, batch_colors, batch_wb, batch_matrix)
        outputs = outputs.float().cpu()
        compute_seconds += time.perf_counter() - compute_started
        blend_started = time.perf_counter()
        for output, (y, x) in zip(outputs, current):
            accum[:, y : y + tile, x : x + tile].add_(output * weight)
            norm[y : y + tile, x : x + tile].add_(weight)
        blend_seconds += time.perf_counter() - blend_started
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    accum.div_(norm.clamp_min_(1e-12))
    tile_seconds = time.perf_counter() - started
    return accum[:, :original_h, :original_w], {
        "seconds": time.perf_counter() - full_started,
        "tile_seconds": tile_seconds,
        "compute_transfer_seconds": compute_seconds,
        "blend_seconds": blend_seconds,
        "megapixels": original_h * original_w / 1e6,
        "tiles": len(coords),
        "tile": tile,
        "overlap": overlap,
        "batch_size": batch_size,
        "compute_precision": precision if amp and device.type == "cuda" else "float32",
        "refinement_compute_precision": getattr(model, "refinement_precision", "float32")
        if device.type == "cuda"
        else "float32",
        "memory_format": "channels_last" if device.type == "cuda" else "contiguous",
        "peak_cuda_gb": torch.cuda.max_memory_allocated(device) / 1e9
        if device.type == "cuda"
        else 0,
    }


def load_checkpoint(path, device="cpu", *, refinement_precision="float32"):
    from .model import JointDemosaic, ModelConfig

    # Hash the same opened inode that was loaded, even if a live trainer
    # atomically replaces its last.pt pathname while the model is loading.
    with Path(path).open("rb") as handle:
        checkpoint = torch.load(handle, map_location="cpu", weights_only=True)
        handle.seek(0)
        checkpoint["loaded_sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
    model = JointDemosaic(ModelConfig.from_checkpoint(checkpoint["model_config"]))
    weights = checkpoint.get("ema", checkpoint["model"])
    missing, unexpected = model.load_state_dict(weights, strict=False)
    if unexpected or any(not key.startswith("context.backbone.") for key in missing):
        raise ValueError(f"Incompatible checkpoint: missing={missing}, unexpected={unexpected}")
    model.set_refinement_precision(refinement_precision)
    return model.to(device), checkpoint
