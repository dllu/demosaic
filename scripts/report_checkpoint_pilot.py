"""NumPy analysis and native crops for a retained-input checkpoint pilot."""

import argparse
import csv
import json
import os
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import display, linear_rgb, noisy_malvar


def checked(item):
    if ref(item["path"]) != item:
        raise ValueError("Retained artifact changed")
    return Path(item["path"])


def band(values):
    """DCT16 annulus 1/8 <= radial frequency < 1/3, native160 pixels."""
    values = np.asarray(values, dtype=np.float64)
    c = np.cos(np.pi * (np.arange(16)[None] + 0.5) * np.arange(16)[:, None] / 16)
    c *= np.sqrt(2 / 16)
    c[0] /= np.sqrt(2)
    f = np.arange(16) / 32
    radius = np.hypot(f[:, None], f[None])
    selected = (radius >= 1 / 8) & (radius < 1 / 3)
    luma = np.einsum("c,bchw->bhw", np.array([0.2126, 0.7152, 0.0722]), values)
    blocks = luma.reshape(len(luma), 10, 16, 10, 16).transpose(0, 1, 3, 2, 4)
    blocks = blocks.reshape(len(luma), 100, 16, 16)
    return (c @ blocks @ c.T)[..., selected], blocks.mean((-1, -2))


def pixels(value, arrays, roi, exposure):
    x, y, w, h = roi
    rendered = display(value.astype(np.float64), arrays, exposure)
    return np.rint(rendered[0, :, y : y + h, x : x + w].transpose(1, 2, 0) * 255).astype(np.uint8)


def statistics(prediction, target, arrays):
    prediction, target = [v[..., 48:208, 48:208].astype(np.float64) for v in (prediction, target)]
    camera_mse = float(np.mean((prediction.clip(0, 1) - target.clip(0, 1)) ** 2))
    srgb_mse = float(np.mean((display(prediction, arrays) - display(target, arrays)) ** 2))
    p, _ = band(linear_rgb(prediction, arrays))
    truth = linear_rgb(target, arrays)
    t, means = band(truth)
    valid = ((truth[0] >= 0) & (truth[0] <= 1)).all(0)
    valid = valid.reshape(10, 16, 10, 16).transpose(0, 2, 1, 3).reshape(100, 256).all(1)
    rms = np.sqrt(np.sum(t[0] ** 2, axis=-1) / 256)
    valid &= (means[0] >= 0.02) & (means[0] <= 0.9) & (rms >= 1e-5)
    contrast = rms / np.maximum(means[0], 1e-12)
    bins = []
    edges = (0, 0.02, 0.05, 0.1, 0.2, np.inf)
    for index, (low, high) in enumerate(pairwise(edges)):
        selected = valid & (contrast >= low) & (contrast < high)
        count = int(selected.sum())
        if not count:
            continue
        a, b = p[0, selected], t[0, selected]
        gain = float(np.sum(a * b) / np.sum(b * b))
        bins.append(
            {
                "bin": index,
                "blocks": count,
                "gain": gain,
                "band_error_RMS": float(np.sqrt(np.sum((a - b) ** 2) / (count * 256))),
                "orthogonal_residual_RMS": float(
                    np.sqrt(np.sum((a - gain * b) ** 2) / (count * 256))
                ),
            }
        )
    return {
        "camera_RGB_PSNR": float(-10 * np.log10(max(camera_mse, 1e-12))),
        "sRGB_PSNR": float(-10 * np.log10(max(srgb_mse, 1e-12))),
        "bands": bins,
    }


