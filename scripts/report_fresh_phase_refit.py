"""Score the fresh phase-refit panel using its frozen development settings."""

import argparse
import os
from itertools import permutations
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import BUDGETS, METHODS
from report_fold_support_pooling import ROI, evaluated, measure
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def donor_errors(row):
    recipe = row["metadata"]["recipe"]
    angles = np.asarray(recipe["wire_angles"])
    expected = (
        np.stack((np.cos(angles), np.sin(angles)), axis=1) / np.asarray(recipe["periods"])[:, None]
    )
    actual = np.asarray(row["frequencies"])
    candidates = []
    for choice in permutations(range(2)):
        pair = actual[list(choice)]
        distance = (
            np.minimum(
                np.linalg.norm(pair - expected, axis=1), np.linalg.norm(pair + expected, axis=1)
            )
            * 256
        )
        candidates.append(tuple(distance))
    return min(candidates, key=sum)


def report(path):
    plan = read_json(path)
    assert plan["frozen_files"][str(Path(__file__))] == reference(__file__)["sha256"]
    root = Path(plan["root"])
    source = root / "output/collection.json"
    complete = read_json(source)
    assert complete["plan"] == reference(path) and complete["query_roles"] == 96
    output = root / "review"
    output.mkdir()
    settings = {
        (v["profile"], v["placement"], v["method"], v["budget_DN16"]): v for v in plan["settings"]
    }
    fixed, transferred, boards = [], [], []
    for binding, group in zip(complete["cases"], plan["groups"], strict=True):
        item = read_json(checked(binding))
        assert all(item[k] == v for k, v in group.items())
        meta = {k: item[k] for k in ("id", "source", "profile", "placement", "CFA")}
        parents = np.load(checked(item["parent"]), allow_pickle=False)
        with np.load(checked(item["target"]), allow_pickle=False) as target:
            truth = target["target"].astype(np.float64)
            quiet = target["quiet"][ROI]
        parent = parents.astype(np.float64)
        base = parent[ROI]
        with np.load(checked(item["predictions"]), allow_pickle=False) as archive:
            frame = {}
            for method in METHODS:
                for threshold in plan["thresholds"]:
                    predicted = f"{method}-t{threshold:g}"
                    values = measure(parent, truth, quiet, archive[predicted])
                    frame[method, threshold] = values
                    fixed.append(
                        {
                            **meta,
                            "method": method,
                            "threshold": threshold,
                            "moments": {name: v.tolist() for name, v in values.items()},
                            **evaluated(values, 1),
                        }
                    )
            by_display = {}
            for method in METHODS:
                for budget in BUDGETS:
                    setting = settings[item["profile"], item["placement"], method, budget]
                    threshold, scale = setting["threshold"], setting["scale"]
                    value = frame[method, threshold]
                    error, before = evaluated(value, scale), evaluated(value, 0)
                    transferred.append(
                        {
                            **meta,
                            **setting,
                            **error,
                            "delta_from_parent": {
                                metric: error[metric] - before[metric] for metric in error
                            },
                        }
                    )
                    if budget == BUDGETS[0]:
                        fixed_name = f"{method}-t{threshold:g}"
                        by_display[method] = base[2] + scale * (archive[fixed_name][2] - base[2])
            if item["source"] in (40, 41) and item["placement"] == "far":
                with np.load(checked(item["sensor"]), allow_pickle=False) as sensor:
                    context = {k: sensor[k][2:3] for k in ("colors", "wb", "matrix")}
                    context["packed"] = sensor["packed"][2:3, :, 64:192, 64:192]
                frames = [
                    noisy_malvar(context)[0],
                    base[2],
                    by_display["fold-average"],
                    by_display["weighted-refit"],
                    archive["weighted-refit-t2"][2],
                    truth[2][ROI],
                ]
                boards.append(
                    native_board(
                        output,
                        item["id"],
                        frames,
                        context,
                        {
                            "group": item,
                            "role": 2,
                            "checkpoint": plan["parent"],
                            "operating_points": {
                                method: settings[
                                    item["profile"], item["placement"], method, BUDGETS[0]
                                ]
                                for method in METHODS
                            },
                        },
                        labels=(
                            "Noisy Malvar",
                            "V143 EMA",
                            "Frozen fold average",
                            "Frozen weighted refit",
                            "Weighted t2",
                            "Exact GT",
                        ),
                    )
                )
    coverage = {
        k: {"errors_native_bins": donor_errors(v), "accepted_halves": v["accepted"]}
        for k, v in complete["donors"].items()
    }
    assert len(fixed) == 512 and len(transferred) == 128 and len(boards) == 4
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(source),
            "fixed_thresholds": fixed,
            "frozen_budget_results": transferred,
            "boards": boards,
            "guide_audit": coverage,
            "training_or_threshold_changes_after_collection": 0,
        },
    )
    print(len(fixed), len(transferred), len(boards), "report complete", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve())
