"""Compact native V195 boards: one current baseline, four endpoints and references."""

from pathlib import Path

import numpy as np
from directional_trial_protocol import MODES, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from lossless_native import load_native
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from review_directional_response import source_guard


def render():
    plan = read(ROOT / "plan-v1.json")
    seal = source_guard(plan)
    assert ref(__file__) == seal["renderer"]
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
    scores = read(ROOT / "scores-v1.json")
    prior_path = Path(plan["V187_plan"]["path"]).parent / "figures-v1.json"
    prior = read(prior_path)
    prior_scores = read(plan["V187_scores"]["path"])
    methods = [method for mode in MODES for method in plan["methods"][mode].values()]
    out = ROOT / "figures-v1"
    out.mkdir()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    displayed_channels = copied_channels = 0

    def board(old, selections):
        nonlocal displayed_channels, copied_channels
        assert ref(old["image"]["path"]) == old["image"]
        source = np.asarray(Image.open(old["image"]["path"]))
        case = old["case"]
        assert ref(case["arrays"]["path"]) == case["arrays"]
        arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
        anchor = np.asarray(old["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
        canvas = Image.new("RGB", (8 + 168 * len(selections), 212), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (8, 4),
            f"{case['id']} | native160px, contrast{old['contrast']:g}, exposure{old['exposure']:g}",
            font=font,
            fill="black",
        )
        panels, bindings = [], {}
        for column, selection in enumerate(selections):
            x = 8 + 168 * column
            if isinstance(selection, str):
                label = selection
                binding = (
                    prior_scores["native_predictions"][case["id"]][selection]
                    if selection == "V187-pooled-wave-EMA"
                    else scores["native_predictions"][case["id"]][selection]
                )
                value = load_native(binding)
                displayed = anchor + old["contrast"] * (value.astype(np.float64) - anchor)
                crop = pixels(displayed, arrays, old["ROI_xywh"], old["exposure"])
                np.testing.assert_array_equal(
                    crop, independent_display(displayed, arrays, old["ROI_xywh"], old["exposure"])
                )
                bindings[selection] = binding
                displayed_channels += crop.size
                provenance = {"prediction": binding}
            else:
                label = selection["label"]
                sx, sy, w, h = selection["xywh"]
                assert w == h == 160
                crop = source[sy : sy + h, sx : sx + w].copy()
                copied_channels += crop.size
                provenance = {"source_figure": old["image"], "source_xywh": selection["xywh"]}
                if label == "Exact constructed GT":
                    target = anchor + old["contrast"] * (
                        arrays["target"].astype(np.float64) - anchor
                    )
                    np.testing.assert_array_equal(
                        crop, pixels(target, arrays, old["ROI_xywh"], old["exposure"])
                    )
            assert crop.shape == (160, 160, 3) and crop.dtype == np.uint8
            short = (
                label.replace("V195-whole-response-", "Whole ")
                .replace("V195-directional-response-", "Directional ")
                .replace("V187-pooled-wave-", "V187 ")
            )
            draw.text((x, 26), short, font=font, fill="black")
            canvas.paste(Image.fromarray(crop), (x, 44))
            panels.append({"label": label, "xywh": [x, 44, 160, 160], **provenance})
        path = out / f"comparison-{len(figures):02d}.png"
        canvas.save(path)
        image = np.asarray(Image.open(path))
        for panel in panels:
            x, y, w, h = panel["xywh"]
            if "source_figure" in panel:
                sx, sy, _, _ = panel["source_xywh"]
                expected = source[sy : sy + h, sx : sx + w]
            else:
                value = load_native(panel["prediction"])
                displayed = anchor + old["contrast"] * (value.astype(np.float64) - anchor)
                expected = independent_display(displayed, arrays, old["ROI_xywh"], old["exposure"])
            np.testing.assert_array_equal(image[y : y + h, x : x + w], expected)
        figures.append(
            {
                "case": case,
                "ROI_xywh": old["ROI_xywh"],
                "anchor": old["anchor"],
                "contrast": old["contrast"],
                "exposure": old["exposure"],
                "image": ref(path),
                "panels": panels,
                "predictions": bindings,
                "source_figure": old["image"],
                "triplet": len(selections) == 3,
                "no_resize": True,
                "checkpoints": {mode: scores["checkpoints"][mode] for mode in MODES},
                "reference_role": case["reference_role"],
            }
        )

    for old in prior["images"]:
        if old["triplet"]:
            # One old EMA triplet per source/transform; make four new triplets.
            if old["panels"][1]["label"] != "V187-pooled-wave-EMA":
                continue
            for method in methods:
                board(old, [old["panels"][0], method, old["panels"][-1]])
        else:
            references = [
                p
                for p in old["panels"]
                if p["label"] == "Exact constructed GT" or p["label"].startswith("ISO")
            ]
            assert references
            board(old, [old["panels"][0], "V187-pooled-wave-EMA", *methods, *references])
    assert len(figures) == 72 and sum(f["triplet"] for f in figures) == 24
    sheets = []
    for start in range(0, len(figures), 4):
        group = figures[start : start + 4]
        canvas = Image.new(
            "RGB",
            (max(Image.open(f["image"]["path"]).width for f in group), 212 * len(group)),
            "#eeeeee",
        )
        for row, item in enumerate(group):
            canvas.paste(Image.open(item["image"]["path"]), (0, 212 * row))
        path = out / f"sheet-{len(sheets):02d}.png"
        canvas.save(path)
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
            "status": "rendered-V195-compact-native-comparisons-awaiting-actual-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "prior_figures": ref(prior_path),
            "images": figures,
            "sheets": sheets,
            "native_figures": 72,
            "native_triplets": 24,
            "no_resize": True,
            "RGB_channels_independently_displayed": displayed_channels,
            "verified_earlier_noisy_reference_channels_copied": copied_channels,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("Rendered 48 compact boards +24 native triplets; actual viewing pending")


if __name__ == "__main__":
    render()