def report(plan_path, collection_path, *, model_label=None):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan, collection = read(plan_path), read(collection_path)
    guard(plan)
    expected = len(plan["observations"])
    if collection["plan"] != ref(plan_path) or collection["counts"] != {
        "root": expected,
        "encoder": expected,
    }:
        raise ValueError("Unexpected pilot collection")
    model_label = model_label or plan.get("model_label", "V123 9k EMA")
    root = Path(plan["root"])
    with (root / "report.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    output = root / "report-v1"
    output.mkdir(exist_ok=False)
    rows = {r["id"]: r for r in collection["observations"]}
    if set(rows) != {o["id"] for o in plan["observations"]}:
        raise ValueError("Missing or unexpected pilot observations")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images, metrics = [], []

    def board(name, cells, metadata):
        canvas = Image.new("RGB", (8 + len(cells) * 168, 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        panels = []
        for i, (label, cell) in enumerate(cells):
            if cell.shape != (160, 160, 3) or cell.dtype != np.uint8:
                raise ValueError("Publish only native160 crops without resizing")
            x, y = 8 + 168 * i, 24
            draw.text((x, 5), label, fill="black", font=font)
            canvas.paste(Image.fromarray(cell), (x, y))
            panels.append({"label": label, "png_xywh": [x, y, 160, 160]})
        path = output / (name + ".png")
        canvas.save(path)
        # Independently reread PNG pixels: every cell must equal its source crop.
        reread = np.asarray(Image.open(path))
        for panel, (_, cell) in zip(panels, cells, strict=True):
            x, y, w, h = panel["png_xywh"]
            np.testing.assert_array_equal(reread[y : y + h, x : x + w], cell)
        images.append({"name": name, "image": ref(path), "panels": panels, **metadata})

    for observation in plan["observations"]:
        with np.load(checked(observation["arrays"]), allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        new = np.load(checked(rows[observation["id"]]["prediction"]), allow_pickle=False)
        controls = observation.get("controls", [])
        predictions = [
            (
                c.get("label", c.get("model", {}).get("label")),
                np.load(checked(c["prediction"]), allow_pickle=False),
            )
            for c in controls
        ]
        predictions.append((model_label, new))
        metadata = {
            "observation_id": observation["id"],
            "checkpoint": plan["checkpoint"],
            "step": plan["step"],
            "input_arrays": observation["arrays"],
            "noise": observation["noise"],
            "display_exposure": observation["display_exposure"],
            "reference_role": observation["reference_role"],
            "no_resize": True,
        }
        if observation["kind"] in {"material", "shadow-material"}:
            with np.load(checked(observation["target"])) as data:
                target = data["target"]
            exposure = observation["display_exposure"]
            case_id = observation["case_id"]
            if observation["kind"] == "shadow-material":
                case_id += "-" + observation["noise"]["name"]
            for label, prediction in predictions:
                metrics.append(
                    {
                        "case": case_id,
                        "method": label,
                        "pattern": observation["pattern"],
                        "draw": 0,
                        "reference_role": observation["reference_role"],
                        **statistics(
                            prediction.astype(np.float64) * exposure,
                            target.astype(np.float64) * exposure,
                            arrays,
                        ),
                    }
                )
            if observation["pattern"] != "RGGB":
                continue
            roi = observation["ROI_xywh"]
            gtlabel = (
                "GT (synthetic)"
                if observation.get("original_case_id", observation["case_id"])
                in ("bark", "raccoon-fur")
                else "Binned ref (not GT)"
            )
            noisy = pixels(noisy_malvar(arrays), arrays, roi, exposure)
            truth = pixels(target, arrays, roi, exposure)
            denoised = pixels(new, arrays, roi, exposure)
            metadata.update({"case": observation["case"], "ROI_xywh": roi})
            board(
                case_id + "-comparison",
                [("Noisy draw0", noisy)]
                + [(label, pixels(p, arrays, roi, exposure)) for label, p in predictions]
                + [(gtlabel, truth)],
                metadata,
            )
            board(
                case_id + "-triplet",
                [("Noisy draw0", noisy), (model_label, denoised), (gtlabel, truth)],
                metadata,
            )
        elif observation["kind"] == "gfx":
            roi = observation["ROI_xywh"]
            exposure = observation["display_exposure"]
            target = np.load(checked(observation["target"]), allow_pickle=False)
            noisy = pixels(noisy_malvar(arrays), arrays, roi, exposure)
            truth = pixels(target, arrays, [0, 0, 160, 160], exposure)
            metadata.update({"ROI_xywh": roi, "source_ROIs": observation["metadata"]["region"]})
            board(
                observation["id"] + "-comparison",
                [("Noisy Malvar", noisy)]
                + [(label, pixels(p, arrays, roi, exposure)) for label, p in predictions]
                + [("ISO100 ref (not GT)", truth)],
                metadata,
            )
            board(
                observation["id"] + "-triplet",
                [
                    ("Noisy Malvar", noisy),
                    (model_label, pixels(new, arrays, roi, exposure)),
                    ("ISO100 ref (not GT)", truth),
                ],
                metadata,
            )
        else:
            exposure = observation["display_exposure"]
            for case in observation["cases"]:
                roi = case["ROI_xywh"]
                noisy = pixels(arrays["noisy_rgb"], arrays, roi, exposure)
                truth = pixels(arrays["reference_rgb"], arrays, roi, exposure)
                metadata_case = {**metadata, "case": case, "ROI_xywh": roi}
                board(
                    observation["id"] + "-" + case["name"] + "-comparison",
                    [("Noisy Malvar", noisy)]
                    + [
                        (label.replace("-profile3879", ""), pixels(p, arrays, roi, exposure))
                        for label, p in predictions
                    ]
                    + [("ISO100 ref (not GT)", truth)],
                    metadata_case,
                )
                board(
                    observation["id"] + "-" + case["name"] + "-triplet",
                    [
                        ("Noisy Malvar", noisy),
                        (model_label, pixels(new, arrays, roi, exposure)),
                        ("ISO100 ref (not GT)", truth),
                    ],
                    metadata_case,
                )
    groups = defaultdict(list)
    for row in metrics:
        groups[(row["case"], row["method"])].append(row)
    summaries = []
    for (case, method), values in groups.items():
        if len(values) != 4 or {v["pattern"] for v in values} != {"RGGB", "BGGR", "GRBG", "GBRG"}:
            raise ValueError("Require the same single draw across all four CFA patterns")
        bands = []
        for entry in values[0]["bands"]:
            matches = [next(b for b in v["bands"] if b["bin"] == entry["bin"]) for v in values]
            if len({b["blocks"] for b in matches}) != 1:
                raise ValueError("Reference-defined blocks changed between patterns")
            bands.append(
                {
                    "bin": entry["bin"],
                    "blocks": entry["blocks"],
                    **{
                        key: float(np.mean([b[key] for b in matches]))
                        for key in ("gain", "band_error_RMS", "orthogonal_residual_RMS")
                    },
                }
            )
        summaries.append(
            {
                "case": case,
                "method": method,
                "CFA_patterns": 4,
                "draws_per_CFA": 1,
                "reference_role": values[0]["reference_role"],
                **{
                    key: float(np.mean([v[key] for v in values]))
                    for key in ("camera_RGB_PSNR", "sRGB_PSNR")
                },
                "bands": bands,
            }
        )
    with (output / "metrics.csv").open("x", newline="") as stream:
        fields = [
            "case",
            "method",
            "pattern",
            "draw",
            "reference_role",
            "camera_RGB_PSNR",
            "sRGB_PSNR",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in metrics)
    save(
        output / "report.json",
        {
            "status": "rendered-and-scored-awaiting-native-review",
            "plan": ref(plan_path),
            "collection": ref(collection_path),
            "reporter": ref(__file__),
            "model_label": model_label,
            "metrics": metrics,
            "summaries": summaries,
            "images": images,
            "new_neural_forwards": 0,
            "RAW_decodes": 0,
            "PNG_channels_verified": sum(len(i["panels"]) * 160 * 160 * 3 for i in images),
            "scope": plan["scope"],
        },
    )
    print(json.dumps({"images": len(images), "rows": len(metrics), "summaries": summaries}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("collection", type=Path)
    parser.add_argument("--model-label")
    args = parser.parse_args()
    report(args.plan, args.collection, model_label=args.model_label)
