"""Compare a signed shared waveform against per-color phase profiles."""

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


def prepare(root, previous):
    origin, predictions, review = (
        previous / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    old, closed, scored = map(read_json, (origin, predictions, review))
    assert closed["plan"] == scored["plan"] == reference(origin)
    assert scored["collection"] == reference(predictions) and len(scored["metrics"]) == 1536
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_shared_phase_shape.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "inputs": [reference(p) for p in (origin, predictions, review)],
            "previous_plan": reference(origin),
            "previous_collection": reference(predictions),
            "previous_report": reference(review),
            "settings": old["settings"],
            "reference_arm": "nominal-guard8",
            "scope": "Matched recenter, guard, phase reliability penalty, pooled held-out support,"
            " and weighted delivery. Fit a shared eight-knot waveform with signed color"
            " amplitudes. Use the original frozen thresholds and correction scales.",
        },
    )


def restore(parent, packed, colors, guide, noise, config, thresholds):
    return restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=thresholds,
        guide_frequencies_xy=guide,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        recenter_phase_guides=True,
        phase_guide_edge_guard_px=8,
        shared_phase_shape=True,
    )


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    old = read_json(checked(plan["previous_plan"]))
    closed = read_json(checked(plan["previous_collection"]))
    fresh = read_json(checked(old["fresh_plan"]))
    cfg = LocalWaveConfig(**old["config"])
    prefix = plan["reference_arm"]
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started = time.monotonic()
    observed, cameras = [], []
    for link in closed["synthetic"]:
        control = read_json(checked(link))
        original = read_json(checked(control["case"]))
        key = original["id"]
        with np.load(checked(original["sensor"])) as f:
            packed, colors = f["packed"][..., 64:192, 64:192], f["colors"]
        parent = np.load(checked(original["parent"]))[..., 128:384, 128:384]
        settings = [
            r
            for r in plan["settings"]
            if (r["profile"], r["placement"]) == (original["profile"], original["placement"])
        ]
        thresholds = tuple(sorted({2, *(r["threshold"] for r in settings)}))
        out, decisions = {}, []
        for role, fixed in enumerate(control["fits"][prefix]):
            values, stats = restore(
                parent[role],
                packed[role],
                colors[role],
                fixed["guide_frequencies_xy"],
                fresh["profiles"][original["profile"]],
                cfg,
                thresholds,
            )
            guarded, shared = fixed["records"][0], stats["records"][0]
            for k in ("edges", "frequencies", "guide_search_excluded"):
                np.testing.assert_array_equal(
                    guarded[k], shared[k], err_msg=f"{key}, role {role}, {k}"
                )
            decisions.append(stats)
            for (kind, t), image in values.items():
                if kind in ("weighted-refit", "pooled-local"):
                    method = "fold-average" if kind == "pooled-local" else kind
                    out.setdefault(f"{method}-t{t:g}", []).append(image)
        binding = write_array(
            output / f"{key}.npz", **{name: np.stack(frames) for name, frames in out.items()}
        )
        receipt = output / f"{key}.json"
        write_json(
            receipt,
            {
                "id": key,
                "control": link,
                "case": control["case"],
                "predictions": binding,
                "fits": decisions,
            },
        )
        observed.append(reference(receipt))
        print(len(observed), key, round(time.monotonic() - started, 3), flush=True)
    for item, control in zip(old["camera"], closed["camera"], strict=True):
        board = item["board"]
        case = board["source"]
        key = board["id"]
        x, y, w, h = case["query_box"]
        assert control["id"] == key
        with np.load(checked(case["query_arrays"])) as source:
            packed = source["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = source["colors"][0]
        parent = np.load(checked(case["parent_prediction"]), mmap_mode="r")[
            0, :, y : y + h, x : x + w
        ]
        fixed = control["fits"]["guard8"]
        values, fit = restore(
            parent, packed, colors, fixed["guide_frequencies_xy"], item["noise"], cfg, (2,)
        )
        for name in ("edges", "frequencies", "guide_search_excluded"):
            np.testing.assert_array_equal(
                fit["records"][0][name], fixed["records"][0][name], err_msg=f"{key}, {name}"
            )
        predictions = write_array(output / f"{key}.npz", shared=values["weighted-refit", 2])
        cameras.append({"id": key, "predictions": predictions, "fit": fit})
    assert len(observed) == 32 and len(cameras) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observed,
            "camera": cameras,
            "synthetic_fits": 96,
            "camera_fits": len(cameras),
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
