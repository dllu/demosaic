"""Compare side-specific evidence using frozen settings and native crops."""

import argparse
import os
from pathlib import Path

import numpy as np
from probe_phase_edge_side import ARMS
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, measure
from report_scene_wave_guides import native_board
from report_shared_phase_shape import color_metrics

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

LABELS = {"validation": "Same-side validation", "profiles": "Separate profiles"}


def near_edge_masks(source, shape):
    recipe = source["metadata"]["recipe"]
    y, x = np.indices(shape) + 0.5 - recipe["size"] / 2
    angle = recipe["edge_angle"]
    distance = x * np.cos(angle) + y * np.sin(angle) - recipe["edge_jitter"]
    distance = distance[ROI]
    return distance < -2, distance > 2, abs(distance) <= 8


def side_metrics(parent, truth, prediction, scale, masks):
    dark, bright, edge = masks
    restored = parent + scale * (prediction.astype(np.float64) - parent)
    weak = truth[2] - truth[1]
    estimate = restored[2] - restored[1]
    return {
        "dark_weak_gain": float(
            np.sum(estimate[:, dark] * weak[:, dark]) / np.sum(weak[:, dark] ** 2)
        ),
        "bright_weak_gain": float(
            np.sum(estimate[:, bright] * weak[:, bright]) / np.sum(weak[:, bright] ** 2)
        ),
        "no_wire_edge_RMS_DN16": float(
            np.sqrt(np.mean((restored[0, :, edge] - truth[0, :, edge]) ** 2)) * 65535
        ),
    }


def camera_boards(output, controls, candidates):
    results = []
    for old, new in zip(controls, candidates, strict=True):
        key = old["id"]
        assert key == new["id"]
        scene = old["source"]
        x, y, w, h = old["ROI_xywh"]
        bx, by, *_ = scene["query_box"]
        crop = np.s_[:, y - by : y - by + h, x - bx : x - bx + w]
        with np.load(checked(scene["query_arrays"])) as arrays:
            ctx = {n: arrays[n] for n in ("wb", "matrix")}
        additions, changes = [], {}
        with (
            np.load(checked(old["guarded_prediction"])) as a,
            np.load(checked(new["predictions"])) as b,
        ):
            for arm in ARMS:
                rgb = display(b[arm][None], ctx, exposure=old["display_exposure"])[0][crop]
                additions.append(
                    (LABELS[arm], np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8))
                )
                diff = b[arm][crop].astype(np.float64) - a["guard8"][crop]
                changes[arm] = float(np.sqrt(np.mean(diff**2)) * 65535)
        image, panels = insert_camera_panels(output, key, old, "Edge guard 8px", additions)
        results.append(
            {
                **old,
                "previous_image": old["image"],
                "image": image,
                "panels": panels,
                "edge_side_predictions": new["predictions"],
                "change_from_independent_RMS_DN16": changes,
            }
        )
    return results


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    controls = read_json(checked(plan["guard_report"]))
    prefix = plan["reference_arm"]
    assert collection["plan"] == reference(path) and collection["synthetic_calls"] == 192
    target = root / "review"
    target.mkdir()
    known = {
        (r["id"], r["method"], r["budget_DN16"]): r
        for r in controls["metrics"]
        if r["arm"] == prefix
    }
    rows, figures = [], []
    for link in collection["synthetic"]:
        run = read_json(checked(link))
        source = read_json(checked(run["case"]))
        before = read_json(checked(run["control"]))
        key = source["id"]
        assert key == run["id"] == before["id"]
        parent = np.load(checked(source["parent"])).astype(np.float64)
        with np.load(checked(source["target"])) as f:
            truth, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        near = source["placement"] == "near"
        masks = near_edge_masks(source, truth.shape[-2:]) if near else ()
        show = source["source"] in (40, 41) and source["placement"] == "near"
        with (
            np.load(checked(before["output"])) as baseline,
            np.load(checked(run["predictions"])) as candidates,
        ):
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    source["profile"],
                    source["placement"],
                ):
                    continue
                suffix = f"{setting['method']}-t{setting['threshold']:g}"
                baseline_row = known[key, setting["method"], setting["budget_DN16"]]
                images = {
                    "independent": baseline[f"{prefix}--{suffix}"],
                    **{arm: candidates[f"{arm}--{suffix}"] for arm in ARMS},
                }
                scale = setting["scale"]
                for label, value in images.items():
                    moments = measure(parent, truth, quiet, value)
                    metrics, base = evaluated(moments, scale), evaluated(moments, 0)
                    if label == "independent":
                        assert all(metrics[m] == baseline_row[m] for m in metrics)
                    rows.append(
                        {
                            "id": key,
                            "source": source["source"],
                            "CFA": source["CFA"],
                            **setting,
                            "model": label,
                            **metrics,
                            **color_metrics(parent[ROI], truth[ROI], value, scale),
                            **(
                                side_metrics(parent[ROI], truth[ROI], value, scale, masks)
                                if near
                                else {}
                            ),
                            "quiet_delta_DN16": metrics["quiet_RMS_DN16"] - base["quiet_RMS_DN16"],
                        }
                    )
                if (
                    show
                    and setting["method"] == "weighted-refit"
                    and setting["budget_DN16"] == 0.02
                ):
                    p = parent[2][ROI]
                    with np.load(checked(source["sensor"])) as data:
                        ctx = {n: data[n][2:3] for n in ("colors", "wb", "matrix")}
                        ctx["packed"] = data["packed"][2:3, :, 64:192, 64:192]
                    figures.append(
                        native_board(
                            target,
                            key,
                            [
                                noisy_malvar(ctx)[0],
                                p,
                                *(p + scale * (img[2] - p) for img in images.values()),
                                truth[2][ROI],
                            ],
                            ctx,
                            {"case": source, "predictions": link, "operating_point": setting},
                            triplet_indices=(0, 4, 5),
                            labels=(
                                "Noisy Malvar",
                                "V143 EMA",
                                "Independent waveform",
                                LABELS["validation"],
                                LABELS["profiles"],
                                "Exact GT",
                            ),
                        )
                    )
    assert len(rows) == 384 and len(known) == 128 and len(figures) == 4
    write_json(
        target / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(closed),
            "metrics": rows,
            "boards": figures,
            "camera": camera_boards(target, controls["camera"], collection["camera"]),
        },
    )
    print("384 paired rows and 12 native boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
