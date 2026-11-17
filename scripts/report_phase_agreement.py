"""Score agreement-weighted delivery and compare it to the retained pooled arm."""

import argparse
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panel, matched_quiet, measure
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def report_synthetic(plan, collection, prior, output):
    rows = [
        {**r, "method": "pooled-t0" if r["method"] == "minimum-t0" else r["method"]}
        for r in prior["fixed_threshold_metrics"]
        if r["method"].startswith("pooled-") or r["method"] == "minimum-t0"
    ]
    assert len(rows) == 128 * len(plan["thresholds"])
    boards = []
    methods = [f"agreement-t{t:g}" for t in plan["thresholds"]]
    for group, observed in zip(plan["groups"], collection["synthetic"], strict=True):
        assert group["id"] == observed["id"]
        with np.load(checked(group["arrays"])) as arrays:
            truth = arrays["target"].astype(np.float64)
            quiet = arrays["quiet"][ROI]
            context = {key: arrays[key][2:3] for key in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
        parent = np.load(checked(group["parent"])).astype(np.float64)
        variants = defaultdict(list)
        for i, view in enumerate(observed["rows"]):
            assert view["role"] == i
            with (
                np.load(checked(view["prediction"])) as new,
                np.load(checked(view["adopted_prediction"])) as old,
            ):
                assert set(new.files) == {*methods, "pooled-t2"}
                np.testing.assert_array_equal(new["pooled-t2"], old["pooled-t2"])
                for method in new.files:
                    variants[method].append(new[method])
        fields = {key: group[key] for key in ("id", "profile", "source", "placement", "CFA")}
        for method in methods:
            moments = measure(parent, truth, quiet, np.stack(variants[method]))
            rows.append(
                {
                    **fields,
                    "method": method,
                    "moments": {key: v.tolist() for key, v in moments.items()},
                    **evaluated(moments, 1),
                }
            )
        if (
            group["profile"] == "iso400"
            and group["CFA"] == "RGGB"
            and group["placement"] == "far"
            and group["source"] in (0, 1)
        ):
            values = [
                noisy_malvar(context)[0],
                parent[2][ROI],
                variants["pooled-t2"][2],
                variants["agreement-t2"][2],
                truth[2][ROI],
            ]
            boards.append(
                native_board(
                    output,
                    group["id"],
                    values,
                    context,
                    {"group": group, "role": 2, "threshold": 2},
                    labels=(
                        "Noisy Malvar",
                        "V143 EMA",
                        "Pooled folds",
                        "Phase agreement",
                        "Exact GT",
                    ),
                    triplet_indices=(0, 3, 4),
                )
            )
    assert len(rows) == 2 * 128 * len(plan["thresholds"]) and len(boards) == 2
    return rows, boards


def report_camera(plan, collection, prior, output):
    originals = {row["id"]: row for row in prior["camera_boards"]}
    boards = []
    for row, result in zip(plan["camera_cases"], collection["camera"], strict=True):
        key = row["id"]
        assert key == result["id"]
        old = originals[key]
        with np.load(checked(row["query_arrays"])) as arrays:
            calibration = {k: arrays[k] for k in ("wb", "matrix")}
        x, y, w, h = old["ROI_xywh"]
        ox, oy = row["query_box"][:2]
        crop = np.s_[:, y - oy : y - oy + h, x - ox : x - ox + w]
        with (
            np.load(checked(result["prediction"])) as new,
            np.load(checked(result["adopted_prediction"])) as control,
        ):
            np.testing.assert_array_equal(new["pooled-t2"], control["pooled-t2"])
            value = new["agreement-t2"]
            correction = value[crop].astype(np.float64) - new["pooled-t2"][crop]
        rgb = display(value[None], calibration, exposure=old["display_exposure"])[0][crop]
        pixels = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        image, panels = insert_camera_panel(
            output, key, old, "Pooled folds", "Phase agreement", pixels
        )
        boards.append(
            {
                "id": key,
                "image": image,
                "prior_board": old["image"],
                "panels": panels,
                "ROI_xywh": old["ROI_xywh"],
                "display_exposure": old["display_exposure"],
                "prediction": result["prediction"],
                "source": row,
                "agreement_minus_pooled_RMS_DN16": float(np.sqrt(np.mean(correction**2)) * 65535),
            }
        )
    assert len(boards) == 8
    return boards


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    collection_path = root / "output/collection.json"
    collection = read_json(collection_path)
    prior = read_json(checked(plan["adopted_report"]))
    assert collection["plan"] == reference(path) and collection["query_roles"] == 384
    output = root / "review"
    output.mkdir()
    rows, boards = report_synthetic(plan, collection, prior, output)
    paired = matched_quiet(
        rows,
        plan["thresholds"],
        plan["positive_quiet_RMS_budgets_DN16"],
        methods=("pooled", "agreement"),
        shared_zero=None,
    )
    assert len(paired) == 192
    adopted = [r for r in prior["leave_one_geometry_out"] if r["method"] == "pooled"]
    assert [r for r in paired if r["method"] == "pooled"] == adopted
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(collection_path),
            "fixed_threshold_metrics": rows,
            "leave_one_geometry_out": paired,
            "synthetic_boards": boards,
            "camera_boards": report_camera(plan, collection, prior, output),
            "pooled_control_outputs_bitexact": 392,
            "adopted_calibration_rows_exact": len(adopted),
            "scope": "Fixed threshold analysis and quiet budgets matched on seven calibration sources;"
            " the held-out geometry supplies no fit/threshold/scale inputs. GFX at fixed t2.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
