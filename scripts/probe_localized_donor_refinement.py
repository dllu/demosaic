"""Refine the edge nuisance and add an independent query-screening control."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_localized_donor_support import deliver_options
from probe_screened_scene_donors import offset_box

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.localized_donor_geometry import localize_donor_geometry


def prepare(root, previous, parallel_only):
    old_plan = reference(previous / "plan.json")
    previous_result = reference(previous / "output/collection.json")
    plan = read_json(checked(old_plan))
    assert read_json(checked(previous_result))["plan"] == old_plan
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_wave_guides.py"]
    )
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                old_plan,
                previous_result,
                plan["camera_baseline"],
                plan["camera_conditions"],
            ],
            "previous": previous_result,
            "parallel_only": parallel_only,
            "arms": [*plan["arms"], *(["parallel"] if parallel_only else ["refined", "query"])],
            "scope": "Replay all base arrays exactly. Use independently refined, full-offset affine-plus-step "
            "nuisance fits in donor screening and each of its two reserved folds. The optional query "
            "arm ranks the same candidate catalog by its A-only Fourier benefit first. Query B/C "
            "support, parent fallback and delivery scale stay the same. The four retained edge-only "
            "fields motivated this follow-up; no new thresholds are tuned against them.",
        },
    )


def unpack(rows):
    views = []
    for row in rows:
        with np.load(checked(row["raw"])) as f:
            views.append((f["packed"], f["colors"], row["box"]))
    return views


def local(views, query, noise, query_measurements=None, *, parallel=False):
    return localize_donor_geometry(
        views,
        query,
        shot=noise["shot"],
        read=noise["read"],
        unequal=True,
        refined_edge=True,
        query_measurements=query_measurements,
        parallel_edge=parallel,
    )


def base_fit(plan, views, query, noise):
    if plan["parallel_only"]:
        return {"parallel": local(views, query, noise, parallel=True)}
    return {"refined": local(views, query, noise)}


def with_query(plan, fit, views, query, noise, measurements):
    if plan["parallel_only"]:
        return fit
    return fit | {"query": local(views, query, noise, measurements)}


def synthetic(plan, previous, config, out):
    query = offset_box(plan["query_xywh"])
    cases = []
    for row in previous:
        c = read_json(checked(row["case"]))
        noise = plan["profiles"][c["profile"]]
        threshold = plan["settings"][c["profile"]]["threshold"]
        views = unpack(row["donors"])
        base = base_fit(plan, views, query, noise)
        packed, colors = sensor_box(c["sensor"], plan["query_xywh"])
        with np.load(checked(row["prediction"])) as f:
            predicted = dict(f)
        outputs, guides = [], []
        for p, raw, layout in zip(predicted["parent"], packed, colors, strict=True):
            fit = with_query(plan, base, views, query, noise, (raw, layout))
            outputs.append(deliver_options(p, raw, layout, fit, query, noise, config, threshold))
            guides.append(fit)
        for arm in guides[0]:
            predicted[arm] = np.stack([v[arm] for v in outputs])
        ctrl = row["edge_control"]
        if ctrl:
            edges = unpack(ctrl["inputs"])
            edge_fit = with_query(
                plan,
                base_fit(plan, edges, query, noise),
                edges,
                query,
                noise,
                (packed[0], colors[0]),
            )
            ctrl = ctrl | {"fits": ctrl["fits"] | edge_fit}
        cases.append(
            row
            | {
                "role2_fits": row.get("role2_fits", row["fits"]) | guides[2],
                "refined_fits_by_role": [
                    a | b
                    for a, b in zip(
                        row.get("refined_fits_by_role", [{}, {}, {}]), guides, strict=True
                    )
                ],
                "edge_control": ctrl,
                "prediction": write_array(out / f"{row['id']}.npz", **predicted),
            }
        )
        print(row["id"], [v["active"] for v in guides[2].values()], flush=True)
    return cases


def camera(plan, previous, config, out):
    source = read_json(checked(plan["camera_baseline"]))["camera"]
    noise_by_key = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    cameras = []
    for row, scene in zip(previous, source, strict=True):
        key, original = scene["id"], scene["source"]
        assert key == row["id"]
        query = row["query"]
        fx, fy, *_ = row["frame"]
        x, y, w, h = original["query_box"]
        noise = noise_by_key[key]
        with np.load(checked(original["query_arrays"])) as f:
            raw, colors = f["packed"][0], f["colors"][0]
        donors = [
            (
                raw[:, (b - fy) // 2 : (b - fy + d) // 2, (a - fx) // 2 : (a - fx + c) // 2],
                colors,
                (a, b, c, d),
            )
            for a, b, c, d in row["fits"]["whole"].get("donor_boxes", [])
        ]
        native = raw[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
        fits = with_query(
            plan, base_fit(plan, donors, query, noise), donors, query, noise, (native, colors)
        )
        with np.load(checked(row["predictions"])) as f:
            predicted = dict(f)
        predicted.update(
            deliver_options(
                predicted["parent"], native, colors, fits, query, noise, config, 2.0, edge=True
            )
        )
        cameras.append(
            row
            | {
                "fits": row["fits"] | fits,
                "predictions": write_array(out / f"{key}.npz", **predicted),
            }
        )
        print(key, [f["active"] for f in fits.values()], flush=True)
    return cameras


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cfg = LocalWaveConfig(**plan["config"])
    previous = read_json(checked(plan["previous"]))
    out = Path(plan["root"]) / "output"
    out.mkdir()
    start = time.monotonic()
    cameras = camera(plan, previous["camera"], cfg, out)
    rows = synthetic(plan, previous["synthetic"], cfg, out)
    assert len(rows) == 16 and len(cameras) == 8
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "synthetic": rows,
            "camera": cameras,
            "seconds": time.monotonic() - start,
            "neural_calls": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    parser.add_argument("--parallel-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve(), args.parallel_only)
    else:
        collect(args.path.resolve())
