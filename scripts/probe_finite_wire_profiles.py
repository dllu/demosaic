"""Compare compact narrow-wire templates against the flexible periodic fit."""

import argparse
import time
from dataclasses import replace
from functools import partial
from pathlib import Path

import numpy as np
from probe_flexible_query_edges import camera, synth
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_shared_projective_phase import target
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
from demosaic.finite_wire_profiles import (
    MINIMUM_PROFILE_GAIN,
    PHASES,
    WIDTHS,
    reserve_wire_profiles,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.reserved_wire_footprint import select_wire_footprint
from demosaic.search_donor_geometry import screening_mask
from demosaic.shared_projective_phase import projective_hessians

PANELS = (
    "projective400",
    "projective6400",
    "synthetic",
    "disjoint",
    "null400",
    "null6400",
    "camera",
)
REPEAT_PANELS = ("repeat-null400", "repeat-null6400")
REPEAT_SEED_SUFFIX = 202611172332
ARMS = ("flexible", "narrow", "narrow-companion")
FOCUSED_ARMS = ("flexible", "footprint", "footprint-narrow")


def prepare(root, source, minimum_gain, focus_companion, within_footprint_gain):
    before = reference(source / "plan.json")
    plan = read_json(checked(before))
    snapshots = {panel: reference(source / f"{panel}.json") for panel in PANELS}
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(),
        root,
        [
            Path(__file__).name,
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
            "inputs": [
                *plan["inputs"],
                before,
                *snapshots.values(),
            ],
            "previous_replay": before,
            "previous_panels": snapshots,
            "template_phases_cycles": PHASES,
            "template_widths_cycles": WIDTHS,
            "minimum_profile_gain": minimum_gain,
            "repeat_seed_suffix": REPEAT_SEED_SUFFIX,
            "focus_companion": focus_companion,
            "within_footprint_gain": within_footprint_gain,
            "profile_arms": FOCUSED_ARMS if focus_companion else ARMS,
            "scope": "Use the same whole-image guides, reserve and complementary delivery CFA sites. "
            "Compare flexible eight-knot profiles with compact periodized line shapes selected by the "
            "held-out RAW reserve. Constructed perspective cases also repeat the previously estimated "
            "companion geometry. Separate signed amplitudes, refit, gates and display scale stay fixed.",
        },
    )


def predict(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    config,
    threshold,
    *,
    edge_side=False,
    hessians=None,
    minimum_gain=MINIMUM_PROFILE_GAIN,
    focus_companion=False,
    within_footprint_gain=None,
):
    stops = (threshold, threshold + 1)
    active = guide["active"]
    envelopes, location = None, None
    if focus_companion and all(active):
        footprints, location = select_wire_footprint(
            packed,
            colors,
            query,
            guide["frequencies_xy"],
            active,
            shot=noise["shot"],
            read=noise["read"],
            config=config,
            record_partner=True,
        )
        footprint = footprints["confirmed"]
        if footprint is not None and location["winner"]["direction"] == 0:
            envelopes = np.stack((np.ones_like(footprint), footprint))
    margin = minimum_gain
    if envelopes is not None and within_footprint_gain is not None:
        margin = within_footprint_gain
    profiles, witness = reserve_wire_profiles(
        packed,
        colors,
        query,
        guide,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        hessians=hessians,
        envelopes=envelopes,
        minimum_gain=margin,
    )
    witness |= {
        "footprint": location,
        "footprint_transferred": envelopes is not None,
        "minimum_gain": margin,
    }
    images, cache = {}, {}
    choices = {"flexible": (None, (None, None))}
    companion = (None, profiles[1] if all(active) else None)
    if focus_companion:
        choices |= {
            "footprint": (envelopes, (None, None)),
            "footprint-narrow": (envelopes, companion),
        }
    else:
        choices |= {"narrow": (None, profiles), "narrow-companion": (None, companion)}
    for arm, (support, chosen) in choices.items():
        key = support is not None, *(p is not None for p in chosen)
        if key not in cache:
            if not any(active):
                cache[key] = {t: parent for t in stops}
            else:
                out, _ = restore_local_waves(
                    parent,
                    packed,
                    colors,
                    shot=noise["shot"],
                    read=noise["read"],
                    config=config,
                    thresholds=stops,
                    evidence_mask=~screening_mask(query),
                    guide_frequencies_xy=guide["frequencies_xy"],
                    guide_phase_hessians_xy=hessians,
                    phase_bins=8,
                    shrink_phase_fit=True,
                    compare_pooled_support=True,
                    compare_pooled_refit=True,
                    phase_edge_side="validation" if edge_side else None,
                    active_guide_directions=active,
                    guide_envelopes=support,
                    guide_profiles=chosen if any(key[1:]) else None,
                )
                cache[key] = {t: out["weighted-refit", t] for t in stops}
        images.update({(arm, i): cache[key][t] for i, t in enumerate(stops)})
    return images, witness


