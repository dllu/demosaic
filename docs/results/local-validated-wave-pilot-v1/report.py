"""Native fixed-pilot comparisons for the input-only validated-wave prototype."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels, statistics

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report(root, output=None):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan = read_json(root / "plan.json")
    collection = read_json(root / "collection.json")
    if collection["plan"] != reference(root / "plan.json") or len(collection["rows"]) != 24:
        raise ValueError("Require all input-only outputs closed before reference access")
    rows = {r["id"]: r for r in collection["rows"]}
    output = root / "report" if output is None else output
    output.mkdir()
    model = (
        reference(root / "analytic-model-v2.json")
        if (root / "analytic-model-v2.json").exists()
        else plan["model"]
    )
    figures, metrics = [], []
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)

    def board(name, cells, meta):
        canvas = Image.new("RGB", (8 + 168 * len(cells), 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        panels = []
        for i, (label, cell) in enumerate(cells):
            if cell.shape != (160, 160, 3) or cell.dtype != np.uint8:
                raise ValueError("Require unchanged native160 RGB8 cells")
            x, y = 8 + 168 * i, 24
            draw.text((x, 5), label, font=font, fill="black")
            canvas.paste(Image.fromarray(cell), (x, y))
            panels.append({"label": label, "xywh": [x, y, 160, 160]})
        path = output / (name + ".png")
        canvas.save(path)
        reread = np.asarray(Image.open(path))
        for panel, (_, cell) in zip(panels, cells, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(reread[y : y + h, x : x + w], cell)
        figures.append({"image": reference(path), "panels": panels, **meta})

    for row in plan["rows"]:
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            arrays = dict(z)
        sample = row["sample"]
        calibration = {k: arrays[k][sample : sample + 1] for k in ["wb", "matrix"]}
        physical = {
            **calibration,
            "packed": arrays["packed"][sample : sample + 1],
            "colors": arrays["colors"][sample : sample + 1],
        }
        parent = np.load(checked(row["parent"]), allow_pickle=False)[sample : sample + 1]
        parent_label = "V143" if row["kind"] == "finite-wire" else "V120"
        values = {
            parent_label: parent,
            **{
                m: np.load(checked(b), allow_pickle=False)[None]
                for m, b in rows[row["id"]]["predictions"].items()
            },
        }
        observation = row.get("observation", {})
        if row["kind"] == "finite-wire":
            if sample != 2:
                continue
            target, truth_roi, gtlabel = (
                arrays["target"][sample : sample + 1],
                row["ROI_xywh"],
                "Exact constructed GT",
            )
            cases = [{"name": row["id"], "ROI_xywh": row["ROI_xywh"]}]
        elif row["kind"] == "material":
            with np.load(checked(observation["target"]), allow_pickle=False) as z:
                target = z["target"]
            for name, value in values.items():
                metrics.append(
                    {
                        "case": row["id"],
                        "method": name,
                        "reference_role": row["reference_role"],
                        **statistics(value, target, calibration),
                    }
                )
            if "contrast0p025" in row["id"]:
                continue
            truth_roi, gtlabel = row["ROI_xywh"], "Exact synthetic GT"
            cases = [{"name": row["id"], "ROI_xywh": row["ROI_xywh"]}]
        elif row["kind"] == "gfx":
            target = np.load(checked(observation["target"]), allow_pickle=False)
            truth_roi, gtlabel = [0, 0, 160, 160], "ISO100 ref, not GT"
            cases = [
                {
                    "name": row["id"],
                    "ROI_xywh": row["ROI_xywh"],
                    "source_ROIs": observation["metadata"]["region"],
                }
            ]
        else:
            target, truth_roi, gtlabel = arrays["reference_rgb"], None, "ISO100 ref, not GT"
            cases = observation["cases"]
        noisy = arrays["noisy_rgb"] if row["kind"] == "mesh" else noisy_malvar(physical)
        for case in cases:
            roi, exposure = case["ROI_xywh"], row["display_exposure"]
            target_roi = roi if truth_roi is None else truth_roi
            noise_cell, truth_cell = (
                pixels(noisy, calibration, roi, exposure),
                pixels(target, calibration, target_roi, exposure),
            )
            main = (
                [("Noisy Malvar", noise_cell)]
                + [
                    (label, pixels(values[key], calibration, roi, exposure))
                    for label, key in [
                        (parent_label, parent_label),
                        ("Global support t2", "global-t2"),
                        ("Local support t2", "local-t2"),
                    ]
                ]
                + [(gtlabel, truth_cell)]
            )
            if row["kind"] == "mesh":
                for key, label in [
                    ("noisy_camera_jpeg", "SOOC ISO6400 JPEG"),
                    ("reference_camera_jpeg", "SOOC ISO100 JPEG"),
                ]:
                    jpeg = np.load(checked(case["camera_JPEGs"][key]["pixels"]), allow_pickle=False)
                    main.append((label, jpeg))
            metadata = {
                "case_id": row["id"],
                "source": row,
                "ROI_xywh": roi,
                "reference_ROI_xywh": target_roi,
                "noise_conditioning": row["noise"],
                "display_exposure": exposure,
                "display_contrast": 1,
                "wb": calibration["wb"].tolist(),
                "matrix": calibration["matrix"].tolist(),
                "reference_role": row["reference_role"],
                "analytic_configuration": model,
                "no_resize": True,
                "case": case,
            }
            name = row["id"] + ("-" + case["name"] if row["kind"] == "mesh" else "")
            board(name + "-comparison", main, metadata)
            board(
                name + "-triplet",
                [
                    ("Noisy Malvar", noise_cell),
                    ("Local support t2", pixels(values["local-t2"], calibration, roi, exposure)),
                    (gtlabel, truth_cell),
                ],
                metadata,
            )
    if "torch" in sys.modules:
        raise RuntimeError("CPU report imported Torch")
    write_json(
        output / "report.json",
        {
            "status": "rendered-fixed-pilot-awaiting-actual-native-viewing",
            "collection": reference(root / "collection.json"),
            "model": model,
            "reporter": reference(__file__),
            "figures": figures,
            "material_metrics": metrics,
            "native_RGB_channels_reread_exact": sum(
                len(x["panels"]) * 160 * 160 * 3 for x in figures
            ),
            "new_neural_forwards": 0,
            "scope": "Fixed pilot, two finite-wire geometries and RGGB/repeat0 materials; both protected real families/allROIs/profiles/JPEGs retained. Global/local matched from identical raw-only candidates. Real/approximate references labeled; no pixelwise GFX scores. All crop pixels native/unresized, actual viewing pending.",
        },
    )
    print(len(figures), "native boards;", len(metrics), "material rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report(args.root.resolve(), args.output.resolve() if args.output else None)
