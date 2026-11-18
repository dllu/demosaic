"""Explicit noisy-scene sessions for native crops and bounded tiled inference."""

import hashlib
import math
import time
from pathlib import Path

import numpy as np
import torch

from .cfa import PATTERNS, pack
from .experiments.artifacts import checked
from .inference import positions
from .precision import COMPUTE_DTYPES, amp_context
from .scene_restoration import EncodedScene, WholeSceneRestorer


def perturb_scene(scene, policy, *, seed=0):
    """Fixed feature interventions; neither targets nor new texture enter here."""
    if policy == "correct":
        return scene
    if policy not in ("masked", "spatial-shuffled"):
        raise ValueError("Choose correct, masked or spatial-shuffled context")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    fields = []
    for feature in scene.features:
        if policy == "masked":
            fields.append(torch.zeros_like(feature))
        else:
            order = torch.randperm(feature.shape[-2] * feature.shape[-1], generator=generator)
            fields.append(
                feature.flatten(2).index_select(2, order.to(feature.device)).view_as(feature)
            )
    return EncodedScene(tuple(fields), scene.grid)


def load_scene_checkpoint(path, *, device="cpu", weights="ema", expected_sha256=None):
    """Load an explicit scene endpoint, checking its parent and all101 tensors."""
    from .models import load_model

    if weights not in ("ema", "model"):
        raise ValueError("Choose EMA or raw model weights explicitly")
    with Path(path).open("rb") as stream:
        state = torch.load(stream, map_location="cpu", weights_only=True)
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Scene checkpoint digest differs")
    parent_binding = state["base_parent"]
    base, parent = load_model(
        "v120",
        checkpoint=checked(parent_binding),
        expected_sha256=parent_binding["sha256"],
        device=device,
    )
    if parent["loaded_sha256"] != parent_binding["sha256"]:
        raise ValueError("Scene parent identity differs")
    model = WholeSceneRestorer(base, mode=state["mode"], adapter_width=state["adapter_width"])
    model.to(device)
    model.load_restoration_state_dict(state[weights])
    state["loaded_sha256"] = digest
    state["loaded_weights"] = weights
    return model.eval(), state