def fresh(plan, config, recipe, profile, *, predictor):
    name = "projective400" if profile == "iso400" else "projective6400"
    old = read_json(checked(plan["previous_panels"][name]))["rows"]
    settings, noise = plan["settings"][profile], plan["profiles"][profile]
    threshold = settings["threshold"]
    root = Path(plan["root"])
    rows = []
    for before in old:
        i = before["case"]
        parent, strong, both, f, _, quiet, metadata = target(i, plan["geometry_seed"])
        guide = before["guide"]
        cfa = np.asarray(PATTERNS[before["CFA"]])
        outputs, receipts = [], []
        for role, truth in enumerate((strong, both)):
            seed = np.random.SeedSequence(
                [plan["geometry_seed"], 1, i, int(profile == "iso6400"), role]
            )
            packed = recipe.corrupt(truth, cfa, np.random.default_rng(seed), noise)
            geometry = before["selection"][role]["directions"][0]
            h = None
            if geometry["accepted"]:
                gradient = np.asarray(geometry["proposed"]) / min(quiet.shape)
                h = projective_hessians(f, gradient)
                h[0] = 0
            values, trace = {}, {}
            for label, hessians in (("planar", None), ("transfer", h)):
                if label == "transfer" and hessians is None:
                    values[label], trace[label] = values["planar"], trace["planar"]
                    continue
                values[label], trace[label] = predictor(
                    parent,
                    packed,
                    cfa,
                    guide,
                    noise,
                    recipe.QUERY,
                    config,
                    threshold,
                    hessians=hessians,
                )
            outputs.append(
                {
                    (f"{label}-{arm}", threshold + t): v
                    for label, images in values.items()
                    for (arm, t), v in images.items()
                }
            )
            receipts.append(trace)
        prior_arrays = checked(before["prediction"])
        with np.load(prior_arrays) as prev:
            np.testing.assert_array_equal(packed, prev["packed"])
            np.testing.assert_array_equal(
                outputs[1]["planar-flexible", threshold], prev["screened"]
            )
            np.testing.assert_array_equal(
                outputs[1]["transfer-flexible", threshold], prev["transfer"]
            )
        images = {arm: image for (arm, t), image in outputs[1].items() if t == threshold}
        rows.append(
            metadata
            | {
                "id": f"{profile}-case{i}",
                "case": i,
                "profile": profile,
                "CFA": before["CFA"],
                "old_prediction": before["prediction"],
                "prediction": write_array(root / f"{profile}-{i}.npz", **images),
                "metrics": score(
                    parent, strong, both, outputs, quiet, settings["scale"], threshold
                ),
                "selection": receipts,
            }
        )
        print(profile, i, metadata["kind"], flush=True)
    return rows


