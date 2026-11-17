"""Score guide errors at the frozen operating points and render native comparisons."""

import argparse
import os
from pathlib import Path

import numpy as np
from probe_phase_guide_recenter import ARMS
from report_fold_support_pooling import ROI, evaluated, insert_camera_panels, measure
from report_fresh_phase_refit import donor_errors
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def camera_boards(output, plan, collection):
    boards = []
    for item, current in zip(plan["camera"], collection["camera"], strict=True):
        board = item["board"]
        case = board["source"]
        assert current["id"] == board["id"]
        x, y, w, h = board["ROI_xywh"]
        bx, by, *_ = case["query_box"]
        crop = np.s_[:, y - by : y - by + h, x - bx : x - bx + w]
        with np.load(checked(case["query_arrays"])) as data:
            calibration = {k: data[k] for k in ("wb", "matrix")}
        with (
            np.load(checked(current["output"])) as future,
            np.load(checked(board["prediction"])) as previous,
        ):
            image = future["weighted-refit-t2"]
            baseline = previous["weighted-refit-t2"]
            change = float(
                np.sqrt(np.mean((image[crop].astype(np.float64) - baseline[crop]) ** 2)) * 65535
            )
            rendered = display(image[None], calibration, exposure=board["display_exposure"])[0][
                crop
            ]
        img, panels = insert_camera_panels(
            output,
            board["id"],
            board,
            "Weighted refit",
            [("Recentered weighted", np.rint(rendered.transpose(1, 2, 0) * 255).astype(np.uint8))],
        )
        boards.append(
            {
                **board,
                "image": img,
                "panels": panels,
                "previous_image": board["image"],
                "new_prediction": current["output"],
                "change_from_weighted_DN16_RMS": change,
            }
        )
    assert len(boards) == 8
    return boards


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    closed = root / "output/collection.json"
    collection = read_json(closed)
    assert collection["plan"] == reference(path) and collection["new_synthetic_calls"] == 480
    fresh = read_json(checked(plan["fresh_report"]))
    originals = {
        (v["id"], v["method"], v["budget_DN16"]): v for v in fresh["frozen_budget_results"]
    }
    output = root / "review"
    output.mkdir()
    rows, boards, guide_checks = [], [], []
    for link in collection["synthetic"]:
        obs = read_json(checked(link))
        case = read_json(checked(obs["case"]))
        assert obs["id"] == case["id"]
        meta = {k: case[k] for k in ("id", "source", "profile", "placement", "CFA")}
        settings = [
            v
            for v in plan["settings"]
            if (v["profile"], v["placement"]) == (case["profile"], case["placement"])
        ]
        assert len(settings) == 4
        parent = np.load(checked(case["parent"])).astype(np.float64)
        with np.load(checked(case["target"])) as target:
            truth, quiet = target["target"].astype(np.float64), target["quiet"][ROI]
        with (
            np.load(checked(case["predictions"])) as baseline,
            np.load(checked(obs["output"])) as variants,
        ):
            view = {}
            for arm in ARMS:
                for v in settings:
                    name = f"{v['method']}-t{v['threshold']:g}"
                    value = baseline[name] if arm == "nominal-fixed" else variants[f"{arm}--{name}"]
                    mom = measure(parent, truth, quiet, value)
                    metrics = evaluated(mom, v["scale"])
                    previous = evaluated(mom, 0)
                    record = {
                        **meta,
                        **v,
                        "arm": arm,
                        **metrics,
                        "delta_from_parent": {k: val - previous[k] for k, val in metrics.items()},
                    }
                    if arm == "nominal-fixed":
                        assert {k: val for k, val in record.items() if k != "arm"} == originals[
                            case["id"], v["method"], v["budget_DN16"]
                        ]
                    rows.append(record)
                    if v["method"] == "weighted-refit" and v["budget_DN16"] == 0.02:
                        base = parent[2][ROI]
                        view[arm] = base + v["scale"] * (value[2] - base)
            if case["source"] in (40, 41) and case["placement"] == "far":
                with np.load(checked(case["sensor"])) as sensor:
                    context = {k: sensor[k][2:3] for k in ("colors", "wb", "matrix")}
                    context["packed"] = sensor["packed"][2:3, :, 64:192, 64:192]
                boards.append(
                    native_board(
                        output,
                        case["id"],
                        [
                            noisy_malvar(context)[0],
                            parent[2][ROI],
                            view["radial-fixed"],
                            view["radial-recentered"],
                            view["nominal-fixed"],
                            truth[2][ROI],
                        ],
                        context,
                        {"case": case, "observed": link, "budget_DN16": 0.02, "settings": settings},
                        labels=(
                            "Noisy Malvar",
                            "V143 EMA",
                            "Wrong period",
                            "Recentered",
                            "Nominal guide",
                            "Exact GT",
                        ),
                    )
                )
        for arm, fits in obs["fits"].items():
            for role, fit in enumerate(fits):
                assert len(fit["records"]) == 1
                original = fit["guide_frequencies_xy"]
                errors_in = donor_errors({"metadata": case["metadata"], "frequencies": original})
                for fold, selected in enumerate(fit["records"][0]["frequencies"]):
                    guide_checks.append(
                        {
                            **meta,
                            "arm": arm,
                            "role": role,
                            "fold": fold,
                            "guide_errors_before": errors_in,
                            "guide_errors_after": donor_errors(
                                {"metadata": case["metadata"], "frequencies": selected}
                            ),
                            "number_moved": sum(
                                a != b for a, b in zip(original, selected, strict=True)
                            ),
                            "matched_units": len(fit["records"][0]["matched_units"]),
                        }
                    )
    assert len(rows) == 768 and len(guide_checks) == 960 and len(boards) == 4
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(closed),
            "metrics": rows,
            "guides": guide_checks,
            "boards": boards,
            "camera": camera_boards(output, plan, collection),
            "nominal_frozen_rows_reproduced_exactly": 128,
        },
    )
    print(len(rows), len(guide_checks), len(boards), "guide stress report complete", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
