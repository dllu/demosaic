"""Replay exact query observations with a two-sided RAW geometry prior."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import report, restore, sample_donor_raw, sensor_box
from probe_fresh_phase_refit import write_array
from report_fold_support_pooling import ROI

from demosaic.bracket_phase_geometry import bracket_donor_geometry
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig

ARMS = ("guarded", "single", "planar", "bracket")
LEFT = (-128, 128, 256, 256)


def prepare(root, previous):
    path = previous / "plan.json"
    old = read_json(path)
    collection = previous / "output/collection.json"
    assert read_json(collection)["plan"] == reference(path)
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    inputs = [
        reference(path),
        reference(collection),
        old["camera_baseline"],
        old["camera_conditions"],
    ]
    write_json(
        root / "plan.json",
        {
            **{
                k: old[k]
                for k in (
                    "camera_baseline",
                    "camera_conditions",
                    "parent_checkpoint",
                    "config",
                    "profiles",
                    "settings",
                    "query_xywh",
                )
            },
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": inputs,
            "single_plan": reference(path),
            "single_collection": reference(collection),
            "left_xywh": LEFT,
            "right_xywh": old["donor_xywh"],
            "left_noise_repeat": 7953,
            "arms": ARMS,
            "rendering": {
                "labels": ["Guarded guide", "One donor", "Fixed planar", "Two donors"],
                "sources": [81, 85],
                "camera_label": "Two donors",
                "contrast": 5,
            },
            "scope": "Reuse all 32 original query groups and the saved right donor. Render an independently "
            "corrupted left donor of the same underlying phase geometry. Select shared curvature "
            "on disjoint folds of both donors; query phase and support stay local. The two fixed "
            "arms share center frequencies. Real comparisons use direct 128-pixel patches above "
            "and below the native query from the same cached RAW observation.",
        },
    )


def fit_synthetic_bracket(old_donor, plan, noise, case, output):
    pixels, colors, metadata = sample_donor_raw(
        case, noise, plan["left_xywh"], plan["left_noise_repeat"]
    )
    with np.load(checked(old_donor["sensor"])) as f:
        right = f["packed"], f["colors"], plan["right_xywh"]
    views = [(pixels, colors, plan["left_xywh"]), right]
    fit = bracket_donor_geometry(
        views,
        plan["query_xywh"],
        old_donor["initial_guide"],
        shot=noise["shot"],
        read=noise["read"],
    )
    return {
        "left": write_array(output, packed=pixels, colors=colors),
        "left_declaration": metadata,
        "right": old_donor["sensor"],
        "right_declaration": old_donor["metadata"],
        "fit": fit,
    }


def camera_replays(plan, cfg, output):
    base = read_json(checked(plan["camera_baseline"]))
    settings = read_json(checked(plan["camera_conditions"]))
    results = []
    for row, condition in zip(base["camera"], settings["camera"], strict=True):
        key, scene = row["id"], row["source"]
        assert key == condition["board"]["id"]
        noise = condition["noise"]
        x, y, w, h = scene["query_box"]
        ax, ay, *_ = scene["absolute_query_xywh"]
        # All established camera queries have at least 128 sensor rows on either side.
        boxes = [(x + w // 2 - 64, yy, 128, 128) for yy in (y - 128, y + h)]
        absolute = [(a + ax - x, b + ay - y, c, d) for a, b, c, d in boxes]
        views = []
        for box, native in zip(boxes, absolute, strict=True):
            packed, colors = sensor_box(scene["query_arrays"], box)
            assert packed.shape == (1, 4, 64, 64)
            views.append((packed[0], colors[0], native))
        fit = bracket_donor_geometry(
            views,
            scene["absolute_query_xywh"],
            scene["guide"],
            shot=noise["shot"],
            read=noise["read"],
        )
        if any(fit["accepted"]):
            parent = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
                0, :, y : y + h, x : x + w
            ]
            packed, colors = sensor_box(scene["query_arrays"], scene["query_box"])
            corrected, _ = restore(
                parent, packed[0], colors[0], fit, noise, cfg, (2.0,), True, True
            )
            prediction = write_array(output / f"{key}.npz", corrected=corrected[2])
        else:
            prediction = row["crosscheck_prediction"]
        results.append(
            {
                "id": key,
                "prediction": prediction,
                "fit": fit,
                "donor_boxes": absolute,
                "donor_inputs": scene["query_arrays"],
            }
        )
    return results


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    started = time.monotonic()
    output = Path(plan["root"]) / "output"
    output.mkdir()
    single = read_json(checked(plan["single_collection"]))
    assert single["plan"] == plan["single_plan"]
    cfg = LocalWaveConfig(**plan["config"])
    records, donors = [], {}
    for previous in single["synthetic"]:
        case = read_json(checked(previous["case"]))
        key, guide = case["id"], previous["guide_key"]
        noise, placement = plan["profiles"][case["profile"]], case["placement"]
        if guide not in donors:
            donors[guide] = fit_synthetic_bracket(
                single["donors"][guide], plan, noise, case, output / f"{guide}-left.npz"
            )
        geom = donors[guide]["fit"]
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        parent = np.load(checked(case["parent"]))[ROI]
        thresholds = sorted(
            {
                s["threshold"]
                for s in plan["settings"]
                if (s["profile"], s["placement"]) == (case["profile"], placement)
            }
        )
        predictions = {}
        for arm in ("planar", "bracket"):
            for role in range(3):
                values, _ = restore(
                    parent[role],
                    packed[role],
                    colors[role],
                    geom,
                    noise,
                    cfg,
                    thresholds,
                    placement == "near",
                    arm == "bracket",
                )
                for t, pixels in values.items():
                    predictions.setdefault(f"{arm}--t{t:g}", []).append(pixels)
        with np.load(checked(previous["prediction"])) as saved:
            for t in thresholds:
                predictions[f"guarded--t{t:g}"] = saved[f"guarded--t{t:g}"]
                predictions[f"single--t{t:g}"] = saved[f"transport--t{t:g}"]
                if not any(geom["accepted"]):
                    np.testing.assert_array_equal(
                        predictions[f"planar--t{t:g}"], predictions[f"bracket--t{t:g}"]
                    )
        records.append(
            {
                "id": key,
                "case": previous["case"],
                "guide_key": guide,
                "prediction": write_array(
                    output / f"{key}.npz", **{k: np.stack(v) for k, v in predictions.items()}
                ),
            }
        )
        print(len(records), key, geom["accepted"], round(time.monotonic() - started, 2), flush=True)
    cameras = camera_replays(plan, cfg, output)
    assert len(records) == 32 and len(cameras) == 8 and len(donors) == 16
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": records,
            "camera": cameras,
            "donors": donors,
            "seconds": time.monotonic() - started,
            "new_neural_calls": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--prepare-from", type=Path)
    actions.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    elif args.report:
        report(args.path.resolve())
    else:
        collect(args.path.resolve())
