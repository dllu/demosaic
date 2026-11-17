"""Compare fresh asymmetric RAW validation fits at frozen settings."""

import argparse
import os
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, measure
from report_phase_edge_side import near_edge_masks, side_metrics
from report_scene_wave_guides import native_board
from report_shared_phase_shape import color_metrics

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

LABELS = {
    "independent": "Independent waveform",
    "same-side": "Same-side validation",
    "bright-half": "Bright cross-edge 0.5",
    "bright-full": "Bright cross-edge 1.0",
}


def camera_boards(output, old_boards, new_rows):
    result = []
    for old, new in zip(old_boards, new_rows, strict=True):
        assert old["id"] == new["id"]
        scene = old["source"]
        x, y, w, h = old["ROI_xywh"]
        bx, by, *_ = scene["query_box"]
        crop = np.s_[:, y - by : y - by + h, x - bx : x - bx + w]
        with np.load(checked(scene["query_arrays"])) as raw:
            capture = {k: raw[k] for k in ("wb", "matrix")}
        additional, rms_changes = [], {}
        with (
            np.load(checked(old["edge_side_predictions"])) as controls,
            np.load(checked(new["prediction"])) as archive,
        ):
            for arm in ("bright-half", "bright-full"):
                rgb = display(archive[arm][None], capture, exposure=old["display_exposure"])[0][
                    crop
                ]
                additional.append(
                    (LABELS[arm], np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8))
                )
                d = archive[arm][crop].astype(np.float64) - controls["validation"][crop]
                rms_changes[arm] = float(np.sqrt(np.mean(d * d)) * 65535)
        image, panels = insert_camera_panels(
            output, new["id"], old, "Same-side validation", additional
        )
        result.append(
            {
                **old,
                "previous_image": old["image"],
                "image": image,
                "panels": panels,
                "asymmetric_prediction": new["prediction"],
                "change_from_same_side_RMS_DN16": rms_changes,
            }
        )
    return result


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    assert collection["plan"] == reference(path) and collection["synthetic_fits"] == 240
    previous = read_json(checked(plan["camera_controls"]))
    output = root / "review"
    output.mkdir()
    rows, boards = [], []
    for artifact in collection["synthetic"]:
        sample = read_json(checked(artifact))
        key = sample["id"]
        parent = np.load(checked(sample["parent"])).astype(np.float64)
        with np.load(checked(sample["target"])) as gt:
            truth, quiet = gt["target"].astype(np.float64), gt["quiet"][ROI]
        near = sample["placement"] == "near"
        masks = near_edge_masks(sample, truth.shape[-2:]) if near else ()
        with np.load(checked(sample["prediction"])) as images:
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    sample["profile"],
                    sample["placement"],
                ):
                    continue
                scale, t = setting["scale"], setting["threshold"]
                variants = {m: images[f"{m}--t{t:g}"] for m in LABELS}
                for label, prediction in variants.items():
                    moments = measure(parent, truth, quiet, prediction)
                    restored, base = evaluated(moments, scale), evaluated(moments, 0)
                    rows.append(
                        {
                            "source": sample["source"],
                            "id": key,
                            "CFA": sample["CFA"],
                            **setting,
                            "model": label,
                            **restored,
                            **color_metrics(parent[ROI], truth[ROI], prediction, scale),
                            **(
                                side_metrics(parent[ROI], truth[ROI], prediction, scale, masks)
                                if near
                                else {}
                            ),
                            "quiet_delta_DN16": restored["quiet_RMS_DN16"] - base["quiet_RMS_DN16"],
                        }
                    )
                if near and sample["source"] in (60, 61) and setting["budget_DN16"] == 0.02:
                    p = parent[2][ROI]
                    with np.load(checked(sample["sensor"])) as data:
                        ctx = {k: data[k][2:3] for k in ("colors", "wb", "matrix")}
                        ctx["packed"] = data["packed"][2:3, :, 64:192, 64:192]
                    boards.append(
                        native_board(
                            output,
                            key,
                            [
                                noisy_malvar(ctx)[0],
                                p,
                                *(p + scale * (img[2] - p) for img in variants.values()),
                                truth[2][ROI],
                            ],
                            ctx,
                            {"case": sample, "prediction": artifact, "operating_point": setting},
                            labels=("Noisy Malvar", "V143 EMA", *LABELS.values(), "Exact GT"),
                            triplet_indices=(0, 4, 6),
                        )
                    )
    assert len(rows) == 160 and len(boards) == 4
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
    print("160 fixed-setting rows and 12 native comparison boards", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
