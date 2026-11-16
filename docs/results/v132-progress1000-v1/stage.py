"""Stage independently audited native endpoint boards for actual inspection."""

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import read, ref, save


def stage(root, output):
    report_path = root / "report-v1/report.json"
    report = read(report_path)
    audit_path = root / "independent-audit-v1.json"
    audit = read(audit_path)
    plan = read(root / "plan-v1.json")
    if audit["status"] != "passed-independent-FFT-metric-and-native-pixel-audit":
        raise ValueError("Require the completed independent native-pixel and metric audit")
    if report["plan"] != ref(root / "plan-v1.json") or report["collection"] != ref(
        root / "collection-v1.json"
    ):
        raise ValueError("Report does not bind this exact endpoint collection")
    if (
        audit["PNG_images"] != len(report["images"])
        or audit["PNG_channels_exact"] != report["PNG_channels_verified"]
    ):
        raise ValueError("Independent pixel coverage differs")
    output.mkdir(parents=True, exist_ok=False)
    images, sheets, triplets = output / "images", output / "sheets", []
    images.mkdir()
    sheets.mkdir()
    records, sheet_records = [], []
    for index, row in enumerate(report["images"]):
        path = Path(row["image"]["path"])
        if ref(path) != row["image"]:
            raise ValueError("Original native board changed")
        target = images / path.name
        shutil.copyfile(path, target)
        if ref(target)["sha256"] != row["image"]["sha256"]:
            raise ValueError("Board copy differs")
        record = {**row, "index": index, "original_image": row["image"], "image": ref(target)}
        records.append(record)
    for first in range(0, len(records), 4):
        group = records[first : first + 4]
        sources = [Image.open(r["image"]["path"]) for r in group]
        if any(p.mode != "RGB" for p in sources):
            raise ValueError("Native boards must already be RGB")
        sheet = Image.new(
            "RGB", (max(p.width for p in sources), sum(p.height for p in sources)), (238, 238, 238)
        )
        y = 0
        placements = []
        for row, pixels in zip(group, sources, strict=True):
            sheet.paste(pixels, (0, y))
            placements.append({"index": row["index"], "xywh": [0, y, pixels.width, pixels.height]})
            y += pixels.height
        path = sheets / f"sheet-{first // 4:02d}.png"
        sheet.save(path)
        reread = np.asarray(Image.open(path))
        for pixels, placement in zip(sources, placements, strict=True):
            x, y, w, h = placement["xywh"]
            np.testing.assert_array_equal(reread[y : y + h, x : x + w], np.asarray(pixels))
        sheets_record = {"image": ref(path), "placements": placements, "no_resize": True}
        sheet_records.append(sheets_record)
    for stem in ["bark", "raccoon-fur"]:
        row = next(r for r in records if r["name"] == stem + "-triplet")
        cells = []
        pixels = np.asarray(Image.open(row["image"]["path"]))
        if len(row["panels"]) != 3:
            raise ValueError("Require noisy/model/exact synthetic GT triplet")
        for panel in row["panels"]:
            x, y, w, h = panel["png_xywh"]
            if (w, h) != (160, 160):
                raise ValueError("Native crop pixels must remain160x160")
            cells.append(pixels[y : y + h, x : x + w])
        path = images / (stem + "-small-triplet.png")
        Image.fromarray(np.concatenate(cells, axis=1)).save(path)
        expected = np.concatenate(cells, axis=1)
        np.testing.assert_array_equal(np.asarray(Image.open(path)), expected)
        triplets.append(
            {
                **row,
                "source_board": row["image"],
                "image": ref(path),
                "panels": [
                    {"label": panel["label"], "png_xywh": [160 * i, 0, 160, 160]}
                    for i, panel in enumerate(row["panels"])
                ],
                "cell_pixels": [160, 160],
                "columns": ["noisy", report["model_label"], "exact constructed GT"],
                "no_resize": True,
            }
        )
    save(
        output / "manifest.json",
        {
            "images": records,
            "small_exact_GT_triplets": triplets,
            "no_resize": True,
            "viewed": False,
        },
    )
    save(
        output / "stage.json",
        {
            "status": "audited-native-boards-staged-awaiting-actual-viewing",
            "report": ref(report_path),
            "collection": ref(root / "collection-v1.json"),
            "plan": ref(root / "plan-v1.json"),
            "independent_audit": ref(audit_path),
            "checkpoint": plan["checkpoint"],
            "manifest": ref(output / "manifest.json"),
            "sheets": sheet_records,
            "native_boards": len(records),
            "triplet_boards": sum(r["name"].endswith("-triplet") for r in records),
            "no_resize": True,
            "new_neural_forwards": 0,
            "new_noise_source_draws": 0,
            "script": ref(__file__),
            "scope": "Copy only already independently audited source PNGs. Sheet/source pixels and two small exact-GT triplets checked byte-for-byte; actual viewing remains required.",
        },
    )
    print("staged", len(records), "native boards;", len(sheet_records), "sheets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    stage(a.root.resolve(), a.output.resolve())
