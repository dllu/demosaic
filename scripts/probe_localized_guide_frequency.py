"""Replay companion-frequency selection with and without anchor localization."""

import argparse
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_finite_wire_profiles import controls
from probe_flexible_query_edges import camera
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import structure_module
from probe_screened_scene_donors import offset_box
from probe_shared_projective_phase import target
from probe_surface_aggregation import field
from probe_wire_envelopes import score

from demosaic.cfa import PATTERNS
from demosaic.donor_frequency_bank import active_anchor
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.finite_wire_profiles import reserve_wire_profiles
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.localized_guide_frequency import frequency_neighborhood, reserve_companion_frequencies
from demosaic.reserved_wire_footprint import select_wire_footprint
from demosaic.search_donor_geometry import screening_mask

ARMS = ("flexible", "fixed-focused", "uniform-frequency", "localized-frequency")
PANELS = (
    "projective400",
    "projective6400",
    "synthetic",
    "disjoint",
    "null400",
    "null6400",
    "camera",
)
PROFILE_NAMES = ("iso400", "iso6400")


def prepare(root, previous, bank):
    original = reference(previous / "plan.json")
    plan = read_json(checked(original))
    source = {
        f"{split}-{profile}": reference(bank / f"{split}-{profile}.json")
        for split in ("synthetic", "disjoint")
        for profile in PROFILE_NAMES
    }
    replays = {panel: reference(previous / f"{panel}.json") for panel in PANELS}
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(),
        root,
        [
            Path(__file__).name,
            "probe_finite_wire_profiles.py",
            "probe_shared_projective_phase.py",
            "probe_matched_query_evidence.py",
        ],
    )
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [*plan["inputs"], original, *source.values(), *replays.values()],
            "conditioned_replay": original,
            "bank_replays": source,
            "prior_profile_panels": replays,
            "shift_bins": 1.0,
            "previous_arms": plan["profile_arms"],
            "profile_arms": ARMS,
            "scope": "Replay ranked candidate frequencies on the same query screening reserve. Compare held-out "
            "conditional predictions with uniform and anchor-derived tapered carrier bases. Both search "
            "policies use the same selected-footprint narrow-profile delivery and independent RAW sites. "
            "Retain original eight-knot and fixed-frequency focused controls. The constructed pairs use "
            "corrupted center guides and exact quadratic curvature for frequency-specific diagnosis.",
        },
    )


def deliver(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    cfg,
    threshold,
    *,
    edge_side,
    hessians,
    taper=None,
    narrow=False,
):
    stops = (threshold, threshold + 1)
    if not any(guide["active"]):
        return {i: parent for i in range(2)}, None
    anchor = active_anchor(guide)
    envelopes = None
    profiles, details = None, None
    if narrow and all(guide["active"]):
        if taper is not None:
            envelopes = np.stack((taper, taper))
            envelopes[anchor] = 1
        options, details = reserve_wire_profiles(
            packed,
            colors,
            query,
            guide,
            shot=noise["shot"],
            read=noise["read"],
            config=cfg,
            hessians=hessians,
            envelopes=envelopes,
            minimum_gain=0 if taper is not None else 1,
        )
        profiles = tuple(None if i == anchor else p for i, p in enumerate(options))
    out, _ = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=cfg,
        thresholds=stops,
        evidence_mask=~screening_mask(query),
        guide_frequencies_xy=guide["frequencies_xy"],
        guide_phase_hessians_xy=hessians,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        phase_edge_side="validation" if edge_side else None,
        active_guide_directions=guide["active"],
        guide_envelopes=envelopes,
        guide_profiles=profiles if profiles and any(p is not None for p in profiles) else None,
    )
    return {i: out["weighted-refit", t] for i, t in enumerate(stops)}, details


