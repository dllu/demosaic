"""Test a reserved-RAW veto on transferring one carrier's footprint to another."""

import argparse
import json
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_fresh_wire_envelopes import targets
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_reserved_wire_footprint import predict
from probe_scene_wire_footprint import PANELS
from probe_screened_scene_donors import offset_box
from probe_surface_aggregation import field
from probe_wire_envelopes import score

from demosaic.cfa import PATTERNS
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.reserved_wire_footprint import select_wire_footprint

CONTROLS = ("fresh400", "fresh6400", "null400", "null6400")
STAGES = (*PANELS, *CONTROLS, "camera")


def bind(directory, names):
    return {name: reference(directory / f"{name}.json") for name in names}


def prepare(root, fundamental, eight, camera, sine, controls):
    extent = reference(fundamental / "plan.json")
    plan = read_json(checked(extent))
    archive = {
        "fundamental": bind(fundamental, PANELS) | bind(camera, ("camera",)),
        "eight": bind(eight, (*PANELS, "camera")),
        "sine": bind(sine, CONTROLS),
        "controls": bind(controls, CONTROLS),
    }
    source = reference(sine / "plan.json")
    root.mkdir()
    work, frozen = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "probe_matched_query_evidence.py"]
    )
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": frozen,
            "inputs": [
                extent,
                source,
                *plan["inputs"],
                *(p for r in archive.values() for p in r.values()),
            ],
            "sine_plan": source,
            "sources": archive,
            "scope": "Compare the other direction's localized prediction to absent and to uniform at the "
            "stronger direction's already confirmed reserve location. Retain the previous partner output "
            "only when all four companion gains are positive. Use the exact saved uniform output otherwise.",
        },
    )


def read_stage(plan, kind, stage):
    return read_json(checked(plan["sources"][kind][stage]))["rows"]


def confirm(raw, colors, guide, noise, query, config, prior):
    if not all(guide["active"]) or not prior.get("confirmed", False):
        return {"accepted": False, "reason": "no anchor"}
    _, receipt = select_wire_footprint(
        raw,
        colors,
        query,
        guide["frequencies_xy"],
        guide["active"],
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        record_partner=True,
    )
    partner = receipt.pop("partner")
    receipt = json.loads(json.dumps(receipt))
    assert all(prior[k] == v for k, v in receipt.items())
    return {
        "accepted": min(*partner["wave_scores"], *partner["localization_scores"]) > 0,
        **partner,
    }


def wires(plan, config, stage):
    split, profile = stage.split("-")
    root = Path(plan["root"])
    noise = plan["profiles"][profile]
    origin = "original_guides" if split == "synthetic" else "disjoint_guides"
    archived = {r["id"]: r for r in read_json(checked(plan["source"][origin]))["synthetic"]}
    guides = ("scene", "exact-center") if split == "synthetic" else ("scene",)
    rows = []
    for first, second in zip(
        read_stage(plan, "fundamental", stage), read_stage(plan, "eight", stage), strict=True
    ):
        key = first["id"]
        old = archived[key]
        assert key == second["id"]
        case = read_json(checked(first["case"]))
        raw, colors = sensor_box(case["sensor"], plan["query_xywh"])
        query = old["query"] if split == "synthetic" else offset_box(plan["query_xywh"])
        roles = old["roles"] if split == "synthetic" else old["rankings"]
        gates = {
            g: [
                confirm(p, c, r["fits"][g], noise, query, config, t[g])
                for p, c, r, t in zip(raw, colors, roles, first["witnesses_flexible"], strict=True)
            ]
            for g in guides
        }
        arrays = {}
        for basis, source in (("fund", first), ("eight", second)):
            with np.load(checked(source["prediction"])) as f:
                for g, t in product(guides, (0, 1)):
                    arrays[field(g, basis, t)] = np.stack(
                        [
                            f[field(g, "partner" if gate["accepted"] else "uniform", t)][i]
                            for i, gate in enumerate(gates[g])
                        ]
                    )
        rows.append(
            {"id": key, "gates": gates, "prediction": write_array(root / f"{key}.npz", **arrays)}
        )
        print(stage, key, sum(x["accepted"] for v in gates.values() for x in v), flush=True)
    return rows


