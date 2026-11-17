"""NumPy-only faithful-detail metrics and native boards for a retained scaling review."""

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np
from analyze_retained_faint_detail import original_source_strata
from PIL import Image, ImageDraw
from report_checkpoint_pilot import pixels, statistics

from demosaic.archive_metrics import color, linear_rgb, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report(root):
    if "torch" in sys.modules or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Saved-output statistics/rendering require NumPy only and hidden CUDA")
    root = Path(root).resolve()
    plan = read_json(root / "plan.json")
    collection = read_json(root / "collection/result.json")
    assert collection["plan"] == reference(root / "plan.json")
    assert len(collection["records"]) == len(plan["observations"]) == 110
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    output = root / "report"
    output.mkdir()
    records = {read_json(checked(b))["id"]: read_json(checked(b)) for b in collection["records"]}
    defaults = {"V120": "V120 EMA", "scale-control10k": "Corpus10k EMA"}
    labels = {key: spec.get("display_label", defaults.get(key, key))
              for key, spec in plan["models"].items()}
    parent = plan.get("parent_label", "V120")
    triplet_model = plan.get("triplet_model", "scale-control10k")
    assert parent in labels and triplet_model in labels
    triplet_column = list(labels).index(triplet_model) + 1
    reference_column = len(labels) + 1
    metric_rows, strata_rows, color_rows, boards, triplets = [], [], [], [], []

    def board(key, cells, metadata):
        rectangles, image = [], Image.new("RGB", (8 + 168 * len(cells), 192), "#eeeeee")
        draw = ImageDraw.Draw(image)
        for i, (label, cell) in enumerate(cells):
            assert cell.shape == (160, 160, 3) and cell.dtype == np.uint8
            x = 8 + 168 * i
            draw.text((x, 5), label, fill="black")
            image.paste(Image.fromarray(cell), (x, 24))
            rectangles.append({"label": label, "png_xywh": [x, 24, 160, 160]})
        path = output / (key + ".png")
        image.save(path)
        reread = np.asarray(Image.open(path))
        for panel, (_, cell) in zip(rectangles, cells, strict=True):
            x, y, w, h = panel["png_xywh"]
            np.testing.assert_array_equal(reread[y:y+h, x:x+w], cell)
        info = {"id": key, "image": reference(path), "panels": rectangles, **metadata}
        write_json(path.with_suffix(".json"), info)
        return info

    for observation in plan["observations"]:
        with np.load(checked(observation["arrays"]), allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        prediction = {v["label"]: np.load(checked(v["prediction"]), allow_pickle=False)
                      for v in records[observation["id"]]["variants"]}
        kind, exposure = observation["kind"], observation["display_exposure"]
        material = kind in {"material", "shadow-material"}
        target, faint = None, False
        if material or kind == "color-spot-check":
            with np.load(checked(observation["target"]), allow_pickle=False) as data:
                target = data["target"]
            assert all(target.shape == value.shape for value in prediction.values())
        if material:
            faint = "contrast0p025-adc" in observation["case_id"]
            group = "faint-ADC" if faint else "shadows" if kind == "shadow-material" else "ordinary"
            for label, value in prediction.items():
                measured = statistics(value.astype(np.float64) * exposure, target.astype(np.float64) * exposure, arrays)
                metric_rows.append({"id": observation["id"], "source_id": observation["source_id"],
                                    "case": observation["case_id"], "group": group, "method": label,
                                    "pattern": observation["pattern"], "reference_role": observation["reference_role"],
                                    **measured})
                if faint:
                    with np.load(checked(observation["case"]["original_target"]), allow_pickle=False) as data:
                        original = data["target"]
                    strata_rows.extend({"id": observation["id"], "source_id": observation["source_id"],
                                        "source_case": observation["original_case_id"], "method": label,
                                        "pattern": observation["pattern"], **r}
                                       for r in original_source_strata(original, value, target, arrays))
        if kind == "color-spot-check":
            for label, value in prediction.items():
                measured = color(value, arrays)
                color_rows.append({"id": observation["id"], "case": observation["case_id"],
                                   "pattern": observation["pattern"], "method": label,
                                   "maximum_absolute_mean_error_DN16": 65535 * max(abs(v) for v in measured["camera_RGB_mean_error"]),
                                   "centered_RGB_RMS_DN16": 65535 * measured["spatially_centered_camera_RGB_RMS"],
                                   **measured})
        selected = not material or observation["pattern"] == "RGGB"
        if kind == "shadow-material":
            selected &= observation["camera_target_gain"] == 1/32 and observation["noise"]["name"] == "iso12800-prior"
        if kind == "color-spot-check":
            selected &= observation["pattern"] == ("BGGR" if observation["case_id"].startswith("h030") else "RGGB")
        if not selected:
            continue
        metadata = {"observation_id": observation["id"], "input_arrays": observation["arrays"],
                    "input_fingerprints": observation["input_fingerprints"], "noise": observation["noise"],
                    "display_exposure": exposure, "models": plan["models"],
                    "weights": {k: v.get("weights", "EMA") for k, v in plan["models"].items()}, "no_resize": True,
                    "reference_role": observation["reference_role"], "source_id": observation.get("source_id"),
                    "source_case": observation.get("case"), "actual_retained_noise_draw": 0,
                    "selection": "Fixed RGGB ordinary/faint and deepest ISO12800 shadows; all standing GFX regions/profiles/ROIs/JPEGs; prior failure hue BGGR and neutral RGGB. No selection from current outcomes."}
        if material or kind == "color-spot-check":
            roi = observation["ROI_xywh"]
            exact = kind == "color-spot-check" or observation.get("original_case_id", observation["case_id"]) in {"bark", "raccoon-fur"}
            reference_label = "Exact synthetic GT" if exact else "Binned ref, not GT"
            values = [("Noisy Malvar", noisy_malvar(arrays)),
                      *[(labels[k], prediction[k]) for k in labels], (reference_label, target)]
            cells = [(name, pixels(v, arrays, roi, exposure)) for name, v in values]
            metadata.update(ROI_xywh=roi, target=observation["target"])
            boards.append(board(observation["id"], cells, metadata))
            triplets.append(board(observation["id"] + "-triplet", [cells[i] for i in [0, triplet_column, reference_column]], metadata))
            if faint:
                x, y, w, h = roi
                anchor = (linear_rgb(target.astype(np.float64), arrays) * exposure)[..., y:y+h, x:x+w].mean((-2,-1), keepdims=True)
                enhanced, clipping = [], []
                for name, value in values:
                    mapped = 0.18 + 20 * (linear_rgb(value.astype(np.float64), arrays) * exposure - anchor)
                    region = mapped[0, :, y:y+h, x:x+w]
                    clipping.append({"label": name, "fraction_channels_clipped": float(np.mean((region < 0) | (region > 1)))})
                    v = region.clip(0, 1)
                    srgb = np.where(v <= .0031308, 12.92*v, 1.055*v**(1/2.4)-.055)
                    enhanced.append((name, np.rint(srgb.transpose(1,2,0)*255).astype(np.uint8)))
                boards.append(board(observation["id"] + "-contrast20", enhanced,
                                    {**metadata, "display_transform": "sRGB(clip(0.18 +20*(exposure*linearRGB -shared target ROI channel mean),0,1))",
                                     "linear_anchor": anchor.tolist(), "clipping": clipping,
                                     "target_usage": "Display anchor only; target never enters inference."}))
        elif kind == "gfx":
            roi = observation["ROI_xywh"]
            target = np.load(checked(observation["target"]), allow_pickle=False)
            cells = [("Noisy Malvar", pixels(noisy_malvar(arrays), arrays, roi, exposure)),
                     *[(labels[k], pixels(prediction[k], arrays, roi, exposure)) for k in labels],
                     ("ISO100 ref, not GT", pixels(target, arrays, [0,0,160,160], exposure))]
            metadata.update(ROI_xywh=roi, source_ROIs=observation["metadata"]["region"], target=observation["target"])
            boards.append(board(observation["id"], cells, metadata))
            triplets.append(board(observation["id"] + "-triplet", [cells[i] for i in [0,triplet_column,reference_column]], metadata))
        else:
            assert kind == "mesh"
            for case in observation["cases"]:
                roi = case["ROI_xywh"]
                cells = [("Noisy Malvar", pixels(arrays["noisy_rgb"], arrays, roi, exposure)),
                         *[(labels[k], pixels(prediction[k], arrays, roi, exposure)) for k in labels],
                         ("ISO100 ref, not GT", pixels(arrays["reference_rgb"], arrays, roi, exposure))]
                for key, label in [("noisy_camera_jpeg", "SOOC ISO6400 JPEG"), ("reference_camera_jpeg", "SOOC ISO100 JPEG")]:
                    value = np.load(checked(case["camera_JPEGs"][key]["pixels"]), allow_pickle=False)
                    assert value.shape == (160,160,3) and value.dtype == np.uint8
                    cells.append((label, value))
                specific = {**metadata, "case": case, "ROI_xywh": roi}
                key = observation["id"] + "-" + case["name"]
                boards.append(board(key, cells, specific))
                triplets.append(board(key + "-triplet", [cells[i] for i in [0,triplet_column,reference_column]], specific))
    assert len(metric_rows) == 96*len(labels) and len(color_rows) == 8*len(labels) and len(boards) == 26 and len(triplets) == 22
    means = {}
    for group in ["ordinary", "shadows", "faint-ADC"]:
        for label in labels:
            rows = [r for r in metric_rows if r["group"] == group and r["method"] == label]
            means[group + "|" + label] = {name: float(np.mean([r[name] for r in rows])) for name in ["sRGB_PSNR", "camera_RGB_PSNR"]}
    paired = []
    for group in ["ordinary", "shadows", "faint-ADC"]:
        for source in sorted({r["source_id"] for r in metric_rows}):
            values = {label: [r for r in metric_rows if r["group"] == group and r["source_id"] == source and r["method"] == label] for label in labels}
            for label in labels:
                if label != parent:
                    paired.append({"group": group, "source_id": source, "candidate": label, "parent": parent,
                                   "candidate_minus_parent_sRGB_dB": float(np.mean([r["sRGB_PSNR"] for r in values[label]])) - float(np.mean([r["sRGB_PSNR"] for r in values[parent]]))})
    table = output / "metrics.csv"
    with table.open("x", newline="") as stream:
        fields = ["id", "source_id", "case", "group", "method", "pattern", "camera_RGB_PSNR", "sRGB_PSNR", "reference_role"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in metric_rows)
    write_json(output / "result.json", {"producer": reference(__file__), "plan": reference(root / "plan.json"),
               "collection": reference(root / "collection/result.json"), "metrics": metric_rows,
               "condition_means": means, "paired_source_differences": paired, "original_source_faint_strata": strata_rows,
               "ADC_color_spot_checks": color_rows, "boards": boards, "triplets": triplets,
               "metrics_csv": reference(table), "actual_viewing": "pending",
               "scope": "All96 retained material inputs/four sources/all4 CFAs, one actual draw each, plus8 preselected ADC colors. Original160-ROI NumPy64 statistics with shared exposure compensation; no new primary427/camera score.26 prospectively selected native boards/22 triplets, all PNG cells reread exact; faint contrast20 uses target only as shared display anchor. Private GFX and binned low-noise PIXLS references are not exact GT. No neural/GPU/RAW/noise/optimizer work; actual native viewing separate."})
    print("Report complete", len(metric_rows), "material rows", len(boards), "native boards")
    print(means)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    report(parser.parse_args().root)
