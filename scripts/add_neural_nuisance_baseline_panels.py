"""Append saved baseline NN pixels to closed full-panel native boards, without inference."""

import argparse
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image, ImageDraw, ImageFont

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def render(current_review, baseline_review, output):
    current = read_json(current_review / "completed.json")
    baseline = read_json(baseline_review / "completed.json")
    same_collection = current["producer_collection"] == baseline["producer_collection"]
    if not same_collection:
        cross = read_json(checked(current["cross_study_comparison"]))
        assert cross["current_summary"] == current["summary"]
        assert cross["baseline_summary"] == baseline["summary"]
        assert cross["paired_input_cases_exact"] == 1164
    checked(current["native_independent_audit"])
    checked(baseline["native_independent_audit"])
    current_collection = read_json(checked(current["producer_collection"]))
    baseline_collection = read_json(checked(baseline["producer_collection"]))
    current_plan = read_json(checked(current_collection["plan"]))
    baseline_plan = read_json(checked(baseline_collection["plan"]))
    current_rows = {r["id"]: r for r in current_plan["rows"]}
    baseline_rows = {r["id"]: r for r in baseline_plan["rows"]}
    current_records = {r["id"]: r for r in current_collection["rows"]}
    baseline_records = {r["id"]: r for r in baseline_collection["rows"]}
    assert len(current_records) == len(baseline_records) == 1164
    original = read_json(checked(current["native_report"]))
    output.mkdir(exist_ok=False)
    figures, channels, preserved = [], 0, 0
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    for figure in original["figures"] + original["stress_figures"]:
        row = figure["source"]
        case = row["id"]
        old_row = baseline_rows[case]
        for key in ("arrays", "parent", "sample", "noise"):
            assert row[key] == current_rows[case][key] == old_row[key]
        for key in ("parent_values", "packed_values", "colors_values"):
            assert current_records[case][key] == baseline_records[case][key]
        sample = row["sample"]
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            data = {k: z[k][sample : sample + 1] for k in ("wb", "matrix")}
        binding = baseline_records[case]["predictions"]["local-t2"]
        value = np.load(checked(binding))[None]
        roi, exposure = figure["ROI_xywh"], figure["display_exposure"]
        assert figure["no_resize"] and figure.get("display_contrast", 1) == 1
        cell = crop(value, data, roi, exposure)
        assert cell.shape == (160, 160, 3)
        source = np.asarray(Image.open(checked(figure["image"])).convert("RGB"))
        if same_collection:
            # A self-join rehearsal must reproduce the already audited NN cell.
            panel = next(p for p in figure["panels"] if p["label"] == "Fixed proposal NN")
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(cell, source[y : y + h, x : x + w])
        h, w = source.shape[:2]
        x, y = w, 24
        canvas = Image.new("RGB", (w + 168, h), "#eeeeee")
        canvas.paste(Image.fromarray(source), (0, 0))
        canvas.paste(Image.fromarray(cell), (x, y))
        ImageDraw.Draw(canvas).text((x, 5), "Prior256 NN t2", font=font, fill="black")
        path = output / Path(figure["image"]["path"]).name
        canvas.save(path)
        encoded = np.asarray(Image.open(path))
        np.testing.assert_array_equal(encoded[:, :w], source)
        np.testing.assert_array_equal(encoded[y : y + 160, x : x + 160], cell)
        channels += cell.size
        preserved += source.size
        figures.append(
            {
                **figure,
                "image": reference(path),
                "original_current_board": figure["image"],
                "baseline_prediction": binding,
                "baseline_configuration": baseline_plan["model"],
                "baseline_panel": {"label": "Prior256 NN t2", "xywh": [x, y, 160, 160]},
                "panels": [
                    *figure["panels"],
                    {"label": "Prior256 NN t2", "xywh": [x, y, 160, 160]},
                ],
            }
        )
    assert len(figures) == 64 and "torch" not in sys.modules
    write_json(
        output / "report.json",
        {
            "script": reference(__file__),
            "current_completed": reference(current_review / "completed.json"),
            "baseline_completed": reference(baseline_review / "completed.json"),
            "figures": figures,
            "appended_RGB_channels_exact": channels,
            "original_RGB_channels_preserved_exact": preserved,
            "self_join_audited_NN_cells_exact": same_collection,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "scope": "Closed full panels only; identical actual inputs/parent/calibration/native160 ROI/exposure for baseline/current. Every original board pixel preserved and every appended baseline pixel reread exactly. Real ISO100/AHD references remain qualitative, never exact GT; no real-reference scoring or RAW decoding.",
        },
    )
    return output / "report.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current_review", type=Path)
    parser.add_argument("baseline_review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(
        render(args.current_review.resolve(), args.baseline_review.resolve(), args.output.resolve())
    )
