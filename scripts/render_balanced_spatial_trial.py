"""Render fixed V168 native views with V169 balanced/branch diagnostics."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_directional_bank_trial import guard, read, ref, save

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V169-balanced-spatial-v3"


def render():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    result = read(ROOT / "scores-v1.json")
    assert result["component_forwards"] == result["original_predictions_replayed_exact"] == 1644
    prior = read(plan["prior_figures"]["path"])
    out = ROOT / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    channels = 0
    copied_channels = 0
    for index, item in enumerate(prior["images"]):
        assert ref(item["image"]["path"]) == item["image"]
        old = np.asarray(Image.open(item["image"]["path"]))
        case = item["case"]
        a = dict(np.load(case["arrays"]["path"]))
        anchor = np.asarray(item["anchor"]).reshape(1, 3, 1, 1)
        values = result["native_predictions"][case["id"]]
        sources = []
        bindings = {}

        def copied(panel, label=None, *, sources=sources, old=old):
            nonlocal copied_channels
            x, y, w, h = panel["xywh"]
            assert w == h == 160
            sources.append((label or panel["label"], old[y : y + h, x : x + w].copy()))
            copied_channels += w * h * 3

        def predicted(
            method,
            *,
            values=values,
            anchor=anchor,
            item=item,
            a=a,
            sources=sources,
            bindings=bindings,
        ):
            nonlocal channels
            binding = values[method]
            assert ref(binding["path"]) == binding
            value = np.load(binding["path"])
            displayed = anchor + item["contrast"] * (value.astype(np.float64) - anchor)
            actual = pixels(displayed, a, item["ROI_xywh"], item["exposure"])
            expected = independent_display(displayed, a, item["ROI_xywh"], item["exposure"])
            np.testing.assert_array_equal(actual, expected)
            assert actual.shape == (160, 160, 3)
            channels += actual.size
            sources.append((method, actual))
            bindings[method] = binding

        if "triplet_source_board" in item:
            label = item["panels"][1]["label"]
            endpoint = "EMA" if "EMA" in label else "raw"
            method = (
                ("balanced" if label.startswith("Fine mesh") else "spectral-only") + "-" + endpoint
            )
            copied(item["panels"][0])
            predicted(method)
            copied(item["panels"][-1])
        else:
            mapping = {p["label"]: p for p in item["panels"]}
            for name, label in [
                ("Noisy Malvar", None),
                ("V143 parent", None),
                ("Fine mesh raw1k", "V168 raw"),
                ("Fine mesh EMA1k", "V168 EMA"),
            ]:
                copied(mapping[name], label)
            for method in [
                "balanced-raw",
                "balanced-EMA",
                "spectral-only-raw",
                "spectral-only-EMA",
                "spatial-only-raw",
                "spatial-only-EMA",
            ]:
                predicted(method)
            for panel in item["panels"]:
                if panel["label"].startswith("V161") or panel["label"] in [
                    "Periodic detail",
                    "Exact constructed GT",
                    "ISO100 AHD, not GT",
                    "ISO6400 JPEG native",
                    "ISO100 JPEG, not GT",
                ]:
                    copied(panel)
        board = Image.new("RGB", (8 + 168 * len(sources), 212), "#eeeeee")
        draw = ImageDraw.Draw(board)
        draw.text(
            (8, 4),
            f"{case['id']} | V169 fixed weights,contrast{item['contrast']:g},RAW exposure{item['exposure']:g}",
            font=font,
            fill="black",
        )
        panels = []
        for j, (label, value) in enumerate(sources):
            x = 8 + 168 * j
            draw.text((x, 26), label, font=font, fill="black")
            board.paste(Image.fromarray(value), (x, 44))
            panels.append({"label": label, "xywh": [x, 44, 160, 160]})
        path = out / f"comparison-{index:02d}.png"
        board.save(path)
        check = np.asarray(Image.open(path))
        for panel, (_, value) in zip(panels, sources, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(check[y : y + h, x : x + w], value)
        figures.append(
            {
                "case": case,
                "ROI_xywh": item["ROI_xywh"],
                "anchor": item["anchor"],
                "contrast": item["contrast"],
                "exposure": item["exposure"],
                "image": ref(path),
                "panels": panels,
                "predictions": bindings,
                "source_figure": item["image"],
                "no_resize": True,
                "triplet": "triplet_source_board" in item,
            }
        )
    assert len(figures) == 72 and sum(i["triplet"] for i in figures) == 24
    sheets = []
    for n in range(18):
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
            "status": "rendered-awaiting-actual-original-detail-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "images": figures,
            "sheets": sheets,
            "new_RGB_channels_independently_checked": channels,
            "unchanged_RGB_channels_copied_exact": copied_channels,
            "no_resize": True,
            "native_figures": 72,
            "native_triplets": 24,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("Rendered72 native figures/24triplets;new channels", channels, "copied", copied_channels)


if __name__ == "__main__":
    render()