def controls(plan, cfg, recipe, profile, *, predictor, repeat=False):
    origin = read_json(checked(plan["screened_receipts"]["replication"]))["rows"]
    name = "null400" if profile == "iso400" else "null6400"
    old = read_json(checked(plan["previous_panels"][name]))["rows"]
    noise = plan["profiles"][profile]
    threshold = plan["settings"][profile]["threshold"]
    rows = []
    for case, prior in zip((r for r in origin if r["profile"] == profile), old, strict=True):
        style, trial = case["style"], case["trial"]
        assert style == prior["style"] and trial == prior["trial"]
        ctor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        parent = ctor(style, case["angle_radians"], *case["width_shift_level_height"])
        cfa = np.asarray(PATTERNS[case["CFA"]])
        seed = [*case["noise_seed"], REPEAT_SEED_SUFFIX] if repeat else case["noise_seed"]
        rng = np.random.default_rng(np.random.SeedSequence(seed))
        packed = recipe.corrupt(parent, cfa, rng, noise)
        guide = {"active": [True, True], "frequencies_xy": case["guide_frequencies_xy"]}
        images, witnesses = predictor(
            parent, packed, cfa, guide, noise, recipe.QUERY, cfg, threshold
        )
        metrics = {}
        for (arm, t), image in images.items():
            delta = (image[recipe.MEASURE].astype(float) - parent[recipe.MEASURE]) * 65535
            m = {
                "RMS_DN16": float(np.sqrt(np.mean(delta**2))),
                "max_abs_DN16": float(np.max(np.abs(delta))),
                "changed_pixels": int(np.any(delta != 0, axis=0).sum()),
            }
            if arm == "flexible" and not repeat:
                assert m == prior["metrics"][field("null", "screened", t)]
            metrics[field("null", arm, t)] = m
        rows.append(
            {
                "style": style,
                "trial": trial,
                "profile": profile,
                "noise_seed": seed,
                "metrics": metrics,
                "witness": witnesses,
            }
        )
        print(profile, style, trial, flush=True)
    return rows


def run(path, panel):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    cfg = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    profile = "iso6400" if panel.endswith("6400") else "iso400"
    start = time.monotonic()
    predictor = partial(
        predict,
        minimum_gain=plan["minimum_profile_gain"],
        focus_companion=plan["focus_companion"],
        within_footprint_gain=plan["within_footprint_gain"],
    )
    if panel.startswith(("null", "projective", "repeat-null")):
        recipe = structure_module(plan["structure"])
        if panel.startswith("projective"):
            rows = fresh(plan, cfg, recipe, profile, predictor=predictor)
        else:
            rows = controls(
                plan, cfg, recipe, profile, predictor=predictor, repeat=panel in REPEAT_PANELS
            )
    else:
        out = path.parent / f"arrays-{panel}"
        out.mkdir()
        original = read_json(checked(plan["previous_panels"][panel]))["rows"]
        rows = (
            camera(plan, original, out, cfg, predictor=predictor)
            if panel == "camera"
            else synth(plan, original, cfg, panel, out, predictor=predictor)
        )
        key = "predictions" if panel == "camera" else "prediction"
        for row, before in zip(rows, original, strict=True):
            assert row["id"] == before["id"]
            with np.load(checked(row[key])) as new, np.load(checked(before[key])) as old:
                for name in old.files:
                    np.testing.assert_array_equal(new[name], old[name])
                for name in (x for x in new.files if "-flexible" in x):
                    np.testing.assert_array_equal(
                        new[name], old[name.replace("-flexible", "-screened")]
                    )
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
    cmd = cli.add_subparsers(dest="mode", required=True)
    develop = cmd.add_parser("prepare")
    develop.add_argument("root", type=Path)
    develop.add_argument("source", type=Path)
    develop.add_argument("--minimum-gain", type=float, default=MINIMUM_PROFILE_GAIN)
    develop.add_argument("--focus-companion", action="store_true")
    develop.add_argument("--within-footprint-gain", type=float)
    execute = cmd.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("panel", choices=(*PANELS, *REPEAT_PANELS))
    args = cli.parse_args()
    if args.mode == "prepare":
        if args.within_footprint_gain is not None and not args.focus_companion:
            cli.error("--within-footprint-gain requires --focus-companion")
        prepare(
            args.root.resolve(),
            args.source.resolve(),
            args.minimum_gain,
            args.focus_companion,
            args.within_footprint_gain,
        )
    else:
        run(args.plan.resolve(), args.panel)
