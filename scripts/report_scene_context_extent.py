"""Score and render the fixed-RAW distant and nearby preview interventions."""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from report_fold_support_pooling import insert_camera_panels
from report_full_faint_photo_panel import LUMA, band, band_sums, original_masks

from demosaic.archive_metrics import linear_rgb, photometry
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.reporting import display_crop

METHODS = ("full", "blur-distant", "blur-near")


def rms(values):
    return float(np.sqrt(np.mean(values.astype(np.float64) ** 2)) * 65535)


def load_arrays(record, keys):
    with np.load(checked(record), allow_pickle=False) as source:
        return {key: source[key] for key in keys}


def metrics(arrays, predictions):
    target = arrays["crop_target"]
    inputs = {key: arrays["crop_" + key] for key in ("wb", "matrix")}
    masks = original_masks(target, inputs)
    target_band = band(np.einsum("c,bchw->bhw", LUMA, linear_rgb(target, inputs)))
    rows = []
    for method, value in predictions.items():
        bands = band(np.einsum("c,bchw->bhw", LUMA, linear_rgb(value, inputs)))
        means = photometry(value, {**inputs, "target": target})
        for i, statistics in enumerate(band_sums(bands, target_band, masks)):
            rows.append(
                {
                    "method": method,
                    "crop": i,
                    "srgb_psnr": float(means["srgb_psnr"][i]),
                    "linear_psnr": float(means["linear_psnr"][i]),
                    "weak_band_sums": statistics.get("0"),
                    "quiet_band_sums": statistics.get("quiet"),
                    "output_change_DN16": rms(value[i].astype(np.float64) - predictions["full"][i]),
                }
            )
    return rows


def render(output, old, arrays, predictions):
    info = old["case"]
    roi = info["ROI_xywh"]
    index = info["crop_index"]
    x, y, w, h = roi
    assert (w, h) == (160, 160)
    wb, matrix = [torch.from_numpy(arrays[k][index : index + 1]) for k in ("wb", "matrix")]
    names = {"full": "Spatial2k", "blur-distant": "Distant blur", "blur-near": "Near blur"}
    rendered = {}
    for key, value in predictions.items():
        image = display_crop(
            torch.from_numpy(value[index : index + 1]),
            wb,
            matrix,
            roi,
            exposure=old["display_exposure"],
        )
        rendered[key] = np.rint(image.clip(0, 1) * 255).astype(np.uint8)
    old_panel = next(p for p in old["panels"] if p["label"] == names["full"])
    px, py, _, _ = old_panel["png_xywh"]
    with Image.open(checked(old["image"])) as saved:
        np.testing.assert_array_equal(saved.crop((px, py, px + w, py + h)), rendered["full"])
    base = {
        **old,
        "panels": [p for p in old["panels"] if p["label"] not in ("Local-only2k", "Pooled2k")],
    }
    image, panels = insert_camera_panels(
        output,
        old["id"],
        base,
        names["full"],
        [(names[key], rendered[key]) for key in METHODS[1:]],
    )
    return {
        **old,
        "source_image": old["image"],
        "image": image,
        "panels": panels,
        "output_change_DN16": {
            key: rms(
                value[index, :, y : y + h, x : x + w].astype(np.float64)
                - predictions["full"][index, :, y : y + h, x : x + w]
            )
            for key, value in predictions.items()
        },
    }


def report(collection_file, native_file, output):
    collection = read_json(collection_file)
    plan = read_json(checked(collection["plan"]))
    original = read_json(checked(plan["original"]))
    native = read_json(native_file)
    assert native["plan"] == plan["original"]
    stored = {row["case"]: row for row in collection["rows"]}
    output.mkdir()
    all_metrics, boards = [], []
    for case in original["observations"]:
        key = case["id"]
        record = stored[key]
        predictions = {
            name: np.load(checked(record["prediction"][name]), allow_pickle=False)
            for name in METHODS
        }
        development = case["kind"] == "development"
        prefix = "crop_" if development else ""
        arrays = load_arrays(case["arrays"], [prefix + k for k in ("wb", "matrix")])
        if development:
            arrays.update(load_arrays(case["arrays"], ("crop_target",)))
            all_metrics.extend({"case": key, **row} for row in metrics(arrays, predictions))
        displays = {k: arrays[prefix + k] for k in ("wb", "matrix")}
        for old in native["boards"]:
            if old["observation"] == key:
                rows = render(output, old, displays, predictions)
                boards.append(rows)
    assert len(all_metrics) == 48 and len(boards) == 16
    write_json(
        output / "result.json",
        {
            "reporter": reference(__file__),
            "collection": reference(collection_file),
            "source_native": reference(native_file),
            "metrics": all_metrics,
            "boards": boards,
            "scope": "All 16 exact-GT crops scored. Camera ROIs compare changes to full-context predictions without scoring independent reference data.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", type=Path)
    parser.add_argument("native", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(2)
    report(args.collection.resolve(), args.native.resolve(), args.output.resolve())