class SceneInferenceSession:
    """One immutable CPU RAW snapshot, one encoded scene, many native queries.

    Inputs must be a normalized, even-sized sensor mosaic and explicit camera
    calibration. No clean/reference image is accepted. Context is built before
    extracting crops; crop origins preserve the scene's Bayer phase. This
    experimental API does not silently replace ordinary model inference.
    """

    @torch.inference_mode()
    def __init__(
        self,
        model,
        raw,
        colors,
        *,
        shot,
        read,
        wb,
        matrix,
        preview_long_side=1024,
        preview_exposure=1.0,
        precision="float32",
        context_policy="correct",
        context_seed=0,
    ):
        began = time.perf_counter()
        if (
            precision not in COMPUTE_DTYPES
            or context_policy not in ("correct", "masked", "spatial-shuffled")
            or not all(math.isfinite(n) and n >= 0 for n in (shot, read))
        ):
            raise ValueError("Require finite nonnegative noise and explicit inference policies")
        self.raw = torch.as_tensor(np.asarray(raw) if isinstance(raw, np.ndarray) else raw)
        self.raw = self.raw.detach().to(device="cpu", dtype=torch.float32, copy=True).contiguous()
        if (
            self.raw.ndim != 2
            or min(self.raw.shape) < 4
            or any(n % 2 for n in self.raw.shape)
            or not np.isfinite(self.raw.numpy()).all()
        ):
            raise ValueError("Require a finite even complete sensor mosaic")
        device = next(model.parameters()).device
        self.colors = torch.as_tensor(colors, device=device)
        self.wb = torch.as_tensor(wb, device=device, dtype=torch.float32)
        self.matrix = torch.as_tensor(matrix, device=device, dtype=torch.float32)
        if (
            self.colors.shape != (4,)
            or tuple(self.colors.tolist()) not in PATTERNS.values()
            or self.wb.shape != (3,)
            or self.matrix.shape != (3, 3)
            or not torch.isfinite(self.wb).all()
            or not torch.isfinite(self.matrix).all()
            or (self.wb <= 0).any()
        ):
            raise ValueError("Require actual Bayer phases, positive WB and finite camera matrix")
        self.colors = self.colors.long()
        self.model = model.eval()
        self.device, self.precision = device, precision
        self.shot, self.read = float(shot), float(read)
        if hasattr(model.base, "set_noise"):
            model.base.set_noise(shot, read)
        self.scene = None
        if model.mode != "none":
            # Packing and area reduction stay on CPU; only the bounded RGB
            # preview moves to the encoder device in encode_scene.
            with amp_context(device, dtype=precision):
                encoded = model.encode_scene(
                    pack(self.raw[None, None])[0],
                    self.colors.cpu(),
                    self.wb.cpu(),
                    self.matrix.cpu(),
                    long_side=preview_long_side,
                    exposure=preview_exposure,
                )
            self.scene = perturb_scene(encoded, context_policy, seed=context_seed)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        self.metadata = {
            "native_hw": list(self.raw.shape),
            "mode": model.mode,
            "context_policy": context_policy,
            "context_seed": context_seed,
            "preview_long_side": preview_long_side,
            "preview_exposure": preview_exposure,
            "compute_precision": precision if device.type == "cuda" else "float32",
            "scene_encoder_calls": int(self.scene is not None),
            "setup_scene_seconds": time.perf_counter() - began,
            "scope": "One noisy full-scene encoding; no clean/reference input or self ensemble. Native crop queries keep coordinates and actual CFA phase. Timing excludes checkpoint loading.",
        }

    @torch.inference_mode()
    def predict_boxes(self, boxes_xywh, *, batch_size=4):
        boxes = [tuple(b) for b in boxes_xywh]
        h, w = self.raw.shape
        if (
            type(batch_size) is not int
            or batch_size < 1
            or not boxes
            or len({b[2:] for b in boxes}) != 1
            or any(
                len(b) != 4
                or any(type(v) is not int for v in b)
                or min(b[:2]) < 0
                or min(b[2:]) < 32
                or b[0] % 2
                or b[1] % 2
                or b[2] % 16
                or b[3] % 16
                or b[0] + b[2] > w
                or b[1] + b[3] > h
                for b in boxes
            )
        ):
            raise ValueError(
                "Require equal-size in-scene native boxes, even origins and16-pixel axes"
            )
        outputs = []
        for start in range(0, len(boxes), batch_size):
            current = boxes[start : start + batch_size]
            mosaics = torch.stack([self.raw[y : y + bh, x : x + bw] for x, y, bw, bh in current])
            packed = pack(mosaics[:, None].to(self.device))
            variance = packed.clamp_min(0) * self.shot + self.read
            colors = self.colors[None].expand(len(current), -1)
            wb = self.wb[None].expand(len(current), -1)
            matrix = self.matrix[None].expand(len(current), -1, -1)
            with amp_context(self.device, dtype=self.precision):
                prediction = self.model(
                    packed, variance, colors, wb, matrix, scene=self.scene, boxes_xywh=current
                )
            outputs.append(prediction.float().cpu())
        return torch.cat(outputs)


@torch.inference_mode()
def restore_scene_tiled(session, *, tile=256, overlap=64, batch_size=4):
    """Blend native tiles from an existing session; encode no additional scenes."""
    began = time.perf_counter()
    h, w = session.raw.shape
    if (
        type(tile) is not int
        or tile < 32
        or tile % 16
        or min(h, w) < tile
        or type(overlap) is not int
        or overlap < 0
        or overlap % 2
        or overlap >= tile
        or type(batch_size) is not int
        or batch_size < 1
    ):
        raise ValueError("Require a fitting16-pixel tile, even overlap and positive batch size")
    coords = [
        (x, y, tile, tile)
        for y in positions(h, tile, tile - overlap)
        for x in positions(w, tile, tile - overlap)
    ]
    edge = torch.hann_window(tile, periodic=False).clamp_min(0.02)
    weight = edge[:, None] * edge[None, :]
    accum = torch.zeros(3, h, w, dtype=torch.float32)
    norm = torch.zeros(h, w, dtype=torch.float32)
    for start in range(0, len(coords), batch_size):
        current = coords[start : start + batch_size]
        outputs = session.predict_boxes(current, batch_size=batch_size)
        for value, (x, y, bw, bh) in zip(outputs, current, strict=True):
            accum[:, y : y + bh, x : x + bw].add_(value * weight)
            norm[y : y + bh, x : x + bw].add_(weight)
    accum.div_(norm.clamp_min_(1e-12))
    return accum, session.metadata | {
        "tile_seconds": time.perf_counter() - began,
        "tile": tile,
        "overlap": overlap,
        "batch_size": batch_size,
        "tiles": len(coords),
        "tile_grid_alignment": 2,
        "tile_stride": tile - overlap,
    }