def predict(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    cfg,
    threshold,
    *,
    edge_side=False,
    hessians=None,
    nominations=(),
):
    anchor = active_anchor(guide)
    baseline, _ = deliver(
        parent,
        packed,
        colors,
        guide,
        noise,
        query,
        cfg,
        threshold,
        edge_side=edge_side,
        hessians=hessians,
    )
    if anchor is None:
        return {(arm, t): value for arm in ARMS for t, value in baseline.items()}, {
            "status": "no guide"
        }
    partner = 1 - anchor
    companion = guide["frequencies_xy"][partner]
    local_moves = (
        frequency_neighborhood(companion, min(query[2:]))
        if guide["active"][partner] or len(guide.get("screened_frequencies_xy", ())) == 2
        else []
    )
    candidates = [*nominations, *local_moves]
    active = [i == anchor for i in range(2)]
    taper, support = None, None
    if any(guide["active"][i] for i in range(2) if i != anchor) or candidates:
        masks, support = select_wire_footprint(
            packed,
            colors,
            query,
            guide["frequencies_xy"],
            active,
            shot=noise["shot"],
            read=noise["read"],
            config=cfg,
        )
        taper = masks["confirmed"]
    if candidates:
        guided, details = reserve_companion_frequencies(
            packed,
            colors,
            query,
            guide,
            candidates,
            shot=noise["shot"],
            read=noise["read"],
            config=cfg,
            envelope=taper,
            hessians=hessians,
        )
    else:
        guided, details = {"uniform": guide}, {"status": "no companion nominations"}
    guided["localized"] = guided.get("localized", guided["uniform"])
    results = {("flexible", t): value for t, value in baseline.items()}
    records = {}
    cache = {}
    for arm, g in zip(ARMS[1:], (guide, guided["uniform"], guided["localized"]), strict=True):
        key = (*g["active"], *np.asarray(g["frequencies_xy"]).ravel())
        if key not in cache:
            cache[key] = deliver(
                parent,
                packed,
                colors,
                g,
                noise,
                query,
                cfg,
                threshold,
                edge_side=edge_side,
                hessians=hessians,
                taper=taper,
                narrow=True,
            )
        values, trace = cache[key]
        results.update({(arm, t): value for t, value in values.items()})
        records[arm] = {
            "frequencies_xy": g["frequencies_xy"],
            "active": g["active"],
            "shape": trace,
        }
    return results, {
        "footprint": support,
        "footprint_used": taper is not None,
        "selection": details,
        "delivered_guides": records,
    }


def ordinary(plan, cfg, panel):
    previous = read_json(checked(plan["prior_profile_panels"][panel]))["rows"]
    case_key = "original_guides" if panel == "synthetic" else "disjoint_guides"
    guides = {row["id"]: row for row in read_json(checked(plan["source"][case_key]))["synthetic"]}
    bank = {
        row["id"]: row
        for profile in PROFILE_NAMES
        for row in read_json(checked(plan["bank_replays"][f"{panel}-{profile}"]))["rows"]
    }
    result = []
    folder = Path(plan["root"]) / f"arrays-{panel}"
    folder.mkdir()
    for before in previous:
        name = before["id"]
        g = guides[name]
        case = read_json(checked(before["case"]))
        profile = case["profile"]
        prior_bank = bank[name]
        assert prior_bank["case"] == before["case"]
        shot_read = plan["profiles"][profile]
        threshold = plan["settings"][profile]["threshold"]
        samples, cfa = sensor_box(case["sensor"], plan["query_xywh"])
        query = g["query"] if panel == "synthetic" else offset_box(plan["query_xywh"])
        rows, traces = [], []
        with np.load(checked(before["prediction"])) as archived:
            parents = archived["parent"]
            for role, (rgb, raw, colors) in enumerate(zip(parents, samples, cfa, strict=True)):
                opts = (
                    g["roles"][role]["fits"]
                    if panel == "synthetic"
                    else g["rankings"][role]["fits"]
                )
                options = ("scene", "exact-center") if panel == "synthetic" else ("scene",)
                correction, receipts = {}, {}
                for label in options:
                    nominations = (
                        []
                        if label != "scene"
                        else [
                            e["frequency_xy"]
                            for e in prior_bank["bank_records"][role]["bank"]["shortlist"]
                            if e["donor_valid"]
                        ]
                    )
                    images, receipts[label] = predict(
                        rgb,
                        raw,
                        colors,
                        opts[label],
                        shot_read,
                        query,
                        cfg,
                        threshold,
                        nominations=nominations,
                    )
                    for (arm, offset), image in images.items():
                        key = field(label, arm, offset)
                        correction[key] = image
                        if arm == "flexible":
                            np.testing.assert_array_equal(image, archived[key][role])
                rows.append(correction)
                traces.append(receipts)
        result.append(
            before
            | {
                "previous": before["prediction"],
                "bank": prior_bank["prediction"],
                "traces": traces,
                "prediction": write_array(
                    folder / f"{name}.npz",
                    parent=parents,
                    **{k: np.stack([r[k] for r in rows]) for k in rows[0]},
                ),
            }
        )
        print(panel, name, flush=True)
    return result


