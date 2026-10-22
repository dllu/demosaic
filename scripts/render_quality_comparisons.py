"""Render current-model comparisons from shipped native crops, without resizing."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build_native_crop_board import case_key, identity, read_crop, reference
from PIL import Image, ImageDraw, ImageFont


def render(manifest, noisy_preview_tolerance=0):
    data = json.loads(manifest.read_text())
    outputs = []
    for name, group in data["groups"].items():
        cases, labels, images = {}, {}, {}
        for crop in group["native_crops"]:
            parts, _, source = read_crop(manifest, crop, group["kind"])
            original, sha = identity(crop)
            label = group["labels"][original]
            key = case_key(crop, group["kind"])
            if (key, label) in images:
                raise ValueError("Duplicate comparison case/model")
            images[key, label] = (parts, crop, source)
            cases.setdefault(key, crop)
            if label in labels and labels[label] != sha:
                raise ValueError("Model identity changes across cases")
            labels[label] = sha
        methods = sorted(labels, key=lambda value: (value == "RawNIND", value))
        if set(images) != {(case, model) for case in cases for model in methods}:
            raise ValueError("Incomplete comparison rectangle")
        columns = [
            "Noisy (Malvar)",
            *methods,
            "Exact synthetic GT" if name == "photo" else "ISO100 ref (not GT)",
        ]
        canvas = Image.new("RGB", (100 + len(columns) * 168, 48 + len(cases) * 192), "white")
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype("DejaVuSans.ttf", 13)
        for index, column in enumerate(columns):
            draw.text(
                (104 + index * 168, 12),
                column,
                font=font,
                fill="#166534" if column == data["preferred_model"] else "black",
            )
        cells, preview_differences = [], []
        for row, (key, metadata) in enumerate(cases.items()):
            anchor = images[key, methods[0]][0]
            for model in methods:
                parts, crop, _ = images[key, model]
                if not np.array_equal(parts[2], anchor[2]):
                    raise ValueError("Reference pixels differ across methods")
                difference = np.abs(parts[0].astype(int) - anchor[0].astype(int))
                if int(difference.max()) > noisy_preview_tolerance:
                    raise ValueError("Noisy preview exceeds its declared RGB8 tolerance")
                preview_differences.append(
                    {
                        "case": key,
                        "model": model,
                        "channel_values_differing": int(np.count_nonzero(difference)),
                        "maximum_absolute_RGB8_difference": int(difference.max()),
                    }
                )
                fields = (
                    ("condition", "pattern", "evaluation_tile_xywh", "display_exposure")
                    if name == "photo"
                    else (
                        "conditioning",
                        "context_xywh",
                        "shared_wb",
                        "shared_matrix",
                        "display_exposure",
                    )
                )
                if any(crop[field] != metadata[field] for field in fields):
                    raise ValueError("Shared physical/display metadata differs")
                if name != "photo" and any(
                    crop["region"][field] != metadata["region"][field]
                    for field in ("name", "noisy_xy", "reference_xy", "size")
                ):
                    raise ValueError("Shared GFX coordinates differ")
            title = metadata.get("region", {}).get("name", metadata.get("source_id", ""))
            draw.text((4, 60 + row * 192), title[:11], font=font, fill="black")
            parts = [anchor[0], *[images[key, model][0][1] for model in methods], anchor[2]]
            for column, pixels in enumerate(parts):
                x, y = 104 + column * 168, 48 + row * 192
                canvas.paste(Image.fromarray(pixels), (x, y))
                cells.append(
                    {
                        "case": key,
                        "label": columns[column],
                        "xywh": [x, y, 160, 160],
                        "pixel_sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
                    }
                )
        output = manifest.parent / f"{name}-comparison.png"
        canvas.save(output)
        with Image.open(output) as saved:
            pixels = np.asarray(saved)
            for cell in cells:
                x, y, w, h = cell["xywh"]
                assert (
                    hashlib.sha256(pixels[y : y + h, x : x + w].tobytes()).hexdigest()
                    == cell["pixel_sha256"]
                )
        receipt = {
            "manifest": reference(manifest),
            "image": reference(output),
            "driver": reference(__file__),
            "model_checkpoints": labels,
            "cells": cells,
            "native_pixels_unchanged": True,
            "reference_shared_exactly": True,
            "noisy_preview_tolerance_DN": noisy_preview_tolerance,
            "noisy_preview_differences": preview_differences,
        }
        output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
        outputs.append(reference(output))
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--noisy-preview-tolerance-dn", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()
    print(json.dumps(render(args.manifest, args.noisy_preview_tolerance_dn)))
