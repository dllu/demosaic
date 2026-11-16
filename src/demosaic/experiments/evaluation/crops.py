"""Native-pixel triplets with one explicit display transform and provenance."""

import io
import math
from pathlib import Path

import numpy as np
from PIL import Image

from ..artifacts import reference, write_json
from .native import publish_exclusive


def display_pixels(value, arrays, roi, exposure):
    """Match the independent FP64 display used by the existing native reviews."""
    value = np.asarray(value)
    if value.ndim != 4 or value.shape[:2] != (1, 3) or not np.isfinite(value).all():
        raise ValueError("Expected finite 1x3xHxW RGB")
    x, y, width, height = roi
    if any(type(n) is not int for n in roi) or min(x, y) < 0 or min(width, height) < 1:
        raise ValueError("Expected an integer positive crop within the image")
    if x + width > value.shape[-1] or y + height > value.shape[-2]:
        raise ValueError("Crop lies outside the image")
    if not math.isfinite(exposure) or exposure <= 0:
        raise ValueError("Display exposure must be positive and finite")
    rgb = np.einsum(
        "bij,bjhw->bihw",
        arrays["matrix"].astype(np.float64),
        value.astype(np.float64) * exposure * arrays["wb"].astype(np.float64)[..., None, None],
    ).clip(0, 1)
    rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
    return np.rint(rgb[0, :, y : y + height, x : x + width].transpose(1, 2, 0) * 255).astype(
        np.uint8
    )


def write_triplet(
    path,
    noisy,
    restored,
    target,
    arrays,
    *,
    roi,
    exposure,
    source,
    checkpoint,
    noise,
    reference_kind,
):
    if reference_kind not in ("exact-GT", "independent-ISO100-reference", "approximate-reference"):
        raise ValueError("Declare the reference type explicitly")
    if not (noisy.shape == restored.shape == target.shape):
        raise ValueError("Triplet inputs must share coordinates and shape")
    cells = [display_pixels(v, arrays, roi, exposure) for v in (noisy, restored, target)]
    panel = np.concatenate(cells, axis=1)
    buffer = io.BytesIO()
    Image.fromarray(panel).save(buffer, format="PNG")
    publish_exclusive(path, buffer.getvalue())
    metadata = {
        "image": reference(path),
        "source": source,
        "ROI_xywh": list(roi),
        "checkpoint": checkpoint,
        "noise_conditioning": noise,
        "display_exposure": exposure,
        "display_contrast": 1,
        "wb": arrays["wb"].tolist(),
        "matrix": arrays["matrix"].tolist(),
        "reference_kind": reference_kind,
        "columns": ["noisy", "restored", reference_kind],
        "cell_pixels_wh": [roi[2], roi[3]],
        "resized": False,
    }
    write_json(Path(path).with_suffix(".json"), metadata)
    return metadata