def constructed(plan, cfg, profile):
    recipe = structure_module(plan["structure"])
    name = "projective400" if profile == "iso400" else "projective6400"
    old = read_json(checked(plan["previous_panels"][name]))["rows"]
    settings, noise = plan["settings"][profile], plan["profiles"][profile]
    stage = Path(plan["root"])
    result = []
    for row in old:
        i = row["case"]
        p, strong, both, exact, curvature, quiet, metadata = target(i, plan["geometry_seed"])
        altered = exact.copy()
        weak = altered[1]
        weak += (
            plan["shift_bins"]
            * (-1 if i % 2 else 1)
            * weak
            / (np.linalg.norm(weak) * min(quiet.shape))
        )
        guide = {"active": [True, True], "frequencies_xy": altered.tolist()}
        cfa = np.asarray(PATTERNS[row["CFA"]])
        states, traces = [], []
        for role, truth in enumerate((strong, both)):
            seed = np.random.SeedSequence(
                [plan["geometry_seed"], 1, i, int(profile == "iso6400"), role]
            )
            packed = recipe.corrupt(truth, cfa, np.random.default_rng(seed), noise)
            images, trace = predict(
                p,
                packed,
                cfa,
                guide,
                noise,
                recipe.QUERY,
                cfg,
                settings["threshold"],
                hessians=curvature,
            )
            states.append(
                {(arm, settings["threshold"] + t): value for (arm, t), value in images.items()}
            )
            traces.append(trace)
        with np.load(checked(row["prediction"])) as prior:
            np.testing.assert_array_equal(prior["packed"], packed)
            np.testing.assert_array_equal(prior["target"], both)
        result.append(
            metadata
            | {
                "id": f"{profile}-case{i}",
                "case": i,
                "CFA": row["CFA"],
                "profile": profile,
                "known_frequency": exact.tolist(),
                "input_guide": guide,
                "trace": traces,
                "old_prediction": row["prediction"],
                "prediction": write_array(
                    stage / f"{profile}-{i}.npz",
                    **{
                        arm: value
                        for (arm, t), value in states[1].items()
                        if t == settings["threshold"]
                    },
                ),
                "metrics": score(
                    p, strong, both, states, quiet, settings["scale"], settings["threshold"]
                ),
            }
        )
        print(profile, i, metadata["kind"], flush=True)
    return result


def run(path, panel):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    cfg = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    profile = "iso6400" if panel.endswith("6400") else "iso400"
    start = time.monotonic()
    if panel.startswith("projective"):
        rows = constructed(plan, cfg, profile)
    elif panel.startswith("null"):
        rows = controls(plan, cfg, structure_module(plan["structure"]), profile, predictor=predict)
    elif panel == "camera":
        out = path.parent / "arrays-camera"
        out.mkdir()
        old = read_json(checked(plan["prior_profile_panels"]["camera"]))["rows"]
        rows = camera(plan, old, out, cfg, predictor=predict)
        for row, prior in zip(rows, old, strict=True):
            with (
                np.load(checked(row["predictions"])) as f,
                np.load(checked(prior["predictions"])) as g,
            ):
                for name in ("scene-flexible", "spectral-flexible", "parent"):
                    np.testing.assert_array_equal(f[name], g[name])
    else:
        rows = ordinary(plan, cfg, panel)
    write_json(
        path.parent / f"{panel}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_subparsers(dest="mode", required=True)
    setup = modes.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("source", type=Path)
    setup.add_argument("bank", type=Path)
    execute = modes.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("panel", choices=PANELS)
    args = cli.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.source.resolve(), args.bank.resolve())
    else:
        run(args.plan.resolve(), args.panel)
