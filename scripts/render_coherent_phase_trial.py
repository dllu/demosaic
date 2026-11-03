"""Native six-endpoint coherent-phase comparisons using unchanged V148 ROIs."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar


def main(root):
    plan = read(root / "plan-v1.json")
    previous = Path(plan["previous"])
    cases = {c["id"]: c for c in read(root / "quality-design-v1.json")["observations"]}
    collections = read(root / "review-result-v1.json")["collections"]
    labels = list(collections)
    assert len(labels) == 6
    assert labels == read(root / "quality-design-v1.json")["endpoints"]
    predictions = {
        label: {o["id"]: o["prediction"] for o in read(binding["path"])["observations"]}
        for label, binding in collections.items()
    }
    templates = []
    for item in read(previous / "figures-v1.json")["images"]:
        if "triplet_source_board" not in item:
            templates.append(
                {
                    "case": cases[item["case"]["id"]],
                    "ROI_xywh": item["ROI_xywh"],
                    "anchor": item["anchor"],
                    "contrast": item["contrast"],
                    "exposure": item["exposure"],
                    "source_board": item["image"],
                }
            )
    assert len(templates) == 42
    out = root / "figures-v1"
    out.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images = []
    channels = triplet_channels = 0
    for index, item in enumerate(templates):
        case, roi = item["case"], item["ROI_xywh"]
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        values = [noisy_malvar(a), np.load(case["parent"]["path"])] + [
            np.load(predictions[label][case["id"]]["path"]) for label in labels
        ]
        names = [
            "Noisy Malvar",
            "V143 parent",
            "Native raw1k",
            "Native EMA1k",
            "Aligned raw1k",
            "Aligned EMA1k",
            "Context raw1k",
            "Context EMA1k",
        ]
        if case["kind"] == "mesh":
            values.append(np.load(case["periodic_detail"]["path"]))
            names.append("Periodic detail")
        target = (
            a["reference_rgb"]
            if "reference_rgb" in a
            else np.load(case["reference_binding"]["path"])
            if case["kind"] == "real"
            else a["target"]
        )
        values.append(target)
        names.append("ISO100 AHD, not GT" if case["kind"] == "real" else "Exact constructed GT")
        anchor = np.array(item["anchor"]).reshape(1, 3, 1, 1)
        contrast, exposure = item["contrast"], item["exposure"]
        cells = []
        for j, value in enumerate(values):
            selected_roi = (
                [0, 0, 160, 160]
                if case["kind"] == "real"
                and j == len(values) - 1
                and value.shape[-2:] == (160, 160)
                else roi
            )
            transformed = anchor + contrast * (value.astype(np.float64) - anchor)
            cell = pixels(transformed, a, selected_roi, exposure)
            np.testing.assert_array_equal(
                cell, independent_display(transformed, a, selected_roi, exposure)
            )
            cells.append(cell)
        if case["kind"] == "real" and "cases" in case:
            window = next(v for v in case["cases"] if v["ROI_xywh"] == roi)
            for key, name in (
                ("noisy_camera_jpeg", "ISO6400 JPEG native"),
                ("reference_camera_jpeg", "ISO100 JPEG, not GT"),
            ):
                binding = window["camera_JPEGs"][key]["pixels"]
                assert ref(binding["path"]) == binding
                cells.append(np.load(binding["path"]))
                names.append(name)
        board = Image.new("RGB", (8 + 168 * len(cells), 212), "#eeeeee")
        draw = ImageDraw.Draw(board)
        draw.text(
            (8, 4),
            f"{case['id']} | paired1k, contrast{contrast}, RAW exposure{exposure:g}",
            font=font,
            fill="black",
        )
        panels = []
        for j, (name, cell) in enumerate(zip(names, cells, strict=True)):
            assert cell.shape == (160, 160, 3)
            xywh = [8 + 168 * j, 44, 160, 160]
            board.paste(Image.fromarray(cell), xywh[:2])
            draw.text((xywh[0], 24), name, font=font, fill="black")
            panels.append({"label": name, "xywh": xywh})
            channels += cell.size
        dest = out / f"comparison-{index:02d}.png"
        board.save(dest)
        reread = np.asarray(Image.open(dest))
        for panel, cell in zip(panels, cells, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(reread[y : y + h, x : x + w], cell)
        record = {
            **item,
            "image": ref(dest),
            "panels": panels,
            "no_resize": True,
            "JPEG_display": "native sRGB8 without exposure/contrast change"
            if "cases" in case
            else None,
        }
        images.append(record)
        make_triplets = (case["kind"] == "mesh" and case["present"] and contrast == 1) or (
            case["kind"] == "photo" and "3e638bbb" in case["id"]
        )
        if make_triplets:
            for j, label in enumerate(labels):
                sources = [0, j + 2, len(values) - 1]
                triplet = Image.new("RGB", (512, 212), "#eeeeee")
                td = ImageDraw.Draw(triplet)
                td.text(
                    (8, 4),
                    f"{case['id']} | contrast{contrast}, exposure{exposure:g}",
                    font=font,
                    fill="black",
                )
                tp = []
                for col, source in enumerate(sources):
                    xywh = [8 + 168 * col, 44, 160, 160]
                    triplet.paste(Image.fromarray(cells[source]), xywh[:2])
                    td.text((xywh[0], 24), names[source], font=font, fill="black")
                    tp.append(
                        {
                            "label": names[source],
                            "xywh": xywh,
                            "source_xywh": panels[source]["xywh"],
                        }
                    )
                    triplet_channels += cells[source].size
                dest = out / f"comparison-{index:02d}-{label}-triplet.png"
                triplet.save(dest)
                actual = np.asarray(Image.open(dest))
                for panel, source in zip(tp, sources, strict=True):
                    x, y, w, h = panel["xywh"]
                    np.testing.assert_array_equal(actual[y : y + h, x : x + w], cells[source])
                images.append(
                    {
                        **record,
                        "image": ref(dest),
                        "panels": tp,
                        "triplet_source_board": record["image"],
                    }
                )
    assert len(images) == 66
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
        dest = out / f"sheet-{start // 4:02d}.png"
        sheet.save(dest)
        actual = np.asarray(Image.open(dest))
        for j, item in enumerate(subset):
            pixels0 = np.asarray(Image.open(item["image"]["path"]))
            h, w, _ = pixels0.shape
            np.testing.assert_array_equal(actual[j * 212 : j * 212 + h, :w], pixels0)
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
            "status": "rendered-and-independently-pixel-checked",
            "review": ref(root / "review-result-v1.json"),
            "renderer": ref(__file__),
            "images": images,
            "sheets": sheets,
            "checkpoints": {k: read(v["path"])["export"] for k, v in collections.items()},
            "parent": plan["parent"],
            "direct_RGB_channels": channels,
            "triplet_RGB_channels": triplet_channels,
            "all_RGB_channels_checked": channels + triplet_channels,
            "no_resize": True,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Fixed V148 source-board ROIs/transforms:26 main boards+16 mixed controls, plus24 repeated-cell triplets for six endpoints. All160x160 native crops, no resize; all real priors/windows/JPEGs and photo/flat controls. Real references not GT. Actual native viewing remains required.",
        },
    )
    print(
        "Rendered66 native figures; independently checked RGB channels", channels + triplet_channels
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
