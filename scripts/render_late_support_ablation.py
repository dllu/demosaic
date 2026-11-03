"""Native same-ROI views of the post-hoc local-support intervention."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar


def main(root):
    point = root / "support-ablation-v1"
    full = {o["id"]: o["prediction"] for o in read(point / "collection-v1.json")["observations"]}
    raw = {
        o["id"]: o["prediction"]
        for o in read(root / "review-v1/raw-step1000/collection-v1.json")["observations"]
    }
    selected = []
    for item in read(root / "figures-v1.json")["images"]:
        if "source_board" in item:
            continue
        case = item["case"]
        keep = case["kind"] == "real"
        keep |= case["kind"] == "mesh" and case["present"] and item["shared_display_contrast"] == 40
        keep |= case["id"] in (
            "flat512-gray-l0.02-iso6400-prior-RGGB",
            "flat512-gray-l0.02-iso12800-prior-RGGB",
            "organic-02a76fd33b5e1414a0504f0b3f0aeb03a569b6f4-photo-faint-RGGB",
            "photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-dark-RGGB",
        )
        if keep:
            selected.append(item)
    assert len(selected) == 14
    out = point / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images = []
    channels = 0
    for index, item in enumerate(selected):
        case = item["case"]
        a = dict(np.load(case["arrays"]["path"]))
        roi = item["ROI_xywh"]
        labels = ["Noisy Malvar", "V143 parent", "V147 learned support", "V147 full support"]
        sources = [
            noisy_malvar(a),
            np.load(case["parent"]["path"]),
            np.load(raw[case["id"]]["path"]),
            np.load(full[case["id"]]["path"]),
        ]
        if case["kind"] == "mesh":
            labels.append("Periodic detail")
            sources.append(np.load(case["periodic_detail"]["path"]))
        labels.append("ISO100 AHD, not GT" if case["kind"] == "real" else "Exact constructed GT")
        target = (
            a["reference_rgb"]
            if "reference_rgb" in a
            else np.load(case["reference_binding"]["path"])
            if case["kind"] == "real"
            else a["target"]
        )
        sources.append(target)
        anchor = np.array(item["shared_camera_RGB_anchor"]).reshape(1, 3, 1, 1)
        contrast, exposure = item["shared_display_contrast"], item["RAW_exposure"]
        cells = []
        for j, source in enumerate(sources):
            selected_roi = (
                [0, 0, 160, 160]
                if case["kind"] == "real"
                and j == len(sources) - 1
                and source.shape[-2:] == (160, 160)
                else roi
            )
            transformed = anchor + contrast * (source.astype(np.float64) - anchor)
            cell = pixels(transformed, a, selected_roi, exposure)
            np.testing.assert_array_equal(
                cell, independent_display(transformed, a, selected_roi, exposure)
            )
            cells.append(cell)
        if case["kind"] == "real" and "cases" in case:
            window = next(w for w in case["cases"] if w["ROI_xywh"] == roi)
            for key, label in (
                ("noisy_camera_jpeg", "ISO6400 JPEG native"),
                ("reference_camera_jpeg", "ISO100 JPEG, not GT"),
            ):
                binding = window["camera_JPEGs"][key]["pixels"]
                assert ref(binding["path"]) == binding
                cells.append(np.load(binding["path"]))
                labels.append(label)
        board = Image.new("RGB", (8 + 168 * len(cells), 212), "#eeeeee")
        draw = ImageDraw.Draw(board)
        draw.text(
            (8, 4),
            f"{case['id']} | local-support diagnostic, RAW contrast{contrast}, exposure{exposure:g}",
            font=font,
            fill="black",
        )
        panels = []
        for j, (label, cell) in enumerate(zip(labels, cells, strict=True)):
            assert cell.shape == (160, 160, 3)
            xywh = [8 + 168 * j, 44, 160, 160]
            board.paste(Image.fromarray(cell), xywh[:2])
            draw.text((xywh[0], 24), label, font=font, fill="black")
            panels.append({"label": label, "xywh": xywh})
            channels += cell.size
        dest = out / f"view-{index:02d}.png"
        board.save(dest)
        actual = np.asarray(Image.open(dest))
        for panel, cell in zip(panels, cells, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(actual[y : y + h, x : x + w], cell)
        images.append(
            {
                "image": ref(dest),
                "source_board": item["image"],
                "case": case,
                "ROI_xywh": roi,
                "shared_camera_RGB_anchor": anchor.ravel().tolist(),
                "shared_display_contrast": contrast,
                "RAW_exposure": exposure,
                "panels": panels,
                "no_resize": True,
                "full_support_prediction": full[case["id"]],
                "JPEG_display": "native sRGB8" if "cases" in case else None,
            }
        )
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
            source = np.asarray(Image.open(v["image"]["path"]))
            h, w, _ = source.shape
            np.testing.assert_array_equal(actual[j * 212 : j * 212 + h, :w], source)
        sheets.append(
            {
                "image": ref(dest),
                "indices": list(range(start, start + len(subset))),
                "no_resize": True,
            }
        )
    save(
        point / "figures-v1.json",
        {
            "status": "rendered-and-independently-pixel-checked",
            "collection": ref(point / "collection-v1.json"),
            "renderer": ref(__file__),
            "images": images,
            "sheets": sheets,
            "RGB_channels_checked": channels,
            "no_resize": True,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Post-hoc diagnostic: same14 source boards/ROIs/transforms as completed review; all real priors/windows, two weak meshes at40x diagnostic contrast, two noisy flats, faint feathers and actual512 dark bird. Real references not GT; JPEGs native. Full support changes only the spatial gate, same raw weights.",
        },
    )
    print("Rendered14 ablation figures /4 sheets; checked RGB channels", channels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
