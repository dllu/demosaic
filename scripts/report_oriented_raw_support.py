"""Score three fixed support footprints and render native comparisons."""

import argparse
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, matched_quiet, measure
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

LABELS = {"square": "Square", "along": "Along wire", "across": "Across wire"}


def report_synthetic(plan, collection, prior, saved, output, labels):
    rows = [
        {**row, "method": row["method"].replace("subharmonic-", "square-")}
        for row in prior["fixed_threshold_metrics"]
        if row["method"].startswith("subharmonic-")
    ]
    thresholds = plan["thresholds"]
    assert len(rows) == 128 * len(thresholds)
    boards = []
    methods = [f"{mode}-t{t:g}" for mode in labels if mode != "square" for t in thresholds]
    for group, observed, before in zip(
        plan["groups"], collection["synthetic"], saved["synthetic"], strict=True
    ):
        assert group["id"] == observed["id"] == before["id"]
        with np.load(checked(group["arrays"])) as arrays:
            truth = arrays["target"].astype(np.float64)
            quiet = arrays["quiet"][ROI]
            context = {key: arrays[key][2:3] for key in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
        parent = np.load(checked(group["parent"])).astype(np.float64)
        variants = defaultdict(list)
        old_name = "subharmonic-t2" if before["changed"] else "pooled-t2"
        for i, view in enumerate(observed["rows"]):
            assert (
                view["role"] == i and view["adopted_prediction"] == before["rows"][i]["prediction"]
            )
            with (
                np.load(checked(view["prediction"])) as new,
                np.load(checked(view["adopted_prediction"])) as old,
            ):
                assert set(new.files) == {*methods, "square-t2"}
                np.testing.assert_array_equal(new["square-t2"], old[old_name])
                for method in new.files:
                    variants[method].append(new[method])
        fields = {k: group[k] for k in ("id", "profile", "source", "placement", "CFA")}
        for method in methods:
            moments = measure(parent, truth, quiet, np.stack(variants[method]))
            rows.append(
                {
                    **fields,
                    "method": method,
                    "moments": {k: v.tolist() for k, v in moments.items()},
                    **evaluated(moments, 1),
                }
            )
        if group["CFA"] == "RGGB" and group["placement"] == "far" and group["source"] in (0, 1):
            values = [
                noisy_malvar(context)[0],
                parent[2][ROI],
                *[variants[f"{mode}-t2"][2] for mode in labels],
                truth[2][ROI],
            ]
            boards.append(
                native_board(
                    output,
                    group["id"],
                    values,
                    context,
                    {"group": group, "role": 2, "threshold": 2},
                    labels=("Noisy Malvar", "V143 EMA", *labels.values(), "Exact GT"),
                    triplet_indices=(0, 3, 5),
                )
            )
    assert len(boards) == 4 and len(rows) == 3 * 128 * len(thresholds)
    return rows, boards


def report_camera(plan, collection, prior, saved, output, labels):
    originals = {row["id"]: row for row in prior["camera_boards"]}
    boards = []
    for case, result, before in zip(
        plan["camera_cases"], collection["camera"], saved["camera"], strict=True
    ):
        key = case["id"]
        assert key == result["id"] == before["id"]
        assert result["adopted_prediction"] == before["prediction"]
        old = originals[key]
        with np.load(checked(case["query_arrays"])) as data:
            cal = {k: data[k] for k in ("wb", "matrix")}
        x, y, w, h = old["ROI_xywh"]
        ox, oy = case["query_box"][:2]
        crop = np.s_[:, y - oy : y - oy + h, x - ox : x - ox + w]
        addition, changes = [], {}
        with (
            np.load(checked(result["prediction"])) as data,
            np.load(checked(before["prediction"])) as control,
        ):
            square = data["square-t2"]
            old_name = "subharmonic-t2" if before["changed"] else "pooled-t2"
            np.testing.assert_array_equal(square, control[old_name])
            for method, label in labels.items():
                if method == "square":
                    continue
                value = data[f"{method}-t2"]
                rgb = display(value[None], cal, exposure=old["display_exposure"])[0][crop]
                addition.append((label, np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)))
                changes[method] = float(
                    np.sqrt(np.mean((value[crop].astype(np.float64) - square[crop]) ** 2)) * 65535
                )
        image, panels = insert_camera_panels(output, key, old, "Subharmonic test", addition)
        boards.append(
            {
                "id": key,
                "image": image,
                "prior_board": old["image"],
                "panels": panels,
                "ROI_xywh": old["ROI_xywh"],
                "display_exposure": old["display_exposure"],
                "source": case,
                "prediction": result["prediction"],
                "change_from_square_RMS_DN16": changes,
            }
        )
    assert len(boards) == 8
    return boards


def report(path, *, labels=LABELS, driver=__file__):
    plan = read_json(path)
    assert len(labels) == 3 and next(iter(labels)) == "square"
    assert plan["frozen_files"][str(Path(driver))] == reference(driver)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    prior = read_json(checked(plan["adopted_report"]))
    saved = read_json(checked(plan["adopted_collection"]))
    assert collection["plan"] == reference(path) and collection["query_roles"] == 384
    output = root / "review"
    output.mkdir()
    rows, boards = report_synthetic(plan, collection, prior, saved, output, labels)
    matched = matched_quiet(
        rows,
        plan["thresholds"],
        plan["positive_quiet_RMS_budgets_DN16"],
        methods=tuple(labels),
        shared_zero=None,
    )
    assert len(matched) == 288
    assert [r for r in matched if r["method"] == "square"] == [
        {**r, "method": "square"}
        for r in prior["leave_one_geometry_out"]
        if r["method"] == "subharmonic"
    ]
    write_json(
        output / "result.json",
        {
            "driver": reference(driver),
            "plan": reference(path),
            "collection": reference(closed),
            "fixed_threshold_metrics": rows,
            "leave_one_geometry_out": matched,
            "synthetic_boards": boards,
            "camera_boards": report_camera(plan, collection, prior, saved, output, labels),
            "square_t2_controls_bitexact": 392,
            "square_heldout_rows_exact": 96,
            "scope": "Support variants evaluated on actual CFA samples. Matched-budget calibration excludes the"
            " test geometry. Real-camera comparisons use fixed t2 and qualitative references.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
