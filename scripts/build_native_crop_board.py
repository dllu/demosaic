"""Build native160px review boards from saved crop PNGs; no inference or resizing."""

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

KINDS = {
    "synthetic": ("GT (synthetic)", ("source_id", "evaluation_tile_xywh", "condition", "source")),
    "analytic": ("GT (analytic)", ("source_id", "evaluation_tile_xywh", "condition", "source")),
    "camera": ("AHD reference", ("scene", "prepared_crop", "conditioning", "evaluation_tile_xywh")),
    "gfx": ("ISO100 ref (not GT)", ("region", "context_xywh", "full_frame", "conditioning")),
    "three-camera": (
        "RawNIND (not GT)",
        ("source_sha256", "region", "sensor_roi_xywh", "context_roi_xywh", "conditioning"),
    ),
    "hue": ("GT (analytic)", ("case", "ROI_xywh", "conditioning")),
    "highlights": ("ISO100 AHD / not GT", ("region", "ROI_xywh", "source", "conditioning")),
}
MODEL_FIELDS = {
    "image",
    "caption",
    "png_sha256",
    "panels",
    "model",
    "model_label",
    "checkpoint_sha256",
    "compute_precision",
    "device",
    "runtime",
    "model_index",
    "case_index",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reference(path, data=None):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path.read_bytes() if data is None else data)}


def identity(crop):
    model = crop.get("model", {})
    label = crop.get("model_label", model.get("label"))
    hashes = [
        value
        for value in (
            crop.get("checkpoint_sha256"),
            model.get("sha256"),
            model.get("weight_sha256"),
        )
        if value is not None
    ]
    sha = hashes[0] if hashes else None
    if not isinstance(label, str) or not label:
        raise ValueError("Missing model label")
    if model.get("label", label) != label or any(value != sha for value in hashes):
        raise ValueError("Conflicting model label or checkpoint hash")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("Missing recorded checkpoint SHA256")
    return label, sha


def case_key(crop, kind):
    if kind in ("synthetic", "analytic"):
        value = crop["source_id"]
    elif kind == "camera":
        value = [crop["scene"], crop["prepared_crop"]["id"]]
    elif kind == "three-camera":
        value = [crop["source_sha256"], crop["region"]]
    elif kind == "hue":
        value = crop["case"]["id"]
    else:
        value = crop["region"]["name"]
    return json.dumps(value, sort_keys=True)


def read_crop(report, crop, kind):
    expected_label, required = KINDS[kind]
    for key in (*required, "display_exposure", "reference", "pixel_scale", "display_encoding"):
        if key not in crop:
            raise ValueError(f"Missing shared crop metadata: {key}")
    if (
        len(crop["panels"]) != 3
        or crop["panels"][0]["label"] != "Noisy (Malvar)"
        or crop["panels"][2]["label"] != expected_label
    ):
        raise ValueError("Reference label does not match the explicitly selected report kind")
    path = (report.parent / crop["image"]).resolve()
    if not path.is_relative_to(report.parent.resolve()):
        raise ValueError("Crop PNG is outside its report directory")
    data = path.read_bytes()
    if digest(data) != crop["png_sha256"]:
        raise ValueError("Crop PNG hash mismatch")
    with Image.open(io.BytesIO(data)) as image:
        if image.mode != "RGB":
            raise ValueError("Expected RGB8 display PNG")
        pixels = np.asarray(image).copy()
    parts, rects = [], []
    for panel in crop["panels"]:
        rect = panel["png_xywh"]
        if len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError("Panel coordinates must be integer xywh")
        x, y, w, h = rect
        if (
            (w, h) != (160, 160)
            or x < 0
            or y < 0
            or x + w > pixels.shape[1]
            or y + h > pixels.shape[0]
        ):
            raise ValueError("Panel must be an in-bounds native160px square")
        if any(x < a + c and a < x + w and y < b + d and b < y + h for a, b, c, d in rects):
            raise ValueError("Panel rectangles overlap")
        rects.append(rect)
        parts.append(pixels[y : y + h, x : x + w])
    settings = {k: v for k, v in crop.items() if k not in MODEL_FIELDS}
    return parts, settings, reference(path, data)


