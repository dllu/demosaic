"""Audit exact mixed-scene quiet errors and render unscaled diagnostic crops."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from report_checkpoint_pilot import pixels
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import noisy_malvar


def independent_display(value, arrays, roi, exposure):
    rgb = np.einsum(
        "bij,bjhw->bihw",
        arrays["matrix"].astype(np.float64),
        value.astype(np.float64) * exposure * arrays["wb"].astype(np.float64)[..., None, None],
    ).clip(0, 1)
    rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
    x, y, w, h = roi
    return np.rint(rgb[0, :, y : y + h, x : x + w].transpose(1, 2, 0) * 255).astype(np.uint8)


def main(root):
    point = root / "mixed-quiet-v1"
    plan = read(point / "plan-v1.json")
    result = read(point / "result-v1.json")
    assert result["plan"] == ref(point / "plan-v1.json")
    assert result["counts"] == {"parent": 32, "DINO": 32, "raw-step1000": 32, "EMA-step1000": 32}
    rows = defaultdict(dict)
    for row in result["rows"]:
        assert row["method"] not in rows[row["id"]]
        rows[row["id"]][row["method"]] = row
    scalar_checks = 0
    out = point / "figures-v1"
    out.mkdir(exist_ok=False)
    images = []
    channels = 0
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    for case in plan["observations"]:
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        values = {}
        for label, row in rows[case["id"]].items():
            assert ref(row["prediction"]["path"]) == row["prediction"]
            values[label] = np.load(row["prediction"]["path"])
        assert set(values) == {"parent", "raw-step1000", "EMA-step1000"}
        # Independently form each160x160 quiet channel from explicit slices.
        for label, value in values.items():
            e = value.astype(np.float64) - a["target"].astype(np.float64)
            crop = np.stack([e[0, c, 176:336, 80:240] for c in range(3)])
            dc = crop.mean((1, 2))
            delta = value[..., 176:336, 80:240].astype(np.float64) - values["parent"][
                ..., 176:336, 80:240
            ].astype(np.float64)
            actual = {
                "full_RMS_DN16": np.sqrt(np.mean(e * e)) * 65535,
                "quiet_RMS_DN16": np.sqrt(np.mean(crop * crop)) * 65535,
                "quiet_spatial_RMS_DN16": np.sqrt(np.mean((crop - dc[:, None, None]) ** 2)) * 65535,
                "quiet_correction_RMS_DN16": np.sqrt(np.mean(delta * delta)) * 65535,
            }
            for key, number in actual.items():
                assert abs(rows[case["id"]][label][key] - number) < 1e-10
                scalar_checks += 1
        if case["pattern"] != "RGGB":
            continue
        noisy = noisy_malvar(a)
        for name, roi, contrast in (
            ("quiet", case["quiet_ROI_xywh"], 40),
            ("edge", case["edge_ROI_xywh"], 1),
        ):
            anchor = (
                a["target"][..., 176:336, 80:240].mean((-2, -1), keepdims=True).astype(np.float64)
            )
            labels = [
                "Noisy Malvar",
                "V143 parent",
                "V147 raw1000",
                "V147 EMA1000",
                "Exact constructed GT",
            ]
            sources = [
                noisy,
                values["parent"],
                values["raw-step1000"],
                values["EMA-step1000"],
                a["target"],
            ]
            board = Image.new("RGB", (848, 212), "#eeeeee")
            draw = ImageDraw.Draw(board)
            draw.text(
                (8, 4),
                f"{case['id']} | {name}, contrast{contrast}, exposure8",
                font=font,
                fill="black",
            )
            panels = []
            for j, (label, source) in enumerate(zip(labels, sources, strict=True)):
                transformed = anchor + contrast * (source.astype(np.float64) - anchor)
                cell = pixels(transformed, a, roi, 8)
                np.testing.assert_array_equal(cell, independent_display(transformed, a, roi, 8))
                assert cell.shape == (160, 160, 3)
                xywh = [8 + j * 168, 44, 160, 160]
                board.paste(Image.fromarray(cell), xywh[:2])
                draw.text((xywh[0], 24), label, font=font, fill="black")
                panels.append({"label": label, "xywh": xywh})
                channels += cell.size
            dest = out / f"{case['id']}-{name}.png"
            board.save(dest)
            actual = np.asarray(Image.open(dest))
            for panel, source in zip(panels, sources, strict=True):
                x, y, w, h = panel["xywh"]
                np.testing.assert_array_equal(
                    actual[y : y + h, x : x + w],
                    independent_display(
                        anchor + contrast * (source.astype(np.float64) - anchor), a, roi, 8
                    ),
                )
            images.append(
                {
                    "image": ref(dest),
                    "case": case,
                    "ROI_xywh": roi,
                    "exposure": 8,
                    "contrast_about_quiet_GT": contrast,
                    "camera_RGB_anchor": anchor.ravel().tolist(),
                    "panels": panels,
                    "no_resize": True,
                }
            )
    assert scalar_checks == 384 and len(images) == 16 and channels == 6144000
    groups = defaultdict(list)
    for row in result["rows"]:
        groups[row["method"], row["noise"]].append(row)
    summary = [
        {
            "method": method,
            "noise": noise,
            "cases": len(group),
            **{
                k: float(np.mean([r[k] for r in group]))
                for k in (
                    "full_RMS_DN16",
                    "quiet_RMS_DN16",
                    "quiet_spatial_RMS_DN16",
                    "quiet_correction_RMS_DN16",
                )
            },
        }
        for (method, noise), group in groups.items()
    ]
    sheets = []
    for i in range(0, 16, 4):
        sheet = Image.new("RGB", (848, 848), "white")
        for j, item in enumerate(images[i : i + 4]):
            board = Image.open(item["image"]["path"])
            sheet.paste(board, (0, 212 * j))
        dest = out / f"sheet-{i // 4:02d}.png"
        sheet.save(dest)
        reread = np.asarray(Image.open(dest))
        for j, item in enumerate(images[i : i + 4]):
            np.testing.assert_array_equal(
                reread[j * 212 : (j + 1) * 212], np.asarray(Image.open(item["image"]["path"]))
            )
        sheets.append({"image": ref(dest), "indices": list(range(i, i + 4)), "no_resize": True})
    save(
        point / "report-v1.json",
        {
            "status": "pass-independent-metrics-and-native-pixels",
            "result": ref(point / "result-v1.json"),
            "reporter": ref(__file__),
            "scalar_checks": scalar_checks,
            "RGB_channels_checked": channels,
            "summary": summary,
            "images": images,
            "sheets": sheets,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Quiet rectangle80,176,160,160 is exact constant target; this does not assert the entire left quarter of every analytic scene is constant. Exposure8 shared; quiet contrast40 about exact target, edge contrast1. Native160 pixels, no resize.",
        },
    )
    print("PASS384 mixed-scene scalar checks and6144000 native RGB channels")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
