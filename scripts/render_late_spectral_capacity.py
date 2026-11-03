"""Native GT-oracle boards plus unchanged standing-real V148 baselines."""

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar


def main(root):
    plan = read(root / "plan-v1.json")
    trial = Path(plan["trial"])
    previous = read(trial / "figures-v1.json")
    templates = [v for v in previous["images"] if "triplet_source_board" not in v]
    assert len(templates) == 42
    diagnostic = {o["id"]: o for o in read(root / "result-v1.json")["observations"]}
    review = read(trial / "review-result-v1.json")
    baselines = {}
    for label in ("scalar-control-raw-step1000", "phase-matrix-raw-step1000"):
        collection = read(review["collections"][label]["path"])
        baselines[label] = {o["id"]: o["prediction"] for o in collection["observations"]}
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    names = [
        "Noisy Malvar",
        "V143 parent",
        "Scalar raw1k",
        "Matrix raw1k",
        "GT scalar/frozen",
        "GT scalar/full",
        "GT matrix/frozen",
        "GT matrix/full",
        "GT matrix/alpha",
        "GT L2 relaxed",
        "GT band residual",
        "GT unbanded",
        "Constructed GT",
    ]
    out = root / "figures-v1"
    out.mkdir(exist_ok=False)
    images, channels = [], 0
    for index, item in enumerate(templates):
        case = item["case"]
        if case["kind"] == "real":
            dest = out / f"unchanged-V148-real-{index:02d}.png"
            shutil.copyfile(item["image"]["path"], dest)
            assert ref(dest)["sha256"] == item["image"]["sha256"]
            images.append(
                {
                    **item,
                    "image": ref(dest),
                    "adopted_real_baseline": True,
                    "original_V148_board": item["image"],
                }
            )
            continue
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        bindings = [case["parent"]] + [baselines[k][case["id"]] for k in baselines]
        bindings += [diagnostic[case["id"]]["predictions"][k] for k in plan["modes"]]
        for binding in bindings:
            assert ref(binding["path"]) == binding
        values = [noisy_malvar(a)] + [np.load(b["path"]) for b in bindings] + [a["target"]]
        assert len(values) == len(names) == 13
        anchor = np.array(item["anchor"]).reshape(1, 3, 1, 1)
        cells = []
        for value in values:
            transformed = anchor + item["contrast"] * (value.astype(np.float64) - anchor)
            cell = pixels(transformed, a, item["ROI_xywh"], item["exposure"])
            np.testing.assert_array_equal(
                cell, independent_display(transformed, a, item["ROI_xywh"], item["exposure"])
            )
            assert cell.shape == (160, 160, 3)
            cells.append(cell)
        board = Image.new("RGB", (8 + 168 * len(cells), 212), "#eeeeee")
        draw = ImageDraw.Draw(board)
        draw.text(
            (8, 4),
            f"GT-ORACLE DIAGNOSTIC: uses target inside output | {case['id']} | contrast{item['contrast']} exposure{item['exposure']:g}",
            font=font,
            fill="#880000",
        )
        panels = []
        for j, (name, cell) in enumerate(zip(names, cells, strict=True)):
            xywh = [8 + 168 * j, 44, 160, 160]
            board.paste(Image.fromarray(cell), xywh[:2])
            draw.text((xywh[0], 24), name, font=font, fill="#880000" if 4 <= j <= 11 else "black")
            panels.append({"label": name, "xywh": xywh, "uses_GT_inside_output": 4 <= j <= 11})
            channels += cell.size
        dest = out / f"comparison-{index:02d}.png"
        board.save(dest)
        actual = np.asarray(Image.open(dest))
        for p, cell in zip(panels, cells, strict=True):
            x, y, w, h = p["xywh"]
            np.testing.assert_array_equal(actual[y : y + h, x : x + w], cell)
        record = {
            **item,
            "image": ref(dest),
            "original_V148_board": item["image"],
            "panels": panels,
            "adopted_real_baseline": False,
            "oracle_prediction_bindings": diagnostic[case["id"]]["predictions"],
            "oracle_uses_exact_GT": True,
            "no_resize": True,
        }
        images.append(record)
        triplet = (case["kind"] == "mesh" and case["present"] and item["contrast"] == 1) or (
            case["kind"] == "photo" and "3e638bbb" in case["id"]
        )
        if triplet:
            sources = [0, 8, 12]
            board = Image.new("RGB", (512, 212), "#eeeeee")
            draw = ImageDraw.Draw(board)
            draw.text(
                (8, 4), f"GT ORACLE (not inference) | {case['id']}", font=font, fill="#880000"
            )
            tp = []
            for j, k in enumerate(sources):
                xywh = [8 + 168 * j, 44, 160, 160]
                board.paste(Image.fromarray(cells[k]), xywh[:2])
                draw.text((xywh[0], 24), names[k], font=font, fill="#880000" if j == 1 else "black")
                tp.append(
                    {
                        "label": names[k],
                        "xywh": xywh,
                        "source_xywh": panels[k]["xywh"],
                        "uses_GT_inside_output": j == 1,
                    }
                )
                channels += cells[k].size
            dest = out / f"comparison-{index:02d}-GT-oracle-triplet.png"
            board.save(dest)
            actual = np.asarray(Image.open(dest))
            for p, k in zip(tp, sources, strict=True):
                x, y, w, h = p["xywh"]
                np.testing.assert_array_equal(actual[y : y + h, x : x + w], cells[k])
            images.append(
                {
                    **record,
                    "image": ref(dest),
                    "panels": tp,
                    "triplet_source_board": record["image"],
                }
            )
    assert len(images) == 46 and sum(v["adopted_real_baseline"] for v in images) == 8
    sheets = []
    for start in range(0, len(images), 4):
        subset = images[start : start + 4]
        sheet = Image.new(
            "RGB",
            (max(Image.open(v["image"]["path"]).width for v in subset), 212 * len(subset)),
            "white",
        )
        for j, v in enumerate(subset):
            sheet.paste(Image.open(v["image"]["path"]), (0, j * 212))
        dest = out / f"sheet-{start // 4:02d}.png"
        sheet.save(dest)
        actual = np.asarray(Image.open(dest))
        for j, v in enumerate(subset):
            expected = np.asarray(Image.open(v["image"]["path"]))
            h, w, _ = expected.shape
            np.testing.assert_array_equal(actual[j * 212 : j * 212 + h, :w], expected)
        sheets.append(
            {
                "image": ref(dest),
                "indices": list(range(start, start + len(subset))),
                "no_resize": True,
            }
        )
    save(
        root / "figures-v1.json",
        {
            "status": "rendered-and-independently-pixel-checked-awaiting-actual-viewing",
            "renderer": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "diagnostic": ref(root / "result-v1.json"),
            "images": images,
            "sheets": sheets,
            "new_oracle_figures": 38,
            "adopted_real_figures": 8,
            "RGB_channels_independently_checked": channels,
            "no_resize": True,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "All34 existing constructed-target boards show8 GT-using diagnostics plus fixed baselines. Four repeated-cell triplets. Eight unchanged realV148 boards retain both standing scenes, priors/windows/JPEGs, with no GT oracle or pixelwise reference scoring. All cells160x160 native, no resize. Actual viewing remains required.",
        },
    )
    print(
        "Rendered38 GT-oracle figures plus8 unchanged real baseline boards; checked channels",
        channels,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.absolute())