def build(reports, output, kind, labels=None):
    """Require a complete method-by-case rectangle and retain every input crop receipt."""
    output = Path(output)
    receipt_path = output.with_suffix(".json")
    if output.suffix != ".png" or output.exists() or receipt_path.exists():
        raise ValueError("Choose a new PNG and receipt path")
    cases, models, hashes, inputs, sources = {}, [], {}, [], []
    for index, report in enumerate(map(Path, reports)):
        report_data = report.read_bytes()
        inputs.append(reference(report, report_data))
        crops = json.loads(report_data)["native_crops"]
        if not crops:
            raise ValueError("Report has no saved native crops")
        for crop in crops:
            model, sha = identity(crop)
            if model not in models:
                models.append(model)
            if hashes.setdefault(model, sha) != sha:
                raise ValueError("One model label names different checkpoints")
            key = (index, case_key(crop, kind))
            case = cases.setdefault(key, {})
            if model in case:
                raise ValueError("Duplicate model/case crop")
            parts, settings, png = read_crop(report, crop, kind)
            case[model] = (parts, settings, png, crop)
            sources.append({"report_index": index, "image": png, "crop": crop})
    if labels is not None and (
        set(labels) != set(models) or len(set(labels.values())) != len(models)
    ):
        raise ValueError("Display labels must uniquely map every recorded method")
    names = [labels[m] if labels is not None else m for m in models]
    last = "AHD reference (not exact GT)" if kind == "camera" else KINDS[kind][0]
    row_names = ["Noisy (Malvar)", *names, last]
    ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left = max(180, max(ruler.textbbox((0, 0), n)[2] for n in row_names) + 16)
    image = Image.new("RGB", (left + 168 * len(cases), 48 + 184 * len(row_names)), "white")
    draw = ImageDraw.Draw(image)
    cells = []
    for col, (key, case) in enumerate(cases.items()):
        if set(case) != set(models):
            raise ValueError("Incomplete method-by-case rectangle")
        first_parts, first_settings, _, _ = case[models[0]]
        for parts, settings, _, _ in case.values():
            if settings != first_settings:
                raise ValueError(
                    "Source/ROI/noise/display/reference metadata differs across methods"
                )
            if not np.array_equal(parts[0], first_parts[0]) or not np.array_equal(
                parts[2], first_parts[2]
            ):
                raise ValueError("Noisy/reference pixels differ across methods")
        draw.text((left + 168 * col, 4), f"Report {key[0] + 1}", fill="black")
        draw.text((left + 168 * col, 20), key[1].strip('"')[:24], fill="black")
        rows = [(models[0], 0), *((m, 1) for m in models), (models[0], 2)]
        for row, (model, part) in enumerate(rows):
            parts, _, png, crop = case[model]
            x, y = left + 168 * col, 72 + 184 * row
            draw.text((4, 56 + 184 * row), row_names[row], fill="black")
            image.paste(Image.fromarray(parts[part]), (x, y))
            cells.append(
                {
                    "case": list(key),
                    "row_label": row_names[row],
                    "model_label": model,
                    "part": part,
                    "image": png,
                    "source_xywh": crop["panels"][part]["png_xywh"],
                    "board_xywh": [x, y, 160, 160],
                    "pixel_sha256": digest(parts[part].tobytes()),
                }
            )
    # Validate every input before creating either output; never overwrite existing artifacts.
    for item in inputs:
        if reference(item["path"]) != item:
            raise ValueError("Report changed during board construction")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        image.save(stream, format="PNG")
    with Image.open(output) as saved:
        readback = np.asarray(saved)
    for cell in cells:
        x, y, w, h = cell["board_xywh"]
        if digest(readback[y : y + h, x : x + w].tobytes()) != cell["pixel_sha256"]:
            raise ValueError("Saved board pixel mismatch")
    result = {
        "status": "saved-native-board-awaiting-manual-review",
        "kind": kind,
        "driver": reference(__file__),
        "reports": inputs,
        "board": reference(output),
        "models": [
            {"label": m, "display_label": n, "sha256": hashes[m]}
            for m, n in zip(models, names, strict=True)
        ],
        "native_cells_exact": len(cells),
        "source_triplets": sources,
        "cells": cells,
        "scope": "Saved RGB8 preview PNG rearrangement only. Every cell is an unchanged native160px square; shared metadata and noisy/reference pixels match across methods. Recorded checkpoint hashes are retained, not rehashed here. No inference, new score, quality finding, training or promotion. Manual review remains required.",
    }
    with receipt_path.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--kind", choices=KINDS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--labels", type=Path, help="Optional complete original-label to display-label JSON map"
    )
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text()) if args.labels else None
    result = build(args.reports, args.output, args.kind, labels)
    print(
        json.dumps({"board": result["board"], "native_cells_exact": result["native_cells_exact"]})
    )


if __name__ == "__main__":
    main()
