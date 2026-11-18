"""Replay fixed donor guides with predictive and orthogonal matched RAW scores."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_screened_scene_donors import offset_box

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.search_donor_geometry import screening_mask

MODES = ("weighted-refit", "matched-refit", "orthogonal-refit")


def prepare(root, previous):
    old_plan = reference(previous / "plan.json")
    collection = reference(previous / "output/collection.json")
    old = read_json(checked(old_plan))
    assert read_json(checked(collection))["plan"] == old_plan
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_wave_guides.py"]
    )
    write_json(
        root / "plan.json",
        old
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "previous": collection,
            "inputs": [old_plan, collection, old["camera_baseline"], old["camera_conditions"]],
            "modes": MODES,
            "synthetic_guides": ["fixed", "scene", "exact-center"],
            "camera_guides": ["scene", "spectral"],
            "threshold_offsets": [0, 1],
            "scope": "Compare query validation scores using identical disjoint CFA folds, selected "
            "guides, candidate fits and delivery. Always keep the old predictive score. Exact-center "
            "is a diagnostic using planted nominal direction vectors only, on all three roles. "
            "No clean support, wave profile, amplitude or pixel enters any score or correction.",
        },
    )


def output_key(guide, mode, offset):
    return f"{guide}-{mode}" + ("-strict" if offset else "")


def deliver(parent, packed, colors, fits, noise, query, cfg, threshold, *, edges=False):
    evidence = ~screening_mask(query)
    results = {"parent": parent}
    summaries = {}
    for guide, fit in fits.items():
        values, summary = {}, {}
        if any(fit["active"]):
            values, summary = restore_local_waves(
                parent,
                packed,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=cfg,
                thresholds=(threshold, threshold + 1),
                evidence_mask=evidence,
                guide_frequencies_xy=fit["frequencies_xy"],
                phase_bins=8,
                shrink_phase_fit=True,
                compare_pooled_support=True,
                compare_pooled_refit=True,
                compare_matched_refit=True,
                phase_edge_side="validation" if edges else None,
                active_guide_directions=fit["active"],
            )
        summaries[guide] = summary
        for mode in MODES:
            for offset in (0, 1):
                results[output_key(guide, mode, offset)] = values.get(
                    (mode, threshold + offset), parent
                )
    return results, summaries


def synthetic(plan, rows, cfg, out):
    query = offset_box(plan["query_xywh"])
    records = []
    for row in rows:
        case = read_json(checked(row["case"]))
        profile = case["profile"]
        noise = plan["profiles"][profile]
        threshold = plan["settings"][profile]["threshold"]
        shape = case["metadata"]["recipe"]
        angles = np.asarray(shape["wire_angles"])
        frequencies = (
            np.column_stack((np.cos(angles), np.sin(angles)))
            / np.asarray(shape["periods"])[:, None]
        )
        exact = {"active": [True, True], "frequencies_xy": frequencies.tolist()}
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        with np.load(checked(row["prediction"])) as archive:
            old = {k: archive[k] for k in ("parent", "parallel", "window_scene")}
        repeated, receipts = [], []
        for parent, samples, cfa, window, fixed in zip(
            old["parent"],
            packed,
            colors,
            row["scene_window_fits"],
            row["refined_fits_by_role"],
            strict=True,
        ):
            fits = {
                "fixed": fixed["parallel"],
                "scene": window["window_scene"],
                "exact-center": exact,
            }
            values, witnesses = deliver(parent, samples, cfa, fits, noise, query, cfg, threshold)
            repeated.append(values)
            receipts.append({"fits": fits, "scores": witnesses})
        arrays = {k: np.stack([r[k] for r in repeated]) for k in repeated[0]}
        for name, original in (("fixed", "parallel"), ("scene", "window_scene")):
            np.testing.assert_array_equal(
                arrays[output_key(name, "weighted-refit", 0)], old[original]
            )
        records.append(
            {
                "id": row["id"],
                "case": row["case"],
                "query": query,
                "prediction": write_array(out / f"{row['id']}.npz", **arrays),
                "roles": receipts,
                "previous_prediction": row["prediction"],
            }
        )
        print(row["id"], "both controls exact", flush=True)
    return records


def camera(plan, rows, cfg, out):
    sources = read_json(checked(plan["camera_baseline"]))["camera"]
    noises = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    results = []
    for row, witness in zip(rows, sources, strict=True):
        key, source = witness["id"], witness["source"]
        assert key == row["id"]
        query = row["query"]
        x, y, w, h = source["query_box"]
        with np.load(checked(source["query_arrays"])) as data:
            packed = data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = data["colors"][0]
        with np.load(checked(row["predictions"])) as a:
            parent = a["parent"]
            fits = {name: row["fits"][f"window_{name}"] for name in plan["camera_guides"]}
            values, witnesses = deliver(
                parent, packed, colors, fits, noises[key], query, cfg, 2, edges=True
            )
            for name in fits:
                np.testing.assert_array_equal(
                    values[output_key(name, "weighted-refit", 0)], a[f"window_{name}"]
                )
        results.append(
            row
            | {
                "fits": fits,
                "matched_query_scores": witnesses,
                "predictions": write_array(out / f"{key}.npz", **values),
                "previous_predictions": row["predictions"],
            }
        )
        print(key, "both controls exact", flush=True)
    return results


def collect(path):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    old = read_json(checked(plan["previous"]))
    cfg = LocalWaveConfig(**plan["config"])
    out = Path(plan["root"]) / "output"
    out.mkdir()
    start = time.monotonic()
    rows = synthetic(plan, old["synthetic"], cfg, out)
    cams = camera(plan, old["camera"], cfg, out)
    assert len(rows) == 16 and len(cams) == 8
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "CPU_wall_seconds": time.monotonic() - start,
            "restoration_calls": 0,
            "synthetic": rows,
            "camera": cams,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    run = actions.add_parser("collect")
    run.add_argument("plan", type=Path)
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.previous.resolve())
    else:
        collect(args.plan.resolve())
