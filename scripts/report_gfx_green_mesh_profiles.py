"""Render matched nominal/nearby-profile mesh comparisons from retained predictions."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from prepare_gfx_green_mesh_inputs import binding, save

from demosaic.color import linear_to_srgb, srgb_to_linear
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def checked(item):
    path = Path(item["path"])
    if binding(path) != item:
        raise ValueError(f"Changed retained artifact: {path}")
    return path


def read(item):
    return json.loads(checked(item).read_text())


def pixels(values):
    return np.rint(values.clip(0, 1) * 255).astype(np.uint8)


@torch.inference_mode()
def main(nominal_path, nearby_path, output):
    torch.set_num_threads(2)
    nominal, nearby = [json.loads(Path(p).read_text()) for p in (nominal_path, nearby_path)]
    inputs = [read(r["inputs"]) for r in (nominal, nearby)]
    arrays = []
    for r in inputs:
        with np.load(checked(r["input_arrays"]), allow_pickle=False) as data:
            arrays.append({k: data[k] for k in data.files})
    if arrays[0].keys() != arrays[1].keys():
        raise ValueError("Input fields differ")
    for key in arrays[0].keys() - {"variance"}:
        np.testing.assert_array_equal(arrays[0][key], arrays[1][key])
    for key in ("cases", "source_bindings", "registrations"):
        if inputs[0][key] != inputs[1][key]:
            raise ValueError(f"Changed comparison geometry/source: {key}")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    exposure = 16.0
    tensors = {k: torch.from_numpy(v) for k, v in arrays[0].items()}
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    rendered = []
    triplets = []
    for model in ("V114", "V115"):
        methods = [
            next(r for r in nominal["methods"] if r["label"] == model),
            next(r for r in nearby["methods"] if r["label"] == model + "-profile3879"),
        ]
        predictions = []
        for method, source in zip(methods, inputs, strict=True):
            if method["source_inputs_sha256"] != source["input_arrays"]["sha256"]:
                raise ValueError("Prediction conditioning binding differs")
            prediction = np.load(checked(method["prediction"]), allow_pickle=False)
            assert prediction.shape == (1, 3, 768, 768) and np.isfinite(prediction).all()
            predictions.append(torch.from_numpy(prediction))
        labels = [
            "ISO6400 camera JPEG",
            "Noisy Malvar",
            model + " nominal prior",
            model + " nearby profile",
            "ISO100 AHD, not GT",
            "ISO100 camera JPEG",
        ]
        for case in inputs[0]["cases"]:
            roi = case["ROI_xywh"]
            panels = {}
            for label, key in [(labels[1], "noisy_rgb"), (labels[4], "reference_rgb")]:
                panels[label] = display_crop(
                    tensors[key], tensors["wb"], tensors["matrix"], roi, exposure=exposure
                )
            for role, label in [
                ("noisy_camera_jpeg", labels[0]),
                ("reference_camera_jpeg", labels[5]),
            ]:
                jpeg = np.load(checked(case["camera_JPEGs"][role]["pixels"]), allow_pickle=False)
                panels[label] = linear_to_srgb(
                    (srgb_to_linear(jpeg.astype(np.float32) / 255) * exposure).clip(0, 1)
                )
            for label, prediction in zip(labels[2:4], predictions, strict=True):
                panels[label] = display_crop(
                    prediction, tensors["wb"], tensors["matrix"], roi, exposure=exposure
                )
            board = Image.new("RGB", (6 * 176 + 8, 192), "#eeeeee")
            draw = ImageDraw.Draw(board)
            rectangles = []
            for col, label in enumerate(labels):
                draw.text((8 + col * 176, 5), label, fill="black", font=font)
                board.paste(Image.fromarray(pixels(panels[label])), (8 + col * 176, 24))
                rectangles.append({"label": label, "png_xywh": [8 + col * 176, 24, 160, 160]})
            path = output / f"{model}-{case['name']}-4EV.png"
            board.save(path)
            rendered.append(
                {"model": model, "case": case, "image": binding(path), "panels": rectangles}
            )
            method = methods[1]
            receipt = save_triplet(
                output / "triplets",
                method["label"] + case["name"],
                [
                    (labels[1], panels[labels[1]]),
                    (model + " nearby profile", panels[labels[3]]),
                    ("ISO100 ref, not GT", panels[labels[4]]),
                ],
                caption="Fixed DSCF3879 profile on DSCF3842; independent DSCF3835 reference, not GT.",
                metadata={
                    "case": case,
                    "method": method,
                    "conditioning": inputs[1]["conditioning"],
                    "source_bindings": inputs[0]["source_bindings"],
                    "input_arrays": inputs[1]["input_arrays"],
                    "display_exposure": exposure,
                    "reference": "DSCF3835 ISO100 f/5.6, independent AHD; not exact GT",
                },
            )
            triplets.append(
                {
                    "model": model,
                    "case": case["name"],
                    "image": binding(output / "triplets" / receipt["image"]),
                    "metadata": binding(
                        (output / "triplets" / receipt["image"]).with_suffix(".json")
                    ),
                }
            )
    result = {
        "status": "rendered-retained-predictions-awaiting-native-review",
        "renderer": binding(__file__),
        "nominal": binding(nominal_path),
        "nearby": binding(nearby_path),
        "conditioning": {"nominal": inputs[0]["conditioning"], "nearby": inputs[1]["conditioning"]},
        "inputs_equal_except_variance": True,
        "source_bindings": inputs[0]["source_bindings"],
        "display_exposure": exposure,
        "native_pixel_size": [160, 160],
        "boards": rendered,
        "triplets": triplets,
        "new_neural_forwards": 0,
        "new_RAW_decodes": 0,
        "new_noise_observations": 0,
        "scope": "Retained context predictions only. No resampling, fitting, scoring, calibration truth or full-frame/speed claim.",
    }
    save(output / "manifest.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nominal", type=Path)
    parser.add_argument("nearby", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.nominal, args.nearby, args.output)
