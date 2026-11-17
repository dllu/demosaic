"""Measure phase-guide cross-checks on the frozen nominal and stressed cohorts."""

import argparse
import os
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, measure
from report_fresh_phase_refit import donor_errors
from report_phase_edge_side import near_edge_masks, side_metrics
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def cameras(output, before, after):
    rows = []
    for old, new in zip(before, after, strict=True):
        key = old["id"]
        assert key == new["id"]
        a, b, w, h = old["ROI_xywh"]
        scene = old["source"]
        x, y, *_ = scene["query_box"]
        roi = np.s_[:, b - y : b - y + h, a - x : a - x + w]
        with np.load(checked(scene["query_arrays"])) as sensor:
            ctx = {k: sensor[k] for k in ("wb", "matrix")}
        with (
            np.load(checked(old["edge_side_predictions"])) as old_array,
            np.load(checked(new["prediction"])) as new_array,
        ):
            pixels = new_array["corrected"]
            delta = pixels[roi].astype(np.float64) - old_array["validation"][roi]
        rgb = display(pixels[None], ctx, exposure=old["display_exposure"])[0][roi]
        rendered = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        image, panels = insert_camera_panels(
            output, key, old, "Same-side validation", [("Cross-checked guide", rendered)]
        )
        rows.append(
            {
                **old,
                "previous_image": old["image"],
                "image": image,
                "panels": panels,
                "crosscheck_prediction": new["prediction"],
                "change_DN16": float(np.sqrt(np.mean(delta**2)) * 65535),
            }
        )
    return rows


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    receipt = root / "output/collection.json"
    done = read_json(receipt)
    assert done["plan"] == reference(path) and done["synthetic_fits"] == 96
    output = root / "review"
    output.mkdir()
    rows, boards, geometry = [], [], []
    for binding in done["synthetic"]:
        group = read_json(checked(binding))
        case = read_json(checked(group["case"]))
        control = read_json(checked(group["control"]["source"]))
        parent = np.load(checked(case["parent"])).astype(np.float64)
        with np.load(checked(case["target"])) as f:
            truth, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        near = case["placement"] == "near"
        masks = near_edge_masks(case, truth.shape[-2:]) if near else ()
        prefix = group["control_prefix"]
        source = case["source"]
        for role, (a, b) in enumerate(zip(control["fits"][prefix], group["fits"], strict=True)):
            for fold in (0, 1):
                geometry.append(
                    {
                        "id": case["id"],
                        "role": role,
                        "fold": fold,
                        "query": case["placement"],
                        "profile": case["profile"],
                        "prior_error": donor_errors(
                            {
                                "metadata": case["metadata"],
                                "frequencies": a["records"][0]["frequencies"][fold],
                            }
                        ),
                        "new_error": donor_errors(
                            {
                                "metadata": case["metadata"],
                                "frequencies": b["records"][0]["frequencies"][fold],
                            }
                        ),
                        "crosschecks": b["records"][0]["guide_crosschecks"][fold],
                    }
                )
        with (
            np.load(checked(group["prediction"])) as changed,
            np.load(checked(group["control_prediction"])) as baseline,
        ):
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    case["profile"],
                    case["placement"],
                ):
                    continue
                scale, t = setting["scale"], setting["threshold"]
                old_key = f"{prefix}--t{t:g}" if near else f"{prefix}--weighted-refit-t{t:g}"
                samples = {"guarded": baseline[old_key], "crosschecked": changed[f"t{t:g}"]}
                for arm, prediction in samples.items():
                    fit = measure(parent, truth, quiet, prediction)
                    scores = evaluated(fit, scale)
                    rows.append(
                        {
                            "id": case["id"],
                            "source": source,
                            "CFA": case["CFA"],
                            **setting,
                            "arm": arm,
                            **scores,
                            **(
                                side_metrics(parent[ROI], truth[ROI], prediction, scale, masks)
                                if near
                                else {}
                            ),
                            "quiet_delta_DN16": scores["quiet_RMS_DN16"]
                            - evaluated(fit, 0)["quiet_RMS_DN16"],
                            "moments": {k: v.tolist() for k, v in fit.items()},
                        }
                    )
                if near and source in (60, 61) and setting["budget_DN16"] == 0.02:
                    p = parent[2][ROI]
                    with np.load(checked(case["sensor"])) as f:
                        ctx = {k: f[k][2:3] for k in ("colors", "wb", "matrix")}
                        ctx["packed"] = f["packed"][2:3, :, 64:192, 64:192]
                    boards.append(
                        native_board(
                            output,
                            case["id"],
                            [
                                noisy_malvar(ctx)[0],
                                p,
                                *(p + scale * (f[2] - p) for f in samples.values()),
                                truth[2][ROI],
                            ],
                            ctx,
                            {"case": case, "prediction": binding, "operating_point": setting},
                            labels=(
                                "Noisy Malvar",
                                "V143 EMA",
                                "Guarded guide",
                                "Cross-checked guide",
                                "Exact GT",
                            ),
                            triplet_indices=(0, 3, 4),
                        )
                    )
    assert len(rows) == 128 and len(geometry) == 192 and len(boards) == 4
    old = read_json(checked(plan["camera_report"]))
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(receipt),
            "metrics": rows,
            "geometry": geometry,
            "boards": boards,
            "camera": cameras(output, old["camera"], done["camera"]),
        },
    )
    print("128 metrics, 192 fold records, 12 native boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(11)
    report(parser.parse_args().path.resolve())
