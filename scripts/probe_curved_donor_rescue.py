"""Test adding one independently confirmed swept carrier to a selected bracket."""

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
from demosaic.search_donor_geometry import recover_curved_direction, screening_mask


def prepare(root, previous, fresh):
    paths = [
        previous / "plan.json",
        previous / "output/collection.json",
        fresh / "plan.json",
        fresh / "output/collection.json",
    ]
    bindings = [reference(p) for p in paths]
    base, held_out = read_json(paths[0]), read_json(paths[2])
    assert read_json(paths[1])["plan"] == bindings[0]
    assert read_json(paths[3])["plan"] == bindings[2]
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        base
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                *bindings,
                base["camera_baseline"],
                base["camera_conditions"],
                base["previous_plan"],
            ],
            "retained": bindings[1],
            "fresh": bindings[3],
            "fresh_plan": bindings[2],
            "arms": ["guarded", "planar", "weighted", "scene", "curved"],
            "rendering": base["rendering"]
            | {
                "labels": [
                    "Guarded guide",
                    "Spectral rank",
                    "Weighted context",
                    "Scene affinity",
                    "Added curvature",
                ],
                "camera_label": "Added curvature",
                "sources": [83, 85],
            },
            "fresh_device": held_out["parent_device"],
            "scope": "Keep the chosen appearance-first bracket. On brackets with one supported screened "
            "family, test a second family allowing 45 degrees and 0.06 cycles/pixel between the A-only "
            "peaks. Accept only shared curvature beating individual planar donor fits on the "
            "reserved samples. Keep original first geometry and deliver through exact prior query "
            "evidence and scaling. The peak spread was chosen after inspecting retained geometry; "
            "fresh observations provide a separate check.",
        },
    )


def loaded_rows(bindings, boxes):
    views = []
    for binding, box in zip(bindings, boxes, strict=True):
        with np.load(checked(binding)) as f:
            views.append((f["packed"], f["colors"], box))
    return views


def update_query(parent, sensor, colors, fit, views, query, noise, cfg, t, placement, cached):
    cache_key = (
        tuple(map(tuple, fit.get("donor_boxes", []))),
        tuple(fit["active"]),
        tuple(map(tuple, fit.get("frequencies_xy", []))),
    )
    if cache_key not in cached:
        cached[cache_key] = recover_curved_direction(
            views, query, fit, shot=noise["shot"], read=noise["read"]
        )
    geometry = cached[cache_key]
    if not geometry["curved_direction_added"]:
        return geometry, None
    return geometry, deliver(
        parent,
        sensor,
        colors,
        geometry,
        noise,
        cfg,
        t,
        placement == "near",
        True,
        evidence_mask=~screening_mask(query),
    )


