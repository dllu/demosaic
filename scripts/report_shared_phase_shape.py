"""Measure matched quiet, detail, and color errors for a shared waveform."""

import argparse
import os
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panel, measure
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def color_metrics(parent, reference_rgb, prediction, scale):
    clean = reference_rgb[2] - reference_rgb[1]
    repair = parent + scale * (prediction.astype(np.float64) - parent)
    increment = repair[2] - repair[1]
    projected = (increment * clean).sum(axis=(1, 2))
    expected = (clean * clean).sum(axis=(1, 2))
    error = increment - clean
    chroma = error - error.mean(axis=0, keepdims=True)
    return {
        "response_RGB": (projected / expected).tolist(),
        "centered_chroma_increment_RMS_DN16": float(np.sqrt(np.mean(chroma**2)) * 65535),
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
            context = {n: arrays[n] for n in ("wb", "matrix")}
        with (
            np.load(checked(old["guarded_prediction"])) as controls_npz,
            np.load(checked(new["predictions"])) as candidates_npz,
        ):
            shared = candidates_npz["shared"]
            previous = controls_npz["guard8"][crop].astype(np.float64)
            diff = shared[crop].astype(np.float64) - previous
        rgb = display(shared[None], context, exposure=old["display_exposure"])[0][crop]
        pixels = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        image, panels = insert_camera_panel(
            output, key, old, "Edge guard 8px", "Shared waveform", pixels
        )
        results.append(
            {
                **old,
                "previous_image": old["image"],
                "image": image,
                "panels": panels,
                "shared_prediction": new["predictions"],
                "shared_minus_independent_RMS_DN16": float(np.sqrt(np.mean(diff**2)) * 65535),
            }
        )
    return results


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    previous = read_json(checked(plan["previous_report"]))
    arm = plan["reference_arm"]
    assert collection["plan"] == reference(path) and collection["synthetic_fits"] == 96
    output = root / "review"
    output.mkdir()
    previous_rows = {
        (r["id"], r["method"], r["budget_DN16"]): r for r in previous["metrics"] if r["arm"] == arm
    }
    rows, boards = [], []
    for link in collection["synthetic"]:
        case = read_json(checked(link))
        original = read_json(checked(case["case"]))
        control = read_json(checked(case["control"]))
        key = original["id"]
        assert key == case["id"] == control["id"]
        context = np.load(checked(original["parent"])).astype(np.float64)
        parent = context[ROI]
        with np.load(checked(original["target"])) as f:
            truth, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        show = original["source"] in (40, 41) and original["placement"] == "far"
        with (
            np.load(checked(control["output"])) as baseline,
            np.load(checked(case["predictions"])) as candidate,
        ):
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    original["profile"],
                    original["placement"],
                ):
                    continue
                k = f"{setting['method']}-t{setting['threshold']:g}"
                frozen = previous_rows[key, setting["method"], setting["budget_DN16"]]
                both = {"independent": baseline[f"{arm}--{k}"], "shared": candidate[k]}
                for model, prediction in both.items():
                    values = measure(context, truth, quiet, prediction)
                    scale = setting["scale"]
                    metrics = evaluated(values, scale)
                    parent_metrics = evaluated(values, 0)
                    if model == "independent":
                        assert all(metrics[name] == frozen[name] for name in metrics)
                    rows.append(
                        {
                            "id": key,
                            "source": original["source"],
                            "CFA": original["CFA"],
                            **setting,
                            "model": model,
                            **metrics,
                            **color_metrics(parent, truth[ROI], prediction, scale),
                            "quiet_delta_DN16": metrics["quiet_RMS_DN16"]
                            - parent_metrics["quiet_RMS_DN16"],
                        }
                    )
                if (
                    show
                    and setting["method"] == "weighted-refit"
                    and setting["budget_DN16"] == 0.02
                ):
                    p = parent[2]
                    with np.load(checked(original["sensor"])) as sensor:
                        ctx = {n: sensor[n][2:3] for n in ("colors", "wb", "matrix")}
                        ctx["packed"] = sensor["packed"][2:3, :, 64:192, 64:192]
                    boards.append(
                        native_board(
                            output,
                            key,
                            [
                                noisy_malvar(ctx)[0],
                                p,
                                *(p + scale * (v[2] - p) for v in both.values()),
                                candidate["weighted-refit-t2"][2],
                                truth[2][ROI],
                            ],
                            ctx,
                            {"case": original, "predictions": link, "operating_point": setting},
                            labels=(
                                "Noisy Malvar",
                                "V143 EMA",
                                "Independent waveform",
                                "Shared waveform",
                                "Shared at threshold 2",
                                "Exact GT",
                            ),
                        )
                    )
    assert len(rows) == 256 and len(boards) == 4 and len(previous_rows) == 128
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(closed),
            "metrics": rows,
            "boards": boards,
            "camera": camera_boards(output, previous["camera"], collection["camera"]),
        },
    )
    print("256 fixed-setting rows, 128 matched controls and 12 camera/synthetic boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
