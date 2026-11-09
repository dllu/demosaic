"""Native V200 boards: quieter V187,V195,both V197 EMAs,two new states and references."""

from pathlib import Path

import numpy as np
from admit_scale_supported_cfa_wave import MODES
from directional_trial_protocol import read, ref, save
from lossless_native import load_native
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from review_scale_supported_cfa_wave import review_plan, source_guard
from train_scale_supported_cfa_wave import ROOT


def render():
    plan = review_plan()
    seal = source_guard(plan)
    correction = None
    assert ref(__file__) == seal["renderer"]
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V200-two-endpoint")
    scores = read(ROOT / "scores-v1.json")
    prior_path = Path(plan["prior_figures"]["path"])
    prior = read(prior_path)
    prior_scores = read(plan["baseline_scores"]["path"])
    methods = [method for mode in MODES for method in plan["methods"][mode].values()]
    old_scores = {
        key: read(plan[key]["path"]) for key in ["V187_scores", "V197_scores", "V198_scores"]
    }
    previous_methods = [
        "V187-pooled-wave-EMA",
        "V195-whole-response-EMA",
        "V197-innovation-wave-EMA",
        "V198-CFA-wave-raw",
        "V198-CFA-wave-EMA",
    ]

    def prediction(case_id, method):
        if method == "V195-whole-response-EMA":
            source = prior_scores
        elif method == "V187-pooled-wave-EMA":
            source = old_scores["V187_scores"]
        elif method.startswith("V198-"):
            source = old_scores["V198_scores"]
        elif method.startswith("V197-"):
            source = old_scores["V197_scores"]
        else:
            source = scores
        return source["native_predictions"][case_id][method]

    out = ROOT / "figures-v1"
    out.mkdir(exist_ok=correction is not None)
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
                binding = prediction(case["id"], selection)
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
                label.replace("V200-scale-wave-", "V200 ")
                .replace("V198-CFA-wave-", "V198 ")
                .replace("V187-pooled-wave-", "V187 ")
                .replace("V197-RAW-wave-", "V197 RAW ")
                .replace("V197-innovation-wave-", "V197 Innov ")
                .replace("V195-whole-response-", "V195 ")
            )
            draw.text((x, 26), short, font=font, fill="black")
            canvas.paste(Image.fromarray(crop), (x, 44))
            panels.append({"label": label, "xywh": [x, 44, 160, 160], **provenance})
        path = out / f"comparison-{len(figures):02d}.png"
        if path.exists():
            assert correction is not None
            np.testing.assert_array_equal(np.asarray(Image.open(path)), np.asarray(canvas))
        else:
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
                "reference_role": case.get("reference_role")
                or "; ".join(
                    p["label"]
                    for p in panels
                    if p["label"] == "Exact constructed GT" or p["label"].startswith("ISO")
                ),
            }
        )

    for old in prior["images"]:
        if old["triplet"]:
            # One previous innovation EMA triplet per source/transform; make both new triplets.
            if old["panels"][1]["label"] != "V198-CFA-wave-EMA":
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
            board(old, [old["panels"][0], *previous_methods, *methods, *references])
    assert len(figures) == 60 and sum(f["triplet"] for f in figures) == 12
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
            "status": "rendered-V200-compact-native-comparisons-awaiting-actual-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "prior_figures": ref(prior_path),
            "images": figures,
            "sheets": sheets,
            "native_figures": 60,
            "native_triplets": 12,
            "no_resize": True,
            "RGB_channels_independently_displayed": displayed_channels,
            "verified_earlier_noisy_reference_channels_copied": copied_channels,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
            "metadata_correction": ref(ROOT / "render-source-v2.json") if correction else None,
            "existing_partial_images_preserved": len(correction["partial_images"])
            if correction
            else 0,
        },
    )
    print("Rendered 48 compact boards +12 native triplets; actual viewing pending")


if __name__ == "__main__":
    render()
