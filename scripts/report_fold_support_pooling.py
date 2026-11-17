"""Measure fixed thresholds and cross-validated quiet-error operating points."""

import argparse
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import display, noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json

ROI = np.s_[..., 128:384, 128:384]
METHODS = ("minimum", "pooled")


def error_polynomial(error, correction, full_size=None):
    """Return coefficients for mean squared DN16 error at a correction scale."""
    size = full_size or error.size
    base = np.sum(error**2, dtype=np.float64)
    cross = 2 * np.sum(
        error[ROI] * correction if full_size else error * correction, dtype=np.float64
    )
    square = np.sum(correction**2, dtype=np.float64)
    return np.array([base, cross, square]) * (65535.0**2 / size)


def projection(image, correction, target):
    denominator = np.sum(target**2)
    return (
        np.array(
            [
                np.sum(image * target),
                np.sum(correction * target[ROI]),
            ]
        )
        / denominator
    )


def measure(parent, truth, quiet, restored):
    correction = restored.astype(np.float64) - parent[ROI]
    error = parent - truth
    weak, strong = truth[2] - truth[1], truth[1] - truth[0]
    increment = correction[2] - correction[1]
    return {
        "quiet_mse": error_polynomial(error[ROI][..., quiet], correction[..., quiet]),
        "query_mse": error_polynomial(error[ROI], correction),
        "weak_increment_mse": error_polynomial(error[2] - error[1], increment, weak.size),
        "weak_gain": projection(parent[2] - parent[1], increment, weak),
        "strong_gain": projection(parent[1] - parent[0], correction[1] - correction[0], strong),
        "weak_absent_projection": projection(error[1], correction[1], weak),
    }


def evaluated(moment, alpha):
    result = {}
    for key, coefficient in moment.items():
        value = np.polynomial.polynomial.polyval(alpha, coefficient)
        result[key.replace("_mse", "_RMS_DN16")] = (
            float(np.sqrt(max(0, value))) if key.endswith("_mse") else float(value)
        )
    return result


def scale_at_budget(quiet, budget):
    """Use the largest scale with calibration quiet RMS within the additive budget."""
    base, cross, square = quiet
    excess = (np.sqrt(base) + budget) ** 2 - base
    if cross + square <= excess:
        return 1.0
    root = np.sqrt(cross**2 + 4 * square * excess)
    if cross >= 0:
        return float(2 * excess / (root + cross))
    return float((root - cross) / (2 * square))


