"""Compare phase measurement pooling behind the saved two-boundary query fits."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
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
from demosaic.search_donor_geometry import screening_mask
from demosaic.surface_phase_aggregation import SURFACE_AGGREGATION

MODES = ("weighted-refit", "square-average", "tangent-average", "tangent-predictive-gate")


def prepare(root, previous):
    source = reference(previous / "output/collection.json")
    collected = read_json(checked(source))
    old = read_json(checked(collected["plan"]))
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
            "previous": source,
            "inputs": [source, old["camera_baseline"], old["camera_conditions"]],
            "config": collected["compared_configs"]["parallel"],
            "phase_averages": SURFACE_AGGREGATION.to_dict(),
            "modes": MODES,
            "scope": "Compare square and equal-area tangent phase-conditioned measurements on the "
            "saved planar guides, with the same two-boundary query nuisance. Hold out the same "
            "Bayer samples, use conditional-null residuals in both validation and delivery, and "
            "compare the tangent estimate with its own gate and the original predictive gate.",
        },
    )


def field(guide, mode, offset):
    return f"{guide}-{mode}" + ("-strict" if offset else "")


def deliver(parent, samples, colors, guides, noise, query, cfg, threshold, *, edges=False):
    values, diagnostics = {"parent": parent}, {}
    for name, guide in guides.items():
        output, witness = {}, {}
        if any(guide["active"]):
            output, witness = restore_local_waves(
                parent,
                samples,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=cfg,
                thresholds=(threshold, threshold + 1),
                evidence_mask=~screening_mask(query),
                guide_frequencies_xy=guide["frequencies_xy"],
                phase_bins=8,
                shrink_phase_fit=True,
                compare_pooled_support=True,
                compare_pooled_refit=True,
                compare_phase_averages=True,
                phase_edge_side="validation" if edges else None,
                active_guide_directions=guide["active"],
            )
        diagnostics[name] = witness
        values.update(
            {
                field(name, mode, offset): output.get((mode, threshold + offset), parent)
                for mode in MODES
                for offset in (0, 1)
            }
        )
    return values, diagnostics


def verify_control(new, previous, names):
    for guide in names:
        for offset in (0, 1):
            key = field(guide, "weighted-refit", offset)
            np.testing.assert_array_equal(new[key], previous[f"parallel-{key}"])


def synthetic(plan, rows, cfg, out):
    records = []
    for row in rows:
        case = read_json(checked(row["case"]))
        noise = plan["profiles"][case["profile"]]
        threshold = plan["settings"][case["profile"]]["threshold"]
        samples, cfa = sensor_box(case["sensor"], plan["query_xywh"])
        arrays, witnesses = [], []
        with np.load(checked(row["prediction"])) as old:
            for rgb, raw, colors, witness in zip(
                old["parent"], samples, cfa, row["roles"], strict=True
            ):
                guides = {n: witness["fits"][n] for n in ("scene", "exact-center")}
                result, details = deliver(
                    rgb, raw, colors, guides, noise, row["query"], cfg, threshold
                )
                arrays.append(result)
                witnesses.append(details)
            produced = {k: np.stack([r[k] for r in arrays]) for k in arrays[0]}
            verify_control(produced, old, ("scene", "exact-center"))
        records.append(
            {
                "id": row["id"],
                "case": row["case"],
                "previous": row["prediction"],
                "prediction": write_array(out / f"{row['id']}.npz", **produced),
                "witnesses": witnesses,
            }
        )
        print(row["id"], "exact controls", flush=True)
    return records


def camera(plan, rows, cfg, out):
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    noise = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    records = []
    for row, prior in zip(rows, baseline, strict=True):
        key, source = prior["id"], prior["source"]
        assert key == row["id"]
        x, y, w, h = source["query_box"]
        with np.load(checked(source["query_arrays"])) as data:
            packed = data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = data["colors"][0]
        with np.load(checked(row["predictions"])) as old:
            result, witness = deliver(
                old["parent"],
                packed,
                colors,
                row["fits"],
                noise[key],
                row["query"],
                cfg,
                2,
                edges=True,
            )
            verify_control(result, old, row["fits"])
        records.append(
            {
                "id": key,
                "fits": row["fits"],
                "query": row["query"],
                "previous": row["predictions"],
                "predictions": write_array(out / f"{key}.npz", **result),
                "witnesses": witness,
            }
        )
        print(key, "exact controls", flush=True)
    return records


def collect(path):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    before = read_json(checked(plan["previous"]))
    cfg = LocalWaveConfig(**plan["config"])
    out = Path(plan["root"]) / "output"
    out.mkdir()
    start = time.monotonic()
    synth = synthetic(plan, before["synthetic"], cfg, out)
    cams = camera(plan, before["camera"], cfg, out)
    assert len(synth) == 16 and len(cams) == 8
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "CPU_wall_seconds": time.monotonic() - start,
            "restoration_calls": 0,
            "synthetic": synth,
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
