"""Native local/global phase comparisons; old panel pixels remain exact."""

import argparse
from pathlib import Path

import numpy as np
from audit_coherent_pair_evidence_trial import terminal
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_coherent_pair_evidence_trial import METHODS, ROOT, guard, read, ref, save


def render(root=ROOT, *, fixture=False):
    plan = read(root / "plan-v1.json")
    if fixture:
        assert root != ROOT and plan["fixture_only_no_actual_V183_quality"] is True
    else:
        assert root == ROOT
        guard(plan)
        seal = read(root / "render-source-v1.json")
        assert seal["renderer"] == ref(__file__) and seal["plan"] == ref(root / "plan-v1.json")
        terminal(root / "scores-v1.json")
        for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
            assert read(root / name)["status"].startswith("pass-")
    result = read(root / "scores-v1.json")
    assert result["counts"] == plan["expected_quality_counts"]
    prior = read(plan["prior_figures"]["path"])
    out = root / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    channels = copied_channels = 0
    for old in prior["images"]:
        if old["triplet"] and not old["panels"][1]["label"].startswith("V181-flat-spatial-"):
            continue
        assert ref(old["image"]["path"]) == old["image"]
        source = np.asarray(Image.open(old["image"]["path"]))
        case = old["case"]
        a = dict(np.load(case["arrays"]["path"], allow_pickle=False))
        values = result["native_predictions"][case["id"]]
        anchor = np.asarray(old["anchor"]).reshape(1, 3, 1, 1)
        variants = []
        if old["triplet"]:
            endpoint = "raw" if old["panels"][1]["label"].endswith("-raw") else "EMA"
            for arm in ["evidence"]:
                variants.append([old["panels"][0], METHODS[arm][endpoint], old["panels"][-1]])
        else:
            assert [p["label"] for p in old["panels"][:13]] == [
                "Noisy Malvar",
                "V143 parent",
                "V169 EMA",
                "V172-EMA",
                "V175-EMA",
                "V178-control-raw",
                "V178-control-EMA",
                "V178-evidence-raw",
                "V178-evidence-EMA",
                "V180-local-phase-raw",
                "V180-local-phase-EMA",
                "V181-flat-spatial-raw",
                "V181-flat-spatial-EMA",
            ]
            selections = (
                old["panels"][:13]
                + [METHODS["evidence"][e] for e in ["raw", "EMA"]]
                + old["panels"][13:]
            )
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
                f"{'CPU LAYOUT FIXTURE / NO V183 QUALITY | ' if fixture else ''}{case['id']} | V183 coherent response vs completed V181,contrast{old['contrast']:g},RAW exposure{old['exposure']:g}",
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
    assert len(figures) == 60 and sum(f["triplet"] for f in figures) == 12 and channels == 8294400
    assert copied_channels == 58137600
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
        root / "figures-v1.json",
        {
            "status": "rendered-layout-fixture-not-quality"
            if fixture
            else "rendered-awaiting-actual-native-viewing",
            "fixture_only_no_actual_V183_quality": fixture,
            "plan": ref(root / "plan-v1.json"),
            "scores": ref(root / "scores-v1.json"),
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
    print("Rendered60nativefigures12triplets;fixture", fixture, "newchannels", channels, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path)
    args = parser.parse_args()
    render(args.fixture_root if args.fixture_root else ROOT, fixture=args.fixture_root is not None)
