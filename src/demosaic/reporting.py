"""Small native-pixel comparisons for performance reports (no image resampling)."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .color import render
from .safety import writable_path


def display_crop(rgb, wb, matrix, xywh, *, exposure=1.0):
    """Render just one B=1 camera-RGB crop, with an explicit common exposure."""
    x, y, w, h = xywh
    return (
        render(rgb[..., y : y + h, x : x + w] * exposure, wb, matrix)[0]
        .permute(1, 2, 0)
        .cpu()
        .numpy()
    )


def center_crop(shape, *, size=160, border=0):
    h, w = shape[-2:]
    size = min(size, h - 2 * border, w - 2 * border)
    if size < 1:
        raise ValueError("No pixels remain inside the report border")
    return [(w - size) // 2, (h - size) // 2, size, size]


def save_triplet(output, key, panels, *, caption, metadata):
    """Save three already-rendered HWC crops, each at exactly one pixel per pixel.

    No resizing, sharpening, independent exposure, or matplotlib rasterization.
    The receipt records each panel's exact pixel rectangle in the PNG canvas.
    """
    if len(panels) != 3:
        raise ValueError("A triplet requires noisy, denoised and reference panels")
    images = []
    for label, values in panels:
        values = np.asarray(values)
        if values.ndim != 3 or values.shape[-1] != 3 or not np.isfinite(values).all():
            raise ValueError("Expected finite HWC RGB display crops")
        images.append((label, np.rint(np.clip(values, 0, 1) * 255).astype(np.uint8)))
    shape = images[0][1].shape
    if any(values.shape != shape for _, values in images):
        raise ValueError("Native triplet panels must have matching dimensions")
    h, w, _ = shape
    gap, header = 8, 24
    canvas = Image.new("RGB", (3 * w + 4 * gap, h + header + gap), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    rectangles = []
    for i, (label, values) in enumerate(images):
        left = gap + i * (w + gap)
        draw.text((left, 5), label, fill="black")
        canvas.paste(Image.fromarray(values), (left, header))
        rectangles.append({"label": label, "png_xywh": [left, header, w, h]})
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    name = f"crop-{hashlib.sha256(key.encode()).hexdigest()[:16]}"
    path = output / f"{name}.png"
    canvas.save(path)
    receipt = {
        "image": path.name,
        "caption": caption,
        "pixel_scale": "1 image pixel = 1 PNG pixel; open original at 100%",
        "display_encoding": "8-bit sRGB preview; evaluation uses unquantized predictions",
        "panels": rectangles,
        "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **metadata,
    }
    path.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def write_report(output, result, crops, *, title, note, metrics):
    """Place the selected native crops alongside the numerical report."""
    lines = [f"# {title}", "", note, "", "| Model / subset | " + " | ".join(metrics) + " |"]
    lines.append("| --- | " + " | ".join("---:" for _ in metrics) + " |")
    for row in result["overall"]:
        values = [row["metrics"].get(name, {}).get("mean") for name in metrics]
        formatted = [f"{value:.4f}" if value is not None else "—" for value in values]
        lines.append(f"| {row['model']} / {row['kind']} | " + " | ".join(formatted) + " |")
    lines += [
        "",
        "Crops are selected by source/condition before viewing model output. Each panel is",
        "a native 160-pixel crop (smaller only if the evaluation tile requires it), with",
        "identical color and exposure transforms. Open the PNG at 100% if the viewer scales it.",
        "Noisy = Malvar demosaicing without denoising. Crop receipts record coordinates and settings.",
        "",
    ]
    for crop in crops:
        lines += [crop["caption"], "", f"![Native crop comparison]({crop['image']})", ""]
        source = crop.get("source", {})
        if source.get("page_url"):
            lines += [
                (
                    f"Source: [{source.get('title', 'Wikimedia Commons')}]({source['page_url']}), "
                    f"{source.get('author', '')}, [{source.get('license', '')}]({source.get('license_url', '')}). "
                    f"Modified: {source.get('bin_factor', 8)}× binning, crop, synthetic sensor noise and restoration."
                ),
                "",
            ]
    lines += ["Full metrics, checkpoint hashes and protocol: [summary.json](summary.json).", ""]
    (Path(output) / "report.md").write_text("\n".join(lines))