def report_synthetic(plan, collected, output):
    expected = {
        f"{name}-t{t:g}" for name in METHODS for t in plan["thresholds"] if t or name == "minimum"
    }
    rows, boards = [], []
    for group, result in zip(plan["groups"], collected["synthetic"], strict=True):
        assert result["id"] == group["id"]
        with np.load(checked(group["arrays"])) as arrays:
            truth = arrays["target"].astype(np.float64)
            quiet = arrays["quiet"][ROI]
            context = {key: arrays[key][2:3] for key in ("colors", "wb", "matrix")}
            context["packed"] = arrays["packed"][2:3, :, 64:192, 64:192]
        parent = np.load(checked(group["parent"])).astype(np.float64)
        by_method = defaultdict(list)
        for role, row in enumerate(result["rows"]):
            assert row["role"] == role
            with (
                np.load(checked(row["prediction"])) as data,
                np.load(checked(row["adopted_prediction"])) as control,
            ):
                assert set(data.files) == expected
                for t in (0, 2, 4):
                    np.testing.assert_array_equal(
                        data[f"minimum-t{t}"], control[f"shrunken-profile-t{t}"]
                    )
                for method in data.files:
                    by_method[method].append(data[method])
        fields = {k: group[k] for k in ("id", "profile", "source", "placement", "CFA")}
        for method, values in by_method.items():
            moments = measure(parent, truth, quiet, np.stack(values))
            rows.append(
                {
                    **fields,
                    "method": method,
                    "moments": {k: v.tolist() for k, v in moments.items()},
                    **evaluated(moments, 1.0),
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
                by_method["minimum-t2"][2],
                by_method["pooled-t2"][2],
                truth[2][ROI],
            ]
            boards.append(
                native_board(
                    output,
                    group["id"],
                    values,
                    context,
                    {"group": group, "role": 2, "threshold": 2},
                    labels=("Noisy Malvar", "V143 EMA", "Minimum fold", "Pooled folds", "Exact GT"),
                    triplet_indices=(0, 3, 4),
                )
            )
    assert len(rows) == 128 * len(expected) and len(boards) == 2
    return rows, boards


def matched_quiet(rows, thresholds, budgets, *, methods=METHODS, shared_zero="minimum"):
    by_source = defaultdict(list)
    for row in rows:
        by_source[row["profile"], row["placement"], row["source"], row["method"]].append(row)
    means = {}
    for key, items in by_source.items():
        assert len(items) == 4 and len({v["CFA"] for v in items}) == 4
        means[key] = {
            k: np.mean([v["moments"][k] for v in items], axis=0) for k in items[0]["moments"]
        }
    out = []
    for profile, placement in sorted({key[:2] for key in means}):
        for budget in budgets:
            for test in range(8):
                calibrate = [i for i in range(8) if i != test]
                for name in methods:
                    choices = []
                    for t in thresholds:
                        method = name if t or shared_zero is None else shared_zero
                        key = f"{method}-t{t:g}"
                        training = [means[profile, placement, index, key] for index in calibrate]
                        quiet = np.mean([v["quiet_mse"] for v in training], axis=0)
                        gain = np.mean([v["weak_gain"] for v in training], axis=0)
                        alpha = scale_at_budget(quiet, budget) if gain[1] > 0 else 0.0
                        rms = np.sqrt(np.polynomial.polynomial.polyval(alpha, quiet))
                        assert rms <= np.sqrt(quiet[0]) + budget + 1e-10
                        choices.append(
                            (gain[0] + alpha * gain[1], -t, alpha, key, rms - np.sqrt(quiet[0]))
                        )
                    _, neg_t, alpha, key, calibrated_delta = max(choices)
                    moment = means[profile, placement, test, key]
                    result = evaluated(moment, alpha)
                    baseline = evaluated(moment, 0)
                    out.append(
                        {
                            "profile": profile,
                            "placement": placement,
                            "source": test,
                            "method": name,
                            "budget_DN16": budget,
                            "threshold": -neg_t,
                            "scale": alpha,
                            "calibration_sources": calibrate,
                            "calibration_quiet_delta_DN16": calibrated_delta,
                            **result,
                            "delta_from_parent": {k: result[k] - baseline[k] for k in result},
                        }
                    )
    return out


def insert_camera_panel(output, key, old, after_label, new_label, new_pixels):
    source = np.asarray(Image.open(checked(old["image"])))
    cells = []
    for panel in old["panels"]:
        x, y, w, h = panel["png_xywh"]
        cells.append((panel["label"], source[y : y + h, x : x + w]))
        if panel["label"] == after_label:
            cells.append((new_label, new_pixels))
    assert len(cells) == len(old["panels"]) + 1
    board = Image.new("RGB", (8 + 168 * len(cells), 192), "#eeeeee")
    drawer = ImageDraw.Draw(board)
    panels = []
    for i, (label, cell) in enumerate(cells):
        assert cell.shape == (160, 160, 3)
        x = 8 + 168 * i
        board.paste(Image.fromarray(cell), (x, 24))
        drawer.text((x, 5), label, fill="black")
        panels.append({"label": label, "png_xywh": [x, 24, 160, 160]})
    dest = output / f"{key}.png"
    board.save(dest)
    rendered = np.asarray(Image.open(dest))
    for panel, (_, pixels) in zip(panels, cells, strict=True):
        x, y, w, h = panel["png_xywh"]
        np.testing.assert_array_equal(rendered[y : y + h, x : x + w], pixels)
    return reference(dest), panels


def report_camera(plan, collected, output):
    adopted = read_json(checked(plan["adopted_report"]))
    originals = {row["id"]: row for row in adopted["camera_boards"]}
    boards = []
    for row, result in zip(plan["camera_cases"], collected["camera"], strict=True):
        key = row["id"]
        assert result["id"] == key
        old = originals[key]
        native = old["original_board"]
        with np.load(checked(row["query_arrays"])) as arrays:
            calibration = {k: arrays[k] for k in ("wb", "matrix")}
        x, y, w, h = native["ROI_xywh"]
        ox, oy = row["query_box"][:2]
        crop = np.s_[:, y - oy : y - oy + h, x - ox : x - ox + w]
        with (
            np.load(checked(result["prediction"])) as data,
            np.load(checked(result["adopted_prediction"])) as control,
        ):
            for t in (0, 2, 4):
                np.testing.assert_array_equal(
                    data[f"minimum-t{t}"], control[f"shrunken-profile-t{t}"]
                )
            value = data["pooled-t2"]
            correction = value[crop].astype(np.float64) - data["minimum-t2"][crop]
        rgb = display(value[None], calibration, exposure=native["display_exposure"])[0][crop]
        pixels = np.rint(rgb.transpose(1, 2, 0) * 255).astype(np.uint8)
        image, panels = insert_camera_panel(
            output, key, old, "Shrunken phase fit", "Pooled folds", pixels
        )
        boards.append(
            {
                "id": key,
                "image": image,
                "prior_board": old["image"],
                "panels": panels,
                "ROI_xywh": native["ROI_xywh"],
                "display_exposure": native["display_exposure"],
                "prediction": result["prediction"],
                "source": row,
                "pooled_minus_minimum_RMS_DN16": float(np.sqrt(np.mean(correction**2)) * 65535),
            }
        )
    assert len(boards) == 8
    return boards


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    collection_path = root / "output/collection.json"
    collected = read_json(collection_path)
    assert collected["plan"] == reference(path) and collected["query_roles"] == 384
    output = root / "review"
    output.mkdir()
    rows, boards = report_synthetic(plan, collected, output)
    paired = matched_quiet(rows, plan["thresholds"], plan["positive_quiet_RMS_budgets_DN16"])
    assert len(paired) == 192
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(collection_path),
            "fixed_threshold_metrics": rows,
            "leave_one_geometry_out": paired,
            "synthetic_boards": boards,
            "camera_boards": report_camera(plan, collected, output),
            "minimum_controls_exact": 384 * 3 + 8 * 3,
            "scope": "Fixed score sweep and three calibration budgets. RMS for calibration is the square"
            " root of equally weighted source and CFA MSE. Budget is set relative to the parent"
            " RMS on the seven calibration sources. The held-out source supplies no labels for"
            " selection, and its actual quiet cost can differ. Standing GFX crops are fixed t2.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
