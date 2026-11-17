"""Evaluate donor frequency coverage and the delivered query correction."""

import argparse
import os
from collections import defaultdict
from itertools import permutations
from pathlib import Path

import numpy as np
from report_fold_support_pooling import ROI, evaluated, insert_camera_panel, matched_quiet, measure
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def coverage(assessment):
    plan = read_json(checked(assessment["synthetic_plan"]))
    rows = []
    for key, value in assessment["synthetic"].items():
        recipe = plan["donors"][key]["simulation"]["recipe"]
        truth = np.array(
            [
                (np.cos(a) / p, np.sin(a) / p)
                for a, p in zip(recipe["wire_angles"], recipe["periods"], strict=True)
            ]
        )
        row = {"guide": key, "accepted": value["accepted"]}
        for method in ("existing", "revised"):
            fits = np.array(value[method])
            delta = (
                np.minimum(
                    np.linalg.norm(truth[:, None] - fits, axis=-1),
                    np.linalg.norm(truth[:, None] + fits, axis=-1),
                )
                * 256
            )
            order = min(permutations(range(2)), key=lambda v: delta[0, v[0]] + delta[1, v[1]])
            row[f"{method}_distances_bins"] = [float(delta[i, j]) for i, j in enumerate(order)]
        rows.append(row)
    assert len(rows) == 16
    return rows


def report_synthetic(plan, collection, prior, saved, output):
    old_rows = {
        (r["id"], "pooled-t0" if r["method"] == "minimum-t0" else r["method"]): {
            **r,
            "method": "pooled-t0" if r["method"] == "minimum-t0" else r["method"],
        }
        for r in prior["fixed_threshold_metrics"]
        if r["method"].startswith("pooled-") or r["method"] == "minimum-t0"
    }
    rows, boards = list(old_rows.values()), []
    thresholds = plan["thresholds"]
    for group, current, control in zip(
        plan["groups"], collection["synthetic"], saved["synthetic"], strict=True
    ):
        key = group["id"]
        assert key == current["id"] == control["id"]
        if not current["changed"]:
            assert current["rows"] == control["rows"]
            rows.extend(
                {
                    **old_rows[key, f"pooled-t{t:g}"],
                    "method": f"subharmonic-t{t:g}",
                }
                for t in thresholds
            )
            continue
        with np.load(checked(group["arrays"])) as arrays:
            truth = arrays["target"].astype(np.float64)
            quiet = arrays["quiet"][ROI]
            context = {v: arrays[v][2:3] for v in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
        parent = np.load(checked(group["parent"])).astype(np.float64)
        variants = defaultdict(list)
        for i, view in enumerate(current["rows"]):
            assert view["role"] == i
            with np.load(checked(view["prediction"])) as new:
                assert set(new.files) == {f"subharmonic-t{t:g}" for t in thresholds}
                for method in new.files:
                    variants[method].append(new[method])
        info = {v: group[v] for v in ("id", "profile", "source", "placement", "CFA")}
        for method, values in variants.items():
            moments = measure(parent, truth, quiet, np.stack(values))
            rows.append(
                {
                    **info,
                    "method": method,
                    "moments": {v: w.tolist() for v, w in moments.items()},
                    **evaluated(moments, 1.0),
                }
            )
        if group["CFA"] == "RGGB":
            with np.load(checked(control["rows"][2]["prediction"])) as data:
                pooled = data["pooled-t2"]
            values = [
                noisy_malvar(context)[0],
                parent[2][ROI],
                pooled,
                variants["subharmonic-t2"][2],
                truth[2][ROI],
            ]
            boards.append(
                native_board(
                    output,
                    key,
                    values,
                    context,
                    {
                        "group": group,
                        "role": 2,
                        "threshold": 2,
                        "applied_guide": current["guide"]["revised"],
                    },
                    labels=(
                        "Noisy Malvar",
                        "V143 EMA",
                        "Existing guide",
                        "Subharmonic test",
                        "Exact GT",
                    ),
                    triplet_indices=(0, 3, 4),
                )
            )
    assert len(rows) == 2 * 128 * len(thresholds)
    return rows, boards


def report_camera(plan, collection, prior, saved, output):
    baseline = {r["id"]: r for r in prior["camera_boards"]}
    boards = []
    for case, result, before in zip(
        plan["camera_cases"], collection["camera"], saved["camera"], strict=True
    ):
        key = case["id"]
        assert key == result["id"] == before["id"]
        old = baseline[key]
        x, y, w, h = old["ROI_xywh"]
        ox, oy = case["query_box"][:2]
        crop = np.s_[:, y - oy : y - oy + h, x - ox : x - ox + w]
        if not result["changed"]:
            assert result["prediction"] == before["prediction"]
        with (
            np.load(checked(result["prediction"])) as a,
            np.load(checked(before["prediction"])) as b,
        ):
            restored = a["subharmonic-t2" if result["changed"] else "pooled-t2"]
            difference = restored[crop].astype(np.float64) - b["pooled-t2"][crop]
        with np.load(checked(case["query_arrays"])) as data:
            context = {k: data[k] for k in ("wb", "matrix")}
        rgb = display(restored[None], context, exposure=old["display_exposure"])[0][crop]
        pixels = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        image, panels = insert_camera_panel(
            output, key, old, "Pooled folds", "Subharmonic test", pixels
        )
        boards.append(
            {
                "id": key,
                "image": image,
                "panels": panels,
                "ROI_xywh": old["ROI_xywh"],
                "display_exposure": old["display_exposure"],
                "prior_board": old["image"],
                "source": case,
                "prediction": result["prediction"],
                "guide_changed": result["changed"],
                "difference_from_pooled_DN16": float(np.sqrt(np.mean(difference**2)) * 65535),
            }
        )
    assert len(boards) == 8
    return boards


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    collected_path = root / "output/collection.json"
    collection = read_json(collected_path)
    assert collection["plan"] == reference(path)
    prior = read_json(checked(plan["adopted_report"]))
    saved = read_json(checked(plan["adopted_collection"]))
    out = root / "review"
    out.mkdir()
    metrics, synthetic = report_synthetic(plan, collection, prior, saved, out)
    matched = matched_quiet(
        metrics,
        plan["thresholds"],
        plan["positive_quiet_RMS_budgets_DN16"],
        methods=("pooled", "subharmonic"),
        shared_zero=None,
    )
    assert len(matched) == 192
    assert [r for r in matched if r["method"] == "pooled"] == [
        r for r in prior["leave_one_geometry_out"] if r["method"] == "pooled"
    ]
    write_json(
        out / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(collected_path),
            "fixed_threshold_metrics": metrics,
            "leave_one_geometry_out": matched,
            "synthetic_boards": synthetic,
            "camera_boards": report_camera(plan, collection, prior, saved, out),
            "donor_coverage": coverage(read_json(checked(plan["donor_assessment"]))),
            "scope": "Geometry-only guide change with exact original pooled waveform, sensor scores, and synthesis."
            " Unchanged rows adopt their original output; reference geometry enters post-collection coverage only.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().plan.resolve())
