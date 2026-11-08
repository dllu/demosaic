"""Keep V169 native ROIs/transforms while comparing two learned matching residual endpoints."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_directional_bank_trial import guard, read, ref, save

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V172-local-noise-matching-v1"


def render():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    result = read(ROOT / "scores-method-labels-v2.json")
    assert result["counts"] == {"wrapper": 1644, "frozen": 1644, "network": 1500, "sampler": 7500}
    prior = read(plan["prior_figures"]["path"])
    out = ROOT / "figures-v2"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    channels = copied_channels = 0
    for old in prior["images"]:
        if old["triplet"] and not old["panels"][1]["label"].startswith("V171-"):
            continue
        assert ref(old["image"]["path"]) == old["image"]
        source = np.asarray(Image.open(old["image"]["path"]))
        case = old["case"]
        a = dict(np.load(case["arrays"]["path"]))
        values = result["native_predictions"][case["id"]]
        anchor = np.asarray(old["anchor"]).reshape(1, 3, 1, 1)
        panels = []
        bindings = {}
        if old["triplet"]:
            methods = ["V172-raw"] if old["panels"][1]["label"] == "V171-raw" else ["V172-EMA"]
            selections = [old["panels"][0], *methods, old["panels"][-1]]
        else:
            mapping = {p["label"]: p for p in old["panels"]}
            selections = [
                mapping["Noisy Malvar"],
                mapping["V143 parent"],
                mapping["V169 EMA"],
                mapping["V171-EMA"],
                "V172-raw",
                "V172-EMA",
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
        for selection in selections:
            if isinstance(selection, str):
                binding = values[selection]
                assert ref(binding["path"]) == binding
                value = np.load(binding["path"])
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
            f"{case['id']} | V172 local noise matching,contrast{old['contrast']:g},RAW exposure{old['exposure']:g}",
            font=font,
            fill="black",
        )
        records = []
        for j, (label, value) in enumerate(panels):
            x = 8 + 168 * j
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
    assert len(figures) == 60 and sum(i["triplet"] for i in figures) == 12
    sheets = []
    for n in range(15):
        group = figures[n * 4 : n * 4 + 4]
        width = max(Image.open(i["image"]["path"]).width for i in group)
        sheet = Image.new("RGB", (width, 848), "#eeeeee")
        for j, item in enumerate(group):
            sheet.paste(Image.open(item["image"]["path"]), (0, j * 212))
        path = out / f"sheet-{n:02d}.png"
        sheet.save(path)
        sheets.append(
            {"indices": list(range(n * 4, n * 4 + 4)), "image": ref(path), "no_resize": True}
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
            "native_figures": 60,
            "native_triplets": 12,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("Rendered60 native figures/12triplets;new/copied channels", channels, copied_channels)


if __name__ == "__main__":
    render()
