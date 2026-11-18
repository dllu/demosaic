"""Compare query admission thresholds on an already donor-confirmed frequency bank."""

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_donor_frequency_bank import alternate_admissions, eight_refit, local_slice
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_scene_wire_footprint import STAGES
from probe_screened_scene_donors import offset_box
from probe_surface_aggregation import field

from demosaic.donor_frequency_bank import active_anchor
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig


def prepare(root, bank, oracle=False):
    old = reference(bank / "plan.json")
    plan = read_json(checked(old))
    stages = {s: reference(bank / f"{s}.json") for s in STAGES}
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [old, *stages.values(), *plan["inputs"]],
            "banks": stages,
            "oracle_frequency": oracle,
            "scope": "Compare trusting the highest donor-confirmed companion with requiring positive gains "
            "against the null and baseline on both query reserve folds. Reuse the exact saved bank and "
            "reserve scores. Both alternatives retain the established independent query delivery check.",
            **(
                {
                    "scope": "Diagnostic only. Nominal weak frequency ranks the confirmed bank. The "
                    "nearest candidate must be within one native bin and improve the existing match. "
                    "The final RAW fit and per-color validation use the original independent samples."
                }
                if oracle
                else {}
            ),
        },
    )


def oracle_guide(initial, decision, query, weak):
    anchor = active_anchor(initial)
    validated = [r["frequency_xy"] for r in decision["bank"]["shortlist"] if r["donor_valid"]]
    if anchor is None or not validated:
        return initial

    def distance(f):
        f = np.asarray(f)
        return min(np.linalg.norm(weak - f), np.linalg.norm(weak + f)) * min(query[2:])

    index = 1 - anchor
    closest = min(validated, key=distance)
    frequencies = list(initial["frequencies_xy"])
    if distance(closest) > 1 or (
        initial["active"][index] and distance(closest) >= distance(frequencies[index])
    ):
        return initial
    frequencies[index] = closest
    return initial | {"frequencies_xy": frequencies, "active": [True, True]}


def replay(
    parent,
    raw,
    colors,
    initial,
    decision,
    query,
    noise,
    config,
    threshold,
    previous,
    *,
    edge=False,
    nominal_weak=None,
):
    guides = (
        {"oracle": oracle_guide(initial, decision, query, nominal_weak)}
        if nominal_weak is not None
        else alternate_admissions(initial, decision["query_selection"])
    )
    fits = {}
    values = {}
    for arm, guide in guides.items():
        if guide == initial:
            restored = previous["screened"]
        elif guide == decision["final_guide"]:
            restored = previous["bank"]
        else:
            frequency = tuple(map(tuple, guide["frequencies_xy"]))
            if frequency not in fits:
                fits[frequency] = eight_refit(
                    parent, raw, colors, guide, query, noise, config, threshold, camera=edge
                )
            restored = fits[frequency]
        values.update({(arm, o): x for o, x in restored.items()})
    return values, guides


def synth(plan, config, stage, rows, output):
    split, iso = stage.split("-")
    main = split == "synthetic"
    key = "original_guides" if main else "disjoint_guides"
    originals = {r["id"]: r for r in read_json(checked(plan["source"][key]))["synthetic"]}
    query = offset_box(plan["query_xywh"])
    noise, threshold = plan["profiles"][iso], plan["settings"][iso]["threshold"]
    carried = []
    for row in rows:
        k = row["id"]
        case = read_json(checked(row["case"]))
        weak = None
        if plan.get("oracle_frequency", False):
            recipe = case["metadata"]["recipe"]
            theta = recipe["wire_angles"][1]
            weak = np.asarray([np.cos(theta), np.sin(theta)]) / recipe["periods"][1]
        samples, layouts = sensor_box(case["sensor"], plan["query_xywh"])
        current = originals[k]
        roles = current["roles"] if main else current["rankings"]
        with np.load(checked(row["prediction"])) as old:
            arrays = dict(old)
        results, records = [], []
        for i, (raw, colors, prev, bank) in enumerate(
            zip(samples, layouts, roles, row["bank_records"], strict=True)
        ):
            storage = {
                a: {j: arrays[field("scene", a, j)][i] for j in (0, 1)}
                for a in ("screened", "bank")
            }
            values, choices = replay(
                arrays["parent"][i],
                raw,
                colors,
                prev["fits"]["scene"],
                bank,
                query,
                noise,
                config,
                threshold,
                storage,
                nominal_weak=weak,
            )
            results.append(values)
            records.append(choices)
        values = {
            field("scene", arm, o): np.stack([d[arm, o] for d in results]) for arm, o in results[0]
        }
        carried.append(
            row
            | {
                "before": row["prediction"],
                "admission": records,
                "prediction": write_array(output / f"{k}.npz", **(arrays | values)),
            }
        )
        print(stage, k, flush=True)
    return carried


def camera(plan, config, rows, output):
    sources = read_json(checked(plan["camera_baseline"]))["camera"]
    originals = read_json(checked(plan["previous"]))["camera"]
    profiles = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    carried = []
    for row, old, source in zip(rows, originals, sources, strict=True):
        key, source = source["id"], source["source"]
        assert key == row["id"] == old["id"]
        query = old["query"]
        x, y, *_ = source["query_box"]
        frame = (query[0] - x, query[1] - y)
        with np.load(checked(source["query_arrays"])) as f:
            raw, colors = local_slice(f["packed"][0], query, frame), f["colors"][0]
        with np.load(checked(row["predictions"])) as f:
            values = dict(f)
        receipts = {}
        for g, guide in old["fits"].items():
            saved = {a: {o: values[field(g, a, o)] for o in (0, 1)} for a in ("screened", "bank")}
            fitted, receipts[g] = replay(
                values["parent"],
                raw,
                colors,
                guide,
                row["bank_records"][g],
                query,
                profiles[key],
                config,
                2,
                saved,
                edge=True,
            )
            values.update({field(g, arm, o): x for (arm, o), x in fitted.items()})
        carried.append(
            row
            | {
                "before": row["predictions"],
                "admission": receipts,
                "predictions": write_array(output / f"{key}.npz", **values),
            }
        )
        print("camera", key, flush=True)
    return carried


def run(path, stage):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    if stage == "camera" and plan.get("oracle_frequency", False):
        raise ValueError("The nominal-frequency diagnostic requires constructed targets")
    root = path.parent
    output = root / f"arrays-{stage}"
    output.mkdir()
    config = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    previous = read_json(checked(plan["banks"][stage]))["rows"]
    rows = (
        camera(plan, config, previous, output)
        if stage == "camera"
        else synth(plan, config, stage, previous, output)
    )
    write_json(
        root / f"{stage}.json",
        {"plan": reference(path), "producer": reference(__file__), "rows": rows},
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_subparsers(dest="mode", required=True)
    setup = modes.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("bank", type=Path)
    setup.add_argument("--oracle-frequency", action="store_true")
    execute = modes.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("stage", choices=STAGES)
    args = cli.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.bank.resolve(), args.oracle_frequency)
    else:
        run(args.plan.resolve(), args.stage)
