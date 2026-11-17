"""Native fixed-ROI boards/triplets after all new coloured-wire corrections close."""

import argparse
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report(root):
    assert read_json(root / "comparison-result.json")["all_corrections_closed"]
    assert len(read_json(root / "scores-v1.json")["rows"]) == 400
    plan = read_json(root / "plan.json")
    comparison = read_json(root / "comparison-plan.json")
    parents = {
        g["group"]: g["parent"] for g in read_json(root / "parents-collection.json")["groups"]
    }
    records = {
        v["name"]: {r["id"]: r for r in read_json(Path(v["root"]) / "collection.json")["rows"]}
        for v in comparison["variants"]
    }
    output = root / "native"
    output.mkdir()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    channels = 0
    for group in plan["groups"]:
        case = group["cases"][2]
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            physical = {k: z[k][2:3] for k in ["packed", "colors", "wb", "matrix"]}
            truth = z["target"][2:3]
        values = {
            "Noisy Malvar": noisy_malvar(physical),
            "V120": np.load(checked(parents[group["id"]]))[2:3],
            "Exact GT": truth,
        }
        bindings = {}
        for name, rows in records.items():
            for mode in ["conditional-local-t2", "local-t2"]:
                key = name + "::" + mode
                bindings[key] = rows[case]["predictions"][mode]
                values[key] = np.load(checked(bindings[key]))[None]
        layouts = []
        for arm, mode in [("analytic", "conditional-local-t2"), ("neural", "local-t2")]:
            panels = [("Noisy Malvar", "Noisy Malvar"), ("V120", "V120")]
            panels += [
                (label, name + "::" + mode)
                for label, name in [
                    ("Broad", "broad"),
                    ("Fine phase", "fine-phase"),
                    ("Fine H1", "fine-sinusoidal"),
                    ("Joint colour", "joint-fine"),
                ]
            ]
            panels += [("Exact constructed GT", "Exact GT")]
            layouts.append((group["id"] + "-" + arm + "-comparison", panels))
            if group["pattern"] == "RGGB":
                layouts.append(
                    (
                        group["id"] + "-" + arm + "-triplet",
                        [
                            ("Noisy Malvar", "Noisy Malvar"),
                            ("Joint colour", "joint-fine::" + mode),
                            ("Exact constructed GT", "Exact GT"),
                        ],
                    )
                )
        for name, layout in layouts:
            canvas = Image.new("RGB", (8 + 168 * len(layout), 192), "#eeeeee")
            draw = ImageDraw.Draw(canvas)
            panels = []
            for j, (label, key) in enumerate(layout):
                expected = crop(values[key], physical, [176, 176, 160, 160], 16.0)
                np.testing.assert_array_equal(
                    expected, pixels(values[key], physical, [176, 176, 160, 160], 16.0)
                )
                x, y = 8 + 168 * j, 24
                canvas.paste(Image.fromarray(expected), (x, y))
                draw.text((x, 5), label, fill="black", font=font)
                panels.append(
                    {
                        "label": label,
                        "method": key,
                        "xywh": [x, y, 160, 160],
                        "prediction": bindings.get(key),
                    }
                )
            path = output / (name + ".png")
            canvas.save(path)
            encoded = np.asarray(Image.open(path))
            for panel in panels:
                x, y, w, h = panel["xywh"]
                np.testing.assert_array_equal(
                    encoded[y : y + h, x : x + w],
                    crop(values[panel["method"]], physical, [176, 176, 160, 160], 16.0),
                )
                channels += w * h * 3
            figures.append(
                {
                    "image": reference(path),
                    "panels": panels,
                    "group": group,
                    "ROI_xywh": [176, 176, 160, 160],
                    "display_exposure": 16.0,
                    "display_contrast": 1,
                    "wb": physical["wb"].tolist(),
                    "matrix": physical["matrix"].tolist(),
                    "parent": parents[group["id"]],
                    "parent_checkpoint": plan["checkpoint"],
                    "reference_role": "Exact newly constructed coloured sensor RGB GT",
                    "no_resize": True,
                }
            )
    assert len(figures) == 40
    write_json(
        output / "report.json",
        {
            "script": reference(__file__),
            "scores": reference(root / "scores-v1.json"),
            "figures": figures,
            "RGB_crop_channels_exact": channels,
            "independent_display_functions_match": True,
            "scope": "All192 corrections/scoring closed before rendering.40 native fixed-ROI boards/triplets, allCFAs/priors, separate nuisance arms. No crop selection from GT/output quality, no resized pixels. Actual viewing and final independent audit/publication still pending.",
        },
    )
    print("40 native figures;", channels, "exact crop channels; actual viewing pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    report(parser.parse_args().root)
