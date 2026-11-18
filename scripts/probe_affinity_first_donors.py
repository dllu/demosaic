"""Restore queries after ranking spectrally compatible pairs by appearance."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import report, sensor_box
from probe_fresh_phase_refit import write_array
from probe_screened_scene_donors import offset_box
from probe_search_donor_geometry import deliver
from report_fold_support_pooling import ROI

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.search_donor_geometry import screening_mask, search_donor_geometry

ARMS = ("guarded", "planar", "weighted", "near", "scene")
CONTEXT = ARMS[-2:]
PREVIOUS = {"guarded": "guarded", "planar": "planar", "weighted": "scene"}


def prepare(root, earlier):
    plan_path = reference(earlier / "plan.json")
    collection_path = reference(earlier / "output/collection.json")
    source = read_json(checked(plan_path))
    collection = read_json(checked(collection_path))
    assert collection["plan"] == plan_path
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        {
            **{
                k: source[k]
                for k in (
                    "camera_baseline",
                    "camera_conditions",
                    "parent_checkpoint",
                    "config",
                    "profiles",
                    "settings",
                    "query_xywh",
                    "previous_plan",
                    "synthetic_appearance_stress",
                    "photos",
                    "encoder_revision",
                )
            },
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                plan_path,
                collection_path,
                source["camera_baseline"],
                source["camera_conditions"],
                source["previous_plan"],
            ],
            "source_plan": plan_path,
            "source_collection": collection_path,
            "arms": ARMS,
            "rendering": {
                "labels": [
                    "Guarded guide",
                    "Spectral rank",
                    "Weighted context",
                    "Near affinity",
                    "Scene affinity",
                ],
                "sources": [81, 85],
                "camera_label": "Scene affinity",
                "contrast": 5,
            },
            "scope": "Use archived role-specific context affinities and exact RAW observations. Among "
            "brackets passing the same screening spectrum checks, select by the weaker donor's affinity "
            "before any withheld tests. Fit geometry on the selected donor pair and deliver only "
            "query-supported additions. Same query evidence masks, fixed thresholds and guarded fallback "
            "as the matched weighted-context comparison. No new neural forwards. The synthetic panel "
            "was used to motivate the rank change and is a development replay.",
        },
    )


def choose(views, query, noise, prior, arm):
    return search_donor_geometry(
        views,
        query,
        shot=noise["shot"],
        read=noise["read"],
        donor_affinity=prior["affinities"][arm],
        affinity_first=True,
    )


def same_geometry(a, b):
    keys = ("donor_boxes", "active", "frequencies_xy", "hessians_xy")
    return all(a.get(k) == b.get(k) for k in keys)


def camera_replays(plan, previous, cfg, output):
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    conditions = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    rows = []
    for row, control in zip(baseline, previous, strict=True):
        key, source = row["id"], row["source"]
        assert key == control["id"]
        ox, oy, *_ = control["frame"]
        x, y, w, h = source["query_box"]
        absolute = source["absolute_query_xywh"]
        noise = conditions[key]
        with np.load(checked(source["query_arrays"])) as f:
            packed, colors = f["packed"][0], f["colors"][0]
        views = []
        for box in control["candidate_boxes"]:
            bx, by, bw, bh = box
            start_x, start_y = (bx - ox) // 2, (by - oy) // 2
            tiles = packed[:, start_y : start_y + bh // 2, start_x : start_x + bw // 2]
            views.append((tiles, colors, box))
        parent = np.load(checked(source["parent_prediction"]), mmap_mode="r")[
            0, :, y : y + h, x : x + w
        ]
        native = packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
        eligible = ~screening_mask(absolute)
        predictions = {
            "planar": control["predictions"]["planar"],
            "weighted": control["predictions"]["scene"],
        }
        fits = {"planar": control["fits"]["planar"], "weighted": control["fits"]["scene"]}
        reuses = {}
        for arm in CONTEXT:
            fit = choose(views, absolute, noise, control, arm)
            match = next((key for key, prior in fits.items() if same_geometry(fit, prior)), None)
            if match is not None:
                predictions[arm] = predictions[match]
                reuses[arm] = match
            elif any(fit["active"]):
                values = deliver(
                    parent,
                    native,
                    colors,
                    fit,
                    noise,
                    cfg,
                    (2.0,),
                    True,
                    False,
                    evidence_mask=eligible,
                )
                predictions[arm] = write_array(output / f"{key}-{arm}.npz", corrected=values[2.0])
            else:
                predictions[arm] = row["crosscheck_prediction"]
                reuses[arm] = "cross-checked fallback"
            fits[arm] = fit
        rows.append(
            control
            | {
                "fit": fits["scene"],
                "prediction": predictions["scene"],
                "fits": fits,
                "predictions": predictions,
                "reused": reuses,
            }
        )
        print(key, [fits[arm]["active"] for arm in CONTEXT], flush=True)
    return rows


def synthetic_replays(plan, previous, cfg, output):
    old = read_json(checked(plan["previous_plan"]))
    spec = plan["synthetic_appearance_stress"]
    boxes = [offset_box(b) for b in (old["left_xywh"], old["right_xywh"], *spec["decoy_boxes"])]
    query = offset_box(plan["query_xywh"])
    eligible = ~screening_mask(query)
    records = []
    for row in previous:
        case = read_json(checked(row["case"]))
        noise = plan["profiles"][case["profile"]]
        thresholds = sorted(
            {
                s["threshold"]
                for s in plan["settings"]
                if (s["profile"], s["placement"]) == (case["profile"], case["placement"])
            }
        )
        views = []
        for donor, box in zip(row["decoys"], boxes, strict=True):
            with np.load(checked(donor["raw"])) as pixels:
                views.append((pixels["packed"], pixels["colors"], box))
        with np.load(checked(row["prediction"])) as f:
            pred = {
                f"{arm}--t{t:g}": f[f"{source}--t{t:g}"]
                for arm, source in PREVIOUS.items()
                for t in thresholds
            }
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        parent = np.load(checked(case["parent"]), mmap_mode="r")[ROI]
        guides = []
        for role, prior in enumerate(row["rankings"]):
            fits = {arm: prior["fits"][PREVIOUS[arm]] for arm in ("planar", "weighted")}
            values = {
                arm: {t: pred[f"{arm}--t{t:g}"][role] for t in thresholds} for arm in PREVIOUS
            }
            reuses = {}
            for arm in CONTEXT:
                fit = choose(views, query, noise, prior, arm)
                match = next((key for key, f in fits.items() if same_geometry(fit, f)), None)
                if match is not None:
                    values[arm] = values[match]
                    reuses[arm] = match
                elif any(fit["active"]):
                    values[arm] = deliver(
                        parent[role],
                        packed[role],
                        colors[role],
                        fit,
                        noise,
                        cfg,
                        thresholds,
                        case["placement"] == "near",
                        False,
                        evidence_mask=eligible,
                    )
                else:
                    values[arm] = values["guarded"]
                    reuses[arm] = "guarded"
                fits[arm] = fit
                for t in thresholds:
                    pred.setdefault(f"{arm}--t{t:g}", []).append(values[arm][t])
            guides.append(prior | {"fits": fits, "reused": reuses})
        records.append(
            row
            | {
                "rankings": guides,
                "prediction": write_array(
                    output / f"{row['id']}.npz", **{k: np.asarray(v) for k, v in pred.items()}
                ),
            }
        )
        print(len(records), row["id"], guides[-1]["reused"], flush=True)
    return records


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    previous = read_json(checked(plan["source_collection"]))
    assert previous["plan"] == plan["source_plan"]
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    start = time.monotonic()
    camera = camera_replays(plan, previous["camera"], cfg, output)
    write_json(output / "camera-collection.json", {"plan": reference(path), "camera": camera})
    synthetic = synthetic_replays(plan, previous["synthetic"], cfg, output)
    assert len(camera) == 8 and len(synthetic) == 32
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "camera": camera,
            "synthetic": synthetic,
            "seconds": time.monotonic() - start,
            "new_neural_forwards": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--prepare-from", type=Path)
    group.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    elif args.report:
        report(args.path.resolve())
    else:
        collect(args.path.resolve())