def camera(plan, source, cfg, out):
    rows = read_json(checked(plan["camera_baseline"]))["camera"]
    conditions = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    result = []
    for old, row in zip(source, rows, strict=True):
        key, s = row["id"], row["source"]
        assert old["id"] == key
        x, y, w, h = s["query_box"]
        ox, oy, *_ = old["frame"]
        abs_box = s["absolute_query_xywh"]
        with np.load(checked(s["query_arrays"])) as data:
            raw, cs = data["packed"][0], data["colors"][0]
        views = [
            (
                raw[:, (b - oy) // 2 : (b - oy + d) // 2, (a - ox) // 2 : (a - ox + c) // 2],
                cs,
                (a, b, c, d),
            )
            for a, b, c, d in old["candidate_boxes"]
        ]
        p = np.load(checked(s["parent_prediction"]), mmap_mode="r")[0, :, y : y + h, x : x + w]
        alt, pixels = update_query(
            p,
            raw[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
            cs,
            old["fits"]["scene"],
            views,
            abs_box,
            conditions[key],
            cfg,
            (2.0,),
            "near",
            {},
        )
        prediction = (
            old["predictions"]["scene"]
            if pixels is None
            else write_array(out / f"{key}.npz", corrected=pixels[2.0])
        )
        result.append(
            old
            | {
                "fit": alt,
                "prediction": prediction,
                "fits": old["fits"] | {"curved": alt},
                "predictions": old["predictions"] | {"curved": prediction},
            }
        )
        print(key, alt["curved_direction_added"], flush=True)
    return result


def synthetic(plan, source, cfg, out, held_out):
    inherited = read_json(checked(plan["previous_plan"]))
    decoys = plan["synthetic_appearance_stress"]["decoy_boxes"]
    boxes = [offset_box(b) for b in (inherited["left_xywh"], inherited["right_xywh"], *decoys)]
    query = offset_box(plan["query_xywh"])
    fresh_plan = read_json(checked(plan["fresh_plan"])) if held_out else None
    records, cached = [], {}
    for row in source:
        case = read_json(checked(row if held_out else row["case"]))
        row = case if held_out else row
        profile, placement = case["profile"], "far" if held_out else case["placement"]
        noise = plan["profiles"][profile]
        if held_out:
            views = loaded_rows(
                [d["raw"] for d in case["donors"]], [d["box"] for d in case["donors"]]
            )
            with np.load(checked(case["parent"])) as f:
                parent = f["parent"][ROI]
            thresholds = [fresh_plan["settings"][profile]["threshold"]]
            ar = lambda arm, _t: arm
            arms = fresh_plan["arms"]
        else:
            views = loaded_rows([d["raw"] for d in row["decoys"]], boxes)
            parent = np.load(checked(case["parent"]), mmap_mode="r")[ROI]
            thresholds = sorted(
                {
                    s["threshold"]
                    for s in plan["settings"]
                    if (s["profile"], s["placement"]) == (profile, placement)
                }
            )
            ar = lambda arm, t: f"{arm}--t{t:g}"
            arms = plan["arms"][:-1]
        with np.load(checked(row["prediction"])) as f:
            predictions = {ar(arm, t): f[ar(arm, t)] for arm in arms for t in thresholds}
        native, colors = sensor_box(case["sensor"], plan["query_xywh"])
        guides = []
        cache = cached.setdefault((profile, case["source"]), {})
        for role, witness in enumerate(row["rankings"]):
            fit, pixels = update_query(
                parent[role],
                native[role],
                colors[role],
                witness["fits"]["scene"],
                views,
                query,
                noise,
                cfg,
                thresholds,
                placement,
                cache,
            )
            guides.append(witness | {"fits": witness["fits"] | {"curved": fit}})
            for t in thresholds:
                v = predictions[ar("scene", t)][role] if pixels is None else pixels[t]
                predictions.setdefault(ar("curved", t), []).append(v)
        destination = out / ("fresh-" if held_out else "") / f"{row['id']}.npz"
        result = row | {
            "rankings": guides,
            "prediction": write_array(
                destination, **{k: np.asarray(v) for k, v in predictions.items()}
            ),
        }
        records.append(result)
        print(
            row["id"], [v["fits"]["curved"]["curved_direction_added"] for v in guides], flush=True
        )
    return records


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    old = read_json(checked(plan["retained"]))
    fresh = read_json(checked(plan["fresh"]))
    out = Path(plan["root"]) / "output"
    out.mkdir()
    (out / "fresh-").mkdir()
    config = LocalWaveConfig(**plan["config"])
    start = time.monotonic()
    cameras = camera(plan, old["camera"], config, out)
    saved = synthetic(plan, old["synthetic"], config, out, False)
    new = synthetic(plan, fresh["cases"], config, out, True)
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "camera": cameras,
            "synthetic": saved,
            "fresh": new,
            "seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path, nargs=2)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), *(p.resolve() for p in args.prepare_from))
    elif args.report:
        report(args.path.resolve())
    else:
        collect(args.path.resolve())
