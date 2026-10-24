"""Exact Bayer rotations/reflections for optional eight-view inference."""

import torch

from .cfa import pack, unpack


def _transform(value, turns, reflected):
    value = torch.rot90(value, turns, (-2, -1))
    return (value.flip(-1) if reflected else value).contiguous()


@torch.inference_mode()
def predict_dihedral8(model, packed, variance, colors, wb=None, matrix=None):
    """Average eight predictions in camera RGB, with no resampling or fitting.

    Transform sensor samples, variances and CFA colors together. WB/matrix and
    the model's shot/read conditioning keep their original camera meanings.
    Only the current view and a float64 sum persist; return float32 before the
    caller's usual tile blending, clipping, display conversion or RGB16 export.
    """
    if getattr(model, "training", False):
        raise ValueError("Eight-view inference requires an evaluation-mode model")
    if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
        raise ValueError("Expected matching B×4×H×W packed measurements and variances")
    batch = packed.shape[0]
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    if colors.shape != (batch, 4):
        raise ValueError("Expected four CFA colors per image")
    raw, noise = unpack(packed), unpack(variance)
    color_tile = colors.reshape(batch, 1, 2, 2)
    total = None
    expected_shape = (batch, 3, raw.shape[-2], raw.shape[-1])
    for reflected in (False, True):
        for turns in range(4):
            prediction = model(
                pack(_transform(raw, turns, reflected)),
                pack(_transform(noise, turns, reflected)),
                _transform(color_tile, turns, reflected).reshape(batch, 4),
                wb,
                matrix,
            ).float()
            if reflected:
                prediction = prediction.flip(-1)
            prediction = torch.rot90(prediction, -turns, (-2, -1))
            if prediction.shape != expected_shape:
                raise ValueError("Restoration must return native B×3×2H×2W camera RGB")
            if total is None:
                total = prediction.double()
            else:
                total.add_(prediction)
    return total.div_(8).float()
