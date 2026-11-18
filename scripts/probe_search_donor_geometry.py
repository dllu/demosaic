"""Compare screened, held-out RAW donor search with frozen guide controls."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import report, sample_donor_raw, sensor_box
from probe_fresh_phase_refit import write_array
from report_fold_support_pooling import ROI

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.search_donor_geometry import candidate_boxes, search_donor_geometry

ARMS = ("guarded", "planar", "bracket", "screened-planar", "screened-curved")


def prepare(root, previous):
    previous_plan = reference(previous / "plan.json")
    previous_collection = reference(previous / "output/collection.json")
    old = read_json(checked(previous_plan))
    assert read_json(checked(previous_collection))["plan"] == previous_plan
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
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
                    "left_xywh",
                    "right_xywh",
                )
            },
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                previous_plan,
                previous_collection,
                old["camera_baseline"],
                old["camera_conditions"],
            ],
            "previous_plan": previous_plan,
            "previous_collection": previous_collection,
            "decoy_declarations": [
                {
                    "box": [128, -128, 256, 256],
                    "repeat": 7954,
                    "turn_degrees": 40,
                    "amplitude": 0.055,
                },
                {"box": [128, 384, 256, 256], "repeat": 7955, "turn_degrees": 0, "amplitude": 0},
            ],
            "camera_tile_size": 128,
            "camera_tile_stride": 64,
            "arms": ARMS,
            "rendering": {
                "labels": [
                    "Guarded guide",
                    "Fixed planar",
                    "Fixed two donors",
                    "Search planar",
                    "Search curved",
                ],
                "sources": [81, 85],
                "camera_label": "Donor search",
                "contrast": 5,
            },
            "scope": (
                "Six screening peaks per disjoint candidate. Search ranks matched carriers on an "
                "absolute 25% donor RAW subset. The selected donor pair stays fixed while two folds "
                "of the remaining samples verify local planes and shared curvature. Query evidence "
                "determines phase, color, amplitude and support. Camera search uses the retained "
                "512/768-pixel native windows. Synthetic controls reuse the two known donors and "
                "add a turned-wire candidate and an edge-only candidate opposite one another."
            ),
        },
    )


def deliver(
    parent, packed, colors, fit, noise, cfg, thresholds, near, curved, *, evidence_mask=None
):
    hessians = fit["hessians_xy"] if curved else None
    output, _ = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=cfg,
        thresholds=thresholds,
        evidence_mask=evidence_mask,
        guide_frequencies_xy=fit["frequencies_xy"],
        guide_phase_hessians_xy=hessians,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        phase_edge_side="validation" if near else None,
        active_guide_directions=fit["active"],
    )
    return {t: output["weighted-refit", t] for t in thresholds}


def camera_replays(plan, cfg, output):
    base = read_json(checked(plan["camera_baseline"]))
    settings = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    rows = []
    for row in base["camera"]:
        key, scene = row["id"], row["source"]
        noise = settings[key]
        x, y, w, h = scene["query_box"]
        ax, ay, *_ = absolute = scene["absolute_query_xywh"]
        ox, oy = ax - x, ay - y
        with np.load(checked(scene["query_arrays"])) as sensor:
            full, colors = sensor["packed"][0], sensor["colors"][0]
        frame = (ox, oy, 2 * full.shape[2], 2 * full.shape[1])
        boxes = candidate_boxes(
            frame, absolute, plan["camera_tile_size"], plan["camera_tile_stride"]
        )
        donors = [
            (
                full[:, (b - oy) // 2 : (b - oy + d) // 2, (a - ox) // 2 : (a - ox + c) // 2],
                colors,
                (a, b, c, d),
            )
            for a, b, c, d in boxes
        ]
        fit = search_donor_geometry(
            donors, absolute, shot=noise["shot"], read=noise["read"], fit_curvature=True
        )
        prediction = row["crosscheck_prediction"]
        if any(fit["active"]):
            parent = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
                0, :, y : y + h, x : x + w
            ]
            packed = full[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            corrected = deliver(parent, packed, colors, fit, noise, cfg, (2.0,), True, True)[2]
            prediction = write_array(output / f"{key}.npz", corrected=corrected)
        rows.append(
            {
                "id": key,
                "prediction": prediction,
                "fit": fit,
                "frame": frame,
                "donor_inputs": scene["query_arrays"],
            }
        )
        print(key, fit["candidate_count"], fit["with_peaks"], fit["active"], flush=True)
    return rows


def synthetic_donors(plan, old, case, noise, key, output):
    views = []
    for side in ("left", "right"):
        with np.load(checked(old[side])) as data:
            views.append((data["packed"], data["colors"], plan[f"{side}_xywh"]))
    bindings = []
    for k, spec in enumerate(plan["decoy_declarations"]):
        recipe = case["metadata"]["recipe"]
        turn = np.deg2rad(spec["turn_degrees"])
        altered = case | {
            "metadata": {
                "recipe": recipe | {"wire_angles": [float(a + turn) for a in recipe["wire_angles"]]}
            }
        }
        raw, colors, declaration = sample_donor_raw(
            altered, noise, spec["box"], spec["repeat"], amplitude=spec["amplitude"]
        )
        views.append((raw, colors, spec["box"]))
        bindings.append(
            {
                "sensor": write_array(output / f"{key}-decoy{k}.npz", packed=raw, colors=colors),
                "declaration": declaration,
            }
        )
    return {
        "left": old["left"],
        "right": old["right"],
        "decoys": bindings,
        "fit": search_donor_geometry(
            views, plan["query_xywh"], shot=noise["shot"], read=noise["read"], fit_curvature=True
        ),
    }


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    previous = read_json(checked(plan["previous_collection"]))
    assert previous["plan"] == plan["previous_plan"]
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started = time.monotonic()
    camera = camera_replays(plan, cfg, output)
    records, donors = [], {}
    for record in previous["synthetic"]:
        case = read_json(checked(record["case"]))
        key = record["guide_key"]
        noise = plan["profiles"][case["profile"]]
        before_edge = case["placement"] == "near"
        if key not in donors:
            donors[key] = synthetic_donors(plan, previous["donors"][key], case, noise, key, output)
        fit = donors[key]["fit"]
        thresholds = tuple(
            sorted(
                {
                    s["threshold"]
                    for s in plan["settings"]
                    if (s["profile"], s["placement"]) == (case["profile"], case["placement"])
                }
            )
        )
        with np.load(checked(record["prediction"])) as saved:
            predictions = {
                f"{arm}--t{t:g}": saved[f"{arm}--t{t:g}"] for arm in ARMS[:3] for t in thresholds
            }
        if any(fit["active"]):
            packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
            parent = np.load(checked(case["parent"]), mmap_mode="r")[ROI]
            for arm, curved in (("screened-planar", False), ("screened-curved", True)):
                roles = [
                    deliver(p, r, c, fit, noise, cfg, thresholds, before_edge, curved)
                    for p, r, c in zip(parent, packed, colors, strict=True)
                ]
                predictions.update(
                    {f"{arm}--t{t:g}": np.stack([role[t] for role in roles]) for t in thresholds}
                )
        else:
            for arm in ARMS[-2:]:
                predictions.update(
                    {f"{arm}--t{t:g}": predictions[f"guarded--t{t:g}"] for t in thresholds}
                )
        records.append(
            record | {"prediction": write_array(output / f"{case['id']}.npz", **predictions)}
        )
        print(
            len(records),
            case["id"],
            fit["active"],
            round(time.monotonic() - started, 2),
            flush=True,
        )
    assert len(records) == 32 and len(donors) == 16 and len(camera) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": records,
            "camera": camera,
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
