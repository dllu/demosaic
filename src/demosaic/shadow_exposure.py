"""Optional shadow exposure of reviewed photographic material, without geometry changes."""

import hashlib
import json
import math
import random

import torch

from .precision import ieee_fp32

POLICY = "reviewed-shadow-green-v1"
MIN_GREEN = 2**-10
MAX_GREEN = 2**-5
MIN_GAIN = 2**-6


def reviewed_shadow_options(config):
    fraction = config.get("reviewed_shadow_fraction", 0.0)
    if (
        isinstance(fraction, bool)
        or not isinstance(fraction, (int, float))
        or not math.isfinite(fraction)
        or not 0 <= fraction <= 1
    ):
        raise ValueError("Reviewed shadow fraction must be finite and within [0,1]")
    policy = config.get("reviewed_shadow_policy", POLICY if fraction else None)
    if policy != (POLICY if fraction else None):
        raise ValueError("Unknown or inactive reviewed shadow exposure policy")
    return float(fraction), policy


def require_resume_reviewed_shadows(previous, current):
    if reviewed_shadow_options(previous) != reviewed_shadow_options(current):
        raise ValueError("Resume reviewed shadow exposure differs; initialize a new run")


def reviewed_shadow_levels(clean, *, fraction, seed, step, device):
    """Use source provenance and a local stream, leaving source/model RNG untouched."""
    reviewed_shadow_options({"reviewed_shadow_fraction": fraction})
    if not fraction:
        return None
    if step < 1 or type(seed) is not int:
        raise ValueError("Reviewed shadow exposure requires a seed and positive data step")
    sources = clean.get("source")
    if sources is None or len(sources) != len(clean["rgb"]):
        raise ValueError("Reviewed shadow exposure requires per-example source provenance")
    result = []
    for source in sources:
        source = json.loads(source)
        if source["kind"] != "photographic" or source.get("reviewed_roi_xywh") is None:
            result.append(0.0)
            continue
        if type(source.get("draw_index")) is not int or not source.get("source_id"):
            raise ValueError("Reviewed shadow source identity/index is missing")
        payload = f"{POLICY}:{seed}:{step}:{source['draw_index']}:{source['source_id']}".encode()
        value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")
        rng = random.Random(value)
        selected = rng.random() < fraction
        result.append(2 ** rng.uniform(-10, -5) if selected else 0.0)
    return torch.tensor(result, dtype=torch.float32, device=device)


def validate_shadow_levels(levels, rgb, *, training):
    if levels is None:
        return
    if (
        not training
        or not isinstance(levels, torch.Tensor)
        or levels.shape != (len(rgb),)
        or levels.device != rgb.device
        or not levels.is_floating_point()
        or not torch.isfinite(levels).all()
        or not ((levels == 0) | ((levels >= MIN_GREEN) & (levels <= MAX_GREEN))).all()
    ):
        raise ValueError(
            "Shadow green levels require training-only matching finite per-example values"
        )


def apply_shadow_exposure(rgb, inverse, wb, exposure, levels):
    """Keep legacy exposure for unselected samples; bound selected gain to1/64–1.

    The clean camera-green mean is measured before the ordinary random exposure.
    The requested mean may be unreachable at the bounded gain; retain the actual
    applied gain as metadata rather than claiming exact brightness targeting.
    """
    if levels is None or not (levels > 0).any():
        return exposure
    with torch.autocast(rgb.device.type, enabled=False), ieee_fp32():
        sensor_green = (
            torch.sum(rgb.float() * inverse[:, 1, :, None, None].float(), dim=1)
            / wb[:, 1, None, None].float()
        )
        mean = sensor_green.mean(dim=(-2, -1)).clamp_min(1e-12)
        selected_gain = (levels.float() / mean).clamp(MIN_GAIN, 1)
        selected = (levels > 0)[:, None, None, None]
        return torch.where(selected, selected_gain[:, None, None, None], exposure)
