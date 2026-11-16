"""Closed-cohort H1/aggregation comparisons and maximum-correction stress views."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report(
    root,
    output,
    *,
    method_label="Phase avg local t2",
    check_old_h1=True,
    control_method="H1-local-t2",
    control_label="H1 local t2",
):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan, collection = read_json(root / "plan.json"), read_json(root / "collection.json")
    original = read_json(root / "report/report.json")
    if len(collection["rows"]) != len(plan["rows"]) or original["collection"] != reference(
        root / "collection.json"
    ):
        raise ValueError("Require the complete declared cohort before any target/image analysis")
    output.mkdir(exist_ok=False)
    records = {r["id"]: r for r in collection["rows"]}
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures, channels = [], 0
    for figure in original["figures"]:
        if not Path(figure["image"]["path"]).stem.endswith("-comparison"):
            continue
        row = figure["source"]
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            calibration = {k: z[k][row["sample"] : row["sample"] + 1] for k in ("wb", "matrix")}
        values = np.load(checked(records[row["id"]]["predictions"][control_method]))[None]
        cell = pixels(values, calibration, figure["ROI_xywh"], figure["display_exposure"])
        # The independent channelwise display helper checks the newly inserted cell.
        np.testing.assert_array_equal(
            cell, crop(values, calibration, figure["ROI_xywh"], figure["display_exposure"])
        )
        canvas = Image.open(checked(figure["image"])).convert("RGB")
        panels = [dict(p) for p in figure["panels"]]
        assert panels[2]["label"] == "Global support t2"
        x, y, w, h = panels[2]["xywh"]
        canvas.paste(Image.fromarray(cell), (x, y))
        draw = ImageDraw.Draw(canvas)
        for column, label in [(2, control_label), (3, method_label)]:
            px = panels[column]["xywh"][0]
            draw.rectangle((px, 0, px + 160, 23), fill="#eeeeee")
            draw.text((px, 5), label, fill="black", font=font)
            panels[column]["label"] = label
        path = output / Path(figure["image"]["path"]).name
        canvas.save(path)
        encoded = np.asarray(Image.open(path))
        np.testing.assert_array_equal(encoded[y : y + h, x : x + w], cell)
        channels += cell.size
        figures.append(
            dict(
                figure,
                image=reference(path),
                panels=panels,
                original_aggregation_board=figure["image"],
                H1_prediction=records[row["id"]]["predictions"][control_method],
                scope="Existing audited board with only H1 control cell and two headings replaced; unchanged native pixels/calibration/ROI/references/JPEGs.",
            )
        )
    stress = []
    for row in plan["rows"]:
        if row["kind"] not in ("gfx", "mesh"):
            continue
        record, sample = records[row["id"]], row["sample"]
        parent = np.load(checked(row["parent"]))[sample : sample + 1]
        h1 = np.load(checked(record["predictions"][control_method]))[None]
        aggregate = np.load(checked(record["predictions"]["local-t2"]))[None]
        error = np.mean((aggregate[0].astype(np.float64) - parent[0]) ** 2, axis=0)
        integral = np.pad(error.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        energy = (
            integral[160:, 160:]
            - integral[:-160, 160:]
            - integral[160:, :-160]
            + integral[:-160, :-160]
        )
        y, x = np.unravel_index(np.argmax(energy), energy.shape)
        roi = [int(x), int(y), 160, 160]
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            data = {k: z[k][sample : sample + 1] for k in ("wb", "matrix", "packed", "colors")}
            noisy = z["noisy_rgb"] if row["kind"] == "mesh" else noisy_malvar(data)
        canvas = Image.new("RGB", (680, 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        panels = []
        cells = []
        for j, (label, value) in enumerate(
            zip(
                ("Noisy Malvar", "V120", control_label, method_label),
                (noisy, parent, h1, aggregate),
                strict=True,
            )
        ):
            cell = pixels(value, data, roi, row["display_exposure"])
            np.testing.assert_array_equal(cell, crop(value, data, roi, row["display_exposure"]))
            px = 8 + j * 168
            canvas.paste(Image.fromarray(cell), (px, 24))
            draw.text((px, 5), label, fill="black", font=font)
            panels.append({"label": label, "xywh": [px, 24, 160, 160]})
            cells.append(cell)
        path = output / (row["id"] + "-stress.png")
        canvas.save(path)
        encoded = np.asarray(Image.open(path))
        for cell, panel in zip(cells, panels, strict=True):
            px, py, w, h = panel["xywh"]
            np.testing.assert_array_equal(encoded[py : py + h, px : px + w], cell)
            channels += cell.size
        stress.append(
            {
                "image": reference(path),
                "panels": panels,
                "source": row,
                "ROI_xywh": roi,
                "display_exposure": row["display_exposure"],
                "display_contrast": 1,
                "no_resize": True,
                "selection": "After inference: native160 square with largest mean squared camera-RGB correction over V120, deterministic first maximum. No GT/reference selection or reference at this extra ROI.",
                "correction_ROI_RMS_DN16": float(np.sqrt(energy[y, x] / 160**2) * 65535),
                "checkpoint": plan["model"],
            }
        )
    finite = read_json(root / "finite-scores.json")
    sources = len({g["metadata"]["recipe"]["source"] for g in plan["finite_groups"]})
    means = []
    for prior in ("iso400", "iso1600", "iso6400"):
        for placement in ("near", "far"):
            for method in ("V143", *records[plan["rows"][0]["id"]]["predictions"]):
                rows = [
                    r
                    for r in finite["rows"]
                    if (r["profile"], r["placement"], r["method"]) == (prior, placement, method)
                ]
                assert len(rows) == sources
                keys = [k for k, v in rows[0].items() if isinstance(v, float)]
                means.append(
                    {
                        "profile": prior,
                        "placement": placement,
                        "method": method,
                        "sources": sources,
                        "views": len(rows),
                        **{k: float(np.mean([r[k] for r in rows])) for k in keys},
                    }
                )
    # Check new H1 controls against existing completed matching-stage inputs/outputs.
    equivalence = []
    if check_old_h1:
        previous = root.parents[0] / "local-wave-shapes-pilot-v1/matching"
        old = read_json(previous / "collection.json")
        key = lambda r: tuple(
            r[k]["sha256"] for k in ("parent_values", "packed_values", "colors_values")
        )
        lookup = {key(r): r for r in old["rows"]}
        for record in collection["rows"]:
            prior = lookup.get(key(record))
            if prior is None:
                continue
            diffs = []
            for method, binding in prior["predictions"].items():
                a, b = (
                    np.load(checked(binding)),
                    np.load(checked(record["predictions"]["H1-" + method])),
                )
                assert np.array_equal(a, b)
                diffs.append({"method": method, "byte_exact_values": True})
            equivalence.append({"case": record["id"], "previous": prior["id"], "methods": diffs})
        assert len(equivalence) == 24
    elif not plan.get("shared_global_CFA_partition"):
        raise ValueError("Skipping old per-tile controls requires a declared global split")
    assert "torch" not in sys.modules
    write_json(
        output / "report.json",
        {
            "plan": reference(root / "plan.json"),
            "collection": reference(root / "collection.json"),
            "source_report": reference(root / "report/report.json"),
            "figures": figures,
            "stress_figures": stress,
            "means": means,
            "H1_equivalence_cases": equivalence,
            "H1_equivalence_scope": "Original per-tile split controls"
            if check_old_h1
            else "Global split differs from historical per-tile masks; standalone global-mask control checks are separate",
            "new_or_replaced_RGB_channels_exact": channels,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "scope": f"{sources} reused geometries, one CFA/repeat across3 priors, declared fixed thresholds{plan['thresholds']}. Native {control_label}/{method_label} comparisons and post-inference correction stress views; references qualitative except constructed/synthetic targets. No population-confidence claim. Actual viewing remains pending.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--method-label", default="Phase avg local t2")
    parser.add_argument("--skip-old-h1-equivalence", action="store_true")
    parser.add_argument("--control-method", default="H1-local-t2")
    parser.add_argument("--control-label", default="H1 local t2")
    args = parser.parse_args()
    report(
        args.root.resolve(),
        args.output.resolve(),
        method_label=args.method_label,
        check_old_h1=not args.skip_old_h1_equivalence,
        control_method=args.control_method,
        control_label=args.control_label,
    )
