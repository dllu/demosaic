"""Report matched quiet-RMS weak-detail recovery and native phase-drift crops."""

import argparse
from itertools import product
from pathlib import Path

import numpy as np
from report_fold_support_pooling import (
    ROI,
    evaluated,
    insert_camera_panels,
    measure,
    scale_at_budget,
)
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def make_camera_board(output, old, new):
    assert old["id"] == new["id"]
    a, b, w, h = old["ROI_xywh"]
    scene = old["source"]
    x, y, *_ = scene["query_box"]
    roi = np.s_[:, b - y : b - y + h, a - x : a - x + w]
    with np.load(checked(scene["query_arrays"])) as sensor:
        ctx = {k: sensor[k] for k in ("wb", "matrix")}
    with np.load(checked(new["prediction"])) as changed:
        pixels = changed["corrected"]
    with np.load(checked(old["crosscheck_prediction"])) as control:
        delta = pixels[roi].astype(np.float64) - control["corrected"][roi]
    rgb = display(pixels[None], ctx, exposure=old["display_exposure"])[0][roi]
    rendered = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
    keep = {"Noisy Malvar", "V120 EMA", "Cross-checked guide", "ISO100 AHD ref"}
    selected = [c for c in old["panels"] if c["label"] in keep or "JPEG" in c["label"]]
    image, panels = insert_camera_panels(
        output,
        old["id"],
        old | {"panels": selected},
        "Cross-checked guide",
        [("Phase drift", rendered)],
    )
    return old | {
        "comparison_source": old["image"],
        "image": image,
        "panels": panels,
        "drift_prediction": new["prediction"],
        "drift_fit": new["fit"],
        "change_DN16": float(np.sqrt(np.mean(delta**2)) * 65535),
    }


def aggregate(rows, plan):
    groups = []
    for setting, kind in product(plan["settings"], ("all", "spacing", "curved", "straight")):
        metrics = {}
        for arm in plan["arms"]:
            subset = [
                r["moments"]
                for r in rows
                if r["setting"] == setting
                and r["arm"] == arm
                and (kind == "all" or r["kind"] == kind)
            ]
            metrics[arm] = {k: np.mean([row[k] for row in subset], 0) for k in subset[0]}
        parent = evaluated(metrics["planar"], 0)
        fixed = {arm: evaluated(m, setting["scale"]) for arm, m in metrics.items()}
        budget = max(0, min(r["quiet_RMS_DN16"] for r in fixed.values()) - parent["quiet_RMS_DN16"])
        capped = {}
        for arm, m in metrics.items():
            scale = min(setting["scale"], scale_at_budget(m["quiet_mse"], budget))
            capped[arm] = evaluated(m, scale) | {"scale": scale}
        groups.append(
            {"setting": setting, "kind": kind, "parent": parent, "fixed": fixed, "matched": capped}
        )
    return groups


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    receipt = root / "output/collection.json"
    done = read_json(receipt)
    assert done["plan"] == reference(path)
    output = root / "review"
    output.mkdir()
    rows, boards = [], []
    for binding in done["synthetic"]:
        case = read_json(checked(binding))
        parent = np.load(checked(case["parent"])).astype(np.float64)
        with np.load(checked(case["target"])) as f:
            target, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        with np.load(checked(case["prediction"])) as stored:
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    case["profile"],
                    case["placement"],
                ):
                    continue
                t, scale = setting["threshold"], setting["scale"]
                predicted = {k: stored[f"{k}--t{t:g}"] for k in plan["arms"]}
                for arm, pixels in predicted.items():
                    fit = measure(parent, target, quiet, pixels)
                    rows.append(
                        {
                            "id": case["id"],
                            "kind": case["kind"],
                            "arm": arm,
                            "setting": setting,
                            "moments": {k: v.tolist() for k, v in fit.items()},
                            "fixed": evaluated(fit, scale),
                        }
                    )
                if (case["profile"], case["placement"], setting["budget_DN16"]) == (
                    "iso400",
                    "near",
                    0.02,
                ) and case["source"] in (80, 83):
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
                                *(p + scale * (f[2] - p) for f in predicted.values()),
                                target[2][ROI],
                            ],
                            ctx,
                            {"case_receipt": binding, "operating_point": setting},
                            labels=(
                                "Noisy Malvar",
                                "V143 EMA",
                                "Planar guide",
                                "Phase drift",
                                "Exact GT",
                            ),
                            triplet_indices=(0, 3, 4),
                        )
                    )
    old = read_json(checked(plan["camera_baseline"]))
    cameras = [
        make_camera_board(output, a, b) for a, b in zip(old["camera"], done["camera"], strict=True)
    ]
    assert len(rows) == 128 and len(boards) == 2 and len(cameras) == 8
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(receipt),
            "metrics": rows,
            "aggregates": aggregate(rows, plan),
            "boards": boards,
            "camera": cameras,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    report(parser.parse_args().path.resolve())
