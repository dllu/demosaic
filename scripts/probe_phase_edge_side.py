"""Separate held-out evidence and phase fits at strong RAW step edges."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

ARMS = ("validation", "profiles")


def prepare(root, previous):
    plan, collection, report = (
        previous / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    old, closed, scored = map(read_json, (plan, collection, report))
    assert closed["plan"] == scored["plan"] == reference(plan)
    assert scored["collection"] == reference(collection)
    assert closed["new_synthetic_calls"] == 576 and closed["new_camera_calls"] == 16
    root.mkdir()
    work, sources = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_phase_edge_side.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": sources,
            "inputs": [reference(p) for p in (plan, collection, report)],
            "guard_plan": reference(plan),
            "guard_collection": reference(collection),
            "guard_report": reference(report),
            "reference_arm": "nominal-guard8",
            "settings": old["settings"],
            "arms": ARMS,
            "scope": "Validation arm keeps intact query profiles and gathers evidence on each side."
            " Profiles arm additionally fits both sides and scores those components separately."
            " Frequency, nuisance, variance, both validation folds and development settings stay fixed.",
        },
    )


def restore(parent, packed, colors, noise, config, thresholds, control_fit, arm):
    images, fit = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=thresholds,
        guide_frequencies_xy=control_fit["guide_frequencies_xy"],
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        recenter_phase_guides=True,
        phase_guide_edge_guard_px=8,
        phase_edge_side=arm,
    )
    record = fit["records"][0]
    for key in ("edges", "frequencies", "guide_search_excluded"):
        np.testing.assert_array_equal(record[key], control_fit["records"][0][key])
    return images, fit


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    old = read_json(checked(plan["guard_plan"]))
    closed = read_json(checked(plan["guard_collection"]))
    fresh = read_json(checked(old["fresh_plan"]))
    cfg = LocalWaveConfig(**old["config"])
    prefix = plan["reference_arm"]
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started = time.monotonic()
    observed, cameras = [], []
    for link in closed["synthetic"]:
        control = read_json(checked(link))
        source = read_json(checked(control["case"]))
        key = source["id"]
        with np.load(checked(source["sensor"])) as data:
            packed, colors = data["packed"][..., 64:192, 64:192], data["colors"]
        parent = np.load(checked(source["parent"]))[..., 128:384, 128:384]
        thresholds = tuple(
            sorted(
                {
                    2,
                    *(
                        r["threshold"]
                        for r in plan["settings"]
                        if (r["profile"], r["placement"])
                        == (source["profile"], source["placement"])
                    ),
                }
            )
        )
        out, fits = {}, {}
        for arm in ARMS:
            decisions = []
            for role, before in enumerate(control["fits"][prefix]):
                values, stat = restore(
                    parent[role],
                    packed[role],
                    colors[role],
                    fresh["profiles"][source["profile"]],
                    cfg,
                    thresholds,
                    before,
                    arm,
                )
                decisions.append(stat)
                for (kind, t), image in values.items():
                    if kind in ("weighted-refit", "pooled-local"):
                        method = "fold-average" if kind == "pooled-local" else kind
                        out.setdefault(f"{arm}--{method}-t{t:g}", []).append(image)
            fits[arm] = decisions
        predictions = write_array(
            output / f"{key}.npz", **{name: np.stack(frames) for name, frames in out.items()}
        )
        receipt = output / f"{key}.json"
        write_json(
            receipt,
            {
                "id": key,
                "case": control["case"],
                "control": link,
                "predictions": predictions,
                "fits": fits,
            },
        )
        observed.append(reference(receipt))
        print(len(observed), key, round(time.monotonic() - started, 3), flush=True)
    for item, control in zip(old["camera"], closed["camera"], strict=True):
        b = item["board"]
        s = b["source"]
        key = b["id"]
        assert control["id"] == key
        x, y, w, h = s["query_box"]
        with np.load(checked(s["query_arrays"])) as sensor:
            packed = sensor["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = sensor["colors"][0]
        parent = np.load(checked(s["parent_prediction"]), mmap_mode="r")[0, :, y : y + h, x : x + w]
        outputs, fits = {}, {}
        for arm in ARMS:
            values, fit = restore(
                parent, packed, colors, item["noise"], cfg, (2,), control["fits"]["guard8"], arm
            )
            outputs[arm] = values["weighted-refit", 2]
            fits[arm] = fit
        pred = write_array(output / f"{key}.npz", **outputs)
        cameras.append({"id": key, "predictions": pred, "fits": fits})
    assert len(observed) == 32 and len(cameras) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observed,
            "camera": cameras,
            "synthetic_calls": len(observed) * 3 * len(ARMS),
            "camera_calls": len(cameras) * len(ARMS),
            "seconds": time.monotonic() - started,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    else:
        collect(args.path.resolve())