def rail_controls(plan, config, stage):
    sine = read_json(checked(plan["sine_plan"]))
    recipe = structure_module(sine["structure"])
    profile = "iso6400" if stage.endswith("6400") else "iso400"
    noise, setting = plan["profiles"][profile], plan["settings"][profile]
    saved = read_stage(plan, "sine", stage)
    complex_fit = read_stage(plan, "controls", stage)
    rows = []
    if stage.startswith("null"):
        original = read_json(checked(sine["null_source"]))["rows"]
        cases = [r for r in original if r["profile"] == profile]
        for row, first, second in zip(cases, saved, complex_fit, strict=True):
            style = row["style"]
            ctor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
            parent = ctor(style, row["angle_radians"], *row["width_shift_level_height"])
            colors = np.asarray(PATTERNS[row["CFA"]])
            rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
            packed = recipe.corrupt(parent, colors, rng, noise)
            guide = {"active": [True, True], "frequencies_xy": row["guide_frequencies_xy"]}
            gate = confirm(packed, colors, guide, noise, recipe.QUERY, config, first["selection"])
            arm = "partner" if gate["accepted"] else "uniform"
            rows.append(
                {
                    "style": style,
                    "trial": row["trial"],
                    "gate": gate,
                    "metrics": {
                        basis + suffix: r["metrics"][arm + suffix]
                        for basis, r in (("fund", first), ("eight", second))
                        for suffix in ("", "-strict")
                    },
                }
            )
    else:
        seed = sine["fresh_seed"]
        t = setting["threshold"]
        for i, (first, second) in enumerate(zip(saved, complex_fit, strict=True)):
            parent, strong, both, frequencies, masks, _ = targets(i, seed)
            colors = np.asarray(PATTERNS[first["CFA"]])
            guide = {"active": [True, True], "frequencies_xy": frequencies.tolist()}
            gates = []
            for j, truth in enumerate((strong, both)):
                rng = np.random.default_rng(
                    np.random.SeedSequence([seed, 1, int(profile == "iso6400"), i, j])
                )
                raw = recipe.corrupt(truth, colors, rng, noise)
                gates.append(
                    confirm(raw, colors, guide, noise, recipe.QUERY, config, first["selection"][j])
                )
            if gates[0]["accepted"] == gates[1]["accepted"]:
                arm = "partner" if gates[0]["accepted"] else "uniform"
                metrics = {
                    basis + suffix: r["metrics"][arm + suffix]
                    for basis, r in (("fund", first), ("eight", second))
                    for suffix in ("", "-strict")
                }
            else:
                metrics = {}
                for full, basis in ((False, "fund"), (True, "eight")):
                    images = []
                    for j, (truth, gate) in enumerate(zip((strong, both), gates, strict=True)):
                        seed_words = [seed, 1, int(profile == "iso6400"), i, j]
                        raw = recipe.corrupt(
                            truth,
                            colors,
                            np.random.default_rng(np.random.SeedSequence(seed_words)),
                            noise,
                        )
                        output, _ = predict(
                            parent,
                            raw,
                            colors,
                            guide,
                            noise,
                            recipe.QUERY,
                            config,
                            t,
                            partner_only=True,
                            full_profile=full,
                        )
                        arm = "partner" if gate["accepted"] else "uniform"
                        images.append({(basis, k): output[arm, k] for k in (t, t + 1)})
                    metrics.update(
                        score(
                            parent, strong, both, images, masks["exact"] == 0, setting["scale"], t
                        )
                    )
            rows.append({"case": i, "gates": gates, "metrics": metrics})
    return rows


def camera(plan, config):
    earlier = read_json(checked(plan["previous"]))["camera"]
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    conditions = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    rows = []
    for old, b, x, y in zip(
        earlier,
        baseline,
        read_stage(plan, "fundamental", "camera"),
        read_stage(plan, "eight", "camera"),
        strict=True,
    ):
        key = old["id"]
        assert key == b["id"] == x["id"] == y["id"]
        qx, qy, w, h = b["source"]["query_box"]
        with np.load(checked(b["source"]["query_arrays"])) as f:
            packed = f["packed"][0, :, qy // 2 : (qy + h) // 2, qx // 2 : (qx + w) // 2]
            colors = f["colors"][0]
        gates = {
            g: confirm(
                packed, colors, guide, conditions[key], old["query"], config, x["flexible_edges"][g]
            )
            for g, guide in old["fits"].items()
        }
        rows.append({"id": key, "gates": gates})
    return rows


def run(path, stage):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    config = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    if stage == "camera":
        rows = camera(plan, config)
    elif stage in CONTROLS:
        rows = rail_controls(plan, config, stage)
    else:
        rows = wires(plan, config, stage)
    write_json(
        path.parent / f"{stage}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("prepare")
    for arg in ("root", "fundamental", "eight", "camera", "sine", "controls"):
        setup.add_argument(arg, type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("stage", choices=STAGES)
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(
            *(
                getattr(args, k).resolve()
                for k in ("root", "fundamental", "eight", "camera", "sine", "controls")
            )
        )
    else:
        run(args.plan.resolve(), args.stage)
