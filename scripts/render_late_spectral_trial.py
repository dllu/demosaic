"""Unscaled native comparisons for both late spectral endpoints."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar

FRESH_VIEWS = (
    "flat512-gray-l0.02-adc-only-RGGB",
    "flat512-gray-l0.02-iso6400-prior-RGGB",
    "flat512-gray-l0.02-iso12800-prior-RGGB",
    "flat512-h210-s0.50-l0.02-iso6400-prior-RGGB",
    "flat512-gray-l0.18-iso12800-prior-RGGB",
    "flat512-gray-l0.90-iso12800-prior-RGGB",
)


def main(ROOT):
    queue = read(ROOT / "quality-design-v1.json")
    result = read(ROOT / "scores-v1.json")
    assert result["design"] == ref(ROOT / "quality-design-v1.json")
    observations = queue["observations"]
    by_case = {o["id"]: o for o in observations}
    by_id = {}
    for row in result["rows"]:
        by_id.setdefault(row["id"], {})[row["method"]] = row
    chosen = [
        "mesh-seed2026112302-present-iso6400-prior-RGGB",
        "mesh-seed2026112309-present-iso6400-prior-RGGB",
        "mesh-seed2026112304-absent-iso6400-prior-RGGB",
    ]
    chosen += [o["id"] for o in observations if o["kind"] == "real"]
    chosen += [
        "organic-02a76fd33b5e1414a0504f0b3f0aeb03a569b6f4-photo-faint-RGGB",
        "organic-dabacecd4780a1c230f8e9fce6ca1a604bdeab4c-photo-dark-RGGB",
        "organic-6b3920bceba82d95ecf9351d47f6f94267694bd0-photo-dark-RGGB",
        "gray-l0.02-adc-only-RGGB",
        "gray-l0.02-iso12800-prior-RGGB",
        *FRESH_VIEWS,
    ]
    chosen += [
        "photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-faint-RGGB",
        "photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-dark-RGGB",
    ]
    out = ROOT / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images = []
    channels = 0
    for identity in chosen:
        case = by_case[identity]
        rows = by_id[identity]
        a = dict(np.load(case["arrays"]["path"]))
        labels = ["Noisy Malvar", "V143 parent", "V147 raw1000", "V147 EMA1000"]
        values = [noisy_malvar(a)] + [
            np.load(rows[m]["prediction"]["path"])
            for m in ("parent", "raw-step1000", "EMA-step1000")
        ]
        if case["kind"] == "mesh":
            labels.append("Periodic detail")
            values.append(np.load(rows["periodic-detail"]["prediction"]["path"]))
        if case["kind"] != "real":
            target = a["target"]
            labels.append("Exact constructed GT")
        else:
            target = (
                a["reference_rgb"]
                if "reference_rgb" in a
                else np.load(case["reference_binding"]["path"])
            )
            labels.append("ISO100 AHD, not GT")
        values.append(target)
        roi = case.get("ROI_xywh", [176, 176, 160, 160])
        if case["kind"] == "mesh" and not case["present"]:
            delta = np.max(np.abs(values[2] - values[1]), axis=(0, 1))
            yy, xx = np.unravel_index(np.argmax(delta), delta.shape)
            roi = [int(np.clip(xx - 80, 0, 352)), int(np.clip(yy - 80, 0, 352)), 160, 160]
        windows = case.get("cases", [{"name": "crop", "ROI_xywh": roi}])
        if case["kind"] == "mesh":
            contrasts = [1, 40] if case["present"] else [40]
        elif case["kind"] == "photo":
            contrasts = [8] if case["variant"]["name"] == "photo-faint" else [1]
        elif case["kind"] == "flat":
            peak = max(case["source"]["linear_srgb"]) if case.get("fresh") else 0.02
            contrasts = [40 if peak <= 0.02 else 8 if peak <= 0.18 else 4]
        else:
            contrasts = [1]
        exposure = (
            (4 if not case.get("fresh") or max(case["source"]["linear_srgb"]) <= 0.02 else 1)
            if case["kind"] == "flat"
            else case.get("display_exposure", 8)
        )
        for window in windows:
            for contrast in contrasts:
                roi = window["ROI_xywh"]
                anchor = (
                    target.astype(np.float64).mean((-2, -1), keepdims=True)
                    if case["kind"] != "real"
                    else np.zeros((1, 3, 1, 1))
                )
                cells = []
                for j, value in enumerate(values):
                    selected = (
                        [0, 0, 160, 160]
                        if case["kind"] == "real"
                        and j == len(values) - 1
                        and value.shape[-2:] == (160, 160)
                        else roi
                    )
                    cells.append(
                        pixels(
                            anchor + contrast * (value.astype(np.float64) - anchor),
                            a,
                            selected,
                            exposure,
                        )
                    )
                display_labels = list(labels)
                if "camera_JPEGs" in window:
                    for key, label in [
                        ("noisy_camera_jpeg", "ISO6400 JPEG native"),
                        ("reference_camera_jpeg", "ISO100 JPEG, not GT"),
                    ]:
                        binding = window["camera_JPEGs"][key]["pixels"]
                        assert ref(binding["path"]) == binding
                        cells.append(np.load(binding["path"]))
                        display_labels.append(label)
                board = Image.new("RGB", (8 + 168 * len(cells), 212), "#eeeeee")
                draw = ImageDraw.Draw(board)
                draw.text(
                    (8, 4),
                    f"{identity[:80]} | RAW contrast{contrast}, exposure{exposure:g}; late spectral raw/EMA",
                    font=font,
                    fill="black",
                )
                panels = []
                for j, (cell, label) in enumerate(zip(cells, display_labels, strict=True)):
                    assert cell.shape == (160, 160, 3)
                    xywh = [8 + 168 * j, 44, 160, 160]
                    board.paste(Image.fromarray(cell), xywh[:2])
                    draw.text((xywh[0], 24), label, font=font, fill="black")
                    panels.append({"label": label, "xywh": xywh})
                    channels += cell.size
                path = out / f"{identity}-{window['name']}-contrast{contrast}.png"
                board.save(path)
                item = {
                    "image": ref(path),
                    "id": identity,
                    "case": case,
                    "ROI_xywh": roi,
                    "panels": panels,
                    "shared_camera_RGB_anchor": anchor.ravel().tolist(),
                    "shared_display_contrast": contrast,
                    "RAW_exposure": exposure,
                    "JPEG_display": "native sRGB8 without exposure/contrast adjustment"
                    if "camera_JPEGs" in window
                    else None,
                    "no_resize": True,
                }
                images.append(item)
                if (case["kind"] == "mesh" and case["present"] and contrast == 1) or (
                    case["kind"] == "photo" and "3e638bbb" in identity
                ):
                    for endpoint, selected in [("raw1000", 2), ("EMA1000", 3)]:
                        triplet = Image.new("RGB", (512, 212), "#eeeeee")
                        td = ImageDraw.Draw(triplet)
                        td.text(
                            (8, 4),
                            f"{identity} | common exposure{exposure:g}",
                            font=font,
                            fill="black",
                        )
                        tp = []
                        for j, source in enumerate([0, selected, len(values) - 1]):
                            xywh = [8 + 168 * j, 44, 160, 160]
                            triplet.paste(Image.fromarray(cells[source]), xywh[:2])
                            td.text((xywh[0], 24), display_labels[source], font=font, fill="black")
                            tp.append(
                                {
                                    "label": display_labels[source],
                                    "xywh": xywh,
                                    "source_xywh": panels[source]["xywh"],
                                }
                            )
                        path = out / f"{identity}-{endpoint}-triplet.png"
                        triplet.save(path)
                        images.append(
                            {
                                **item,
                                "image": ref(path),
                                "panels": tp,
                                "source_board": item["image"],
                            }
                        )
    assert len(images) == 34 and channels == 10982400
    sheets = []
    for start in range(0, len(images), 4):
        subset = images[start : start + 4]
        sheet = Image.new(
            "RGB",
            (max(Image.open(v["image"]["path"]).width for v in subset), 212 * len(subset)),
            "white",
        )
        for j, item in enumerate(subset):
            sheet.paste(Image.open(item["image"]["path"]), (0, j * 212))
        path = out / f"sheet-{start // 4:02d}.png"
        sheet.save(path)
        sheets.append(
            {
                "image": ref(path),
                "board_indices": list(range(start, start + len(subset))),
                "no_resize": True,
            }
        )
    save(
        ROOT / "figures-v1.json",
        {
            "design": ref(ROOT / "quality-design-v1.json"),
            "result": ref(ROOT / "scores-v1.json"),
            "renderer": ref(__file__),
            "checkpoints": {
                k: read(v["path"])["export"]
                for k, v in read(ROOT / "review-result-v1.json")["collections"].items()
            },
            "images": images,
            "sheets": sheets,
            "direct_rendered_channels": channels,
            "scope": "Fixed prior2 present seeds; absent2304 centered on maximum raw correction after scoring; all real windows;3 organic384 and2 actual512 bird photo variants;2 old256 flats and6 fresh512 fields. Eight triplets repeat source-board cells. All native160, no resizing; photographic/mesh GT is exact constructed target, real ISO100/JPEG is not GT.",
            "new_model_forwards": 0,
            "new_noise_draws": 0,
        },
    )
    print("Rendered34 native figures in9 unscaled sheets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
