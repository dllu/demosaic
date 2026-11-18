"""Score the trained scene spectral arms and render all fixed native boards."""

import argparse
from pathlib import Path

import numpy as np
import torch
from report_fold_support_pooling import insert_camera_panels
from report_full_faint_photo_panel import LUMA, band, band_sums, original_masks
from report_scene_context_extent import rms

from demosaic.archive_metrics import linear_rgb, photometry
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.reporting import display_crop

METHODS = ("parent", "pooled", "spatial", "spatial-shifted")


def render(output, old, values, inputs):
    crop = old["case"]
    index, roi = crop["crop_index"], crop["ROI_xywh"]
    x, y, w, h = roi
    assert (w, h) == (160, 160)
    area = (index, slice(None), slice(y, y + h), slice(x, x + w))
    wb, matrix = (torch.from_numpy(inputs[k][index : index + 1]) for k in ("wb", "matrix"))
    additions = []
    for method, label in (
        ("pooled", "Pooled spectral"),
        ("spatial", "Spatial spectral"),
        ("spatial-shifted", "Shifted spatial spectral"),
    ):
        image = display_crop(
            torch.from_numpy(values[method][index : index + 1]),
            wb,
            matrix,
            roi,
            exposure=old["display_exposure"],
        )
        additions.append((label, np.rint(image.clip(0, 1) * 255).astype(np.uint8)))
    retain = (
        "Noisy (Malvar)",
        "V120 EMA",
        "Exact GT",
        "ISO100 AHD, not GT",
        "ISO6400 camera JPEG",
        "ISO100 camera JPEG",
    )
    previous = {**old, "panels": [p for p in old["panels"] if p["label"] in retain]}
    native, panels = insert_camera_panels(output, old["id"], previous, "V120 EMA", additions)
    return {
        **old,
        "image": native,
        "panels": panels,
        "previous_board": old["image"],
        "output_change_DN16_RMS": {
            k: rms(values[k][area].astype(np.float64) - values["parent"][area]) for k in METHODS[1:]
        },
    }


def score(inputs, values):
    target = inputs["target"]
    target_rgb = linear_rgb(target, inputs)
    coeff = band(np.einsum("c,bchw->bhw", LUMA, target_rgb))
    masks = original_masks(target, inputs)
    for method, sample in values.items():
        metrics = photometry(sample, inputs)
        bands = band(np.einsum("c,bchw->bhw", LUMA, linear_rgb(sample, inputs)))
        for i, moments in enumerate(band_sums(bands, coeff, masks)):
            yield {
                "crop": i,
                "method": method,
                "bands": moments,
                **{k: float(v[i]) for k, v in metrics.items()},
            }


def report(plan_path, collection):
    plan = read_json(plan_path)
    assert plan["reporter"] == reference(__file__)
    result = read_json(collection)
    assert result["plan"] == reference(plan_path) and not result["preflight"]
    output = Path(plan["root"]) / "review"
    output.mkdir()
    fixed = read_json(checked(plan["native_boards"]))
    old = read_json(checked(plan["development"]))
    review_inputs = [
        {
            "id": row["id"],
            "arrays": row["inputs"],
            "source_id": row["source_id"],
            "development": True,
        }
        for row in (read_json(checked(ref)) for ref in old["cases"])
    ]
    native = read_json(checked(plan["native"]))
    review_inputs.extend(
        {"id": r["id"], "arrays": r["arrays"], "source_id": None, "development": False}
        for r in native["observations"]
        if r["kind"] != "development"
    )
    rows, boards = [], []
    for case, binding in zip(review_inputs, result["records"], strict=True):
        record = read_json(checked(binding))
        assert case["id"] == record["id"]
        prefix = "crop_" if case["development"] else ""
        keys = ("wb", "matrix", "target") if case["development"] else ("wb", "matrix")
        with np.load(checked(case["arrays"]), allow_pickle=False) as raw:
            inputs = {key: raw[prefix + key] for key in keys}
        values = {
            name: np.load(checked(ref), allow_pickle=False)
            for name, ref in {"parent": record["parent"], **record["variants"]}.items()
        }
        if case["development"]:
            rows.extend(
                {"id": record["id"], "source_id": case["source_id"], **r}
                for r in score(inputs, values)
            )
        for board in fixed["boards"]:
            if board["observation"] == case["id"]:
                boards.append(render(output, board, values, inputs))
    assert len(rows) == 2048 and len(boards) == 16
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "collection": reference(collection),
            "metrics": rows,
            "boards": boards,
            "scope": "Fixed 64-source clean-target and both standing GFX camera families. "
            "Real AHD and JPEG references viewed as qualitative reference images.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("collection", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(2)
    report(args.plan.resolve(), args.collection.resolve())
