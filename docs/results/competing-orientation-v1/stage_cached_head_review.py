"""Audit and stage actual native review pixels; leave human viewing unclaimed."""

import argparse
import gzip
import hashlib
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.crops import display_pixels
from demosaic.experiments.evaluation.native import load_native


def stage(run, output):
    result_binding = reference(run / "result.json")
    result = read_json(checked(result_binding))
    if result["status"] != "evaluated-awaiting-native-viewing":
        raise ValueError("Expected a completed numerical review")
    figures = read_json(checked(result["figures"]))
    if len(figures["images"]) != 60 or sum(f["triplet"] for f in figures["images"]) != 12:
        raise ValueError("Expected the complete native60 board/12 triplet design")
    for state, binding in result["scores"].items():
        scores = read_json(checked(binding))
        if len(scores["rows"]) != 822 or state not in ["raw", "ema"]:
            raise ValueError("Expected both complete endpoints")
        if any(
            r.get("reference_scored") is not False for r in scores["rows"] if r["kind"] == "real"
        ):
            raise ValueError("Independent real references must not be scored")
    if set(result["scores"]) != {"raw", "ema"}:
        raise ValueError("Missing raw or EMA endpoint")
    output.mkdir(parents=True, exist_ok=False)
    images, evidence, sheets = [output / p for p in ["images", "evidence", "sheets"]]
    for p in [images, evidence, sheets]:
        p.mkdir()
    records, boards = [], []
    candidate_channels = retained_channels = 0
    for figure in figures["images"]:
        source = checked(figure["image"])
        board = np.asarray(Image.open(source).convert("RGB"))
        with np.load(checked(figure["case"]["arrays"]), allow_pickle=False) as a:
            arrays = dict(a)
        for panel in figure["panels"]:
            x, y, w, h = panel["xywh"]
            delivered = board[y : y + h, x : x + w]
            if delivered.shape != (160, 160, 3) or not figure["no_resize"]:
                raise ValueError("Expected unchanged native160 pixels")
            if "prediction" in panel:
                value = load_native(panel["prediction"])
                anchor = np.asarray(figure["anchor"]).reshape(1, 3, 1, 1)
                value = anchor + figure["contrast"] * (value.astype(np.float64) - anchor)
                expected = display_pixels(value, arrays, figure["ROI_xywh"], figure["exposure"])
                if panel["checkpoint"] != result["exports"][panel["state"]]:
                    raise ValueError("Different native panel checkpoint")
                candidate_channels += delivered.size
            else:
                sx, sy, sw, sh = panel["source_xywh"]
                original = np.asarray(Image.open(checked(panel["source_figure"])).convert("RGB"))
                expected = original[sy : sy + sh, sx : sx + sw]
                retained_channels += delivered.size
            np.testing.assert_array_equal(delivered, expected)
        target = images / source.name
        shutil.copyfile(source, target)
        if reference(target)["sha256"] != figure["image"]["sha256"]:
            raise ValueError("Native image copy changed bytes")
        records.append(dict(figure, image=reference(target), original_image=figure["image"]))
        boards.append(Image.fromarray(board))
    sheet_records = []
    for first in range(0, len(boards), 4):
        selected = boards[first : first + 4]
        sheet = Image.new(
            "RGB", (max(p.width for p in selected), sum(p.height for p in selected)), "white"
        )
        y = 0
        for p in selected:
            sheet.paste(p, (0, y))
            y += p.height
        target = sheets / f"sheet-{first // 4:02d}.png"
        sheet.save(target)
        sheet_records.append(
            {"image": reference(target), "indices": list(range(first, first + len(selected)))}
        )
    archives = []
    for source in [
        run / "result.json",
        run / "plan.json",
        run / "figures.json",
        run / "training-audit.json",
        *[checked(b) for b in result["scores"].values()],
    ]:
        name = source.name if source.parent == run else source.parent.name + "-" + source.name
        target = evidence / (name + ".gz")
        data = source.read_bytes()
        with target.open("xb") as f:
            f.write(gzip.compress(data, mtime=0))
        assert (
            hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest()
            == reference(source)["sha256"]
        )
        archives.append(
            {
                "original": reference(source),
                "archive": reference(target),
                "encoding": "gzip; original bytes preserved",
            }
        )
    write_json(images / "manifest.json", dict(figures, images=records, viewed=False))
    write_json(
        output / "stage.json",
        {
            "status": "native-pixels-audited-awaiting-actual-viewing",
            "result": result_binding,
            "archives": archives,
            "manifest": reference(images / "manifest.json"),
            "sheets": sheet_records,
            "candidate_RGB_channels_exact_to_saved_predictions": candidate_channels,
            "retained_RGB_channels_exact_to_source_panels": retained_channels,
            "native_boards": len(records),
            "native_triplets": sum(f["triplet"] for f in records),
            "viewed": False,
            "no_resize": True,
            "script": reference(__file__),
            "scope": "Actual delivered native pixels and exact archive copies. No new inference, noise or training. Staging does not establish quality or actual viewing; record inspection separately.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    stage(args.run.absolute(), args.output.absolute())
