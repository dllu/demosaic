"""Native V178 control/evidence boards and triplets;prior pixels are copied exactly."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_phase_evidence_trial import METHODS, ROOT, guard, read, ref, save


def render():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    result = read(ROOT / "scores-v1.json")
    assert result["counts"] == plan["expected_quality_counts"]
    prior = read(plan["prior_figures"]["path"])
    out = ROOT / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    channels = copied_channels = 0
    for old in prior["images"]:
        if old["triplet"] and not old["panels"][1]["label"].startswith("V175-"):
            continue
        assert ref(old["image"]["path"]) == old["image"]
        source = np.asarray(Image.open(old["image"]["path"]))
        case = old["case"]
        a = dict(np.load(case["arrays"]["path"], allow_pickle=False))
        values = result["native_predictions"][case["id"]]
        anchor = np.asarray(old["anchor"]).reshape(1, 3, 1, 1)
        variants = []
        if old["triplet"]:
            endpoint = "raw" if old["panels"][1]["label"] == "V175-raw" else "EMA"
            for arm in ["control", "evidence"]:
                variants.append([old["panels"][0], METHODS[arm][endpoint], old["panels"][-1]])
        else:
            mapping = {p["label"]: p for p in old["panels"]}
            selections = [
                mapping[name]
                for name in ["Noisy Malvar", "V143 parent", "V169 EMA", "V172-EMA", "V175-EMA"]
            ]
            selections += [
                METHODS[arm][endpoint]
                for arm in ["control", "evidence"]
                for endpoint in ["raw", "EMA"]
            ]
            selections += [
                p
                for p in old["panels"]
                if p["label"].startswith("V161")
                or p["label"]
                in [
                    "Periodic detail",
                    "Exact constructed GT",
                    "ISO100 AHD, not GT",
                    "ISO6400 JPEG native",
                    "ISO100 JPEG, not GT",
                ]
            ]
            variants.append(selections)
        for selections in variants:
            panels = []
            bindings = {}
            for selection in selections:
                if isinstance(selection, str):
                    binding = values[selection]
                    assert ref(binding["path"]) == binding
                    value = np.load(binding["path"], allow_pickle=False)
                    displayed = anchor + old["contrast"] * (value.astype(np.float64) - anchor)
                    actual = pixels(displayed, a, old["ROI_xywh"], old["exposure"])
                    np.testing.assert_array_equal(
                        actual, independent_display(displayed, a, old["ROI_xywh"], old["exposure"])
                    )
                    assert actual.shape == (160, 160, 3)
                    channels += actual.size
                    bindings[selection] = binding
                    panels.append((selection, actual))
                else:
                    x, y, w, h = selection["xywh"]
                    assert w == h == 160
                    panels.append((selection["label"], source[y : y + h, x : x + w].copy()))
                    copied_channels += w * h * 3
            board = Image.new("RGB", (8 + 168 * len(panels), 212), "#eeeeee")
            draw = ImageDraw.Draw(board)
            draw.text(
                (8, 4),
                f"{case['id']} | V178 matched warm-start/evidence,contrast{old['contrast']:g},RAW exposure{old['exposure']:g}",
                font=font,
                fill="black",
            )
            records = []
            for index, (label, value) in enumerate(panels):
                x = 8 + 168 * index
                draw.text((x, 26), label, font=font, fill="black")
                board.paste(Image.fromarray(value), (x, 44))
                records.append({"label": label, "xywh": [x, 44, 160, 160]})
            path = out / f"comparison-{len(figures):02d}.png"
            board.save(path)
            image = np.asarray(Image.open(path))
            for record, (_, value) in zip(records, panels, strict=True):
                x, y, w, h = record["xywh"]
                np.testing.assert_array_equal(image[y : y + h, x : x + w], value)
            figures.append(
                {
                    "case": case,
                    "ROI_xywh": old["ROI_xywh"],
                    "anchor": old["anchor"],
                    "contrast": old["contrast"],
                    "exposure": old["exposure"],
                    "image": ref(path),
                    "panels": records,
                    "predictions": bindings,
                    "source_figure": old["image"],
                    "no_resize": True,
                    "triplet": old["triplet"],
                }
            )
    assert len(figures) == 72 and sum(f["triplet"] for f in figures) == 24 and channels == 16588800
    sheets = []
    for start in range(0, len(figures), 4):
        group = figures[start : start + 4]
        width = max(Image.open(f["image"]["path"]).width for f in group)
        sheet = Image.new("RGB", (width, 212 * len(group)), "#eeeeee")
        for row, item in enumerate(group):
            sheet.paste(Image.open(item["image"]["path"]), (0, 212 * row))
        path = out / f"sheet-{len(sheets):02d}.png"
        sheet.save(path)
        sheets.append(
            {
                "indices": list(range(start, start + len(group))),
                "image": ref(path),
                "no_resize": True,
            }
        )
    save(
        ROOT / "figures-v1.json",
        {
            "status": "rendered-awaiting-actual-native-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "images": figures,
            "sheets": sheets,
            "new_RGB_channels_independently_checked": channels,
            "unchanged_RGB_channels_copied": copied_channels,
            "no_resize": True,
            "native_figures": 72,
            "native_triplets": 24,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("Rendered72nativefigures24triplets;newchannels", channels, flush=True)


if __name__ == "__main__":
    render()
